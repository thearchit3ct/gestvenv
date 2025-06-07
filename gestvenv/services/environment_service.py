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
import subprocess
import logging
from datetime import datetime
from pathlib import Path
import tempfile
import time
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
            return False, "Le nom d'environnement ne peut contenir que des caractères alphanumériques, tirets et underscores"
        
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
                        return False, "Échec: Impossible de créer l'environnement virtuel ou d'installer virtualenv"
                
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
                if abs_env_path == abs_sys_dir:
                    # Vérifier si c'est un sous-répertoire GestVenv
                    if "gestvenv" in str(abs_env_path).lower() or "environments" in str(abs_env_path).lower():
                        continue  # C'est probablement sécuritaire
                    return False, f"Suppression refusée: '{env_path}' est un dossier système"

                # Pour les sous-répertoires
                if str(abs_env_path).startswith(str(abs_sys_dir) + os.sep):
                    # Vérifier le chemin relatif depuis le répertoire système
                    relative_path = abs_env_path.relative_to(abs_sys_dir)
                    # Si c'est dans un sous-dossier gestvenv/environments, c'est OK
                    path_parts = relative_path.parts
                    if any("gestvenv" in part.lower() or "environments" in part.lower() for part in path_parts):
                        continue
                    return False, f"Suppression refusée: '{env_path}' est dans un dossier système"
            except Exception:
                # En cas d'erreur dans la résolution des chemins, continuer
                continue
        
        # Vérifier si le chemin ressemble à un environnement virtuel
        venv_indicators = ["bin/python", "bin/activate", "Scripts/python.exe", "Scripts/activate.bat", "pyvenv.cfg"]
        
        venv_found = False
        for indicator in venv_indicators:
            indicator_path = env_path / indicator.replace("/", os.sep)
            if indicator_path.exists():
                venv_found = True
                break
            
        if not venv_found:
            return False, f"Suppression refusée: '{env_path}' ne semble pas être un environnement virtuel"
        
        # Vérifier que ce n'est pas un répertoire système
        system_directories = [
            "/", "/usr", "/bin", "/etc", "/var", "/home", "/tmp",
            "C:\\", "C:\\Windows", "C:\\Program Files", "C:\\Users"
        ]
        
        abs_env_path = env_path.resolve()
        for sys_dir in system_directories:
            try:
                abs_sys_dir = Path(sys_dir).resolve()
                if abs_env_path == abs_sys_dir:
                    return False, f"Suppression refusée: '{env_path}' est un dossier système"
            except Exception:
                continue
            
        return True, ""
    
    def get_environment_metadata(self, env_path: Path) -> Dict[str, Any]:
        """
        Récupère les métadonnées d'un environnement.

        Args:
            env_path: Chemin de l'environnement

        Returns:
            Dict: Métadonnées de l'environnement
        """
        metadata_file = env_path / ".gestvenv_metadata.json"

        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Erreur lecture métadonnées {env_path}: {e}")

        # Métadonnées par défaut
        return {
            "created_at": datetime.now().isoformat(),
            "python_version": "unknown",
            "temporary": False
        }

    def update_environment_metadata(self, env_path: Path, metadata: Dict[str, Any]) -> None:
        """
        Met à jour les métadonnées d'un environnement.

        Args:
            env_path: Chemin de l'environnement
            metadata: Métadonnées à ajouter/mettre à jour
        """
        metadata_file = env_path / ".gestvenv_metadata.json"

        # Charger les métadonnées existantes
        existing_metadata = self.get_environment_metadata(env_path)

        # Fusionner avec les nouvelles
        existing_metadata.update(metadata)
        existing_metadata["updated_at"] = datetime.now().isoformat()

        # Sauvegarder
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(existing_metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde métadonnées {env_path}: {e}")

    def get_environment_size(self, env_path: Path) -> Dict[str, int]:
        """
        Calcule la taille d'un environnement.

        Args:
            env_path: Chemin de l'environnement

        Returns:
            Dict: Taille en octets (total, lib, bin, etc.)
        """
        size_info = {"total": 0, "lib": 0, "bin": 0, "include": 0, "other": 0}

        try:
            for root, dirs, files in os.walk(env_path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        file_size = file_path.stat().st_size
                        size_info["total"] += file_size

                        # Catégoriser par dossier
                        rel_path = file_path.relative_to(env_path)
                        if rel_path.parts[0] in ["lib", "Lib"]:
                            size_info["lib"] += file_size
                        elif rel_path.parts[0] in ["bin", "Scripts"]:
                            size_info["bin"] += file_size
                        elif rel_path.parts[0] in ["include", "Include"]:
                            size_info["include"] += file_size
                        else:
                            size_info["other"] += file_size
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Erreur calcul taille {env_path}: {e}")

        return size_info

    def export_environment_info(self, name: str, env_path: Path, 
                               include_packages: bool = True) -> Dict[str, Any]:
        """
        Exporte les informations complètes d'un environnement.

        Args:
            name: Nom de l'environnement
            env_path: Chemin de l'environnement
            include_packages: Si True, inclut la liste des packages

        Returns:
            Dict: Informations complètes de l'environnement
        """
        info = {
            "name": name,
            "path": str(env_path),
            "exported_at": datetime.now().isoformat(),
            "exists": env_path.exists(),
            "metadata": self.get_environment_metadata(env_path),
            "health": self.check_environment_health(name, env_path).to_dict(),
            "size": self.get_environment_size(env_path),
            "performance": {"python_version": "unknown"}
        }

        # Ajouter la version Python si possible
        python_exe = self.get_python_executable(name, env_path)
        if python_exe and python_exe.exists():
            try:
                result = subprocess.run([str(python_exe), "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info["performance"]["python_version"] = result.stdout.strip()
            except Exception:
                pass
            
        # Ajouter les packages si demandé
        if include_packages and info["health"]["pip_available"]:
            try:
                pip_exe = self.get_pip_executable(name, env_path)
                if pip_exe:
                    result = subprocess.run([str(pip_exe), "list", "--format=json"], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        info["packages"] = json.loads(result.stdout)
            except Exception:
                info["packages"] = []

        return info
    
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
    
    def create_temporary_environment(self, name: str, python_cmd: str, 
                                   lifetime: Optional[int] = None,
                                   auto_cleanup: bool = True) -> Tuple[bool, str, Path]:
        """
        Crée un environnement virtuel temporaire.
        
        Args:
            name: Nom de l'environnement temporaire
            python_cmd: Commande Python à utiliser
            lifetime: Durée de vie en minutes (None = jusqu'à la fermeture de session)
            auto_cleanup: Si True, programme un nettoyage automatique
            
        Returns:
            Tuple contenant (succès, message, chemin)
        """
        try:
            # Créer un nom unique pour l'environnement temporaire
            temp_name: str = f"temp_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            temp_dir: Path = Path(tempfile.gettempdir()) / "gestvenv_temp" / temp_name
            
            # Créer l'environnement
            success, message = self.create_environment(temp_name, python_cmd, temp_dir)
            if not success:
                return False, message, temp_dir
            
            # Marquer comme temporaire dans les métadonnées
            temp_metadata = {
                "temporary": True,
                "lifetime_minutes": lifetime,
                "auto_cleanup": auto_cleanup,
                "expires_at": (datetime.now() + timedelta(minutes=lifetime)).isoformat() if lifetime else None,
                "session_id": os.getpid()  # ID de session pour le nettoyage
            }
            
            self.update_environment_metadata(temp_dir, temp_metadata)
            
            # Programmer le nettoyage automatique si demandé
            if auto_cleanup and lifetime:
                self._schedule_cleanup(temp_dir, lifetime)
            
            logger.info(f"Environnement temporaire '{temp_name}' créé")
            return True, f"Environnement temporaire créé: {temp_name}", temp_dir
            
        except Exception as e:
            logger.error(f"Erreur création environnement temporaire: {e}")
            return False, f"Erreur: {e}", Path()
    
    def _schedule_cleanup(self, env_path: Path, lifetime_minutes: int) -> None:
        """
        Programme le nettoyage automatique d'un environnement temporaire.
        
        Args:
            env_path: Chemin de l'environnement
            lifetime_minutes: Durée de vie en minutes
        """
        try:
            import threading
            
            def cleanup_after_delay() -> None:
                time.sleep(lifetime_minutes * 60)
                try:
                    if env_path.exists():
                        shutil.rmtree(env_path)
                        logger.info(f"Environnement temporaire nettoyé: {env_path}")
                except Exception as e:
                    logger.error(f"Erreur nettoyage automatique {env_path}: {e}")
            
            cleanup_thread = threading.Thread(target=cleanup_after_delay, daemon=True)
            cleanup_thread.start()
            
        except Exception as e:
            logger.warning(f"Impossible de programmer le nettoyage: {e}")
    
    def cleanup_temporary_environments(self) -> Tuple[int, List[str]]:
        """
        Nettoie tous les environnements temporaires expirés.
        
        Returns:
            Tuple: (nombre d'environnements nettoyés, liste des messages)
        """
        import time
        import tempfile
        from datetime import datetime, timedelta
        cleaned_count = 0
        messages = []
        
        try:
            temp_base_dir = Path(tempfile.gettempdir()) / "gestvenv_temp"
            
            if not temp_base_dir.exists():
                return 0, ["Aucun répertoire temporaire trouvé"]
            
            current_time = datetime.now()
            
            for env_dir in temp_base_dir.iterdir():
                if not env_dir.is_dir():
                    continue
                
                try:
                    metadata = self.get_environment_metadata(env_dir)
                    
                    # Vérifier si l'environnement est temporaire
                    if not metadata.get("temporary", False):
                        continue
                    
                    # Vérifier l'expiration
                    expires_at_str = metadata.get("expires_at")
                    if expires_at_str:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if current_time > expires_at:
                            shutil.rmtree(env_dir)
                            cleaned_count += 1
                            messages.append(f"Environnement temporaire expiré nettoyé: {env_dir.name}")
                    
                    # Vérifier si la session est toujours active
                    session_id = metadata.get("session_id")
                    if session_id and not self._is_process_alive(session_id):
                        shutil.rmtree(env_dir)
                        cleaned_count += 1
                        messages.append(f"Environnement temporaire orphelin nettoyé: {env_dir.name}")
                        
                except Exception as e:
                    messages.append(f"Erreur nettoyage {env_dir.name}: {e}")
                    continue
            
        except Exception as e:
            messages.append(f"Erreur générale nettoyage temporaires: {e}")
        
        return cleaned_count, messages
    
    def _is_process_alive(self, pid: int) -> bool:
        """Vérifie si un processus est encore actif."""
        try:
            import psutil
            return psutil.pid_exists(pid)
        except Exception:
            # Fallback sans psutil
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False
    
    def export_environment_to_yaml(self, name: str, env_path: Path, 
                                  output_path: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Exporte un environnement au format YAML.
        
        Args:
            name: Nom de l'environnement
            env_path: Chemin de l'environnement
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Tuple: (succès, chemin du fichier ou message d'erreur)
        """
        try:
            # Collecter les informations
            info = self.export_environment_info(name, env_path, include_packages=True)
            
            # Structure YAML
            yaml_data = {
                'environment': {
                    'name': info['name'],
                    'description': info['metadata'].get('description', ''),
                    'python_version': info['performance'].get('python_version', ''),
                    'created_at': info['metadata'].get('created_at', ''),
                    'exported_at': info['exported_at']
                },
                'packages': [
                    {
                        'name': pkg.get('name', ''),
                        'version': pkg.get('version', '')
                    }
                    for pkg in info.get('packages', [])
                ],
                'metadata': info['metadata'],
                'health': info['health'],
                'size': info['size']
            }
            
            # Générer le contenu YAML
            yaml_content = self._dict_to_yaml(yaml_data)
            
            # Déterminer le chemin de sortie
            if not output_path:
                output_path = self.get_export_directory() / f"{name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            
            # Écrire le fichier
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(yaml_content, encoding='utf-8')
            
            return True, str(output_path)
            
        except Exception as e:
            logger.error(f"Erreur export YAML {name}: {e}")
            return False, f"Erreur export YAML: {e}"
    
    def _dict_to_yaml(self, data: Dict[str, Any], indent: int = 0) -> str:
        """
        Convertit un dictionnaire en format YAML simple.
        
        Args:
            data: Dictionnaire à convertir
            indent: Niveau d'indentation
            
        Returns:
            str: Contenu YAML
        """
        yaml_lines = []
        indent_str = "  " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                yaml_lines.append(f"{indent_str}{key}:")
                yaml_lines.append(self._dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                yaml_lines.append(f"{indent_str}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        yaml_lines.append(f"{indent_str}- ")
                        for subkey, subvalue in item.items():
                            yaml_lines.append(f"{indent_str}  {subkey}: {self._yaml_escape(subvalue)}")
                    else:
                        yaml_lines.append(f"{indent_str}- {self._yaml_escape(item)}")
            else:
                yaml_lines.append(f"{indent_str}{key}: {self._yaml_escape(value)}")
        
        return "\n".join(yaml_lines)
    
    def _yaml_escape(self, value: Any) -> str:
        """Échappe une valeur pour YAML."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str) and (" " in value or ":" in value):
            return f'"{value}"'
        else:
            return str(value)
    
    def create_environment_snapshot(self, name: str, env_path: Path, 
                                   snapshot_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Crée un snapshot (instantané) d'un environnement.
        
        Args:
            name: Nom de l'environnement
            env_path: Chemin de l'environnement
            snapshot_name: Nom du snapshot (optionnel)
            
        Returns:
            Tuple: (succès, message)
        """
        try:
            if not snapshot_name:
                snapshot_name = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            snapshots_dir = self.get_app_data_dir() / "snapshots"
            snapshots_dir.mkdir(parents=True, exist_ok=True)
            
            snapshot_file = snapshots_dir / f"{snapshot_name}.tar.gz"
            
            # Créer l'archive
            import tarfile
            
            with tarfile.open(snapshot_file, "w:gz") as tar:
                tar.add(env_path, arcname=name)
            
            # Créer les métadonnées du snapshot
            snapshot_metadata = {
                "name": snapshot_name,
                "environment_name": name,
                "created_at": datetime.now().isoformat(),
                "original_path": str(env_path),
                "size": snapshot_file.stat().st_size,
                "environment_metadata": self.get_environment_metadata(env_path)
            }
            
            metadata_file = snapshots_dir / f"{snapshot_name}_metadata.json"
            metadata_file.write_text(json.dumps(snapshot_metadata, indent=2), encoding='utf-8')
            
            logger.info(f"Snapshot créé: {snapshot_name}")
            return True, f"Snapshot créé: {snapshot_file}"
            
        except Exception as e:
            logger.error(f"Erreur création snapshot {name}: {e}")
            return False, f"Erreur création snapshot: {e}"
    
    def restore_environment_from_snapshot(self, snapshot_name: str, 
                                        target_name: Optional[str] = None,
                                        target_path: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Restaure un environnement depuis un snapshot.
        
        Args:
            snapshot_name: Nom du snapshot
            target_name: Nom pour l'environnement restauré
            target_path: Chemin pour l'environnement restauré
            
        Returns:
            Tuple: (succès, message)
        """
        try:
            snapshots_dir = self.get_app_data_dir() / "snapshots"
            snapshot_file = snapshots_dir / f"{snapshot_name}.tar.gz"
            metadata_file = snapshots_dir / f"{snapshot_name}_metadata.json"
            
            if not snapshot_file.exists():
                return False, f"Snapshot '{snapshot_name}' non trouvé"
            
            # Charger les métadonnées
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    snapshot_metadata = json.load(f)
                original_env_name = snapshot_metadata.get("environment_name", snapshot_name)
            else:
                original_env_name = snapshot_name
            
            # Déterminer le nom et le chemin cible
            if not target_name:
                target_name = f"{original_env_name}_restored_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if not target_path:
                target_path = self.get_default_venv_dir() / target_name
            
            # Vérifier que la cible n'existe pas
            if target_path.exists():
                return False, f"L'environnement cible existe déjà: {target_path}"
            
            # Extraire l'archive
            import tarfile
            
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(snapshot_file, "r:gz") as tar:
                tar.extractall(target_path.parent)
                # Renommer si nécessaire
                extracted_path = target_path.parent / original_env_name
                if extracted_path != target_path:
                    extracted_path.rename(target_path)
            
            # Mettre à jour les métadonnées
            restore_metadata = {
                "restored_from_snapshot": snapshot_name,
                "restored_at": datetime.now().isoformat(),
                "original_name": original_env_name
            }
            self.update_environment_metadata(target_path, restore_metadata)
            
            logger.info(f"Environnement restauré: {target_name}")
            return True, f"Environnement restauré: {target_name} à {target_path}"
            
        except Exception as e:
            logger.error(f"Erreur restauration snapshot {snapshot_name}: {e}")
            return False, f"Erreur restauration: {e}"
    
    def list_environment_snapshots(self) -> List[Dict[str, Any]]:
        """
        Liste tous les snapshots d'environnements disponibles.
        
        Returns:
            List: Liste des snapshots avec leurs métadonnées
        """
        snapshots = []
        
        try:
            snapshots_dir = self.get_app_data_dir() / "snapshots"
            
            if not snapshots_dir.exists():
                return snapshots
            
            for snapshot_file in snapshots_dir.glob("*.tar.gz"):
                metadata_file = snapshots_dir / f"{snapshot_file.stem}_metadata.json"
                
                try:
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    else:
                        # Métadonnées par défaut si pas de fichier
                        stat = snapshot_file.stat()
                        metadata = {
                            "name": snapshot_file.stem,
                            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "size": stat.st_size
                        }
                    
                    snapshots.append({
                        "file": str(snapshot_file),
                        "name": metadata.get("name", snapshot_file.stem),
                        "environment_name": metadata.get("environment_name", "unknown"),
                        "created_at": metadata.get("created_at", "unknown"),
                        "size": metadata.get("size", snapshot_file.stat().st_size),
                        "size_mb": metadata.get("size", snapshot_file.stat().st_size) / (1024 * 1024)
                    })
                    
                except Exception as e:
                    logger.warning(f"Erreur lecture snapshot {snapshot_file}: {e}")
                    continue
            
            # Trier par date de création (plus récent en premier)
            snapshots.sort(key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            logger.error(f"Erreur listage snapshots: {e}")
        
        return snapshots
    
    def compare_environments(self, name1: str, env_path1: Path, 
                           name2: str, env_path2: Path) -> Dict[str, Any]:
        """
        Compare deux environnements virtuels.
        
        Args:
            name1: Nom du premier environnement
            env_path1: Chemin du premier environnement
            name2: Nom du second environnement
            env_path2: Chemin du second environnement
            
        Returns:
            Dict: Rapport de comparaison
        """
        comparison = {
            "compared_at": datetime.now().isoformat(),
            "environments": {
                "env1": {"name": name1, "path": str(env_path1)},
                "env2": {"name": name2, "path": str(env_path2)}
            },
            "differences": {
                "packages": {"only_in_env1": [], "only_in_env2": [], "version_differences": []},
                "python_version": {},
                "size": {},
                "health": {}
            },
            "similarities": []
        }
        
        try:
            # Obtenir les informations des deux environnements
            info1 = self.export_environment_info(name1, env_path1, include_packages=True)
            info2 = self.export_environment_info(name2, env_path2, include_packages=True)
            
            # Comparer les packages
            packages1 = {pkg["name"]: pkg["version"] for pkg in info1.get("packages", [])}
            packages2 = {pkg["name"]: pkg["version"] for pkg in info2.get("packages", [])}
            
            # Packages uniquement dans env1
            for pkg_name, version in packages1.items():
                if pkg_name not in packages2:
                    comparison["differences"]["packages"]["only_in_env1"].append({
                        "name": pkg_name, "version": version
                    })
            
            # Packages uniquement dans env2
            for pkg_name, version in packages2.items():
                if pkg_name not in packages1:
                    comparison["differences"]["packages"]["only_in_env2"].append({
                        "name": pkg_name, "version": version
                    })
            
            # Différences de versions
            for pkg_name in set(packages1.keys()) & set(packages2.keys()):
                if packages1[pkg_name] != packages2[pkg_name]:
                    comparison["differences"]["packages"]["version_differences"].append({
                        "name": pkg_name,
                        "env1_version": packages1[pkg_name],
                        "env2_version": packages2[pkg_name]
                    })
            
            # Comparer les versions Python
            py_version1 = info1["performance"].get("python_version", "")
            py_version2 = info2["performance"].get("python_version", "")
            
            if py_version1 != py_version2:
                comparison["differences"]["python_version"] = {
                    "env1": py_version1,
                    "env2": py_version2
                }
            else:
                comparison["similarities"].append(f"Python version: {py_version1}")
            
            # Comparer les tailles
            size1 = info1["size"]["total"]
            size2 = info2["size"]["total"]
            comparison["differences"]["size"] = {
                "env1_bytes": size1,
                "env2_bytes": size2,
                "difference_bytes": abs(size1 - size2),
                "difference_mb": abs(size1 - size2) / (1024 * 1024)
            }
            
            # Comparer la santé
            health1 = info1["health"]
            health2 = info2["health"]
            
            for key in health1.keys():
                if health1.get(key) != health2.get(key):
                    comparison["differences"]["health"][key] = {
                        "env1": health1.get(key),
                        "env2": health2.get(key)
                    }
            
            # Statistiques de similitude
            total_packages = len(set(packages1.keys()) | set(packages2.keys()))
            common_packages = len(set(packages1.keys()) & set(packages2.keys()))
            
            if total_packages > 0:
                similarity_percentage = (common_packages / total_packages) * 100
                comparison["similarity_percentage"] = similarity_percentage
                comparison["similarities"].append(f"Packages communs: {common_packages}/{total_packages} ({similarity_percentage:.1f}%)")
            
        except Exception as e:
            logger.error(f"Erreur comparaison environnements: {e}")
            comparison["error"] = str(e)
        
        return comparison
    
    def migrate_environment(self, name: str, old_path: Path, new_path: Path,
                          preserve_old: bool = False) -> Tuple[bool, str]:
        """
        Migre un environnement vers un nouveau chemin.
        
        Args:
            name: Nom de l'environnement
            old_path: Ancien chemin
            new_path: Nouveau chemin
            preserve_old: Si True, conserve l'ancien environnement
            
        Returns:
            Tuple: (succès, message)
        """
        try:
            if not old_path.exists():
                return False, f"L'environnement source n'existe pas: {old_path}"
            
            if new_path.exists():
                return False, f"La destination existe déjà: {new_path}"
            
            # Créer le répertoire parent
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copier ou déplacer l'environnement
            if preserve_old:
                shutil.copytree(old_path, new_path)
                action = "copié"
            else:
                shutil.move(str(old_path), str(new_path))
                action = "déplacé"
            
            # Mettre à jour les métadonnées
            migration_metadata = {
                "migrated_from": str(old_path),
                "migrated_to": str(new_path),
                "migrated_at": datetime.now().isoformat(),
                "preserve_old": preserve_old
            }
            self.update_environment_metadata(new_path, migration_metadata)
            
            # Réparer les liens internes si nécessaire
            self._fix_environment_paths(new_path)
            
            logger.info(f"Environnement {name} {action} vers {new_path}")
            return True, f"Environnement {action} avec succès vers {new_path}"
            
        except Exception as e:
            logger.error(f"Erreur migration {name}: {e}")
            return False, f"Erreur migration: {e}"
    
    def _fix_environment_paths(self, env_path: Path) -> None:
        """
        Corrige les chemins internes d'un environnement après migration.
        
        Args:
            env_path: Chemin de l'environnement
        """
        try:
            # Corriger pyvenv.cfg
            pyvenv_cfg = env_path / "pyvenv.cfg"
            if pyvenv_cfg.exists():
                content = pyvenv_cfg.read_text(encoding='utf-8')
                # Mettre à jour les chemins si nécessaire
                updated_content = content.replace(
                    f"home = {env_path}",
                    f"home = {Path(sys.executable).parent}"
                )
                pyvenv_cfg.write_text(updated_content, encoding='utf-8')
            
            # Corriger les scripts d'activation si nécessaire
            if self.system != "windows":
                activate_script = env_path / "bin" / "activate"
                if activate_script.exists():
                    content = activate_script.read_text(encoding='utf-8')
                    # Mettre à jour VIRTUAL_ENV dans le script
                    import re
                    updated_content = re.sub(
                        r'VIRTUAL_ENV="[^"]*"',
                        f'VIRTUAL_ENV="{env_path}"',
                        content
                    )
                    activate_script.write_text(updated_content, encoding='utf-8')
            
        except Exception as e:
            logger.warning(f"Impossible de corriger les chemins internes: {e}")
    
    def get_environment_statistics(self) -> Dict[str, Any]:
        """
        Récupère des statistiques globales sur tous les environnements.
        
        Returns:
            Dict: Statistiques des environnements
        """
        stats = {
            "generated_at": datetime.now().isoformat(),
            "total_environments": 0,
            "healthy_environments": 0,
            "broken_environments": 0,
            "total_size_bytes": 0,
            "total_packages": 0,
            "python_versions": {},
            "most_used_packages": {},
            "average_size_mb": 0,
            "oldest_environment": None,
            "newest_environment": None,
            "temporary_environments": 0
        }
        
        try:
            environments_dir = self.get_default_venv_dir()
            if not environments_dir.exists():
                return stats
            
            env_sizes = []
            env_dates = []
            all_packages = []
            
            for env_dir in environments_dir.iterdir():
                if not env_dir.is_dir():
                    continue
                
                stats["total_environments"] += 1
                
                try:
                    # Vérifier la santé
                    health = self.check_environment_health(env_dir.name, env_dir)
                    if health.exists and health.python_available and health.pip_available:
                        stats["healthy_environments"] += 1
                    else:
                        stats["broken_environments"] += 1
                    
                    # Calculer la taille
                    size_info = self.get_environment_size(env_dir)
                    env_size = size_info["total"]
                    stats["total_size_bytes"] += env_size
                    env_sizes.append(env_size)
                    
                    # Obtenir les métadonnées
                    metadata = self.get_environment_metadata(env_dir)
                    
                    # Vérifier si temporaire
                    if metadata.get("temporary", False):
                        stats["temporary_environments"] += 1
                    
                    # Date de création
                    created_at = metadata.get("created_at")
                    if created_at:
                        try:
                            env_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            env_dates.append({
                                "name": env_dir.name,
                                "date": env_date,
                                "date_str": created_at
                            })
                        except Exception:
                            pass
                    
                    # Version Python
                    python_version = metadata.get("python_version", "unknown")
                    if python_version in stats["python_versions"]:
                        stats["python_versions"][python_version] += 1
                    else:
                        stats["python_versions"][python_version] = 1
                    
                    # Packages (si disponibles)
                    if health.exists and health.pip_available:
                        try:
                            pip_exe = self.get_pip_executable(env_dir.name, env_dir)
                            if pip_exe:
                                result = subprocess.run([str(pip_exe), "list", "--format=json"], 
                                                      capture_output=True, text=True, timeout=10)
                                if result.returncode == 0:
                                    packages = json.loads(result.stdout)
                                    stats["total_packages"] += len(packages)
                                    all_packages.extend([pkg["name"] for pkg in packages])
                        except Exception:
                            pass
                    
                except Exception as e:
                    logger.warning(f"Erreur analyse environnement {env_dir.name}: {e}")
                    continue
            
            # Calculer les moyennes
            if env_sizes:
                stats["average_size_mb"] = sum(env_sizes) / len(env_sizes) / (1024 * 1024)
            
            # Environnements les plus anciens/récents
            if env_dates:
                env_dates.sort(key=lambda x: x["date"])
                stats["oldest_environment"] = {
                    "name": env_dates[0]["name"],
                    "created_at": env_dates[0]["date_str"]
                }
                stats["newest_environment"] = {
                    "name": env_dates[-1]["name"],
                    "created_at": env_dates[-1]["date_str"]
                }
            
            # Packages les plus utilisés
            if all_packages:
                from collections import Counter
                package_counts = Counter(all_packages)
                stats["most_used_packages"] = dict(package_counts.most_common(10))
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def search_environments(self, query: str, search_in: List[str] = None) -> List[Dict[str, Any]]:
        """
        Recherche des environnements selon différents critères.
        
        Args:
            query: Terme de recherche
            search_in: Liste des champs à rechercher (name, description, packages, tags)
            
        Returns:
            List: Environnements correspondants
        """
        if not search_in:
            search_in = ["name", "description", "packages", "tags"]
        
        results: list[Any] = []
        query_lower = query.lower()
        
        try:
            environments_dir = self.get_default_venv_dir()
            if not environments_dir.exists():
                return results
            
            for env_dir in environments_dir.iterdir():
                if not env_dir.is_dir():
                    continue
                
                try:
                    match_score = 0
                    match_reasons = []
                    
                    # Recherche dans le nom
                    if "name" in search_in and query_lower in env_dir.name.lower():
                        match_score += 10
                        match_reasons.append("nom")
                    
                    # Obtenir les métadonnées
                    metadata = self.get_environment_metadata(env_dir)
                    
                    # Recherche dans la description
                    if "description" in search_in:
                        description = metadata.get("description", "").lower()
                        if query_lower in description:
                            match_score += 5
                            match_reasons.append("description")
                    
                    # Recherche dans les tags
                    if "tags" in search_in:
                        tags = metadata.get("tags", [])
                        for tag in tags:
                            if query_lower in str(tag).lower():
                                match_score += 3
                                match_reasons.append("tags")
                                break
                    
                    # Recherche dans les packages
                    if "packages" in search_in:
                        health = self.check_environment_health(env_dir.name, env_dir)
                        if health.exists and health.pip_available:
                            try:
                                pip_exe = self.get_pip_executable(env_dir.name, env_dir)
                                if pip_exe:
                                    result = subprocess.run([str(pip_exe), "list", "--format=json"], 
                                                          capture_output=True, text=True, timeout=5)
                                    if result.returncode == 0:
                                        packages = json.loads(result.stdout)
                                        for pkg in packages:
                                            if query_lower in pkg["name"].lower():
                                                match_score += 2
                                                match_reasons.append(f"package:{pkg['name']}")
                                                break
                            except Exception:
                                pass
                    
                    # Ajouter aux résultats si correspondance
                    if match_score > 0:
                        results.append({
                            "name": env_dir.name,
                            "path": str(env_dir),
                            "match_score": match_score,
                            "match_reasons": match_reasons,
                            "metadata": metadata,
                            "health": self.check_environment_health(env_dir.name, env_dir).to_dict()
                        })
                    
                except Exception as e:
                    logger.warning(f"Erreur recherche environnement {env_dir.name}: {e}")
                    continue
            
            # Trier par score de correspondance
            results.sort(key=lambda x: x["match_score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Erreur recherche environnements: {e}")
        
        return results
    
    def get_environment_dependencies(self, name: str, env_path: Path) -> Dict[str, Any]:
        """
        Analyse les dépendances d'un environnement.
        
        Args:
            name: Nom de l'environnement
            env_path: Chemin de l'environnement
            
        Returns:
            Dict: Analyse des dépendances
        """
        analysis = {
            "analyzed_at": datetime.now().isoformat(),
            "environment": name,
            "total_packages": 0,
            "top_level_packages": [],
            "dependency_tree": {},
            "conflicts": [],
            "outdated": [],
            "security_issues": []
        }
        
        try:
            pip_exe = self.get_pip_executable(name, env_path)
            if not pip_exe:
                return analysis
            
            # Obtenir la liste des packages avec dépendances
            result = subprocess.run([str(pip_exe), "show", "--verbose"], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Analyser la sortie pip show
                current_package = None
                packages_info: dict[Any, Any] = {}
                
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('Name:'):
                        current_package = line.split(':', 1)[1].strip()
                        packages_info[current_package] = {}
                    elif current_package and line.startswith('Requires:'):
                        requires = line.split(':', 1)[1].strip()
                        if requires and requires != 'none':
                            packages_info[current_package]['requires'] = [
                                dep.strip() for dep in requires.split(',')
                            ]
                        else:
                            packages_info[current_package]['requires'] = []
                    elif current_package and line.startswith('Required-by:'):
                        required_by = line.split(':', 1)[1].strip()
                        if required_by and required_by != 'none':
                            packages_info[current_package]['required_by'] = [
                                dep.strip() for dep in required_by.split(',')
                            ]
                        else:
                            packages_info[current_package]['required_by'] = []
                
                analysis["total_packages"] = len(packages_info)
                analysis["dependency_tree"] = packages_info
                
                # Identifier les packages de niveau supérieur
                for pkg_name, pkg_info in packages_info.items():
                    if not pkg_info.get('required_by', []):
                        analysis["top_level_packages"].append(pkg_name)
            
            # Vérifier les packages obsolètes
            try:
                result = subprocess.run([str(pip_exe), "list", "--outdated", "--format=json"], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    outdated_packages = json.loads(result.stdout)
                    analysis["outdated"] = outdated_packages
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Erreur analyse dépendances {name}: {e}")
            analysis["error"] = str(e)
        
        return analysis