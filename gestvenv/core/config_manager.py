"""
Module de gestion de la configuration pour GestVenv.

Ce module fournit les fonctionnalités pour stocker et récupérer
les configurations des environnements virtuels, ainsi que pour
gérer l'import/export des configurations.
"""

import os
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from .models import ConfigInfo, EnvironmentInfo

# Configuration du logging
logger = logging.getLogger(__name__)

class ConfigManager:
    """Gestionnaire de configuration pour GestVenv."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialise le gestionnaire de configuration.
        
        Args:
            config_path: Chemin vers le fichier de configuration.
                Si None, utilise le chemin par défaut.
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Utiliser le répertoire par défaut
            self.config_path = self._get_default_config_path()
        
        # Créer le répertoire de configuration s'il n'existe pas
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Charger ou créer la configuration
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> Path:
        """
        Obtient le chemin par défaut du fichier de configuration.
        
        Returns:
            Path: Chemin vers le fichier de configuration par défaut.
        """
        if os.name == 'nt':  # Windows
            config_dir = os.path.join(os.environ.get('APPDATA', ''), 'GestVenv')
        else:  # macOS, Linux et autres
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'gestvenv')
        
        # Assurer que le répertoire existe
        os.makedirs(config_dir, exist_ok=True)
        
        # Utiliser Path normalement, sans forcer WindowsPath sur Unix
        return Path(config_dir) / 'config.json'
    
    def _load_config(self) -> ConfigInfo:
        """
        Charge la configuration depuis le fichier.
        Si le fichier n'existe pas, crée une configuration par défaut.
        
        Returns:
            ConfigInfo: Configuration chargée ou par défaut.
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                logger.debug(f"Configuration chargée depuis {self.config_path}")
                return ConfigInfo.from_dict(config_dict)
            except json.JSONDecodeError as e:
                logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
                # Créer une sauvegarde du fichier corrompu
                backup_path = f"{self.config_path}.bak"
                shutil.copy2(self.config_path, backup_path)
                logger.warning(f"Une sauvegarde du fichier corrompu a été créée: {backup_path}")
                # Créer une nouvelle configuration
                return self._create_default_config()
            except Exception as e:
                logger.error(f"Erreur inattendue lors du chargement de la configuration: {str(e)}")
                return self._create_default_config()
        else:
            logger.info(f"Aucun fichier de configuration trouvé. Création d'une configuration par défaut.")
            return self._create_default_config()
    
    def _create_default_config(self) -> ConfigInfo:
        """
        Crée une configuration par défaut.
        
        Returns:
            ConfigInfo: Configuration par défaut.
        """
        default_config = ConfigInfo(
            environments={},
            active_env=None,
            default_python=self._detect_default_python()
        )
        
        # Sauvegarder la configuration par défaut
        self._save_config(default_config)
        
        return default_config
    
    def _detect_default_python(self) -> str:
        """
        Détecte la commande Python par défaut sur le système.
        
        Returns:
            str: Commande Python par défaut.
        """
        python_commands = ["python3", "python", "py"]
        
        for cmd in python_commands:
            try:
                import subprocess
                result = subprocess.run([cmd, "--version"], 
                                       capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    return cmd
            except Exception:
                continue
        
        # Retour par défaut si aucune commande n'est trouvée
        return "python"
    
    def _save_config(self, config: Optional[ConfigInfo] = None) -> bool:
        """
        Sauvegarde la configuration dans le fichier.
        
        Args:
            config: Configuration à sauvegarder.
                Si None, utilise la configuration actuelle.
        
        Returns:
            bool: True si la sauvegarde réussit, False sinon.
        """
        if config is None:
            config = self.config
        
        try:
            # Créer une sauvegarde de la configuration existante si elle existe
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                shutil.copy2(self.config_path, backup_path)
            
            # Convertir la configuration en dictionnaire
            config_dict = config.to_dict()
            
            # Sauvegarder la nouvelle configuration
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Configuration sauvegardée dans {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
            return False
    
    def save_config(self) -> bool:
        """
        Sauvegarde la configuration actuelle.
        
        Returns:
            bool: True si la sauvegarde réussit, False sinon.
        """
        return self._save_config()
    
    def get_environment(self, env_name: str) -> Optional[EnvironmentInfo]:
        """
        Récupère les informations d'un environnement spécifique.
        
        Args:
            env_name: Nom de l'environnement.
        
        Returns:
            Optional[EnvironmentInfo]: Informations de l'environnement ou None si non trouvé.
        """
        return self.config.environments.get(env_name)
    
    def get_all_environments(self) -> Dict[str, EnvironmentInfo]:
        """
        Récupère tous les environnements.
        
        Returns:
            Dict[str, EnvironmentInfo]: Dictionnaire de tous les environnements.
        """
        return self.config.environments
    
    def add_environment(self, env_info: EnvironmentInfo) -> bool:
        """
        Ajoute un nouvel environnement à la configuration.
        
        Args:
            env_info: Informations de l'environnement.
        
        Returns:
            bool: True si l'ajout réussit, False sinon.
        """
        # Vérifier si l'environnement existe déjà
        if env_info.name in self.config.environments:
            logger.warning(f"L'environnement {env_info.name} existe déjà.")
            return False
        
        # Ajouter l'environnement
        self.config.environments[env_info.name] = env_info
        
        # Sauvegarder la configuration
        return self._save_config()
    
    def update_environment(self, env_info: EnvironmentInfo) -> bool:
        """
        Met à jour la configuration d'un environnement existant.
        
        Args:
            env_info: Nouvelles informations de l'environnement.
        
        Returns:
            bool: True si la mise à jour réussit, False sinon.
        
        Raises:
            ValueError: Si l'environnement n'existe pas.
        """
        if env_info.name not in self.config.environments:
            raise ValueError(f"L'environnement {env_info.name} n'existe pas.")
        
        # Mettre à jour l'environnement
        self.config.environments[env_info.name] = env_info
        
        # Sauvegarder la configuration
        return self._save_config()
    
    def remove_environment(self, env_name: str) -> bool:
        """
        Supprime un environnement de la configuration.
        
        Args:
            env_name: Nom de l'environnement à supprimer.
        
        Returns:
            bool: True si la suppression réussit, False sinon.
        
        Raises:
            ValueError: Si l'environnement n'existe pas.
        """
        if env_name not in self.config.environments:
            raise ValueError(f"L'environnement {env_name} n'existe pas.")
        
        # Supprimer l'environnement
        del self.config.environments[env_name]
        
        # Mettre à jour l'environnement actif si nécessaire
        if self.config.active_env == env_name:
            self.config.active_env = None
        
        # Sauvegarder la configuration
        return self._save_config()
    
    def environment_exists(self, env_name: str) -> bool:
        """
        Vérifie si un environnement existe dans la configuration.
        
        Args:
            env_name: Nom de l'environnement à vérifier.
        
        Returns:
            bool: True si l'environnement existe, False sinon.
        """
        return env_name in self.config.environments
    
    def get_active_environment(self) -> Optional[str]:
        """
        Récupère le nom de l'environnement actif.
        
        Returns:
            Optional[str]: Nom de l'environnement actif ou None si aucun n'est actif.
        """
        return self.config.active_env
    
    def set_active_environment(self, env_name: str) -> bool:
        """
        Définit l'environnement actif.
        
        Args:
            env_name: Nom de l'environnement à activer.
        
        Returns:
            bool: True si l'activation réussit, False sinon.
        
        Raises:
            ValueError: Si l'environnement n'existe pas.
        """
        if not self.environment_exists(env_name):
            raise ValueError(f"L'environnement {env_name} n'existe pas.")
        
        # Définir l'environnement actif
        self.config.active_env = env_name
        
        # Mettre à jour le statut actif dans les environnements
        for name, env in self.config.environments.items():
            env.active = (name == env_name)
        
        # Sauvegarder la configuration
        return self._save_config()
    
    def clear_active_environment(self) -> bool:
        """
        Efface l'environnement actif.
        
        Returns:
            bool: True si l'opération réussit, False sinon.
        """
        # Réinitialiser l'environnement actif
        self.config.active_env = None
        
        # Réinitialiser le statut actif dans tous les environnements
        for env in self.config.environments.values():
            env.active = False
        
        # Sauvegarder la configuration
        return self._save_config()
    
    def get_default_python(self) -> str:
        """
        Récupère la commande Python par défaut.
        
        Returns:
            str: Commande Python par défaut.
        """
        return self.config.default_python
    
    def set_default_python(self, python_command: str) -> bool:
        """
        Définit la commande Python par défaut.
        
        Args:
            python_command: Commande Python à utiliser par défaut.
        
        Returns:
            bool: True si l'opération réussit, False sinon.
        """
        self.config.default_python = python_command
        return self._save_config()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de paramètre.
        
        Args:
            key: Clé du paramètre.
            default: Valeur par défaut si le paramètre n'existe pas.
        
        Returns:
            Any: Valeur du paramètre ou valeur par défaut.
        """
        return self.config.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Définit une valeur de paramètre.
        
        Args:
            key: Clé du paramètre.
            value: Valeur du paramètre.
        
        Returns:
            bool: True si l'opération réussit, False sinon.
        """
        self.config.settings[key] = value
        return self._save_config()
    
    def export_environment_config(self, env_name: str, output_file: Optional[str] = None, 
                                  add_metadata: Optional[Dict[str, Any]] = None) -> Union[str, bool]:
        """
        Exporte la configuration d'un environnement dans un fichier JSON.
        
        Args:
            env_name: Nom de l'environnement à exporter.
            output_file: Chemin du fichier de sortie.
                Si None, retourne le contenu sans l'écrire dans un fichier.
            add_metadata: Métadonnées supplémentaires à inclure.
        
        Returns:
            Union[str, bool]: Contenu JSON si output_file est None,
                sinon True si l'export réussit, False sinon.
        
        Raises:
            ValueError: Si l'environnement n'existe pas.
        """
        if not self.environment_exists(env_name):
            raise ValueError(f"L'environnement {env_name} n'existe pas.")
        
        # Récupérer la configuration de l'environnement
        env_info = self.get_environment(env_name)
        if not env_info:
            raise ValueError(f"Impossible d'obtenir les informations de l'environnement {env_name}.")
        
        # Créer la structure d'export
        export_config = {
            "name": env_name,
            "python_version": env_info.python_version,
            "packages": env_info.packages,
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "exported_by": os.getlogin() if hasattr(os, 'getlogin') else "unknown",
                **(add_metadata or {})
            }
        }
        
        # Convertir en JSON
        json_content = json.dumps(export_config, indent=2, ensure_ascii=False)
        
        # Écrire dans un fichier si spécifié
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_content)
                logger.info(f"Configuration de l'environnement {env_name} exportée dans {output_file}")
                return True
            except Exception as e:
                logger.error(f"Erreur lors de l'export de la configuration: {str(e)}")
                return False
        
        return json_content
    
    def import_environment_config(self, config_file: str, env_name: Optional[str] = None, 
                                  force: bool = False) -> Dict[str, Any]:
        """
        Importe une configuration d'environnement depuis un fichier JSON.
        
        Args:
            config_file: Chemin vers le fichier de configuration.
            env_name: Nom à utiliser pour le nouvel environnement.
                Si None, utilise le nom spécifié dans le fichier.
            force: Si True, écrase un environnement existant.
        
        Returns:
            Dict[str, Any]: Résultat de l'opération d'import.
        
        Raises:
            ValueError: Si le fichier n'existe pas ou n'est pas au format attendu.
        """
        if not os.path.exists(config_file):
            raise ValueError(f"Le fichier de configuration {config_file} n'existe pas.")
        
        try:
            # Charger la configuration depuis le fichier
            with open(config_file, 'r', encoding='utf-8') as f:
                import_config = json.load(f)
            
            # Vérifier le format de la configuration
            if not isinstance(import_config, dict) or "name" not in import_config or "packages" not in import_config:
                raise ValueError("Format de configuration invalide.")
            
            # Déterminer le nom de l'environnement
            target_env_name = env_name or import_config["name"]
            
            # Vérifier si l'environnement existe déjà
            if self.environment_exists(target_env_name) and not force:
                return {
                    "status": "error",
                    "message": f"L'environnement {target_env_name} existe déjà. Utilisez --force pour l'écraser."
                }
            
            # Créer une nouvelle instance d'EnvironmentInfo
            python_version = import_config.get("python_version", self.get_default_python())
            
            # L'objet retourné contient les informations nécessaires pour créer l'environnement
            return {
                "status": "success",
                "env_name": target_env_name,
                "config": {
                    "python_version": python_version,
                    "packages": import_config.get("packages", []),
                    "imported_from": os.path.basename(config_file),
                    "import_metadata": import_config.get("metadata", {})
                }
            }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de décodage JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Erreur lors de l'import de la configuration: {str(e)}")
    
    def get_config_backup_path(self) -> str:
        """
        Obtient le chemin du fichier de sauvegarde de la configuration.
        
        Returns:
            str: Chemin du fichier de sauvegarde.
        """
        return f"{self.config_path}.bak"
    
    def restore_config_backup(self) -> bool:
        """
        Restaure la configuration à partir de la sauvegarde.
        
        Returns:
            bool: True si la restauration réussit, False sinon.
        """
        backup_path = self.get_config_backup_path()
        
        if not os.path.exists(backup_path):
            logger.error("Aucun fichier de sauvegarde trouvé.")
            return False
        
        try:
            # Sauvegarder la configuration actuelle comme .old
            if os.path.exists(self.config_path):
                old_path = f"{self.config_path}.old"
                shutil.copy2(self.config_path, old_path)
            
            # Restaurer depuis la sauvegarde
            shutil.copy2(backup_path, self.config_path)
            
            # Recharger la configuration
            self.config = self._load_config()
            
            logger.info(f"Configuration restaurée depuis {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la restauration de la configuration: {str(e)}")
            return False