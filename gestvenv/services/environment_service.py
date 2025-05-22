"""
Service pour la gestion des environnements virtuels.

Ce module fournit les fonctionnalités pour créer, supprimer et gérer
les environnements virtuels Python et leurs configurations.
"""

import os
import re
import json
import platform
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set

from ..core.models import EnvironmentHealth

# Configuration du logger
logger = logging.getLogger(__name__)

class EnvironmentService:
    """Service pour les opérations sur les environnements virtuels."""
    
    def __init__(self) -> None:
        """Initialise le service d'environnement."""
        self.system = platform.system().lower()  # 'windows', 'linux', 'darwin' (macOS)
    
    def validate_environment_name(self, name: str) -> Tuple[bool, str]:
        """
        Valide un nom d'environnement virtuel.
        
        Args:
            name: Nom d'environnement à valider.
            
        Returns:
            Tuple contenant (validité, message d'erreur si invalide).
        """
        if not name:
            return False, "Le nom d'environnement ne peut pas être vide"
        
        if len(name) > 50:
            return False, "Le nom d'environnement est trop long (maximum 50 caractères)"
        
        # Vérifier que le nom contient uniquement des caractères alphanumériques, tirets et soulignés
        pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
        if not pattern.match(name):
            return False, "Le nom d'environnement ne peut contenir que des lettres, chiffres, tirets et soulignés"
        
        # Noms réservés à éviter
        reserved_names = ["system", "admin", "config", "test", "venv", "env", "environment"]
        if name.lower() in reserved_names:
            return False, f"'{name}' est un nom réservé. Veuillez choisir un autre nom"
        
        return True, ""
    
    def validate_python_version(self, version: str) -> Tuple[bool, str]:
        """
        Valide une spécification de version Python.
        
        Args:
            version: Version Python à valider (ex: "python3.9", "python", "3.10").
            
        Returns:
            Tuple contenant (validité, message d'erreur si invalide).
        """
        if not version:
            return True, ""  # Version vide est valide (utilise la version par défaut)
        
        # Si le format est simplement "python" ou "python3"
        if version in ["python", "python3"]:
            return True, ""
        
        # Si le format est "pythonX.Y" ou "python3.X"
        match = re.match(r'^python(?:3\.(\d+))?$', version)
        if match:
            return True, ""
        
        # Si le format est simplement "3.X"
        match = re.match(r'^3\.(\d+)$', version)
        if match:
            minor_version = int(match.group(1))
            if minor_version < 6:
                return False, "GestVenv nécessite Python 3.6 ou supérieur"
            return True, ""
        
        # Si sous Windows, vérifier le format "py -3.X"
        if self.system == "windows":
            match = re.match(r'^py -3\.(\d+)$', version)
            if match:
                minor_version = int(match.group(1))
                if minor_version < 6:
                    return False, "GestVenv nécessite Python 3.6 ou supérieur"
                return True, ""
        
        return False, "Format de version Python invalide"
    
    def validate_packages_list(self, packages: str) -> Tuple[bool, List[str], str]:
        """
        Valide une liste de packages séparés par des virgules.
        
        Args:
            packages: Chaîne de packages séparés par des virgules.
            
        Returns:
            Tuple contenant (validité, liste de packages, message d'erreur si invalide).
        """
        if not packages:
            return False, [], "La liste de packages ne peut pas être vide"
        
        # Séparer la chaîne en liste de packages
        package_list = [pkg.strip() for pkg in packages.split(",")]
        
        # Valider chaque package individuellement
        invalid_packages = []
        for pkg in package_list:
            valid, message = self._validate_package_name(pkg)
            if not valid:
                invalid_packages.append((pkg, message))
        
        if invalid_packages:
            error_message = "Packages invalides: " + ", ".join([f"{pkg} ({msg})" for pkg, msg in invalid_packages])
            return False, [], error_message
        
        return True, package_list, ""
    
    def _validate_package_name(self, package: str) -> Tuple[bool, str]:
        """
        Valide un nom de package Python, avec éventuellement une version spécifiée.
        
        Args:
            package: Nom du package à valider (ex: "flask", "flask==2.0.1").
            
        Returns:
            Tuple contenant (validité, message d'erreur si invalide).
        """
        if not package:
            return False, "Le nom du package ne peut pas être vide"
        
        # Format de base pour les noms de packages
        # Ce regex permet les formats comme "flask", "flask==2.0.1", "flask>=2.0.1", "flask[extra]"
        pattern = re.compile(r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])(\[[a-zA-Z0-9._-]+\])?((==|>=|<=|>|<|!=)[0-9]+(\.[0-9]+)*)?$')
        
        if not pattern.match(package):
            # Vérifier si c'est un chemin local ou une URL Git
            if package.startswith(("git+", "http://", "https://", "./", "/", "~/")):
                return True, ""
            return False, f"Format de package invalide: {package}"
        
        return True, ""
    
    def validate_output_format(self, format_str: str) -> Tuple[bool, str]:
        """
        Valide un format de sortie spécifié.
        
        Args:
            format_str: Format de sortie à valider.
            
        Returns:
            Tuple contenant (validité, message d'erreur si invalide).
        """
        valid_formats = ["json", "requirements"]
        
        if not format_str:
            return False, "Le format de sortie ne peut pas être vide"
        
        if format_str.lower() not in valid_formats:
            return False, f"Format de sortie invalide. Formats valides: {', '.join(valid_formats)}"
        
        return True, ""
    
    def validate_metadata(self, metadata_str: str) -> Tuple[bool, Dict[str, str], str]:
        """
        Valide une chaîne de métadonnées au format "clé1:valeur1,clé2:valeur2".
        
        Args:
            metadata_str: Chaîne de métadonnées à valider.
            
        Returns:
            Tuple contenant (validité, dictionnaire de métadonnées, message d'erreur si invalide).
        """
        if not metadata_str:
            return True, {}, ""  # Chaîne vide est valide (pas de métadonnées)
        
        metadata = {}
        
        try:
            # Séparer les paires clé:valeur
            pairs = metadata_str.split(",")
            
            for pair in pairs:
                if ":" not in pair:
                    return False, {}, f"Format de métadonnées invalide (manque ':') : {pair}"
                
                key, value = pair.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                if not key:
                    return False, {}, "Les clés de métadonnées ne peuvent pas être vides"
                
                metadata[key] = value
            
            return True, metadata, ""
        except Exception as e:
            return False, {}, f"Erreur lors de la validation des métadonnées: {str(e)}"
    
    def resolve_path(self, path_str: str) -> Path:
        """
        Résout un chemin relatif ou absolu.
        
        Args:
            path_str: Chaîne de caractères représentant un chemin.
            
        Returns:
            Path: Chemin absolu résolu.
        """
        path = Path(path_str)
        
        # Résoudre les chemins relatifs aux utilisateurs (~)
        if path_str.startswith("~"):
            path = Path(os.path.expanduser(path_str))
        
        # Rendre absolu si relatif
        if not path.is_absolute():
            path = Path.cwd() / path
        
        return path.resolve()
    
    def get_app_data_dir(self) -> Path:
        """
        Obtient le répertoire d'application approprié selon le système d'exploitation.
        
        Returns:
            Path: Chemin vers le répertoire d'application.
        """
        if self.system == "windows":
            app_data = os.environ.get("APPDATA")
            return Path(app_data) / "GestVenv"
        elif self.system == "darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "GestVenv"
        else:  # Linux et autres systèmes Unix-like
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config_home:
                return Path(xdg_config_home) / "gestvenv"
            else:
                return Path.home() / ".config" / "gestvenv"
    
    def get_default_venv_dir(self) -> Path:
        """
        Obtient le répertoire par défaut pour les environnements virtuels.
        
        Returns:
            Path: Chemin vers le répertoire des environnements virtuels.
        """
        venv_dir = self.get_app_data_dir() / "environments"
        
        # Création du répertoire si nécessaire
        venv_dir.mkdir(parents=True, exist_ok=True)
        
        return venv_dir
    
    def get_environment_path(self, name: str, custom_path: Optional[str] = None) -> Path:
        """
        Détermine le chemin pour un environnement virtuel.
        
        Args:
            name: Nom de l'environnement.
            custom_path: Chemin personnalisé optionnel.
            
        Returns:
            Path: Chemin vers l'environnement virtuel.
        """
        if custom_path:
            return self.resolve_path(custom_path)
        
        return self.get_default_venv_dir() / name
    
    def get_python_executable(self, name: str, env_path: Path) -> Optional[Path]:
        """
        Obtient le chemin vers l'exécutable Python d'un environnement virtuel.
        
        Args:
            name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Optional[Path]: Chemin vers l'exécutable Python s'il existe, None sinon.
        """
        if not env_path.exists():
            logger.warning(f"L'environnement '{name}' n'existe pas à {env_path}")
            return None
        
        if self.system == "windows":
            python_path = env_path / "Scripts" / "python.exe"
        else:  # macOS et Linux
            python_path = env_path / "bin" / "python"
        
        if python_path.exists():
            return python_path
        
        logger.warning(f"Exécutable Python non trouvé pour l'environnement '{name}'")
        return None
    
    def get_pip_executable(self, name: str, env_path: Path) -> Optional[Path]:
        """
        Obtient le chemin vers l'exécutable pip d'un environnement virtuel.
        
        Args:
            name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Optional[Path]: Chemin vers l'exécutable pip s'il existe, None sinon.
        """
        if not env_path.exists():
            logger.warning(f"L'environnement '{name}' n'existe pas à {env_path}")
            return None
        
        if self.system == "windows":
            pip_path = env_path / "Scripts" / "pip.exe"
        else:  # macOS et Linux
            pip_path = env_path / "bin" / "pip"
        
        if pip_path.exists():
            return pip_path
        
        logger.warning(f"Exécutable pip non trouvé pour l'environnement '{name}'")
        return None
    
    def get_activation_script_path(self, name: str, env_path: Path) -> Optional[Path]:
        """
        Obtient le chemin vers le script d'activation d'un environnement virtuel.
        
        Args:
            name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Optional[Path]: Chemin vers le script d'activation s'il existe, None sinon.
        """
        if not env_path.exists():
            logger.warning(f"L'environnement '{name}' n'existe pas à {env_path}")
            return None
        
        if self.system == "windows":
            activate_path = env_path / "Scripts" / "activate.bat"
        else:  # macOS et Linux
            activate_path = env_path / "bin" / "activate"
        
        if activate_path.exists():
            return activate_path
        
        logger.warning(f"Script d'activation non trouvé pour l'environnement '{name}'")
        return None
    
    def create_environment(self, name: str, python_cmd: str, env_path: Path) -> Tuple[bool, str]:
        """
        Crée un nouvel environnement virtuel.
        
        Args:
            name: Nom de l'environnement.
            python_cmd: Commande Python à utiliser.
            env_path: Chemin où créer l'environnement.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Vérifier si l'environnement existe déjà
        if env_path.exists():
            logger.error(f"L'environnement '{name}' existe déjà à {env_path}")
            return False, f"L'environnement '{name}' existe déjà à {env_path}"
        
        # Créer le répertoire parent si nécessaire
        env_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Créer l'environnement en utilisant le module venv de Python
            import subprocess
            
            cmd = [python_cmd, "-m", "venv", str(env_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.warning(f"Échec de la création avec venv: {result.stderr}")
                
                # Essayer avec virtualenv
                logger.info("Tentative avec virtualenv...")
                
                # Vérifier si virtualenv est installé
                check_cmd = [python_cmd, "-m", "pip", "show", "virtualenv"]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True, shell=False, check=False)
                
                if check_result.returncode != 0:
                    # Essayer d'installer virtualenv
                    logger.info("Installation de virtualenv...")
                    install_cmd = [python_cmd, "-m", "pip", "install", "virtualenv"]
                    install_result = subprocess.run(install_cmd, capture_output=True, text=True, check=False)
                    
                    if install_result.returncode != 0:
                        logger.error("Impossible d'installer virtualenv")
                        return False, "Impossible de créer l'environnement virtuel ou d'installer virtualenv"
                
                # Créer l'environnement avec virtualenv
                venv_cmd = [python_cmd, "-m", "virtualenv", str(env_path)]
                venv_result = subprocess.run(venv_cmd, capture_output=True, text=True, shell=False, check=False)
                
                if venv_result.returncode != 0:
                    logger.error(f"Échec de la création avec virtualenv: {venv_result.stderr}")
                    return False, f"Échec de la création de l'environnement virtuel: {venv_result.stderr}"
            
            logger.info(f"Environnement virtuel '{name}' créé avec succès à {env_path}")
            return True, f"Environnement virtuel '{name}' créé avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'environnement: {str(e)}")
            
            # Nettoyer si nécessaire
            if env_path.exists():
                try:
                    shutil.rmtree(env_path)
                except Exception as cleanup_error:
                    logger.error(f"Erreur lors du nettoyage de l'environnement: {str(cleanup_error)}")
            
            return False, f"Erreur lors de la création de l'environnement: {str(e)}"
    
    def delete_environment(self, env_path: Path) -> Tuple[bool, str]:
        """
        Supprime un environnement virtuel.
        
        Args:
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Tuple contenant (succès, message).
        """
        if not env_path.exists():
            logger.warning(f"L'environnement à {env_path} n'existe pas")
            return True, "L'environnement n'existe pas (déjà supprimé)"
        
        try:
            # Suppression récursive du répertoire de l'environnement
            shutil.rmtree(env_path)
            logger.info(f"Environnement supprimé avec succès: {env_path}")
            return True, "Environnement supprimé avec succès"
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'environnement: {str(e)}")
            return False, f"Erreur lors de la suppression de l'environnement: {str(e)}"
    
    def check_environment_exists(self, env_path: Path) -> bool:
        """
        Vérifie si un environnement virtuel existe à l'emplacement spécifié.
        
        Args:
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            bool: True si l'environnement existe, False sinon.
        """
        if not env_path.exists():
            return False
        
        # Vérifier la présence du fichier de configuration de l'environnement virtuel
        pyvenv_cfg = env_path / "pyvenv.cfg"
        if pyvenv_cfg.exists():
            return True
        
        # Vérifier la présence d'indicateurs alternatifs selon le système
        if self.system == "windows":
            python_exe = env_path / "Scripts" / "python.exe"
            return python_exe.exists()
        else:
            python_bin = env_path / "bin" / "python"
            return python_bin.exists()
    
    def check_environment_health(self, name: str, env_path: Path) -> EnvironmentHealth:
        """
        Vérifie l'état de santé d'un environnement virtuel.
        
        Args:
            name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            EnvironmentHealth: État de santé de l'environnement.
        """
        health = EnvironmentHealth()
        
        # Vérifier si l'environnement existe
        health.exists = env_path.exists()
        if not health.exists:
            return health
        
        # Vérifier si Python est disponible
        python_exe = self.get_python_executable(name, env_path)
        health.python_available = python_exe is not None and python_exe.exists()
        
        # Vérifier si pip est disponible
        pip_exe = self.get_pip_executable(name, env_path)
        health.pip_available = pip_exe is not None and pip_exe.exists()
        
        # Vérifier si le script d'activation existe
        activation_script = self.get_activation_script_path(name, env_path)
        health.activation_script_exists = activation_script is not None and activation_script.exists()
        
        return health
    
    def is_safe_to_delete(self, name: str, env_path: Path) -> Tuple[bool, str]:
        """
        Vérifie s'il est sécuritaire de supprimer un environnement.
        
        Args:
            name: Nom de l'environnement.
            env_path: Chemin vers l'environnement.
            
        Returns:
            Tuple contenant (sécurité, message d'avertissement si non sécuritaire).
        """
        # Vérifier si l'environnement existe
        if not env_path.exists():
            return False, f"L'environnement '{name}' n'existe pas à {env_path}"
        
        # Vérifier si le chemin est sécuritaire (ne contient pas de dossiers système)
        system_directories = [
            os.path.expanduser("~"),
            os.path.expanduser("~/Documents"),
            "/",
            "/usr",
            "/bin",
            "/etc",
            "/var",
            "/home",
            "/tmp",
            "C:\\",
            "C:\\Windows",
            "C:\\Program Files",
            "C:\\Users"
        ]
        
        for sys_dir in system_directories:
            try:
                # Convertir les deux chemins en chemins absolus normalisés pour la comparaison
                abs_sys_dir = Path(sys_dir).resolve()
                abs_env_path = env_path.resolve()
                
                # Vérifier si le chemin est identique ou est un sous-répertoire
                if abs_env_path == abs_sys_dir or str(abs_env_path).startswith(str(abs_sys_dir) + os.sep):
                    # Vérifier si c'est bien un sous-répertoire spécifique à GestVenv
                    if "gestvenv" in str(abs_env_path).lower() or "venv" in str(abs_env_path).lower():
                        continue  # C'est probablement sécuritaire
                    
                    return False, f"Suppression refusée: '{env_path}' semble être un dossier système ou contenu dans un dossier système"
            except Exception:
                # En cas d'erreur dans la résolution des chemins, continuer
                continue
        
        # Vérifier si le chemin ressemble à un environnement virtuel
        venv_indicators = ["bin/python", "bin/activate", "Scripts/python.exe", "Scripts/activate.bat", "pyvenv.cfg"]
        
        any_indicator_found = False
        for indicator in venv_indicators:
            indicator_path = env_path / indicator.replace("/", os.sep)
            if indicator_path.exists():
                any_indicator_found = True
                break
        
        if not any_indicator_found:
            return False, f"Suppression refusée: '{env_path}' ne semble pas être un environnement virtuel"
        
        return True, ""
    
    def get_export_directory(self) -> Path:
        """
        Obtient le répertoire par défaut pour l'exportation des configurations.
        
        Returns:
            Path: Chemin vers le répertoire d'exportation.
        """
        export_dir = self.get_app_data_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir
    
    def get_json_output_path(self, env_name: str) -> Path:
        """
        Obtient le chemin par défaut pour l'exportation JSON d'un environnement.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            
        Returns:
            Path: Chemin par défaut pour l'exportation JSON.
        """
        export_dir = self.get_export_directory()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{env_name}_{timestamp}.json"
        return export_dir / filename
    
    def get_requirements_output_path(self, env_name: str, custom_path: Optional[str] = None) -> Path:
        """
        Obtient le chemin pour l'exportation requirements.txt d'un environnement.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            custom_path: Chemin personnalisé optionnel.
            
        Returns:
            Path: Chemin pour l'exportation requirements.txt.
        """
        if custom_path:
            return self.resolve_path(custom_path)
        
        export_dir = self.get_export_directory()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{env_name}_requirements_{timestamp}.txt"
        return export_dir / filename