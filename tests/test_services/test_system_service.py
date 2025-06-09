"""Tests pour le service SystemService."""

import os
import sys
import platform
import pytest
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from pytest import MonkeyPatch
from datetime import datetime, timedelta

from gestvenv.services.system_service import (
    SystemService, OSType, ProcessState, CommandResult, SystemInfo, ProcessInfo
)

class TestSystemService:
    """Tests pour la classe SystemService."""
    
    @pytest.fixture
    def system_service(self) -> SystemService:
        """Fixture pour créer une instance du service système."""
        return SystemService()
    
    def test_init(self, system_service: SystemService) -> None:
        """Teste l'initialisation du service."""
        assert system_service.os_type in [OSType.WINDOWS, OSType.LINUX, OSType.MACOS, OSType.UNKNOWN]
        assert system_service.system in ["windows", "linux", "darwin"]
        assert system_service._system_info_cache is None
        assert system_service._cache_expiry is None
        assert isinstance(system_service._tracked_processes, dict)
    
    def test_detect_os_type(self, system_service: SystemService) -> None:
        """Teste la détection du type de système d'exploitation."""
        with patch('platform.system') as mock_system:
            # Test Windows
            mock_system.return_value = "Windows"
            os_type = system_service._detect_os_type()
            assert os_type == OSType.WINDOWS
            
            # Test Linux
            mock_system.return_value = "Linux"
            os_type = system_service._detect_os_type()
            assert os_type == OSType.LINUX
            
            # Test macOS
            mock_system.return_value = "Darwin"
            os_type = system_service._detect_os_type()
            assert os_type == OSType.MACOS
            
            # Test système inconnu
            mock_system.return_value = "Unknown"
            os_type = system_service._detect_os_type()
            assert os_type == OSType.UNKNOWN
    
    @patch('subprocess.run')
    def test_run_command_success(self, mock_subprocess: MagicMock, 
                                system_service: SystemService) -> None:
        """Teste l'exécution réussie d'une commande."""
        # Configurer le mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Exécuter la commande
        result = system_service.run_command(["echo", "test"])
        
        # Vérifier le résultat
        assert isinstance(result, CommandResult)
        assert result.returncode == 0
        assert result.stdout == "Command output"
        assert result.stderr == ""
        assert result.command == ["echo", "test"]
        assert result.state == ProcessState.COMPLETED
        assert result.duration > 0
    
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_subprocess: MagicMock,
                                system_service: SystemService) -> None:
        """Teste l'échec d'exécution d'une commande."""
        # Configurer le mock pour retourner une erreur
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"
        mock_subprocess.return_value = mock_result
        
        # Exécuter la commande
        result = system_service.run_command(["false"])
        
        # Vérifier le résultat
        assert result.returncode == 1
        assert result.stderr == "Command failed"
        assert result.state == ProcessState.FAILED
    
    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_subprocess: MagicMock,
                                system_service: SystemService) -> None:
        """Teste le timeout d'une commande."""
        # Configurer le mock pour lever une exception de timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep", "10"], timeout=1, output="", stderr=""
        )
        
        # Exécuter la commande
        result = system_service.run_command(["sleep", "10"], timeout=1)
        
        # Vérifier le résultat
        assert result.returncode == 1
        assert result.state == ProcessState.TIMEOUT
        assert "Timeout" in result.stderr
    
    @patch('subprocess.run')
    def test_run_command_with_env_vars(self, mock_subprocess: MagicMock,
                                      system_service: SystemService) -> None:
        """Teste l'exécution d'une commande avec des variables d'environnement."""
        # Configurer le mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Variables d'environnement
        env_vars = {"TEST_VAR": "test_value"}
        
        # Exécuter la commande
        result = system_service.run_command(["env"], env_vars=env_vars)
        
        # Vérifier que subprocess.run a été appelé avec les bonnes variables
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        
        # Vérifier que les variables d'environnement sont incluses
        env_arg = call_args[1]["env"]
        assert "TEST_VAR" in env_arg
        assert env_arg["TEST_VAR"] == "test_value"
    
    @patch('subprocess.run')
    def test_run_command_background(self, mock_subprocess: MagicMock,
                                   system_service: SystemService) -> None:
        """Teste l'exécution d'une commande en arrière-plan."""
        with patch('subprocess.Popen') as mock_popen:
            # Configurer le mock Popen
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            # Exécuter la commande en arrière-plan
            result = system_service.run_command(["long_running_command"], background=True)
            
            # Vérifier le résultat
            assert result.returncode == 0
            assert result.process_id == 12345
            assert result.state == ProcessState.RUNNING
            assert "PID: 12345" in result.stdout
            
            # Vérifier que le processus est suivi
            assert 12345 in system_service._tracked_processes
    
    @patch('psutil.Process')
    def test_get_process_status(self, mock_psutil_process: MagicMock,
                               system_service: SystemService) -> None:
        """Teste la récupération du statut d'un processus."""
        # Configurer le mock
        mock_process = MagicMock()
        mock_process.name.return_value = "python"
        mock_process.cmdline.return_value = ["python", "script.py"]
        mock_process.status.return_value = "running"
        mock_process.cpu_percent.return_value = 15.5
        mock_process.memory_percent.return_value = 8.2
        mock_process.create_time.return_value = time.time() - 3600
        mock_process.cwd.return_value = "/home/user"
        mock_psutil_process.return_value = mock_process
        
        # Tester la récupération
        process_info = system_service.get_process_status(12345)
        
        # Vérifier le résultat
        assert isinstance(process_info, ProcessInfo)
        assert process_info.pid == 12345
        assert process_info.name == "python"
        assert process_info.command == ["python", "script.py"]
        assert process_info.status == "running"
        assert process_info.cpu_percent == 15.5
        assert process_info.memory_percent == 8.2
        assert process_info.cwd == "/home/user"
    
    @patch('psutil.Process')
    def test_get_process_status_not_found(self, mock_psutil_process: MagicMock,
                                         system_service: SystemService) -> None:
        """Teste la récupération du statut d'un processus inexistant."""
        import psutil
        
        # Configurer le mock pour lever une exception
        mock_psutil_process.side_effect = psutil.NoSuchProcess(12345)
        
        # Tester la récupération
        process_info = system_service.get_process_status(12345)
        
        # Vérifier que None est retourné
        assert process_info is None
    
    @patch('psutil.Process')
    def test_kill_process_success(self, mock_psutil_process: MagicMock,
                                 system_service: SystemService) -> None:
        """Teste la terminaison réussie d'un processus."""
        # Configurer le mock
        mock_process = MagicMock()
        mock_psutil_process.return_value = mock_process
        
        # Ajouter le processus au suivi
        system_service._tracked_processes[12345] = MagicMock()
        
        # Tester la terminaison
        success = system_service.kill_process(12345)
        
        # Vérifier le résultat
        assert success is True
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        
        # Vérifier que le processus a été retiré du suivi
        assert 12345 not in system_service._tracked_processes
    
    @patch('psutil.Process')
    def test_kill_process_force(self, mock_psutil_process: MagicMock,
                               system_service: SystemService) -> None:
        """Teste la terminaison forcée d'un processus."""
        # Configurer le mock
        mock_process = MagicMock()
        mock_psutil_process.return_value = mock_process
        
        # Tester la terminaison forcée
        success = system_service.kill_process(12345, force=True)
        
        # Vérifier le résultat
        assert success is True
        mock_process.kill.assert_called_once()
        mock_process.wait.assert_called_once()
    
    def test_get_activation_command(self, system_service: SystemService, temp_dir: Path) -> None:
        """Teste la génération de la commande d'activation."""
        # Créer un environnement simulé
        env_path = temp_dir / "test_env"
        env_path.mkdir()
        
        if os.name == "nt":
            scripts_dir = env_path / "Scripts"
            scripts_dir.mkdir()
            activate_script = scripts_dir / "activate.bat"
        else:
            bin_dir = env_path / "bin"
            bin_dir.mkdir()
            activate_script = bin_dir / "activate"
        
        activate_script.touch()
        
        # Mock du service d'environnement
        system_service.env_service.get_activation_script_path = MagicMock(return_value=activate_script)
        
        # Tester la génération de commande
        command = system_service.get_activation_command("test_env", env_path)
        
        assert command is not None
        assert str(activate_script) in command
        
        if os.name == "nt":
            # Windows: exécution directe
            assert command.startswith('"')
            assert command.endswith('"')
        else:
            # Unix: source
            assert command.startswith('source')
    
    @patch('subprocess.run')
    def test_run_in_environment(self, mock_subprocess: MagicMock,
                               system_service: SystemService, temp_dir: Path) -> None:
        """Teste l'exécution d'une commande dans un environnement."""
        # Créer un environnement simulé
        env_path = temp_dir / "test_env"
        env_path.mkdir()
        
        if os.name == "nt":
            python_exe = env_path / "Scripts" / "python.exe"
            python_exe.parent.mkdir(exist_ok=True)
        else:
            python_exe = env_path / "bin" / "python"
            python_exe.parent.mkdir(exist_ok=True)
        
        python_exe.touch()
        
        # Mock du service d'environnement
        system_service.env_service.get_python_executable = MagicMock(return_value=python_exe)
        
        # Configurer subprocess
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Script output"
        mock_subprocess.return_value = mock_result
        
        # Tester l'exécution
        result = system_service.run_in_environment("test_env", env_path, ["-c", "print('hello')"])
        
        # Vérifier le résultat
        assert result.returncode == 0
        assert result.stdout == "Script output"
        
        # Vérifier que la commande inclut l'exécutable Python de l'environnement
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        command = call_args[0][0]
        assert str(python_exe) == command[0]
        assert "-c" in command
        assert "print('hello')" in command
    
    @patch('subprocess.run')
    def test_check_python_version(self, mock_subprocess: MagicMock,
                                 system_service: SystemService) -> None:
        """Teste la vérification de version Python."""
        # Configurer le mock pour retourner une version
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Python 3.9.7"
        mock_subprocess.return_value = mock_result
        
        # Tester la vérification
        version = system_service.check_python_version("python3")
        
        assert version == "3.9.7"
        mock_subprocess.assert_called_once_with(
            ["python3", "--version"], timeout=10, capture_output=True, text=True, shell=False, check=False
        )
    
    @patch('subprocess.run')
    def test_check_python_version_not_available(self, mock_subprocess: MagicMock,
                                               system_service: SystemService) -> None:
        """Teste la vérification d'une version Python non disponible."""
        # Configurer le mock pour retourner une erreur
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Command not found"
        mock_subprocess.return_value = mock_result
        
        # Tester la vérification
        version = system_service.check_python_version("python99")
        
        assert version is None
    
    def test_get_available_python_versions(self, system_service: SystemService) -> None:
        """Teste la récupération des versions Python disponibles."""
        with patch.object(system_service, 'check_python_version') as mock_check:
            # Simuler les retours de check_python_version
            def side_effect(cmd):
                if cmd == "python3":
                    return "3.9.7"
                elif cmd == "python3.10":
                    return "3.10.2"
                else:
                    return None
            
            mock_check.side_effect = side_effect
            
            # Tester la récupération
            versions = system_service.get_available_python_versions()
            
            # Vérifier le résultat
            assert len(versions) >= 2
            python3_found = any(v["command"] == "python3" and v["version"] == "3.9.7" for v in versions)
            python310_found = any(v["command"] == "python3.10" and v["version"] == "3.10.2" for v in versions)
            
            assert python3_found
            assert python310_found
    
    @patch('psutil.boot_time')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_count')
    def test_get_system_info(self, mock_cpu_count: MagicMock, mock_disk_usage: MagicMock,
                            mock_virtual_memory: MagicMock, mock_boot_time: MagicMock,
                            system_service: SystemService) -> None:
        """Teste la récupération des informations système."""
        # Configurer les mocks
        mock_boot_time.return_value = time.time() - 3600  # 1 heure d'uptime
        mock_cpu_count.return_value = 8
        
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024 * 1024 * 1024  # 16 GB
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.total = 500 * 1024 * 1024 * 1024  # 500 GB
        mock_disk.free = 100 * 1024 * 1024 * 1024   # 100 GB
        mock_disk_usage.return_value = mock_disk
        
        with patch.object(system_service, 'get_python_info') as mock_python_info:
            mock_python_info.return_value = {
                "version": "3.9.7",
                "implementation": "CPython"
            }
            
            # Tester la récupération
            system_info = system_service.get_system_info()
            
            # Vérifier le résultat
            assert isinstance(system_info, SystemInfo)
            assert system_info.cpu_count == 8
            assert system_info.memory_total == 16 * 1024 * 1024 * 1024
            assert system_info.disk_total == 500 * 1024 * 1024 * 1024
            assert system_info.disk_free == 100 * 1024 * 1024 * 1024
            assert system_info.python_version == "3.9.7"
            assert system_info.python_implementation == "CPython"
    
    def test_get_python_info(self, system_service: SystemService) -> None:
        """Teste la récupération des informations Python."""
        info = system_service.get_python_info()
        
        # Vérifier les clés attendues
        assert "version" in info
        assert "implementation" in info
        assert "build" in info
        assert "compiler" in info
        assert "is_64bit" in info
        assert "executable" in info
        assert "prefix" in info
        assert "path" in info
        
        # Vérifier que les valeurs correspondent à celles de Python en cours
        assert info["version"] == platform.python_version()
        assert info["implementation"] == platform.python_implementation()
        assert info["executable"] == sys.executable
        assert info["prefix"] == sys.prefix
        assert isinstance(info["is_64bit"], bool)
        assert isinstance(info["path"], list)
    
    @patch('subprocess.run')
    def test_check_command_exists(self, mock_subprocess: MagicMock,
                                 system_service: SystemService) -> None:
        """Teste la vérification d'existence d'une commande."""
        # Test commande existante
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        exists = system_service.check_command_exists("python")
        assert exists is True
        
        # Test commande inexistante
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result
        
        exists = system_service.check_command_exists("nonexistent_command")
        assert exists is False
    
    def test_create_directory(self, system_service: SystemService, temp_dir: Path) -> None:
        """Teste la création de répertoires."""
        # Test création réussie
        test_dir = temp_dir / "new_dir" / "nested"
        success = system_service.create_directory(test_dir)
        
        assert success is True
        assert test_dir.exists()
        assert test_dir.is_dir()
        
        # Test répertoire existant
        success = system_service.create_directory(test_dir, exist_ok=True)
        assert success is True
        
        # Test sans créer les parents
        another_dir = temp_dir / "missing_parent" / "child"
        success = system_service.create_directory(another_dir, parents=False)
        assert success is False
    
    def test_get_free_disk_space(self, system_service: SystemService) -> None:
        """Teste la récupération de l'espace disque libre."""
        free_space = system_service.get_free_disk_space(Path.cwd())
        
        assert isinstance(free_space, int)
        assert free_space > 0
    
    def test_get_disk_usage(self, system_service: SystemService) -> None:
        """Teste la récupération de l'utilisation du disque."""
        usage = system_service.get_disk_usage(Path.cwd())
        
        assert "total" in usage
        assert "used" in usage
        assert "free" in usage
        assert isinstance(usage["total"], int)
        assert isinstance(usage["used"], int)
        assert isinstance(usage["free"], int)
        assert usage["total"] > 0
        assert usage["free"] > 0
    
    def test_get_terminal_size(self, system_service: SystemService) -> None:
        """Teste la récupération de la taille du terminal."""
        with patch('shutil.get_terminal_size', return_value=(120, 40)):
            columns, lines = system_service.get_terminal_size()
            assert columns == 120
            assert lines == 40
        
        # Test avec erreur (valeurs par défaut)
        with patch('shutil.get_terminal_size', side_effect=Exception("Terminal error")):
            columns, lines = system_service.get_terminal_size()
            assert columns == 80
            assert lines == 24
    
    def test_check_permissions(self, system_service: SystemService, temp_dir: Path) -> None:
        """Teste la vérification des permissions."""
        # Créer un fichier de test
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")
        
        # Tester les permissions
        permissions = system_service.check_permissions(test_file)
        
        assert "read" in permissions
        assert "write" in permissions
        assert "execute" in permissions
        assert "exists" in permissions
        assert permissions["exists"] is True
        assert permissions["read"] is True
        assert permissions["write"] is True
        
        # Test fichier inexistant
        nonexistent = temp_dir / "nonexistent.txt"
        permissions = system_service.check_permissions(nonexistent)
        assert permissions["exists"] is False
    
    def test_fix_permissions(self, system_service: SystemService, temp_dir: Path) -> None:
        """Teste la correction des permissions."""
        # Créer un fichier de test
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")
        
        # Tester la correction
        success = system_service.fix_permissions(test_file)
        assert success is True
        
        # Test fichier inexistant
        nonexistent = temp_dir / "nonexistent.txt"
        success = system_service.fix_permissions(nonexistent)
        assert success is False
    
    def test_get_environment_variables(self, system_service: SystemService) -> None:
        """Teste la récupération des variables d'environnement."""
        env_vars = system_service.get_environment_variables()
        
        assert isinstance(env_vars, dict)
        assert len(env_vars) > 0
        # Vérifier qu'au moins PATH existe
        assert any("PATH" in key.upper() for key in env_vars.keys())
    
    def test_set_environment_variable(self, system_service: SystemService) -> None:
        """Teste la définition d'une variable d'environnement."""
        success = system_service.set_environment_variable("TEST_VAR", "test_value")
        
        assert success is True
        assert os.environ.get("TEST_VAR") == "test_value"
        
        # Nettoyer
        if "TEST_VAR" in os.environ:
            del os.environ["TEST_VAR"]
    
    @patch('psutil.cpu_percent')
    def test_get_cpu_usage(self, mock_cpu_percent: MagicMock,
                          system_service: SystemService) -> None:
        """Teste la récupération de l'utilisation CPU."""
        mock_cpu_percent.return_value = 45.2
        
        cpu_usage = system_service.get_cpu_usage()
        
        assert cpu_usage == 45.2
        mock_cpu_percent.assert_called_once_with(interval=1.0)
    
    @patch('psutil.virtual_memory')
    def test_get_memory_usage(self, mock_virtual_memory: MagicMock,
                             system_service: SystemService) -> None:
        """Teste la récupération de l'utilisation mémoire."""
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024 * 1024 * 1024  # 16 GB
        mock_memory.available = 8 * 1024 * 1024 * 1024  # 8 GB
        mock_memory.used = 8 * 1024 * 1024 * 1024  # 8 GB
        mock_memory.free = 6 * 1024 * 1024 * 1024  # 6 GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        memory_usage = system_service.get_memory_usage()
        
        assert memory_usage["total"] == 16 * 1024 * 1024 * 1024
        assert memory_usage["available"] == 8 * 1024 * 1024 * 1024
        assert memory_usage["used"] == 8 * 1024 * 1024 * 1024
        assert memory_usage["free"] == 6 * 1024 * 1024 * 1024
        assert memory_usage["percent"] == 50.0
    
    def test_is_admin(self, system_service: SystemService) -> None:
        """Teste la vérification des privilèges administrateur."""
        # On ne peut pas vraiment tester cela de manière fiable
        # car cela dépend de l'utilisateur qui exécute les tests
        is_admin = system_service.is_admin()
        assert isinstance(is_admin, bool)
    
    def test_get_system_uptime(self, system_service: SystemService) -> None:
        """Teste la récupération de l'uptime du système."""
        with patch('psutil.boot_time', return_value=time.time() - 3600):  # 1 heure d'uptime
            uptime = system_service.get_system_uptime()
            
            assert isinstance(uptime, timedelta)
            assert uptime.total_seconds() > 3500  # Environ 1 heure
            assert uptime.total_seconds() < 3700  # Avec marge d'erreur
    
    def test_file_exists(self, system_service: SystemService, temp_dir: Path) -> None:
        """Teste la vérification d'existence de fichier."""
        # Créer un fichier de test
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test")
        
        # Test fichier existant
        assert system_service.file_exists(test_file) is True
        
        # Test fichier inexistant
        nonexistent = temp_dir / "nonexistent.txt"
        assert system_service.file_exists(nonexistent) is False
        
        # Test répertoire (ne devrait pas être considéré comme un fichier)
        assert system_service.file_exists(temp_dir) is False
    
    def test_directory_exists(self, system_service: SystemService, temp_dir: Path) -> None:
        """Teste la vérification d'existence de répertoire."""
        # Test répertoire existant
        assert system_service.directory_exists(temp_dir) is True
        
        # Test répertoire inexistant
        nonexistent = temp_dir / "nonexistent"
        assert system_service.directory_exists(nonexistent) is False
        
        # Test fichier (ne devrait pas être considéré comme un répertoire)
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test")
        assert system_service.directory_exists(test_file) is False
    
    def test_delete_file(self, system_service: SystemService, temp_dir: Path) -> None:
        """Teste la suppression de fichier."""
        # Créer un fichier de test
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test")
        
        # Test suppression réussie
        success = system_service.delete_file(test_file)
        assert success is True
        assert not test_file.exists()
        
        # Test fichier déjà supprimé (devrait retourner True)
        success = system_service.delete_file(test_file)
        assert success is True
    
    def test_delete_directory(self, system_service: SystemService, temp_dir: Path) -> None:
        """Teste la suppression de répertoire."""
        # Créer un répertoire de test
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()
        
        # Test suppression réussie
        success = system_service.delete_directory(test_dir)
        assert success is True
        assert not test_dir.exists()
        
        # Test répertoire avec contenu
        test_dir_with_content = temp_dir / "test_dir_with_content"
        test_dir_with_content.mkdir()
        (test_dir_with_content / "file.txt").write_text("content")
        
        # Suppression récursive
        success = system_service.delete_directory(test_dir_with_content, recursive=True)
        assert success is True
        assert not test_dir_with_content.exists()
    
    def test_cleanup_tracked_processes(self, system_service: SystemService) -> None:
        """Teste le nettoyage des processus suivis."""
        # Ajouter des processus fictifs
        mock_process1 = MagicMock()
        mock_process1.poll.return_value = 0  # Terminé
        mock_process2 = MagicMock()
        mock_process2.poll.return_value = None  # En cours
        
        system_service._tracked_processes[123] = mock_process1
        system_service._tracked_processes[456] = mock_process2
        
        # Nettoyer
        system_service.cleanup_tracked_processes()
        
        # Vérifier que seul le processus terminé a été supprimé
        assert 123 not in system_service._tracked_processes
        assert 456 in system_service._tracked_processes
    
    def test_get_tracked_processes(self, system_service: SystemService) -> None:
        """Teste la récupération des processus suivis."""
        with patch.object(system_service, 'get_process_status') as mock_get_status:
            # Mock d'informations de processus
            mock_process_info = ProcessInfo(
                pid=123,
                name="python",
                command=["python", "script.py"],
                status="running",
                cpu_percent=10.0,
                memory_percent=5.0,
                create_time=datetime.now()
            )
            mock_get_status.return_value = mock_process_info
            
            # Ajouter un processus au suivi
            mock_process = MagicMock()
            mock_process.poll.return_value = None  # Processus toujours actif
            system_service._tracked_processes[123] = mock_process
            
            # Récupérer la liste
            processes = system_service.get_tracked_processes()
            
            assert len(processes) == 1
            assert processes[0]["pid"] == 123
            assert processes[0]["name"] == "python"
            assert processes[0]["status"] == "running"


if __name__ == "__main__":
    pytest.main([__file__])