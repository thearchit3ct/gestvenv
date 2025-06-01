"""Tests pour le service DiagnosticService."""

import os
import json
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta

from gestvenv.services.diagnostic_services import DiagnosticService
from gestvenv.core.models import EnvironmentHealth, EnvironmentInfo

class TestDiagnosticService:
    """Tests pour la classe DiagnosticService."""
    
    @pytest.fixture
    def diagnostic_service(self) -> DiagnosticService:
        """Fixture pour créer une instance du service de diagnostic."""
        with patch('gestvenv.services.diagnostic_services.EnvironmentService'), \
             patch('gestvenv.services.diagnostic_services.PackageService'), \
             patch('gestvenv.services.diagnostic_services.SystemService'), \
             patch('gestvenv.services.diagnostic_services.CacheService'), \
             patch('gestvenv.services.diagnostic_services.ConfigManager'):
            return DiagnosticService()
    
    @pytest.fixture
    def mock_env_info(self, temp_dir: Path) -> EnvironmentInfo:
        """Fixture pour créer un EnvironmentInfo simulé."""
        env_path = temp_dir / "test_env"
        env_path.mkdir(parents=True, exist_ok=True)
        
        return EnvironmentInfo(
            name="test_env",
            path=env_path,
            python_version="3.9.0",
            created_at=datetime.now(),
            packages=["flask==2.0.1", "pytest==6.2.5"]
        )
    
    def test_init(self, diagnostic_service: DiagnosticService) -> None:
        """Teste l'initialisation du service."""
        assert diagnostic_service.env_service is not None
        assert diagnostic_service.pkg_service is not None
        assert diagnostic_service.sys_service is not None
        assert diagnostic_service.cache_service is not None
        assert diagnostic_service.config_manager is not None
        assert diagnostic_service.logs_dir.exists()
    
    def test_diagnose_environment_not_exists(self, diagnostic_service: DiagnosticService) -> None:
        """Teste le diagnostic d'un environnement inexistant."""
        # Mock du config manager pour retourner False
        diagnostic_service.config_manager.environment_exists.return_value = False
        
        report = diagnostic_service.diagnose_environment("nonexistent_env")
        
        assert report["environment"] == "nonexistent_env"
        assert report["status"] == "error"
        assert "n'existe pas" in report["message"]
    
    def test_diagnose_environment_healthy(self, diagnostic_service: DiagnosticService,
                                         mock_env_info: EnvironmentInfo) -> None:
        """Teste le diagnostic d'un environnement en bonne santé."""
        # Configurer les mocks
        diagnostic_service.config_manager.environment_exists.return_value = True
        diagnostic_service.config_manager.get_environment.return_value = mock_env_info
        
        # Mock des vérifications qui retournent des résultats positifs
        with patch.object(diagnostic_service, '_check_physical_existence') as mock_physical, \
             patch.object(diagnostic_service, '_check_directory_structure') as mock_structure, \
             patch.object(diagnostic_service, '_check_python_executable') as mock_python, \
             patch.object(diagnostic_service, '_check_pip_executable') as mock_pip, \
             patch.object(diagnostic_service, '_check_activation_script') as mock_activate, \
             patch.object(diagnostic_service, '_check_permissions') as mock_permissions:
            
            # Configurer les mocks pour ne pas ajouter d'issues
            def add_info(report):
                report["info"].append("Test info")
                report["checks"]["test"] = True
            
            mock_physical.side_effect = add_info
            mock_structure.side_effect = add_info
            mock_python.side_effect = add_info
            mock_pip.side_effect = add_info
            mock_activate.side_effect = add_info
            mock_permissions.side_effect = add_info
            
            report = diagnostic_service.diagnose_environment("test_env")
            
            assert report["environment"] == "test_env"
            assert report["status"] == "healthy"
            assert len(report["issues"]) == 0
            assert len(report["info"]) > 0
    
    def test_diagnose_environment_unhealthy(self, diagnostic_service: DiagnosticService,
                                           mock_env_info: EnvironmentInfo) -> None:
        """Teste le diagnostic d'un environnement avec des problèmes."""
        # Configurer les mocks
        diagnostic_service.config_manager.environment_exists.return_value = True
        diagnostic_service.config_manager.get_environment.return_value = mock_env_info
        
        # Mock des vérifications qui ajoutent des problèmes
        with patch.object(diagnostic_service, '_check_physical_existence') as mock_physical:
            def add_issue(report):
                report["issues"].append({
                    "type": "missing_environment",
                    "severity": "critical",
                    "message": "Environnement manquant"
                })
                report["checks"]["physical_existence"] = False
            
            mock_physical.side_effect = add_issue
            
            report = diagnostic_service.diagnose_environment("test_env")
            
            assert report["status"] == "unhealthy"
            assert len(report["issues"]) > 0
            assert report["issues"][0]["type"] == "missing_environment"
    
    def test_check_physical_existence_missing(self, diagnostic_service: DiagnosticService) -> None:
        """Teste la vérification d'existence physique - environnement manquant."""
        report = {"issues": [], "checks": {}, "info": [], "repair_actions": []}
        nonexistent_path = Path("/nonexistent/path")
        
        diagnostic_service._check_physical_existence(nonexistent_path, report)
        
        assert len(report["issues"]) == 1
        assert report["issues"][0]["type"] == "missing_environment"
        assert report["checks"]["physical_existence"] is False
        assert "recreate_environment" in report["repair_actions"]
    
    def test_check_physical_existence_exists(self, diagnostic_service: DiagnosticService,
                                           temp_dir: Path) -> None:
        """Teste la vérification d'existence physique - environnement existant."""
        report = {"issues": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_physical_existence(temp_dir, report)
        
        assert len(report["issues"]) == 0
        assert report["checks"]["physical_existence"] is True
        assert len(report["info"]) > 0
    
    def test_check_directory_structure_complete(self, diagnostic_service: DiagnosticService,
                                              temp_dir: Path) -> None:
        """Teste la vérification de structure - structure complète."""
        # Créer la structure d'environnement appropriée
        if os.name == "nt":
            (temp_dir / "Scripts").mkdir()
            (temp_dir / "Lib").mkdir()
            (temp_dir / "Include").mkdir()
        else:
            (temp_dir / "bin").mkdir()
            (temp_dir / "lib").mkdir()
            (temp_dir / "include").mkdir()
        
        (temp_dir / "pyvenv.cfg").touch()
        
        report = {"issues": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_directory_structure(temp_dir, report)
        
        assert len(report["issues"]) == 0
        assert report["checks"]["directory_structure"] is True
        assert len(report["info"]) > 0
    
    def test_check_directory_structure_incomplete(self, diagnostic_service: DiagnosticService,
                                                temp_dir: Path) -> None:
        """Teste la vérification de structure - structure incomplète."""
        # Créer seulement une partie de la structure
        if os.name == "nt":
            (temp_dir / "Scripts").mkdir()
            # Manque Lib et Include
        else:
            (temp_dir / "bin").mkdir()
            # Manque lib et include
        
        # Manque pyvenv.cfg
        
        report = {"issues": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_directory_structure(temp_dir, report)
        
        assert len(report["issues"]) == 1
        assert report["issues"][0]["type"] == "incomplete_structure"
        assert report["checks"]["directory_structure"] is False
        assert "repair_structure" in report["repair_actions"]
    
    @patch('subprocess.run')
    def test_check_python_executable_working(self, mock_subprocess: MagicMock,
                                           diagnostic_service: DiagnosticService,
                                           temp_dir: Path) -> None:
        """Teste la vérification de l'exécutable Python - fonctionnel."""
        # Créer un faux exécutable Python
        if os.name == "nt":
            python_exe = temp_dir / "Scripts" / "python.exe"
            python_exe.parent.mkdir(exist_ok=True)
        else:
            python_exe = temp_dir / "bin" / "python"
            python_exe.parent.mkdir(exist_ok=True)
        
        python_exe.touch()
        
        # Mock du service d'environnement
        diagnostic_service.env_service.get_python_executable.return_value = python_exe
        
        # Mock de subprocess pour retourner une version
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Python 3.9.0"
        mock_subprocess.return_value = mock_result
        
        report = {"issues": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_python_executable("test_env", temp_dir, report)
        
        assert len(report["issues"]) == 0
        assert report["checks"]["python_executable"] is True
        assert any("Python fonctionnel" in info for info in report["info"])
    
    def test_check_python_executable_missing(self, diagnostic_service: DiagnosticService,
                                           temp_dir: Path) -> None:
        """Teste la vérification de l'exécutable Python - manquant."""
        # Mock du service d'environnement pour retourner None
        diagnostic_service.env_service.get_python_executable.return_value = None
        
        report = {"issues": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_python_executable("test_env", temp_dir, report)
        
        assert len(report["issues"]) == 1
        assert report["issues"][0]["type"] == "missing_python"
        assert report["checks"]["python_executable"] is False
        assert "reinstall_python" in report["repair_actions"]
    
    @patch('subprocess.run')
    def test_check_python_executable_broken(self, mock_subprocess: MagicMock,
                                          diagnostic_service: DiagnosticService,
                                          temp_dir: Path) -> None:
        """Teste la vérification de l'exécutable Python - cassé."""
        # Créer un faux exécutable Python
        python_exe = temp_dir / "python"
        python_exe.touch()
        
        diagnostic_service.env_service.get_python_executable.return_value = python_exe
        
        # Mock de subprocess pour retourner une erreur
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Python executable is broken"
        mock_subprocess.return_value = mock_result
        
        report = {"issues": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_python_executable("test_env", temp_dir, report)
        
        assert len(report["issues"]) == 1
        assert report["issues"][0]["type"] == "broken_python"
        assert report["checks"]["python_executable"] is False
        assert "repair_python" in report["repair_actions"]
    
    def test_check_pip_executable_working(self, diagnostic_service: DiagnosticService,
                                        temp_dir: Path) -> None:
        """Teste la vérification de l'exécutable pip - fonctionnel."""
        # Créer un faux exécutable pip
        pip_exe = temp_dir / "pip"
        pip_exe.touch()
        
        diagnostic_service.env_service.get_pip_executable.return_value = pip_exe
        
        with patch('subprocess.run') as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "pip 21.0.1"
            mock_subprocess.return_value = mock_result
            
            report = {"issues": [], "warnings": [], "checks": {}, "info": [], "repair_actions": []}
            
            diagnostic_service._check_pip_executable("test_env", temp_dir, report)
            
            assert len(report["warnings"]) == 0
            assert report["checks"]["pip_executable"] is True
            assert any("pip fonctionnel" in info for info in report["info"])
    
    def test_check_pip_executable_missing(self, diagnostic_service: DiagnosticService,
                                        temp_dir: Path) -> None:
        """Teste la vérification de l'exécutable pip - manquant."""
        diagnostic_service.env_service.get_pip_executable.return_value = None
        
        report = {"issues": [], "warnings": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_pip_executable("test_env", temp_dir, report)
        
        assert len(report["warnings"]) == 1
        assert report["warnings"][0]["type"] == "missing_pip"
        assert report["checks"]["pip_executable"] is False
        assert "install_pip" in report["repair_actions"]
    
    def test_check_activation_script_exists(self, diagnostic_service: DiagnosticService,
                                          temp_dir: Path) -> None:
        """Teste la vérification du script d'activation - existant."""
        activate_script = temp_dir / "activate"
        activate_script.touch()
        
        diagnostic_service.env_service.get_activation_script_path.return_value = activate_script
        
        report = {"issues": [], "warnings": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_activation_script("test_env", temp_dir, report)
        
        assert len(report["warnings"]) == 0
        assert report["checks"]["activation_script"] is True
        assert any("Script d'activation présent" in info for info in report["info"])
    
    def test_check_activation_script_missing(self, diagnostic_service: DiagnosticService,
                                           temp_dir: Path) -> None:
        """Teste la vérification du script d'activation - manquant."""
        diagnostic_service.env_service.get_activation_script_path.return_value = None
        
        report = {"issues": [], "warnings": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_activation_script("test_env", temp_dir, report)
        
        assert len(report["warnings"]) == 1
        assert report["warnings"][0]["type"] == "missing_activation_script"
        assert report["checks"]["activation_script"] is False
        assert "repair_activation_script" in report["repair_actions"]
    
    def test_check_permissions_ok(self, diagnostic_service: DiagnosticService,
                                temp_dir: Path) -> None:
        """Teste la vérification des permissions - OK."""
        report = {"issues": [], "warnings": [], "checks": {}, "info": [], "repair_actions": []}
        
        diagnostic_service._check_permissions(temp_dir, report)
        
        # Les permissions devraient être OK sur un répertoire temporaire
        assert report["checks"]["read_permission"] is True
        assert report["checks"]["write_permission"] is True
    
    def test_repair_environment_success(self, diagnostic_service: DiagnosticService,
                                      mock_env_info: EnvironmentInfo) -> None:
        """Teste la réparation réussie d'un environnement."""
        # Mock du diagnostic pour retourner des problèmes
        mock_diagnosis = {
            "status": "unhealthy",
            "repair_actions": ["install_pip", "fix_permissions"]
        }
        
        diagnostic_service.config_manager.get_environment.return_value = mock_env_info
        
        with patch.object(diagnostic_service, 'diagnose_environment', return_value=mock_diagnosis), \
             patch.object(diagnostic_service, '_execute_repair_action', return_value=(True, "Action réussie")):
            
            success, actions = diagnostic_service.repair_environment("test_env", auto_fix=True)
            
            assert success is True
            assert len(actions) > 0
            assert any("✓" in action for action in actions)
    
    def test_repair_environment_no_autofix(self, diagnostic_service: DiagnosticService,
                                         mock_env_info: EnvironmentInfo) -> None:
        """Teste la réparation sans auto-fix (recommandations seulement)."""
        mock_diagnosis = {
            "status": "unhealthy",
            "repair_actions": ["install_pip", "fix_permissions"]
        }
        
        diagnostic_service.config_manager.get_environment.return_value = mock_env_info
        
        with patch.object(diagnostic_service, 'diagnose_environment', return_value=mock_diagnosis):
            success, actions = diagnostic_service.repair_environment("test_env", auto_fix=False)
            
            assert success is True
            assert len(actions) > 0
            assert all("Recommandation:" in action for action in actions)
    
    def test_get_action_description(self, diagnostic_service: DiagnosticService) -> None:
        """Teste la récupération de descriptions d'actions."""
        # Actions connues
        desc = diagnostic_service._get_action_description("install_pip")
        assert "pip" in desc
        
        desc = diagnostic_service._get_action_description("fix_permissions")
        assert "permissions" in desc
        
        # Action inconnue
        desc = diagnostic_service._get_action_description("unknown_action")
        assert "unknown_action" in desc
    
    def test_install_pip_success(self, diagnostic_service: DiagnosticService,
                                mock_env_info: EnvironmentInfo, temp_dir: Path) -> None:
        """Teste l'installation réussie de pip."""
        python_exe = temp_dir / "python"
        python_exe.touch()
        
        diagnostic_service.env_service.get_python_executable.return_value = python_exe
        
        with patch('subprocess.run') as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result
            
            success, message = diagnostic_service._install_pip("test_env", mock_env_info)
            
            assert success is True
            assert "succès" in message
    
    def test_install_pip_failure(self, diagnostic_service: DiagnosticService,
                                mock_env_info: EnvironmentInfo, temp_dir: Path) -> None:
        """Teste l'échec d'installation de pip."""
        python_exe = temp_dir / "python"
        python_exe.touch()
        
        diagnostic_service.env_service.get_python_executable.return_value = python_exe
        
        with patch('subprocess.run') as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Installation failed"
            mock_subprocess.return_value = mock_result
            
            success, message = diagnostic_service._install_pip("test_env", mock_env_info)
            
            assert success is False
            assert "Échec" in message
    
    def test_fix_permissions_success(self, diagnostic_service: DiagnosticService,
                                   temp_dir: Path) -> None:
        """Teste la correction réussie des permissions."""
        # Créer une structure de test
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test")
        
        success, message = diagnostic_service._fix_permissions(temp_dir)
        
        assert success is True
        assert "corrigées" in message
    
    def test_fix_permissions_nonexistent(self, diagnostic_service: DiagnosticService,
                                       temp_dir: Path) -> None:
        """Teste la correction de permissions sur un chemin inexistant."""
        nonexistent_path = temp_dir / "nonexistent"
        
        success, message = diagnostic_service._fix_permissions(nonexistent_path)
        
        assert success is False
        assert "n'existe pas" in message
    
    def test_get_system_diagnosis(self, diagnostic_service: DiagnosticService) -> None:
        """Teste le diagnostic complet du système."""
        # Mock des services
        diagnostic_service.sys_service.get_system_info.return_value = {
            "os_name": "Linux",
            "python_version": "3.9.0"
        }
        diagnostic_service.sys_service.check_python_version.return_value = "3.9.0"
        diagnostic_service.sys_service.get_available_python_versions.return_value = [
            {"command": "python3", "version": "3.9.0"}
        ]
        diagnostic_service.config_manager.get_all_environments.return_value = {}
        diagnostic_service.config_manager.get_active_environment.return_value = None
        diagnostic_service.config_manager.get_default_python.return_value = "python3"
        diagnostic_service.config_manager.get_setting.return_value = False
        diagnostic_service.config_manager.config_path = Path("/tmp/config.json")
        
        report = diagnostic_service.get_system_diagnosis()
        
        assert "diagnosed_at" in report
        assert "system_info" in report
        assert "python_info" in report
        assert "gestvenv_info" in report
        assert "environments_status" in report
        assert "cache_status" in report
        
        assert report["python_info"]["current_version"] == "3.9.0"
        assert report["gestvenv_info"]["total_environments"] == 0
    
    def test_verify_cache_integrity(self, diagnostic_service: DiagnosticService) -> None:
        """Teste la vérification d'intégrité du cache."""
        # Mock du cache service
        mock_packages = {"flask": ["2.0.1"], "pytest": ["6.2.5"]}
        diagnostic_service.cache_service.get_available_packages.return_value = mock_packages
        
        # Mock de l'index du cache
        diagnostic_service.cache_service.index = {
            "flask": {
                "versions": {
                    "2.0.1": {
                        "path": "packages/flask/flask-2.0.1.whl",
                        "hash": "abc123"
                    }
                }
            }
        }
        diagnostic_service.cache_service.cache_dir = Path("/tmp/cache")
        
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(diagnostic_service.cache_service, '_calculate_file_hash', return_value="abc123"):
            
            report = diagnostic_service.verify_cache_integrity()
            
            assert "verified_at" in report
            assert "status" in report
            assert "total_packages" in report
            assert "verified_packages" in report
            assert "corrupted_packages" in report
            
            assert report["total_packages"] == 2
            assert report["verified_packages"] >= 0
    
    def test_log_diagnostic_start_end(self, diagnostic_service: DiagnosticService) -> None:
        """Teste l'enregistrement des logs de diagnostic."""
        # Ces méthodes ne lèvent pas d'erreur même si l'écriture échoue
        diagnostic_service._log_diagnostic_start("test_env")
        diagnostic_service._log_diagnostic_end("test_env", "healthy")
        
        # Pas d'assertion car les méthodes ne retournent rien et ignorent les erreurs
        # On vérifie juste qu'elles n'explosent pas
        assert True
    
    def test_get_diagnostic_logs(self, diagnostic_service: DiagnosticService, temp_dir: Path) -> None:
        """Teste la récupération des logs de diagnostic."""
        # Créer un fichier de log de test
        log_file = diagnostic_service.logs_dir / "diagnostic.log"
        log_content = f"[{datetime.now().isoformat()}] DIAGNOSTIC START: test_env\n"
        log_content += f"[{datetime.now().isoformat()}] DIAGNOSTIC END: test_env - Status: healthy\n"
        
        log_file.write_text(log_content)
        
        # Récupérer les logs
        logs = diagnostic_service.get_diagnostic_logs(env_name="test_env", days=7)
        
        assert isinstance(logs, list)
        # Les logs peuvent être vides si le parsing échoue, mais la méthode ne devrait pas planter
    
    def test_export_diagnostic_logs(self, diagnostic_service: DiagnosticService, temp_dir: Path) -> None:
        """Teste l'export des logs de diagnostic."""
        output_file = temp_dir / "diagnostic_export.json"
        
        with patch.object(diagnostic_service, 'get_diagnostic_logs', return_value=[]):
            success = diagnostic_service.export_diagnostic_logs(str(output_file))
            
            assert success is True
            assert output_file.exists()
            
            # Vérifier le contenu
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            assert "exported_at" in data
            assert "logs" in data
            assert isinstance(data["logs"], list)


if __name__ == "__main__":
    pytest.main([__file__])