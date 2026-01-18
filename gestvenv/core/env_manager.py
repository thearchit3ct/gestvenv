"""
Module de gestion des environnements virtuels pour GestVenv.

Ce module fournit les fonctionnalités principales pour créer, activer, supprimer
et gérer les environnements virtuels Python.
"""

import os
import sys
import json
import shutil
import logging
import datetime
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

# Import des modules utilitaires
from ..utils.path_handler import (
    get_environment_path,
    get_python_executable,
    get_pip_executable,
    get_activation_script_path,
    get_config_file_path,
    resolve_path,
    get_default_export_path,
    ensure_venv_dir
)

from ..core.config_manager import (
    ConfigManager
)

from ..utils.system_commands import (
    create_virtual_environment,
    install_packages,
    uninstall_packages,
    run_command,
    list_installed_packages,
    get_activation_command,
    delete_environment,
    run_in_environment,
    check_python_version,
    get_available_python_versions,
    export_requirements,
    install_from_requirements,
    check_environment_health
)

from ..utils.validators import (
    validate_env_name,
    validate_python_version,
    validate_packages_list,
    validate_path_exists,
    validate_requirements_file,
    validate_config_json,
    validate_environment_exists,
    validate_output_format,
    validate_metadata,
    is_safe_to_delete
)

# Configuration du logger
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """
    Classe principale pour la gestion des environnements virtuels Python.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialise le gestionnaire d'environnements.
        
        Args:
            config_path (Optional[Path]): Chemin vers le fichier de configuration,
                                         utilise le chemin par défaut si non spécifié
        """
        self.config_path = config_path if config_path else get_config_file_path()
        self.config_manager = ConfigManager(self.config_path)
        self.config = self._load_config()
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)
        self._ensure_default_config()
    
    def _load_config(self) -> Dict:
        """
        Charge la configuration depuis le fichier JSON.
        Crée un fichier de configuration par défaut s'il n'existe pas.
        
        Returns:
            Dict: Configuration chargée
        """
        if not self.config_path.exists():
            logger.info(f"Fichier de configuration non trouvé à {self.config_path}")
            # Créer le répertoire parent si nécessaire
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Créer un fichier de configuration par défaut
            default_config: Dict[str, Any] = {
                "environments": {},
                "active_env": None,
                "default_python": "python3" if platform.system() != "Windows" else "python"
            }
            
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=2)
            
            logger.info(f"Fichier de configuration créé avec les valeurs par défaut à {self.config_path}")
            return default_config
        
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
            logger.debug(f"Configuration chargée depuis {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            # Renommer le fichier corrompu et créer un nouveau fichier
            backup_path = self.config_path.with_suffix(f".backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
            self.config_path.rename(backup_path)
            logger.warning(f"Configuration corrompue sauvegardée dans {backup_path}")
            
            # Créer un nouveau fichier de configuration
            default_config = {
                "environments": {},
                "active_env": None,
                "default_python": "python3" if platform.system() != "Windows" else "python"
            }
            
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=2)
            
            logger.info(f"Nouveau fichier de configuration créé avec les valeurs par défaut")
            return default_config
    
    def _save_config(self) -> bool:
        """
        Sauvegarde la configuration actuelle dans le fichier JSON.
        
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        try:
            # Créer une sauvegarde de la configuration existante
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix(".backup")
                shutil.copy2(self.config_path, backup_path)
            
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            
            logger.debug(f"Configuration sauvegardée dans {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}")
            return False
    
    def _ensure_default_config(self) -> None:
        """
        S'assure que la configuration contient toutes les clés requises.
        """
        if "environments" not in self.config:
            self.config["environments"] = {}
        
        if "active_env" not in self.config:
            self.config["active_env"] = None
        
        if "default_python" not in self.config:
            self.config["default_python"] = "python3" if platform.system() != "Windows" else "python"
        
        # Sauvegarder la configuration mise à jour
        self._save_config()
    
    def _run_pip_command(self, env_name, pip_args):
        """
        Exécuter une commande pip dans l'environnement spécifié.
        
        Args:
            env_name (str): Nom de l'environnement.
            pip_args (list): Arguments pour pip.
        
        Returns:
            dict: Résultat de la commande (stdout, stderr, returncode).
        """
        env_path = get_environment_path(env_name)
        
        if self.system == "Windows":
            pip_path = os.path.join(env_path, "Scripts", "pip")
        else:
            pip_path = os.path.join(env_path, "bin", "pip")
        
        cmd = [pip_path] + pip_args
        return run_command(cmd)
    
    def create_environment(self, name: str, python_version: Optional[str] = None,
                           packages: Optional[str] = None, path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Crée un nouvel environnement virtuel Python.
        
        Args:
            name (str): Nom de l'environnement
            python_version (Optional[str]): Version Python à utiliser (ex: "python3.9")
            packages (Optional[str]): Liste de packages à installer séparés par des virgules
            path (Optional[str]): Chemin personnalisé pour l'environnement
            
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message)
        """
        # Valider le nom d'environnement
        valid, error = validate_env_name(name)
        if not valid:
            return False, error
        
        # Vérifier si l'environnement existe déjà
        if name in self.config["environments"]:
            return False, f"L'environnement '{name}' existe déjà"
        
        # Valider la version Python
        if python_version:
            valid, error = validate_python_version(python_version)
            if not valid:
                return False, error
        
        # Si aucune version spécifiée, utiliser la version par défaut
        python_cmd = python_version if python_version else self.config["default_python"]
        
        # Valider et analyser la liste de packages
        package_list = []
        if packages:
            valid, package_list, error = validate_packages_list(packages)
            if not valid:
                return False, error
        
        # Valider le chemin personnalisé s'il est spécifié
        custom_path = None
        if path:
            valid, resolved_path, error = validate_path_exists(path, must_exist=False)
            if not valid:
                return False, error
            custom_path = resolved_path
        
        # Création de l'environnement virtuel
        env_path = custom_path if custom_path else ensure_venv_dir(name)
        
        # Créer l'environnement
        if not create_virtual_environment(name, python_cmd):
            return False, f"Échec de la création de l'environnement '{name}'"
        
        # Installer les packages si spécifiés
        if package_list:
            if not install_packages(name, package_list):
                # En cas d'échec d'installation, essayer de supprimer l'environnement créé
                delete_environment(name)
                return False, f"Échec de l'installation des packages pour l'environnement '{name}'"
        
        # Ajouter l'environnement à la configuration
        python_version_actual = check_python_version(python_cmd)
        
        self.config["environments"][name] = {
            "path": str(env_path),
            "python_version": python_version_actual or python_cmd,
            "created_at": datetime.datetime.now().isoformat(),
            "packages": package_list
        }
        
        # Sauvegarder la configuration
        if not self._save_config():
            return False, "Erreur lors de la sauvegarde de la configuration"
        
        # Si c'est le premier environnement, le définir comme actif
        if len(self.config["environments"]) == 1:
            self.config["active_env"] = name
            self._save_config()
        
        return True, f"Environnement '{name}' créé avec succès"
    
    def activate_environment(self, name: str) -> Tuple[bool, str]:
        """
        Définit un environnement comme actif et retourne la commande pour l'activer.
        
        Args:
            name (str): Nom de l'environnement à activer
            
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message ou commande d'activation)
        """
        # Vérifier si l'environnement existe
        valid, error = validate_environment_exists(name)
        if not valid:
            return False, error
        
        # Obtenir la commande d'activation
        activation_cmd = get_activation_command(name)
        if not activation_cmd:
            return False, f"Impossible de générer la commande d'activation pour l'environnement '{name}'"
        
        # Définir l'environnement comme actif dans la configuration
        self.config["active_env"] = name
        if not self._save_config():
            logger.warning("Erreur lors de la sauvegarde de la configuration, mais l'activation peut continuer")
        
        return True, activation_cmd
    
    def deactivate_environment(self) -> Tuple[bool, str]:
        """
        Désactive l'environnement actif et retourne la commande de désactivation.
        
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message ou commande de désactivation)
        """
        # Vérifier s'il y a un environnement actif
        if not self.config["active_env"]:
            return False, "Aucun environnement actif à désactiver"
        
        # Réinitialiser l'environnement actif dans la configuration
        active_env = self.config["active_env"]
        self.config["active_env"] = None
        
        if not self._save_config():
            logger.warning("Erreur lors de la sauvegarde de la configuration, mais la désactivation peut continuer")
        
        # Retourner la commande de désactivation appropriée selon le système
        if platform.system().lower() == "windows":
            return True, "deactivate"
        else:
            return True, "deactivate"
    
    def delete_environment(self, name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Supprime un environnement virtuel.
        
        Args:
            name (str): Nom de l'environnement à supprimer
            force (bool): Si True, force la suppression sans vérifications supplémentaires
            
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message)
        """
        # Vérifier si l'environnement existe
        valid, error = validate_environment_exists(name)
        if not valid:
            return False, error
        
        # Vérifier s'il est sécuritaire de supprimer l'environnement
        if not force:
            safe, warning = is_safe_to_delete(name)
            if not safe:
                return False, warning
        
        # Si l'environnement est actif, le désactiver d'abord
        if self.config["active_env"] == name:
            self.config["active_env"] = None
        
        # Supprimer l'environnement du système de fichiers
        if not delete_environment(name):
            return False, f"Erreur lors de la suppression de l'environnement '{name}'"
        
        # Supprimer l'environnement de la configuration
        if name in self.config["environments"]:
            del self.config["environments"][name]
        
        # Sauvegarder la configuration
        if not self._save_config():
            return False, "Erreur lors de la sauvegarde de la configuration"
        
        return True, f"Environnement '{name}' supprimé avec succès"
    
    def list_environments(self) -> List[Dict[str, Any]]:
        """
        Liste tous les environnements disponibles avec leurs informations.
        
        Returns:
            List[Dict[str, Any]]: Liste des environnements avec leurs détails
        """
        environments = []
        active_env = self.config["active_env"]
        
        for name, env_info in self.config["environments"].items():
            # Vérifier si l'environnement existe réellement
            env_path = get_environment_path(name)
            exists = env_path and env_path.exists()
            
            # Recueillir les informations de santé si l'environnement existe
            health = check_environment_health(name) if exists else {
                "exists": False,
                "python_available": False,
                "pip_available": False,
                "activation_script_exists": False
            }
            
            # Ajouter les informations de l'environnement à la liste
            environments.append({
                "name": name,
                "path": env_info.get("path", ""),
                "python_version": env_info.get("python_version", ""),
                "created_at": env_info.get("created_at", ""),
                "packages_count": len(env_info.get("packages", [])),
                "active": name == active_env,
                "health": health,
                "exists": exists
            })
        
        return environments
    
    def get_environment_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Obtient des informations détaillées sur un environnement spécifique.
        
        Args:
            name (str): Nom de l'environnement
            
        Returns:
            Optional[Dict[str, Any]]: Dictionnaire d'informations ou None si non trouvé
        """
        # Vérifier si l'environnement existe dans la configuration
        if name not in self.config["environments"]:
            logger.warning(f"L'environnement '{name}' n'existe pas dans la configuration")
            return None
        
        env_info = self.config["environments"][name]
        
        # Vérifier si l'environnement existe sur le disque
        env_path = get_environment_path(name)
        exists = env_path and env_path.exists()
        
        # Recueillir les informations de santé
        health = check_environment_health(name) if exists else {
            "exists": False,
            "python_available": False,
            "pip_available": False,
            "activation_script_exists": False
        }
        
        # Obtenir la liste des packages installés
        installed_packages = list_installed_packages(name) if exists and health["pip_available"] else []
        
        # Préparer les informations détaillées
        detailed_info = {
            "name": name,
            "path": env_info.get("path", ""),
            "python_version": env_info.get("python_version", ""),
            "created_at": env_info.get("created_at", ""),
            "packages_configured": env_info.get("packages", []),
            "packages_installed": installed_packages,
            "active": name == self.config["active_env"],
            "health": health,
            "exists": exists,
            "python_executable": str(get_python_executable(name)) if exists else None,
            "pip_executable": str(get_pip_executable(name)) if exists else None,
            "activation_script": str(get_activation_script_path(name)) if exists else None
        }
        
        return detailed_info
    
    def clone_environment(self, source_name: str, target_name: str) -> Tuple[bool, str]:
        """
        Clone un environnement existant vers un nouveau.
        
        Args:
            source_name (str): Nom de l'environnement source
            target_name (str): Nom du nouvel environnement
            
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message)
        """
        # Vérifier si l'environnement source existe
        valid, error = validate_environment_exists(source_name)
        if not valid:
            return False, error
        
        # Vérifier si le nom cible est valide
        valid, error = validate_env_name(target_name)
        if not valid:
            return False, error
        
        # Vérifier si l'environnement cible existe déjà
        if target_name in self.config["environments"]:
            return False, f"L'environnement cible '{target_name}' existe déjà"
        
        # Obtenir les informations de l'environnement source
        source_info = self.get_environment_info(source_name)
        if not source_info:
            return False, f"Impossible d'obtenir les informations de l'environnement source '{source_name}'"
        
        # Créer un nouvel environnement avec la même version Python
        python_version = source_info["python_version"]
        success, message = self.create_environment(target_name, python_version)
        
        if not success:
            return False, f"Erreur lors de la création du nouvel environnement: {message}"
        
        # Installer les mêmes packages que dans l'environnement source
        packages = source_info["packages_installed"]
        package_names = [f"{pkg['name']}=={pkg['version']}" for pkg in packages]
        
        if package_names:
            if not install_packages(target_name, package_names):
                # En cas d'échec, essayer de supprimer l'environnement créé
                self.delete_environment(target_name)
                return False, f"Erreur lors de l'installation des packages dans le nouvel environnement"
        
        # Mettre à jour la configuration avec les packages installés
        self.config["environments"][target_name]["packages"] = package_names
        if not self._save_config():
            return False, "Erreur lors de la sauvegarde de la configuration"
        
        return True, f"Environnement '{source_name}' cloné avec succès vers '{target_name}'"
    
    def export_environment(self, name: str, output_path: Optional[str] = None,
                           format_type: str = "json", metadata: Optional[str] = None) -> Tuple[bool, str]:
        """
        Exporte la configuration d'un environnement.
        
        Args:
            name (str): Nom de l'environnement à exporter
            output_path (Optional[str]): Chemin de sortie pour le fichier d'export
            format_type (str): Format d'export ('json' ou 'requirements')
            metadata (Optional[str]): Métadonnées supplémentaires à inclure
            
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message ou chemin du fichier)
        """
        # Vérifier si l'environnement existe
        valid, error = validate_environment_exists(name)
        if not valid:
            return False, error
        
        # Valider le format d'export
        valid, error = validate_output_format(format_type)
        if not valid:
            return False, error
        
        # Valider et analyser les métadonnées si spécifiées
        metadata_dict = {}
        if metadata:
            valid, metadata_dict, error = validate_metadata(metadata)
            if not valid:
                return False, error
        
        # Obtenir les informations de l'environnement
        env_info = self.get_environment_info(name)
        if not env_info:
            return False, f"Impossible d'obtenir les informations de l'environnement '{name}'"
        
        # Déterminer le chemin de sortie
        if output_path:
            valid, resolved_path, error = validate_path_exists(output_path, must_exist=False)
            if not valid:
                return False, error
            
            output_file = resolved_path
        else:
            # Utiliser un chemin par défaut
            if format_type.lower() == "requirements":
                output_file = ensure_venv_dir().parent / "exports" / f"{name}_requirements.txt"
            else:
                output_file = get_default_export_path(name)
        
        # Créer le répertoire parent si nécessaire
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Exporter selon le format spécifié
        try:
            if format_type.lower() == "requirements":
                # Exporter au format requirements.txt
                if not export_requirements(name, output_file):
                    return False, f"Erreur lors de l'export des requirements pour l'environnement '{name}'"
            else:
                # Exporter au format JSON
                export_data = {
                    "name": name,
                    "python_version": env_info["python_version"],
                    "packages": [f"{pkg['name']}=={pkg['version']}" for pkg in env_info["packages_installed"]],
                    "metadata": {
                        "exported_at": datetime.datetime.now().isoformat(),
                        "exported_by": os.getlogin() if hasattr(os, "getlogin") else "unknown",
                        **metadata_dict
                    }
                }
                
                with open(output_file, "w") as f:
                    json.dump(export_data, f, indent=2)
            
            return True, f"Environnement '{name}' exporté avec succès vers {output_file}"
        except Exception as e:
            logger.error(f"Erreur lors de l'export de l'environnement: {e}")
            return False, f"Erreur lors de l'export: {str(e)}"
    
    def import_environment(self, input_path: str, name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Importe un environnement depuis un fichier de configuration.
        
        Args:
            input_path (str): Chemin vers le fichier de configuration
            name (Optional[str]): Nom à utiliser pour le nouvel environnement
            
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message)
        """
        # Valider le chemin d'entrée
        valid, path, error = validate_path_exists(input_path)
        if not valid:
            return False, error
        
        # Déterminer le type de fichier
        if path.suffix.lower() == ".json":
            # Valider le fichier JSON
            valid, config, error = validate_config_json(str(path))
            if not valid:
                return False, error
            
            # Utiliser le nom spécifié ou celui du fichier
            env_name = name if name else config["name"]
            
            # Valider le nom d'environnement
            valid, error = validate_env_name(env_name)
            if not valid:
                return False, error
            
            # Vérifier si l'environnement existe déjà
            if env_name in self.config["environments"]:
                return False, f"L'environnement '{env_name}' existe déjà"
            
            # Créer le nouvel environnement
            python_version = config["python_version"]
            success, message = self.create_environment(env_name, python_version)
            
            if not success:
                return False, f"Erreur lors de la création de l'environnement: {message}"
            
            # Installer les packages
            packages = config["packages"]
            if packages:
                if not install_packages(env_name, packages):
                    # En cas d'échec, supprimer l'environnement créé
                    self.delete_environment(env_name)
                    return False, f"Erreur lors de l'installation des packages"
            
            # Mettre à jour la configuration
            self.config["environments"][env_name]["packages"] = packages
            if not self._save_config():
                return False, "Erreur lors de la sauvegarde de la configuration"
            
            return True, f"Environnement importé avec succès sous le nom '{env_name}'"
            
        elif path.suffix.lower() == ".txt":
            # Valider le fichier requirements.txt
            valid, _, error = validate_requirements_file(str(path))
            if not valid:
                return False, error
            
            # Un nom doit être spécifié pour l'import depuis requirements.txt
            if not name:
                return False, "Un nom d'environnement doit être spécifié pour l'import depuis requirements.txt"
            
            # Valider le nom d'environnement
            valid, error = validate_env_name(name)
            if not valid:
                return False, error
            
            # Vérifier si l'environnement existe déjà
            if name in self.config["environments"]:
                return False, f"L'environnement '{name}' existe déjà"
            
            # Créer le nouvel environnement
            success, message = self.create_environment(name)
            
            if not success:
                return False, f"Erreur lors de la création de l'environnement: {message}"
            
            # Installer les packages depuis le fichier requirements.txt
            if not install_from_requirements(name, path):
                # En cas d'échec, supprimer l'environnement créé
                self.delete_environment(name)
                return False, f"Erreur lors de l'installation des packages depuis {path}"
            
            # Mettre à jour les packages dans la configuration
            packages = []
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        packages.append(line.split("#")[0].strip())
            
            self.config["environments"][name]["packages"] = packages
            if not self._save_config():
                return False, "Erreur lors de la sauvegarde de la configuration"
            
            return True, f"Environnement importé avec succès depuis {path} sous le nom '{name}'"
        else:
            return False, f"Format de fichier non pris en charge: {path.suffix}"
    
    def set_default_python(self, python_cmd: str) -> Tuple[bool, str]:
        """
        Définit la commande Python par défaut pour les nouveaux environnements.
        
        Args:
            python_cmd (str): Commande Python à utiliser par défaut
            
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message)
        """
        # Valider la commande Python
        valid, error = validate_python_version(python_cmd)
        if not valid:
            return False, error
        
        # Vérifier si la commande Python est disponible
        version = check_python_version(python_cmd)
        if not version:
            return False, f"La commande Python '{python_cmd}' n'est pas disponible sur le système"
        
        # Mettre à jour la configuration
        self.config["default_python"] = python_cmd
        if not self._save_config():
            return False, "Erreur lors de la sauvegarde de la configuration"
        
        return True, f"Commande Python par défaut définie à '{python_cmd}' (version {version})"
    
    def get_active_environment(self) -> Optional[str]:
        """
        Retourne le nom de l'environnement actif, s'il existe.
        
        Returns:
            Optional[str]: Nom de l'environnement actif ou None
        """
        active_env = self.config["active_env"]
        
        # Vérifier si l'environnement existe encore
        if active_env and active_env not in self.config["environments"]:
            self.config["active_env"] = None
            self._save_config()
            return None
        
        return active_env
    
    def run_command_in_environment(self, env_name: str, command: List[str]) -> Tuple[int, str, str]:
        """
        Exécute une commande dans un environnement virtuel spécifique.
        
        Args:
            env_name (str): Nom de l'environnement
            command (List[str]): Commande à exécuter
            
        Returns:
            Tuple[int, str, str]: Tuple contenant (code de retour, sortie standard, sortie d'erreur)
        """
        # Vérifier si l'environnement existe
        valid, error = validate_environment_exists(env_name)
        if not valid:
            return 1, "", error
        
        # Exécuter la commande dans l'environnement
        return run_in_environment(env_name, command)
    
    def update_packages(self, env_name: str, packages: Optional[str] = None, all_packages: bool = False) -> Tuple[bool, str]:
        """
        Met à jour des packages dans un environnement virtuel.
        
        Args:
            env_name (str): Nom de l'environnement
            packages (Optional[str]): Liste de packages à mettre à jour séparés par des virgules
            all_packages (bool): Si True, met à jour tous les packages
            
        Returns:
            Tuple[bool, str]: Tuple contenant (succès, message)
        """
        # Vérifier si l'environnement existe
        valid, error = validate_environment_exists(env_name)
        if not valid:
            return False, error
        
        # Obtenir la liste des packages à mettre à jour
        package_list = []
        if packages:
            valid, package_list, error = validate_packages_list(packages)
            if not valid:
                return False, error
        elif not all_packages:
            return False, "Aucun package spécifié pour la mise à jour et --all n'est pas utilisé"
        
        # Si all_packages est True, obtenir tous les packages installés
        if all_packages:
            installed_packages = list_installed_packages(env_name)
            if installed_packages is None:
                return False, f"Impossible d'obtenir la liste des packages pour l'environnement '{env_name}'"
            
            package_list = [pkg["name"] for pkg in installed_packages]
            
            if not package_list:
                return False, f"Aucun package installé dans l'environnement '{env_name}'"
        
        # Mettre à jour les packages
        if not install_packages(env_name, package_list, upgrade=True):
            return False, f"Erreur lors de la mise à jour des packages pour l'environnement '{env_name}'"
        
        # Mettre à jour la configuration si nécessaire
        if env_name in self.config["environments"]:
            # Mettre à jour uniquement les packages spécifiés dans la configuration
            configured_packages = self.config["environments"][env_name].get("packages", [])
            updated_packages = []
            
            for pkg in configured_packages:
                # Extraire le nom du package (sans la version)
                pkg_name = pkg.split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].strip()
                
                # Si le package est dans la liste de mise à jour, récupérer sa nouvelle version
                if pkg_name in package_list:
                    # Obtenir la version actuelle installée
                    installed = list_installed_packages(env_name)
                    if installed:
                        for installed_pkg in installed:
                            if installed_pkg["name"] == pkg_name:
                                updated_packages.append(f"{pkg_name}=={installed_pkg['version']}")
                                break
                        else:
                            # Si le package n'est pas trouvé, conserver l'ancienne spécification
                            updated_packages.append(pkg)
                    else:
                        # Si impossible d'obtenir les versions installées, conserver l'ancienne spécification
                        updated_packages.append(pkg)
                else:
                    # Si le package n'est pas dans la liste de mise à jour, conserver l'ancienne spécification
                    updated_packages.append(pkg)
            
            # Mettre à jour la configuration
            self.config["environments"][env_name]["packages"] = updated_packages
            self._save_config()
        
        return True, f"Packages mis à jour avec succès dans l'environnement '{env_name}'"
    
    def environment_exists(self, env_name):
        """
        Vérifier si un environnement existe.
        
        Args:
            env_name (str): Nom de l'environnement à vérifier.
        
        Returns:
            bool: True si l'environnement existe, False sinon.
        """
        return self.config_manager.environment_exists(env_name)
    
    def get_environment_packages(self, env_name):
        """
        Obtenir la liste des packages installés dans un environnement.
        
        Args:
            env_name (str): Nom de l'environnement.
        
        Returns:
            list: Liste des packages installés.
        
        Raises:
            ValueError: Si l'environnement n'existe pas.
        """
        if not self.environment_exists(env_name):
            raise ValueError(f"L'environnement {env_name} n'existe pas.")
        
        # Récupérer la liste des packages depuis la configuration
        env_info = self.config_manager.get_environment(env_name)
        return env_info.get("packages", [])
    
    def refresh_environment_packages(self, env_name):
        """
        Rafraîchir la liste des packages dans la configuration en fonction de ceux installés réellement.
        
        Args:
            env_name (str): Nom de l'environnement.
        
        Returns:
            list: Liste mise à jour des packages.
        
        Raises:
            ValueError: Si l'environnement n'existe pas.
        """
        if not self.environment_exists(env_name):
            raise ValueError(f"L'environnement {env_name} n'existe pas.")
        
        # Exécuter pip freeze pour obtenir la liste des packages installés
        result = self._run_pip_command(env_name, ["freeze"])
        
        if result['returncode'] == 0:
            packages = [line.strip() for line in result['stdout'].splitlines() if line.strip()]
            
            # Mettre à jour la configuration
            env_info = self.config_manager.get_environment(env_name)
            env_info["packages"] = packages
            self.config_manager.update_environment(env_name, env_info)
            
            return packages
        else:
            logger.error(f"Échec du rafraîchissement des packages: {result['stderr']}")
            return self.get_environment_packages(env_name)
        
    def check_for_updates(self, env_name: str) -> Tuple[bool, List[Dict[str, str]], str]:
        """
        Vérifie les mises à jour disponibles pour les packages d'un environnement.
        
        Args:
            env_name (str): Nom de l'environnement
            
        Returns:
            Tuple[bool, List[Dict[str, str]], str]: Tuple contenant (succès, liste des mises à jour, message)
        """
        # Vérifier si l'environnement existe
        valid, error = validate_environment_exists(env_name)
        if not valid:
            return False, [], error
        
        # Obtenir le chemin vers pip
        pip_path = get_pip_executable(env_name)
        if not pip_path:
            return False, [], f"Impossible de trouver pip pour l'environnement '{env_name}'"
        
        # Exécuter la commande pour vérifier les mises à jour
        cmd = [str(pip_path), "list", "--outdated", "--format=json"]
        ret_code, stdout, stderr = run_in_environment(env_name, cmd[1:])
        
        if ret_code != 0:
            return False, [], f"Erreur lors de la vérification des mises à jour: {stderr}"
        
        try:
            # Analyser la sortie JSON
            updates = json.loads(stdout)
            
            # Formater les informations de mise à jour
            formatted_updates = []
            for pkg in updates:
                formatted_updates.append({
                    "name": pkg["name"],
                    "current_version": pkg["version"],
                    "latest_version": pkg["latest_version"]
                })
            
            if not formatted_updates:
                return True, [], "Tous les packages sont à jour"
            
            return True, formatted_updates, f"{len(formatted_updates)} package(s) peuvent être mis à jour"
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des mises à jour: {e}")
            return False, [], f"Erreur lors de l'analyse des mises à jour: {str(e)}"