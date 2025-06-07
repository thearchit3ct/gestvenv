"""
Service de diagnostic pour GestVenv.

Ce module fournit les fonctionnalités pour diagnostiquer la santé des environnements virtuels,
du système et du cache, ainsi que pour effectuer des réparations automatiques.
"""

import os
import sys
import json
import hashlib
import logging
import tempfile
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from gestvenv.services.environment_service import EnvironmentService
from gestvenv.services.package_service import PackageService
from gestvenv.services.system_service import SystemService
from gestvenv.services.cache_service import CacheService
from gestvenv.core.config_manager import ConfigManager

# Configuration du logger
logger = logging.getLogger(__name__)

class DiagnosticService:
    """Service pour le diagnostic et la réparation des environnements virtuels."""
    
    def __init__(self) -> None:
        """Initialise le service de diagnostic."""
        
        self.env_service = EnvironmentService()
        self.pkg_service = PackageService()
        self.sys_service = SystemService()
        self.cache_service = CacheService()
        
        # Configuration manager pour accéder aux paramètres
        self.config_manager = ConfigManager()
        
        # Chemin vers les logs
        self.logs_dir = self._get_logs_directory()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_logs_directory(self) -> Path:
        """Obtient le répertoire des logs."""
        from ..utils.path_utils import get_default_data_dir
        return get_default_data_dir() / "logs"
    
    def diagnose_environment(self, env_name: str, full_check: bool = False) -> Dict[str, Any]:
        """
        Diagnostique un environnement virtuel spécifique.
        
        Args:
            env_name: Nom de l'environnement à diagnostiquer.
            full_check: Si True, effectue un diagnostic complet.
            
        Returns:
            Rapport de diagnostic détaillé.
        """
        try:
            self._log_diagnostic_start(env_name)
            
            # Vérifier si l'environnement existe dans la configuration
            if not self.config_manager.environment_exists(env_name):
                return self._create_error_report(
                    env_name,
                    "L'environnement n'existe pas dans la configuration",
                    "configuration_missing"
                )
            
            # Obtenir les informations de l'environnement
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return self._create_error_report(
                    env_name,
                    "Impossible d'obtenir les informations de l'environnement",
                    "info_retrieval_failed"
                )
            
            # Initialiser le rapport de diagnostic
            report = {
                "environment": env_name,
                "path": str(env_info.path),
                "python_version": env_info.python_version,
                "created_at": env_info.created_at.isoformat() if hasattr(env_info.created_at, 'isoformat') else str(env_info.created_at),
                "diagnosed_at": datetime.now().isoformat(),
                "status": "healthy",
                "issues": [],
                "warnings": [],
                "info": [],
                "checks": {},
                "recommendations": [],
                "repair_actions": []
            }
            
            # Effectuer les vérifications de base
            self._check_physical_existence(env_info.path, report)
            self._check_directory_structure(env_info.path, report)
            self._check_python_executable(env_name, env_info.path, report)
            self._check_pip_executable(env_name, env_info.path, report)
            self._check_activation_script(env_name, env_info.path, report)
            self._check_permissions(env_info.path, report)
            
            # Vérifications approfondies si demandé
            if full_check:
                self._check_packages_integrity(env_name, env_info, report)
                self._check_package_updates(env_name, report)
                self._check_disk_space(env_info.path, report)
                self._check_environment_variables(env_name, env_info.path, report)
                self._check_configuration_consistency(env_name, env_info, report)
                self._check_cache_coherence(env_name, report)
            
            # Déterminer le statut global
            if report["issues"]:
                report["status"] = "unhealthy"
            elif report["warnings"]:
                report["status"] = "degraded"
            
            # Générer des recommandations
            self._generate_recommendations(report)
            
            self._log_diagnostic_end(env_name, str(report["status"]))
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors du diagnostic de l'environnement {env_name}: {str(e)}")
            return self._create_error_report(env_name, f"Erreur de diagnostic: {str(e)}", "diagnostic_error")
    
    def _check_physical_existence(self, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie l'existence physique de l'environnement."""
        if not env_path.exists():
            report["issues"].append({
                "type": "missing_environment",
                "severity": "critical",
                "message": "L'environnement n'existe pas physiquement sur le disque",
                "path": str(env_path)
            })
            report["checks"]["physical_existence"] = False
            report["repair_actions"].append("recreate_environment")
        else:
            report["checks"]["physical_existence"] = True
            report["info"].append("Environnement physiquement présent")
    
    def _check_directory_structure(self, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie la structure des répertoires de l'environnement."""
        if not env_path.exists():
            return
        
        expected_dirs = []
        expected_files = ["pyvenv.cfg"]
        
        if os.name == "nt":  # Windows
            expected_dirs = ["Scripts", "Lib", "Include"]
        else:  # Unix-like
            expected_dirs = ["bin", "lib", "include"]
        
        missing_dirs = []
        missing_files = []
        
        # Vérifier les répertoires
        for dir_name in expected_dirs:
            dir_path = env_path / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
        
        # Vérifier les fichiers
        for file_name in expected_files:
            file_path = env_path / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_dirs or missing_files:
            report["issues"].append({
                "type": "incomplete_structure",
                "severity": "high",
                "message": "Structure de l'environnement incomplète",
                "missing_dirs": missing_dirs,
                "missing_files": missing_files
            })
            report["checks"]["directory_structure"] = False
            report["repair_actions"].append("repair_structure")
        else:
            report["checks"]["directory_structure"] = True
            report["info"].append("Structure de répertoires correcte")
    
    def _check_python_executable(self, env_name: str, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie l'exécutable Python."""
        python_exe = self.env_service.get_python_executable(env_name, env_path)
        
        if not python_exe or not python_exe.exists():
            report["issues"].append({
                "type": "missing_python",
                "severity": "critical",
                "message": "Exécutable Python manquant",
                "expected_path": str(python_exe) if python_exe else "inconnu"
            })
            report["checks"]["python_executable"] = False
            report["repair_actions"].append("reinstall_python")
        else:
            # Tester l'exécution de Python
            try:
                result = subprocess.run([str(python_exe), "--version"], 
                                      capture_output=True, text=True, check=False, timeout=10)
                if result.returncode == 0:
                    report["checks"]["python_executable"] = True
                    report["info"].append(f"Python fonctionnel: {result.stdout.strip()}")
                else:
                    report["issues"].append({
                        "type": "broken_python",
                        "severity": "high",
                        "message": "L'exécutable Python ne fonctionne pas correctement",
                        "error": result.stderr
                    })
                    report["checks"]["python_executable"] = False
                    report["repair_actions"].append("repair_python")
            except Exception as e:
                report["issues"].append({
                    "type": "python_test_failed",
                    "severity": "high",
                    "message": f"Impossible de tester l'exécutable Python: {str(e)}"
                })
                report["checks"]["python_executable"] = False
    
    def _check_pip_executable(self, env_name: str, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie l'exécutable pip."""
        pip_exe = self.env_service.get_pip_executable(env_name, env_path)
        
        if not pip_exe or not pip_exe.exists():
            report["warnings"].append({
                "type": "missing_pip",
                "severity": "medium",
                "message": "Exécutable pip manquant",
                "expected_path": str(pip_exe) if pip_exe else "inconnu"
            })
            report["checks"]["pip_executable"] = False
            report["repair_actions"].append("install_pip")
        else:
            # Tester l'exécution de pip
            try:
                result = subprocess.run([str(pip_exe), "--version"], 
                                      capture_output=True, text=True, check=False, timeout=10)
                if result.returncode == 0:
                    report["checks"]["pip_executable"] = True
                    report["info"].append(f"pip fonctionnel: {result.stdout.strip()}")
                else:
                    report["warnings"].append({
                        "type": "broken_pip",
                        "severity": "medium",
                        "message": "L'exécutable pip ne fonctionne pas correctement",
                        "error": result.stderr
                    })
                    report["checks"]["pip_executable"] = False
                    report["repair_actions"].append("repair_pip")
            except Exception as e:
                report["warnings"].append({
                    "type": "pip_test_failed",
                    "severity": "medium",
                    "message": f"Impossible de tester l'exécutable pip: {str(e)}"
                })
                report["checks"]["pip_executable"] = False
    
    def _check_activation_script(self, env_name: str, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie le script d'activation."""
        activation_script = self.env_service.get_activation_script_path(env_name, env_path)
        
        if not activation_script or not activation_script.exists():
            report["warnings"].append({
                "type": "missing_activation_script",
                "severity": "low",
                "message": "Script d'activation manquant",
                "expected_path": str(activation_script) if activation_script else "inconnu"
            })
            report["checks"]["activation_script"] = False
            report["repair_actions"].append("repair_activation_script")
        else:
            report["checks"]["activation_script"] = True
            report["info"].append("Script d'activation présent")
    
    def _check_permissions(self, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie les permissions sur l'environnement."""
        if not env_path.exists():
            return
        
        try:
            # Vérifier les permissions de lecture/écriture
            if not os.access(env_path, os.R_OK):
                report["issues"].append({
                    "type": "no_read_permission",
                    "severity": "high",
                    "message": "Pas de permission de lecture sur l'environnement"
                })
                report["checks"]["read_permission"] = False
            else:
                report["checks"]["read_permission"] = True
            
            if not os.access(env_path, os.W_OK):
                report["issues"].append({
                    "type": "no_write_permission",
                    "severity": "high",
                    "message": "Pas de permission d'écriture sur l'environnement"
                })
                report["checks"]["write_permission"] = False
                report["repair_actions"].append("fix_permissions")
            else:
                report["checks"]["write_permission"] = True
                
        except Exception as e:
            report["warnings"].append({
                "type": "permission_check_failed",
                "severity": "low",
                "message": f"Impossible de vérifier les permissions: {str(e)}"
            })
    
    def _check_packages_integrity(self, env_name: str, env_info: Any, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie l'intégrité des packages installés."""
        try:
            # Obtenir la liste des packages installés
            installed_packages = self.pkg_service.list_installed_packages(env_name)
            
            if not installed_packages:
                report["info"].append("Aucun package installé")
                report["checks"]["packages_integrity"] = True
                return
            
            # Vérifier la cohérence avec la configuration
            configured_packages = set(env_info.packages) if env_info.packages else set()
            installed_package_specs = set()
            
            broken_packages = []
            for pkg in installed_packages:
                pkg_spec = f"{pkg['name']}=={pkg['version']}"
                installed_package_specs.add(pkg_spec)
                
                # Tester si le package peut être importé (pour les packages Python purs)
                if self._is_importable_package(pkg['name']):
                    try:
                        python_exe = self.env_service.get_python_executable(env_name, env_info.path)
                        if python_exe:
                            result = subprocess.run([
                                str(python_exe), "-c", f"import {pkg['name']}"
                            ], capture_output=True, text=True, check=False, timeout=5)
                            
                            if result.returncode != 0:
                                broken_packages.append(pkg['name'])
                    except Exception:
                        pass  # Ignore les erreurs d'import pour les packages système
            
            # Signaler les packages cassés
            if broken_packages:
                report["issues"].append({
                    "type": "broken_packages",
                    "severity": "medium",
                    "message": f"Packages cassés détectés: {', '.join(broken_packages)}",
                    "packages": broken_packages
                })
                report["repair_actions"].append("reinstall_broken_packages")
            
            # Vérifier la cohérence avec la configuration
            missing_in_config = installed_package_specs - configured_packages
            missing_installed = configured_packages - installed_package_specs
            
            if missing_in_config:
                report["warnings"].append({
                    "type": "packages_not_in_config",
                    "severity": "low",
                    "message": "Packages installés non déclarés dans la configuration",
                    "packages": list(missing_in_config)
                })
            
            if missing_installed:
                report["warnings"].append({
                    "type": "missing_configured_packages",
                    "severity": "medium",
                    "message": "Packages configurés mais non installés",
                    "packages": list(missing_installed)
                })
                report["repair_actions"].append("install_missing_packages")
            
            report["checks"]["packages_integrity"] = len(broken_packages) == 0
            report["info"].append(f"{len(installed_packages)} packages vérifiés")
            
        except Exception as e:
            report["warnings"].append({
                "type": "packages_check_failed",
                "severity": "low",
                "message": f"Impossible de vérifier l'intégrité des packages: {str(e)}"
            })
    
    def _is_importable_package(self, package_name: str) -> bool:
        """Vérifie si un package est censé être importable."""
        # Liste des packages système ou non-importables connus
        non_importable = {
            'pip', 'setuptools', 'wheel', 'pkg-resources', 'pkg_resources',
            'distribute', 'easy-install', 'argparse'
        }
        return package_name.lower() not in non_importable
    
    def _check_package_updates(self, env_name: str, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie les mises à jour disponibles."""
        try:
            updates = self.pkg_service.check_for_updates(env_name)
            
            if updates:
                report["info"].append(f"{len(updates)} mise(s) à jour disponible(s)")
                report["checks"]["updates_available"] = True
                
                # Lister les packages avec des mises à jour critiques
                critical_updates = []
                for update in updates:
                    # Heuristic pour détecter les mises à jour critiques
                    current_parts = update.get("current_version", "0.0.0").split(".")
                    latest_parts = update.get("latest_version", "0.0.0").split(".")
                    
                    try:
                        if (len(current_parts) >= 2 and len(latest_parts) >= 2 and
                            int(latest_parts[0]) > int(current_parts[0])):
                            critical_updates.append(update["name"])
                    except (ValueError, IndexError):
                        pass
                
                if critical_updates:
                    report["warnings"].append({
                        "type": "critical_updates_available",
                        "severity": "medium",
                        "message": f"Mises à jour majeures disponibles: {', '.join(critical_updates)}",
                        "packages": critical_updates
                    })
            else:
                report["info"].append("Tous les packages sont à jour")
                report["checks"]["updates_available"] = False
                
        except Exception as e:
            report["warnings"].append({
                "type": "update_check_failed",
                "severity": "low",
                "message": f"Impossible de vérifier les mises à jour: {str(e)}"
            })
    
    def _check_disk_space(self, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie l'espace disque disponible."""
        try:
            if not env_path.exists():
                return
            
            # Calculer la taille de l'environnement
            env_size = self._calculate_directory_size(env_path)
            
            # Obtenir l'espace libre
            free_space = shutil.disk_usage(env_path).free
            
            # Seuils d'alerte
            low_space_threshold = 100 * 1024 * 1024  # 100 MB
            critical_space_threshold = 50 * 1024 * 1024  # 50 MB
            
            if free_space < critical_space_threshold:
                report["issues"].append({
                    "type": "critically_low_disk_space",
                    "severity": "high",
                    "message": f"Espace disque critique: {free_space // (1024*1024)} MB disponible",
                    "free_space_mb": free_space // (1024*1024)
                })
                report["checks"]["disk_space"] = False
            elif free_space < low_space_threshold:
                report["warnings"].append({
                    "type": "low_disk_space",
                    "severity": "medium",
                    "message": f"Espace disque faible: {free_space // (1024*1024)} MB disponible",
                    "free_space_mb": free_space // (1024*1024)
                })
                report["checks"]["disk_space"] = True
            else:
                report["checks"]["disk_space"] = True
                report["info"].append(f"Espace disque suffisant: {free_space // (1024*1024)} MB disponible")
            
            report["info"].append(f"Taille de l'environnement: {env_size // (1024*1024)} MB")
            
        except Exception as e:
            report["warnings"].append({
                "type": "disk_space_check_failed",
                "severity": "low",
                "message": f"Impossible de vérifier l'espace disque: {str(e)}"
            })
    
    def _calculate_directory_size(self, path: Path) -> int:
        """Calcule la taille totale d'un répertoire."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, FileNotFoundError):
                        pass
        except Exception:
            pass
        return total_size
    
    def _check_environment_variables(self, env_name: str, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie les variables d'environnement."""
        try:
            # Vérifier les variables d'environnement importantes
            python_exe = self.env_service.get_python_executable(env_name, env_path)
            if python_exe:
                # Tester l'environnement Python
                result = subprocess.run([
                    str(python_exe), "-c", 
                    "import sys, os; print('PYTHONPATH:', os.environ.get('PYTHONPATH', 'Not set')); print('VIRTUAL_ENV:', os.environ.get('VIRTUAL_ENV', 'Not set'))"
                ], capture_output=True, text=True, check=False, timeout=10)
                
                if result.returncode == 0:
                    report["info"].append("Variables d'environnement Python accessibles")
                    report["checks"]["environment_variables"] = True
                else:
                    report["warnings"].append({
                        "type": "env_vars_check_failed",
                        "severity": "low",
                        "message": "Impossible de vérifier les variables d'environnement"
                    })
                    
        except Exception as e:
            report["warnings"].append({
                "type": "env_vars_test_failed",
                "severity": "low",
                "message": f"Test des variables d'environnement échoué: {str(e)}"
            })
    
    def _check_configuration_consistency(self, env_name: str, env_info: Any, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie la cohérence de la configuration."""
        try:
            # Vérifier que le chemin dans la config correspond au chemin réel
            config_path = Path(env_info.path)
            
            # Vérifier la cohérence du nom
            if config_path.name != env_name:
                report["warnings"].append({
                    "type": "name_path_mismatch",
                    "severity": "low",
                    "message": f"Le nom de l'environnement ne correspond pas au nom du répertoire",
                    "config_name": env_name,
                    "directory_name": config_path.name
                })
            
            # Vérifier la cohérence de la version Python
            if config_path.exists():
                pyvenv_cfg = config_path / "pyvenv.cfg"
                if pyvenv_cfg.exists():
                    try:
                        with open(pyvenv_cfg, 'r') as f:
                            content = f.read()
                        
                        # Extraire la version Python du fichier pyvenv.cfg
                        import re
                        version_match = re.search(r'version\s*=\s*([0-9.]+)', content)
                        if version_match:
                            actual_version = version_match.group(1)
                            if actual_version not in env_info.python_version:
                                report["warnings"].append({
                                    "type": "python_version_mismatch",
                                    "severity": "low",
                                    "message": "Version Python incohérente entre la configuration et l'environnement",
                                    "config_version": env_info.python_version,
                                    "actual_version": actual_version
                                })
                    except Exception:
                        pass
            
            report["checks"]["configuration_consistency"] = True
            
        except Exception as e:
            report["warnings"].append({
                "type": "config_consistency_check_failed",
                "severity": "low",
                "message": f"Impossible de vérifier la cohérence de la configuration: {str(e)}"
            })
    
    def _check_cache_coherence(self, env_name: str, env_path: Path, report: Dict[str, Any]) -> None:
        """Vérifie la cohérence avec le cache."""
        try:
            # Vérifier si les packages de l'environnement sont disponibles dans le cache
            env_info = self.config_manager.get_environment(env_name)
            if not env_info or not env_info.packages:
                return
            
            cached_packages = 0
            missing_from_cache = []
            
            for pkg_spec in env_info.packages:
                pkg_name = pkg_spec.split('==')[0].split('>')[0].split('<')[0].strip()
                pkg_version = None
                
                if '==' in pkg_spec:
                    pkg_version = pkg_spec.split('==')[1].strip()
                
                if self.cache_service.has_package(pkg_name, pkg_version):
                    cached_packages += 1
                else:
                    missing_from_cache.append(pkg_spec)
            
            if missing_from_cache:
                report["info"].append(f"{len(missing_from_cache)} package(s) manquant(s) dans le cache")
            
            if cached_packages > 0:
                report["info"].append(f"{cached_packages} package(s) disponible(s) dans le cache")
            
            report["checks"]["cache_coherence"] = True
            
        except Exception as e:
            report["warnings"].append({
                "type": "cache_coherence_check_failed",
                "severity": "low",
                "message": f"Impossible de vérifier la cohérence du cache: {str(e)}"
            })
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> None:
        """Génère des recommandations basées sur les problèmes détectés."""
        recommendations = []
        
        # Recommandations basées sur les actions de réparation
        repair_actions = report.get("repair_actions", [])
        
        if "recreate_environment" in repair_actions:
            recommendations.append("Recréer l'environnement virtuel depuis la configuration")
        
        if "reinstall_python" in repair_actions:
            recommendations.append("Réinstaller Python dans l'environnement")
        
        if "install_pip" in repair_actions:
            recommendations.append("Installer pip avec: python -m ensurepip --upgrade")
        
        if "install_missing_packages" in repair_actions:
            recommendations.append("Installer les packages manquants depuis la configuration")
        
        if "reinstall_broken_packages" in repair_actions:
            recommendations.append("Réinstaller les packages cassés")
        
        if "fix_permissions" in repair_actions:
            recommendations.append("Corriger les permissions sur l'environnement")
        
        # Recommandations générales
        if any(issue["severity"] == "critical" for issue in report.get("issues", [])):
            recommendations.append("Effectuer une réparation automatique avec --fix")
        
        if report.get("checks", {}).get("updates_available"):
            recommendations.append("Mettre à jour les packages obsolètes")
        
        report["recommendations"] = recommendations
    
    def repair_environment(self, env_name: str, auto_fix: bool = True) -> Tuple[bool, List[str]]:
        """
        Répare un environnement virtuel basé sur le diagnostic.
        
        Args:
            env_name: Nom de l'environnement à réparer.
            auto_fix: Si True, applique automatiquement les corrections.
            
        Returns:
            Tuple contenant (succès, liste des actions effectuées).
        """
        actions = []
        
        try:
            # Effectuer d'abord un diagnostic complet
            diagnosis = self.diagnose_environment(env_name, full_check=True)
            
            if diagnosis["status"] == "healthy":
                return True, ["L'environnement est déjà en bonne santé"]
            
            # Obtenir les informations de l'environnement
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return False, ["Impossible d'obtenir les informations de l'environnement"]
            
            # Traiter les actions de réparation
            repair_actions = diagnosis.get("repair_actions", [])
            
            for action in repair_actions:
                if not auto_fix:
                    actions.append(f"Recommandation: {self._get_action_description(action)}")
                    continue
                
                success, message = self._execute_repair_action(action, env_name, env_info)
                if success:
                    actions.append(f"✓ {message}")
                else:
                    actions.append(f"✗ {message}")
            
            # Vérifier le résultat si des réparations ont été appliquées
            if auto_fix and any("✓" in action for action in actions):
                # Refaire un diagnostic rapide
                post_diagnosis = self.diagnose_environment(env_name, full_check=False)
                if post_diagnosis["status"] == "healthy":
                    actions.append("✓ Environnement réparé avec succès")
                    return True, actions
                else:
                    actions.append("⚠ Réparation partielle - certains problèmes persistent")
                    return False, actions
            
            return True, actions
            
        except Exception as e:
            logger.error(f"Erreur lors de la réparation de l'environnement {env_name}: {str(e)}")
            actions.append(f"✗ Erreur lors de la réparation: {str(e)}")
            return False, actions
    
    def _get_action_description(self, action: str) -> str:
        """Retourne une description lisible d'une action de réparation."""
        descriptions = {
            "recreate_environment": "Recréer l'environnement virtuel",
            "reinstall_python": "Réinstaller l'exécutable Python",
            "install_pip": "Installer pip",
            "repair_pip": "Réparer pip",
            "install_missing_packages": "Installer les packages manquants",
            "reinstall_broken_packages": "Réinstaller les packages cassés",
            "fix_permissions": "Corriger les permissions",
            "repair_structure": "Réparer la structure des répertoires",
            "repair_activation_script": "Réparer le script d'activation"
        }
        return descriptions.get(action, f"Exécuter l'action: {action}")
    
    def _execute_repair_action(self, action: str, env_name: str, env_info: Any) -> Tuple[bool, str]:
        """Exécute une action de réparation spécifique."""
        try:
            if action == "recreate_environment":
                return self._recreate_environment(env_name, env_info)
            elif action == "install_pip":
                return self._install_pip(env_name, env_info)
            elif action == "repair_pip":
                return self._repair_pip(env_name, env_info)
            elif action == "install_missing_packages":
                return self._install_missing_packages(env_name, env_info)
            elif action == "reinstall_broken_packages":
                return self._reinstall_broken_packages(env_name, env_info)
            elif action == "fix_permissions":
                return self._fix_permissions(env_info.path)
            else:
                return False, f"Action de réparation non implémentée: {action}"
                
        except Exception as e:
            return False, f"Erreur lors de l'exécution de l'action {action}: {str(e)}"
    
    def _recreate_environment(self, env_name: str, env_info: Any) -> Tuple[bool, str]:
        """Recrée un environnement virtuel."""
        try:
            # Sauvegarder les packages avant suppression
            packages_backup = env_info.packages if env_info.packages else []
            
            # Supprimer l'ancien environnement s'il existe
            if env_info.path.exists():
                shutil.rmtree(env_info.path)
            
            # Recréer l'environnement
            success, message = self.env_service.create_environment(
                env_name, env_info.python_version, env_info.path
            )
            
            if not success:
                return False, f"Échec de la recréation: {message}"
            
            # Réinstaller les packages si il y en avait
            if packages_backup:
                pkg_success, pkg_message = self.pkg_service.install_packages(env_name, packages_backup)
                if not pkg_success:
                    return False, f"Environnement recréé mais échec de réinstallation des packages: {pkg_message}"
            
            return True, "Environnement recréé avec succès"
            
        except Exception as e:
            return False, f"Erreur lors de la recréation: {str(e)}"
    
    def _install_pip(self, env_name: str, env_info: Any) -> Tuple[bool, str]:
        """Installe pip dans l'environnement."""
        try:
            python_exe = self.env_service.get_python_executable(env_name, env_info.path)
            if not python_exe:
                return False, "Exécutable Python non trouvé"
            
            # Essayer d'installer pip avec ensurepip
            result = subprocess.run([
                str(python_exe), "-m", "ensurepip", "--upgrade"
            ], capture_output=True, text=True, check=False, timeout=60)
            
            if result.returncode == 0:
                return True, "pip installé avec succès"
            else:
                return False, f"Échec de l'installation de pip: {result.stderr}"
                
        except Exception as e:
            return False, f"Erreur lors de l'installation de pip: {str(e)}"
    
    def _repair_pip(self, env_name: str, env_info: Any) -> Tuple[bool, str]:
        """Répare pip dans l'environnement."""
        try:
            # Essayer d'abord de réinstaller pip
            success, message = self._install_pip(env_name, env_info)
            if success:
                return True, "pip réparé avec succès"
            
            # Si ça échoue, essayer une approche alternative
            python_exe = self.env_service.get_python_executable(env_name, env_info.path)
            if python_exe:
                # Télécharger get-pip.py et l'exécuter
                import urllib.request
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    get_pip_path = Path(temp_dir) / "get-pip.py"
                    
                    try:
                        urllib.request.urlretrieve(
                            "https://bootstrap.pypa.io/get-pip.py", 
                            str(get_pip_path)
                        )
                        
                        result = subprocess.run([
                            str(python_exe), str(get_pip_path)
                        ], capture_output=True, text=True, check=False, timeout=120)
                        
                        if result.returncode == 0:
                            return True, "pip réparé avec get-pip.py"
                        else:
                            return False, f"Échec de la réparation avec get-pip.py: {result.stderr}"
                            
                    except Exception as e:
                        return False, f"Impossible de télécharger get-pip.py: {str(e)}"
            
            return False, message
            
        except Exception as e:
            return False, f"Erreur lors de la réparation de pip: {str(e)}"
    
    def _install_missing_packages(self, env_name: str, env_info: Any) -> Tuple[bool, str]:
        """Installe les packages manquants."""
        try:
            if not env_info.packages:
                return True, "Aucun package configuré"
            
            # Obtenir les packages installés
            installed_packages = self.pkg_service.list_installed_packages(env_name)
            installed_names = {pkg["name"].lower() for pkg in installed_packages}
            
            # Identifier les packages manquants
            missing_packages = []
            for pkg_spec in env_info.packages:
                pkg_name = pkg_spec.split('==')[0].split('>')[0].split('<')[0].strip().lower()
                if pkg_name not in installed_names:
                    missing_packages.append(pkg_spec)
            
            if not missing_packages:
                return True, "Tous les packages configurés sont déjà installés"
            
            # Installer les packages manquants
            success, message = self.pkg_service.install_packages(env_name, missing_packages)
            if success:
                return True, f"Packages manquants installés: {', '.join(missing_packages)}"
            else:
                return False, f"Échec de l'installation des packages manquants: {message}"
                
        except Exception as e:
            return False, f"Erreur lors de l'installation des packages manquants: {str(e)}"
    
    def _reinstall_broken_packages(self, env_name: str, env_info: Any) -> Tuple[bool, str]:
        """Réinstalle les packages cassés."""
        try:
            # Cette méthode nécessiterait une détection plus sophistiquée des packages cassés
            # Pour l'instant, on réinstalle tous les packages configurés
            if not env_info.packages:
                return True, "Aucun package à réinstaller"
            
            success, message = self.pkg_service.install_packages(
                env_name, env_info.packages, upgrade=True
            )
            
            if success:
                return True, "Packages réinstallés avec succès"
            else:
                return False, f"Échec de la réinstallation: {message}"
                
        except Exception as e:
            return False, f"Erreur lors de la réinstallation des packages: {str(e)}"
    
    def _fix_permissions(self, env_path: Path) -> Tuple[bool, str]:
        """Corrige les permissions sur l'environnement."""
        try:
            if not env_path.exists():
                return False, "L'environnement n'existe pas"
            
            # Corriger les permissions récursivement
            for root, dirs, files in os.walk(env_path):
                root_path = Path(root)
                
                # Définir les permissions pour les répertoires
                try:
                    root_path.chmod(0o755)
                except Exception:
                    pass
                
                # Définir les permissions pour les fichiers
                for file in files:
                    file_path = root_path / file
                    try:
                        if file_path.suffix in ['.exe', '.sh', ''] and 'bin' in str(file_path):
                            # Fichiers exécutables
                            file_path.chmod(0o755)
                        else:
                            # Fichiers normaux
                            file_path.chmod(0o644)
                    except Exception:
                        pass
            
            return True, "Permissions corrigées"
            
        except Exception as e:
            return False, f"Erreur lors de la correction des permissions: {str(e)}"
    
    def get_system_diagnosis(self) -> Dict[str, Any]:
        """
        Effectue un diagnostic complet du système.
        
        Returns:
            Rapport de diagnostic système.
        """
        try:
            report = {
                "diagnosed_at": datetime.now().isoformat(),
                "system_info": {},
                "python_info": {},
                "gestvenv_info": {},
                "environments_status": {},
                "cache_status": {},
                "issues": [],
                "warnings": [],
                "recommendations": []
            }
            
            # Informations système
            report["system_info"] = self.sys_service.get_system_info()
            
            # Informations Python
            report["python_info"] = {
                "current_version": self.sys_service.check_python_version("python"),
                "available_versions": self.sys_service.get_available_python_versions(),
                "default_command": self.config_manager.get_default_python()
            }
            
            # Informations GestVenv
            report["gestvenv_info"] = {
                "total_environments": len(self.config_manager.get_all_environments()),
                "active_environment": self.config_manager.get_active_environment(),
                "offline_mode": self.config_manager.get_setting("offline_mode", False),
                "cache_enabled": self.config_manager.get_setting("use_package_cache", True),
                "config_path": str(self.config_manager.config_path)
            }
            
            # Statut des environnements
            environments = self.config_manager.get_all_environments()
            healthy_count = 0
            broken_count = 0
            
            for env_name, env_info in environments.items():
                exists = self.env_service.check_environment_exists(env_info.path)
                if exists:
                    health = self.env_service.check_environment_health(env_name, env_info.path)
                    is_healthy = health.python_available and health.pip_available
                    if is_healthy:
                        healthy_count += 1
                    else:
                        broken_count += 1
                else:
                    broken_count += 1
            
            report["environments_status"] = {
                "total": len(environments),
                "healthy": healthy_count,
                "broken": broken_count
            }
            
            # Statut du cache
            try:
                cache_stats = self.cache_service.get_cache_stats()
                report["cache_status"] = cache_stats
            except Exception as e:
                report["warnings"].append(f"Impossible d'obtenir les statistiques du cache: {str(e)}")
            
            # Vérifications générales
            if broken_count > 0:
                report["issues"].append({
                    "type": "broken_environments",
                    "message": f"{broken_count} environnement(s) endommagé(s) détecté(s)",
                    "severity": "medium"
                })
                report["recommendations"].append("Exécuter un diagnostic individuel sur les environnements cassés")
            
            if not report["python_info"]["current_version"]:
                report["issues"].append({
                    "type": "no_python",
                    "message": "Aucune installation Python détectée",
                    "severity": "critical"
                })
                report["recommendations"].append("Installer Python sur le système")
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors du diagnostic système: {str(e)}")
            return {
                "diagnosed_at": datetime.now().isoformat(),
                "error": f"Erreur lors du diagnostic système: {str(e)}"
            }
    
    def verify_cache_integrity(self) -> Dict[str, Any]:
        """
        Vérifie l'intégrité du cache de packages.
        
        Returns:
            Rapport de vérification du cache.
        """
        try:
            report = {
                "verified_at": datetime.now().isoformat(),
                "status": "healthy",
                "total_packages": 0,
                "verified_packages": 0,
                "corrupted_packages": [],
                "missing_files": [],
                "orphaned_metadata": [],
                "issues": [],
                "warnings": [],
                "recommendations": []
            }
            
            # Obtenir les packages en cache
            available_packages = self.cache_service.get_available_packages()
            report["total_packages"] = sum(len(versions) for versions in available_packages.values())
            
            # Vérifier chaque package
            for package_name, versions in available_packages.items():
                for version in versions:
                    try:
                        # Vérifier si le package existe dans l'index
                        if (package_name in self.cache_service.index and 
                            "versions" in self.cache_service.index[package_name] and
                            version in self.cache_service.index[package_name]["versions"]):
                            
                            package_info = self.cache_service.index[package_name]["versions"][version]
                            package_path = self.cache_service.cache_dir / package_info["path"]
                            
                            # Vérifier l'existence du fichier
                            if not package_path.exists():
                                report["missing_files"].append({
                                    "package": f"{package_name}-{version}",
                                    "expected_path": str(package_path)
                                })
                                continue
                            
                            # Vérifier l'intégrité du fichier
                            expected_hash = package_info.get("hash")
                            if expected_hash:
                                actual_hash = self.cache_service._calculate_file_hash(package_path)
                                if actual_hash != expected_hash:
                                    report["corrupted_packages"].append({
                                        "package": f"{package_name}-{version}",
                                        "path": str(package_path),
                                        "expected_hash": expected_hash,
                                        "actual_hash": actual_hash
                                    })
                                    continue
                            
                            report["verified_packages"] += 1
                        else:
                            report["orphaned_metadata"].append(f"{package_name}-{version}")
                            
                    except Exception as e:
                        report["warnings"].append(f"Erreur lors de la vérification de {package_name}-{version}: {str(e)}")
            
            # Analyser les résultats
            if report["corrupted_packages"]:
                report["status"] = "corrupted"
                report["issues"].append({
                    "type": "corrupted_packages",
                    "count": len(report["corrupted_packages"]),
                    "message": f"{len(report['corrupted_packages'])} package(s) corrompu(s) détecté(s)"
                })
                report["recommendations"].append("Supprimer et re-télécharger les packages corrompus")
            
            if report["missing_files"]:
                report["status"] = "incomplete" if report["status"] == "healthy" else report["status"]
                report["issues"].append({
                    "type": "missing_files",
                    "count": len(report["missing_files"]),
                    "message": f"{len(report['missing_files'])} fichier(s) manquant(s)"
                })
                report["recommendations"].append("Nettoyer les métadonnées orphelines")
            
            if report["orphaned_metadata"]:
                report["warnings"].append({
                    "type": "orphaned_metadata",
                    "count": len(report["orphaned_metadata"]),
                    "message": f"{len(report['orphaned_metadata'])} métadonnée(s) orpheline(s)"
                })
                report["recommendations"].append("Nettoyer les métadonnées orphelines")
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du cache: {str(e)}")
            return {
                "verified_at": datetime.now().isoformat(),
                "status": "error",
                "error": f"Erreur lors de la vérification: {str(e)}"
            }
    
    def _create_error_report(self, env_name: str, message: str, error_type: str) -> Dict[str, Any]:
        """Crée un rapport d'erreur standardisé."""
        return {
            "environment": env_name,
            "diagnosed_at": datetime.now().isoformat(),
            "status": "error",
            "error_type": error_type,
            "message": message,
            "issues": [{
                "type": error_type,
                "severity": "critical",
                "message": message
            }],
            "warnings": [],
            "info": [],
            "checks": {},
            "recommendations": ["Vérifier la configuration et l'existence de l'environnement"],
            "repair_actions": []
        }
    
    def _log_diagnostic_start(self, env_name: str) -> None:
        """Enregistre le début d'un diagnostic."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] DIAGNOSTIC START: {env_name}\n"
        
        log_file = self.logs_dir / "diagnostic.log"
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass  # Ignore les erreurs de logging
    
    def _log_diagnostic_end(self, env_name: str, status: str) -> None:
        """Enregistre la fin d'un diagnostic."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] DIAGNOSTIC END: {env_name} - Status: {status}\n"
        
        log_file = self.logs_dir / "diagnostic.log"
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass  # Ignore les erreurs de logging
    
    def get_diagnostic_logs(self, env_name: Optional[str] = None, 
                          days: int = 7) -> List[Dict[str, Any]]:
        """
        Récupère les logs de diagnostic.
        
        Args:
            env_name: Nom de l'environnement (optionnel, tous si None).
            days: Nombre de jours de logs à récupérer.
            
        Returns:
            Liste des entrées de log.
        """
        logs = []
        log_file = self.logs_dir / "diagnostic.log"
        
        if not log_file.exists():
            return logs
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parser la ligne de log
                    if line.startswith('[') and ']' in line:
                        timestamp_end = line.find(']')
                        timestamp_str = line[1:timestamp_end]
                        content = line[timestamp_end + 2:]
                        
                        try:
                            log_time = datetime.fromisoformat(timestamp_str)
                            if log_time < cutoff_date:
                                continue
                            
                            # Filtrer par environnement si spécifié
                            if env_name and env_name not in content:
                                continue
                            
                            logs.append({
                                "timestamp": timestamp_str,
                                "content": content,
                                "environment": self._extract_env_name_from_log(content)
                            })
                            
                        except ValueError:
                            continue
            
            return sorted(logs, key=lambda x: x["timestamp"], reverse=True)
            
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des logs: {str(e)}")
            return []
    
    def _extract_env_name_from_log(self, content: str) -> Optional[str]:
        """Extrait le nom d'environnement d'une ligne de log."""
        if "DIAGNOSTIC START:" in content:
            return content.split("DIAGNOSTIC START:")[1].strip()
        elif "DIAGNOSTIC END:" in content:
            parts = content.split("DIAGNOSTIC END:")[1].split(" - ")
            if parts:
                return parts[0].strip()
        return None
    
    def export_diagnostic_logs(self, output_path: str, env_name: Optional[str] = None) -> bool:
        """
        Exporte les logs de diagnostic vers un fichier.
        
        Args:
            output_path: Chemin du fichier de sortie.
            env_name: Nom de l'environnement (optionnel).
            
        Returns:
            True si l'export réussit, False sinon.
        """
        try:
            logs = self.get_diagnostic_logs(env_name, days=30)
            
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "environment_filter": env_name,
                "total_entries": len(logs),
                "logs": logs
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export des logs: {str(e)}")
            return False