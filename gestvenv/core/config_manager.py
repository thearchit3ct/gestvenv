"""
Module de gestion de la configuration pour GestVenv.

Ce module fournit les fonctionnalités pour stocker et récupérer
les configurations des environnements virtuels, ainsi que pour
gérer l'import/export des configurations et la sauvegarde/restauration.
"""

import os
import json
import logging
import shutil
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set

from .models import ConfigInfo, EnvironmentInfo

# Configuration du logging
logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Exception levée lors d'erritions de validation de configuration."""
    pass

class ConfigBackupError(Exception):
    """Exception levée lors d'erreurs de sauvegarde/restauration de configuration."""
    pass

class ConfigManager:
    """Gestionnaire de configuration pour GestVenv."""
    
    # Version de la configuration pour la migration
    CONFIG_VERSION = "1.2.0"
    
    # Schéma de validation de base
    REQUIRED_KEYS = {"environments", "active_env", "default_python", "settings"}
    
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
        
        # Chemins pour les sauvegardes
        self.backup_dir = self.config_path.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Charger ou créer la configuration
        self.config = self._load_config()
        
        # Sauvegarder automatiquement lors de la première initialisation
        self._auto_backup()
    
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
                
                # Valider la configuration
                self._validate_config_structure(config_dict)
                
                # Migrer si nécessaire
                config_dict = self._migrate_config_if_needed(config_dict)
                
                logger.debug(f"Configuration chargée depuis {self.config_path}")
                return ConfigInfo.from_dict(config_dict)
                
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logging.error(f"Erreur lors du chargement de la configuration: {e}")
                # Créer une sauvegarde du fichier corrompu
                if config_path and Path(config_path).exists():
                    self._create_backup(config_path, corrupted=True)
                
                # Appeler explicitement _create_default_config
                self.config = self._create_default_config()
                return False
            except ConfigValidationError as e:
                logger.error(f"Configuration invalide: {str(e)}")
                return self._handle_corrupted_config()
            except Exception as e:
                logger.error(f"Erreur inattendue lors du chargement de la configuration: {str(e)}")
                return self._handle_corrupted_config()
        else:
            logger.info(f"Aucun fichier de configuration trouvé. Création d'une configuration par défaut.")
            return self._create_default_config()
    
    def _validate_config_structure(self, config_dict: Dict[str, Any]) -> None:
        """
        Valide la structure de base d'une configuration.
        
        Args:
            config_dict: Dictionnaire de configuration à valider.
            
        Raises:
            ConfigValidationError: Si la configuration est invalide.
        """
        # Vérifier les clés requises
        missing_keys = self.REQUIRED_KEYS - set(config_dict.keys())
        if missing_keys:
            raise ConfigValidationError(f"Clés manquantes dans la configuration: {missing_keys}")
        
        # Vérifier les types
        if not isinstance(config_dict["environments"], dict):
            raise ConfigValidationError("Le champ 'environments' doit être un dictionnaire")
        
        if config_dict["active_env"] is not None and not isinstance(config_dict["active_env"], str):
            raise ConfigValidationError("Le champ 'active_env' doit être une chaîne ou null")
        
        if not isinstance(config_dict["default_python"], str):
            raise ConfigValidationError("Le champ 'default_python' doit être une chaîne")
        
        if not isinstance(config_dict["settings"], dict):
            raise ConfigValidationError("Le champ 'settings' doit être un dictionnaire")
        
        # Vérifier la cohérence de l'environnement actif
        if config_dict["active_env"] and config_dict["active_env"] not in config_dict["environments"]:
            logger.warning(f"Environnement actif '{config_dict['active_env']}' n'existe pas. Réinitialisation.")
            config_dict["active_env"] = None
    
    def _migrate_config_if_needed(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migre une configuration vers la version actuelle si nécessaire.
        
        Args:
            config_dict: Configuration à migrer.
            
        Returns:
            Configuration migrée.
        """
        current_version = config_dict.get("version", "1.0.0")
        
        if current_version == self.CONFIG_VERSION:
            return config_dict
        
        logger.info(f"Migration de la configuration de {current_version} vers {self.CONFIG_VERSION}")
        
        # Sauvegarder avant migration
        self._create_backup("pre_migration")
        
        # Migration étape par étape
        if self._version_compare(current_version, "1.1.0") < 0:
            config_dict = self._migrate_to_v1_1_0(config_dict)
        
        if self._version_compare(current_version, "1.2.0") < 0:
            config_dict = self._migrate_to_v1_2_0(config_dict)
        
        # Mettre à jour la version
        config_dict["version"] = self.CONFIG_VERSION
        config_dict["migrated_at"] = datetime.now().isoformat()
        
        return config_dict
    
    def _migrate_to_v1_1_0(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Migre vers la version 1.1.0."""
        # Ajouter les nouveaux paramètres de cache
        settings = config_dict.get("settings", {})
        
        cache_settings = {
            "use_package_cache": settings.get("package_cache_enabled", True),
            "cache_max_size_mb": 5000,
            "cache_max_age_days": 90,
            "offline_mode": False
        }
        
        settings.update(cache_settings)
        config_dict["settings"] = settings
        
        # Migrer les informations d'environnements
        for env_name, env_data in config_dict.get("environments", {}).items():
            if isinstance(env_data, dict):
                # Ajouter les champs manquants
                if "health" not in env_data:
                    env_data["health"] = {
                        "exists": True,
                        "python_available": True,
                        "pip_available": True,
                        "activation_script_exists": True
                    }
                
                if "metadata" not in env_data:
                    env_data["metadata"] = {}
        
        return config_dict
    
    def _migrate_to_v1_2_0(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Migre vers la version 1.2.0."""
        # Ajouter les nouveaux paramètres avancés
        settings = config_dict.get("settings", {})
        
        advanced_settings = {
            "check_updates_on_activate": settings.get("check_updates_on_activate", True),
            "auto_cleanup_cache": False,
            "parallel_operations": True,
            "operation_timeout": 300,
            "backup_retention_days": 30
        }
        
        settings.update(advanced_settings)
        config_dict["settings"] = settings
        
        # Ajouter les métadonnées de configuration
        config_dict["created_at"] = config_dict.get("created_at", datetime.now().isoformat())
        config_dict["last_modified"] = datetime.now().isoformat()
        
        return config_dict
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """
        Compare deux versions sémantiques.
        
        Returns:
            -1 si version1 < version2, 0 si égales, 1 si version1 > version2
        """
        def version_to_tuple(v: str) -> Tuple[int, ...]:
            return tuple(map(int, v.split('.')))
        
        v1 = version_to_tuple(version1)
        v2 = version_to_tuple(version2)
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    
    def _handle_corrupted_config(self) -> ConfigInfo:
        """Gère une configuration corrompue."""
        # Créer une sauvegarde du fichier corrompu
        if self.config_path.exists():
            corrupted_backup = self.backup_dir / f"corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                shutil.copy2(self.config_path, corrupted_backup)
                logger.warning(f"Sauvegarde du fichier corrompu créée: {corrupted_backup}")
            except Exception as e:
                logger.error(f"Impossible de sauvegarder le fichier corrompu: {str(e)}")
        
        # Essayer de restaurer depuis la sauvegarde la plus récente
        latest_backup = self._get_latest_backup()
        if latest_backup:
            try:
                logger.info(f"Tentative de restauration depuis {latest_backup}")
                return self._restore_from_backup_file(latest_backup)
            except Exception as e:
                logger.error(f"Échec de la restauration depuis la sauvegarde: {str(e)}")
        
        # Créer une nouvelle configuration par défaut
        logger.warning("Création d'une nouvelle configuration par défaut")
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
        
        # Ajouter les métadonnées
        default_config.settings.update({
            "version": self.CONFIG_VERSION,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        })
        
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
                                       capture_output=True, shell=False, text=True, check=False)
                if result.returncode == 0:
                    logger.debug(f"Python par défaut détecté: {cmd}")
                    return cmd
            except Exception:
                continue
        
        # Retour par défaut si aucune commande n'est trouvée
        logger.warning("Aucune commande Python détectée, utilisation de 'python' par défaut")
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
            
            # Mettre à jour les métadonnées
            config.settings["last_modified"] = datetime.now().isoformat()
            
            # Convertir la configuration en dictionnaire
            config_dict = config.to_dict()
            
            # Ajouter les métadonnées de version
            config_dict["version"] = self.CONFIG_VERSION
            
            # Sauvegarder avec validation
            temp_path = self.config_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            # Valider le fichier temporaire
            with open(temp_path, 'r', encoding='utf-8') as f:
                test_config = json.load(f)
                self._validate_config_structure(test_config)
            
            # Remplacer le fichier original
            temp_path.replace(self.config_path)
            
            logger.debug(f"Configuration sauvegardée dans {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
            
            # Nettoyer le fichier temporaire si il existe
            temp_path = self.config_path.with_suffix('.tmp')
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            
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
        success = self._save_config()
        
        if success:
            logger.info(f"Environnement {env_info.name} ajouté à la configuration")
        
        return success
    
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
        success = self._save_config()
        
        if success:
            logger.debug(f"Environnement {env_info.name} mis à jour")
        
        return success
    
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
        success = self._save_config()
        
        if success:
            logger.info(f"Environnement {env_name} supprimé de la configuration")
        
        return success
    
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
        success = self._save_config()
        
        if success:
            logger.info(f"Environnement actif défini à: {env_name}")
        
        return success
    
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
        success = self._save_config()
        
        if success:
            logger.info("Environnement actif effacé")
        
        return success
    
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
        success = self._save_config()
        
        if success:
            logger.info(f"Commande Python par défaut définie à: {python_command}")
        
        return success
    
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
        success = self._save_config()
        
        if success:
            logger.debug(f"Paramètre {key} défini à: {value}")
        
        return success
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Met à jour plusieurs paramètres en une fois.
        
        Args:
            settings: Dictionnaire des paramètres à mettre à jour.
        
        Returns:
            bool: True si l'opération réussit, False sinon.
        """
        self.config.settings.update(settings)
        success = self._save_config()
        
        if success:
            logger.info(f"Paramètres mis à jour: {list(settings.keys())}")
        
        return success
    
    def remove_setting(self, key: str) -> bool:
        """
        Supprime un paramètre.
        
        Args:
            key: Clé du paramètre à supprimer.
        
        Returns:
            bool: True si l'opération réussit, False sinon.
        """
        if key in self.config.settings:
            del self.config.settings[key]
            success = self._save_config()
            
            if success:
                logger.debug(f"Paramètre {key} supprimé")
            
            return success
        
        return True  # Déjà supprimé
    
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
            "export_version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "exported_by": "gestvenv",
            "environment": {
                "name": env_name,
                "python_version": env_info.python_version,
                "created_at": env_info.created_at.isoformat() if hasattr(env_info.created_at, 'isoformat') else str(env_info.created_at),
                "packages": env_info.packages,
                "metadata": env_info.metadata if hasattr(env_info, 'metadata') else {}
            }
        }
        
        # Ajouter les métadonnées supplémentaires
        if add_metadata:
            export_config["environment"]["metadata"].update(add_metadata)
        
        # Convertir en JSON
        json_content = json.dumps(export_config, indent=2, ensure_ascii=False)
        
        # Écrire dans un fichier si spécifié
        if output_file:
            try:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
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
            if "environment" not in import_config:
                # Format ancien ou direct
                if "name" in import_config and "packages" in import_config:
                    env_config = import_config
                else:
                    raise ValueError("Format de configuration invalide.")
            else:
                # Format nouveau avec métadonnées
                env_config = import_config["environment"]
            
            # Déterminer le nom de l'environnement
            target_env_name = env_name or env_config.get("name")
            if not target_env_name:
                raise ValueError("Nom d'environnement non spécifié dans la configuration.")
            
            # Vérifier si l'environnement existe déjà
            if self.environment_exists(target_env_name) and not force:
                return {
                    "status": "error",
                    "message": f"L'environnement {target_env_name} existe déjà. Utilisez --force pour l'écraser."
                }
            
            # Préparer les informations pour la création
            python_version = env_config.get("python_version", self.get_default_python())
            packages = env_config.get("packages", [])
            metadata = env_config.get("metadata", {})
            
            # Ajouter les métadonnées d'import
            metadata["imported_from"] = os.path.basename(config_file)
            metadata["imported_at"] = datetime.now().isoformat()
            if "export_version" in import_config:
                metadata["source_export_version"] = import_config["export_version"]
            
            return {
                "status": "success",
                "env_name": target_env_name,
                "config": {
                    "python_version": python_version,
                    "packages": packages,
                    "metadata": metadata
                }
            }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de décodage JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Erreur lors de l'import de la configuration: {str(e)}")
    
    def create_backup(self, backup_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Crée une sauvegarde de la configuration actuelle.
        
        Args:
            backup_name: Nom de la sauvegarde (optionnel).
        
        Returns:
            Tuple[bool, str]: (succès, chemin de la sauvegarde ou message d'erreur).
        """
        try:
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_path = self.backup_dir / f"{backup_name}.json"
            
            # Créer la sauvegarde avec métadonnées
            backup_data = {
                "backup_version": "1.0",
                "created_at": datetime.now().isoformat(),
                "original_config_path": str(self.config_path),
                "config": self.config.to_dict()
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Sauvegarde créée: {backup_path}")
            return True, str(backup_path)
            
        except Exception as e:
            error_msg = f"Erreur lors de la création de la sauvegarde: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _create_backup(self, backup_name: str) -> None:
        """Crée une sauvegarde interne (sans gestion d'erreur)."""
        try:
            self.create_backup(backup_name)
        except Exception as e:
            logger.warning(f"Impossible de créer la sauvegarde {backup_name}: {str(e)}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Liste les sauvegardes disponibles.
        
        Returns:
            List[Dict[str, Any]]: Liste des sauvegardes avec leurs métadonnées.
        """
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("*.json"):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                    
                    backup_info = {
                        "name": backup_file.stem,
                        "path": str(backup_file),
                        "size": backup_file.stat().st_size,
                        "created_at": backup_data.get("created_at", "Unknown"),
                        "version": backup_data.get("backup_version", "Unknown")
                    }
                    
                    # Ajouter des informations sur le contenu
                    if "config" in backup_data:
                        config = backup_data["config"]
                        backup_info["environments_count"] = len(config.get("environments", {}))
                        backup_info["active_env"] = config.get("active_env")
                    
                    backups.append(backup_info)
                    
                except Exception as e:
                    logger.warning(f"Impossible de lire la sauvegarde {backup_file}: {str(e)}")
            
            # Trier par date de création (plus récent en premier)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            logger.error(f"Erreur lors de la liste des sauvegardes: {str(e)}")
        
        return backups
    
    def restore_from_backup(self, backup_name: str) -> Tuple[bool, str]:
        """
        Restaure la configuration depuis une sauvegarde.
        
        Args:
            backup_name: Nom de la sauvegarde à restaurer.
        
        Returns:
            Tuple[bool, str]: (succès, message).
        """
        backup_path = self.backup_dir / f"{backup_name}.json"
        
        if not backup_path.exists():
            return False, f"Sauvegarde '{backup_name}' non trouvée"
        
        try:
            return self._restore_from_backup_file(backup_path)
        except Exception as e:
            error_msg = f"Erreur lors de la restauration: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _restore_from_backup_file(self, backup_path: Path) -> ConfigInfo:
        """Restaure depuis un fichier de sauvegarde spécifique."""
        # Créer une sauvegarde de la configuration actuelle avant restauration
        self._create_backup("pre_restore")
        
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        if "config" not in backup_data:
            raise ConfigBackupError("Format de sauvegarde invalide")
        
        # Valider la configuration de sauvegarde
        config_dict = backup_data["config"]
        self._validate_config_structure(config_dict)
        
        # Créer l'objet ConfigInfo
        restored_config = ConfigInfo.from_dict(config_dict)
        
        # Mettre à jour la configuration actuelle
        self.config = restored_config
        
        # Sauvegarder la configuration restaurée
        if not self._save_config():
            raise ConfigBackupError("Impossible de sauvegarder la configuration restaurée")
        
        logger.info(f"Configuration restaurée depuis {backup_path}")
        return restored_config
    
    def _get_latest_backup(self) -> Optional[Path]:
        """Récupère le chemin de la sauvegarde la plus récente."""
        backups = self.list_backups()
        if backups:
            return Path(backups[0]["path"])
        return None
    
    def delete_backup(self, backup_name: str) -> Tuple[bool, str]:
        """
        Supprime une sauvegarde.
        
        Args:
            backup_name: Nom de la sauvegarde à supprimer.
        
        Returns:
            Tuple[bool, str]: (succès, message).
        """
        backup_path = self.backup_dir / f"{backup_name}.json"
        
        if not backup_path.exists():
            return False, f"Sauvegarde '{backup_name}' non trouvée"
        
        try:
            backup_path.unlink()
            logger.info(f"Sauvegarde supprimée: {backup_name}")
            return True, f"Sauvegarde '{backup_name}' supprimée avec succès"
        except Exception as e:
            error_msg = f"Erreur lors de la suppression de la sauvegarde: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def clean_old_backups(self, days: int = 30) -> Tuple[int, int]:
        """
        Nettoie les anciennes sauvegardes.
        
        Args:
            days: Âge maximum des sauvegardes à conserver.
        
        Returns:
            Tuple[int, int]: (nombre de sauvegardes supprimées, espace libéré en octets).
        """
        deleted_count = 0
        freed_space = 0
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            for backup_file in self.backup_dir.glob("*.json"):
                try:
                    stat = backup_file.stat()
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    if modified_time < cutoff_date:
                        freed_space += stat.st_size
                        backup_file.unlink()
                        deleted_count += 1
                        logger.debug(f"Ancienne sauvegarde supprimée: {backup_file.name}")
                        
                except Exception as e:
                    logger.warning(f"Erreur lors de la suppression de {backup_file}: {str(e)}")
            
            if deleted_count > 0:
                logger.info(f"Nettoyage terminé: {deleted_count} sauvegarde(s) supprimée(s), {freed_space // 1024} KB libérés")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des sauvegardes: {str(e)}")
        
        return deleted_count, freed_space
    
    def reset_config(self, keep_environments: bool = False) -> Tuple[bool, str]:
        """
        Remet la configuration à zéro.
        
        Args:
            keep_environments: Si True, conserve les environnements existants.
        
        Returns:
            Tuple[bool, str]: (succès, message).
        """
        try:
            # Créer une sauvegarde avant reset
            self._create_backup("pre_reset")
            
            if keep_environments:
                # Conserver les environnements existants
                environments = self.config.environments
                active_env = self.config.active_env
                
                # Créer une nouvelle configuration
                self.config = self._create_default_config()
                
                # Restaurer les environnements
                self.config.environments = environments
                self.config.active_env = active_env
                
                message = "Configuration réinitialisée (environnements conservés)"
            else:
                # Reset complet
                self.config = self._create_default_config()
                message = "Configuration complètement réinitialisée"
            
            # Sauvegarder la nouvelle configuration
            if self._save_config():
                logger.info(message)
                return True, message
            else:
                return False, "Erreur lors de la sauvegarde de la configuration réinitialisée"
                
        except Exception as e:
            error_msg = f"Erreur lors de la réinitialisation: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _auto_backup(self) -> None:
        """Crée automatiquement une sauvegarde périodique."""
        try:
            # Vérifier si une sauvegarde automatique est nécessaire
            auto_backup_path = self.backup_dir / "auto_backup.json"
            should_backup = True
            
            if auto_backup_path.exists():
                # Vérifier l'âge de la dernière sauvegarde automatique
                stat = auto_backup_path.stat()
                last_backup = datetime.fromtimestamp(stat.st_mtime)
                if (datetime.now() - last_backup).days < 1:
                    should_backup = False
            
            if should_backup:
                self.create_backup("auto_backup")
                
        except Exception as e:
            logger.debug(f"Erreur lors de la sauvegarde automatique: {str(e)}")
    
    def validate_integrity(self) -> Tuple[bool, List[str]]:
        """
        Valide l'intégrité de la configuration.
        
        Returns:
            Tuple[bool, List[str]]: (intégrité OK, liste des problèmes détectés).
        """
        issues = []
        
        try:
            # Vérifier la structure de base
            self._validate_config_structure(self.config.to_dict())
            
            # Vérifier la cohérence des environnements
            for env_name, env_info in self.config.environments.items():
                if env_name != env_info.name:
                    issues.append(f"Nom incohérent pour l'environnement {env_name}")
                
                if not hasattr(env_info, 'path') or not env_info.path:
                    issues.append(f"Chemin manquant pour l'environnement {env_name}")
                
                if not hasattr(env_info, 'python_version') or not env_info.python_version:
                    issues.append(f"Version Python manquante pour l'environnement {env_name}")
            
            # Vérifier l'environnement actif
            if self.config.active_env and self.config.active_env not in self.config.environments:
                issues.append(f"Environnement actif '{self.config.active_env}' n'existe pas")
            
            # Vérifier les paramètres critiques
            required_settings = ["auto_activate", "package_cache_enabled"]
            for setting in required_settings:
                if setting not in self.config.settings:
                    issues.append(f"Paramètre manquant: {setting}")
            
        except ConfigValidationError as e:
            issues.append(f"Erreur de validation: {str(e)}")
        except Exception as e:
            issues.append(f"Erreur inattendue lors de la validation: {str(e)}")
        
        return len(issues) == 0, issues
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé de la configuration.
        
        Returns:
            Dict[str, Any]: Résumé de la configuration.
        """
        return {
            "config_path": str(self.config_path),
            "version": self.config.settings.get("version", "Unknown"),
            "created_at": self.config.settings.get("created_at", "Unknown"),
            "last_modified": self.config.settings.get("last_modified", "Unknown"),
            "total_environments": len(self.config.environments),
            "active_environment": self.config.active_env,
            "default_python": self.config.default_python,
            "offline_mode": self.get_setting("offline_mode", False),
            "cache_enabled": self.get_setting("use_package_cache", True),
            "settings_count": len(self.config.settings),
            "backup_count": len(self.list_backups())
        }
    
    # Méthodes de compatibilité pour les fonctionnalités de cache
    def set_offline_mode(self, enabled: bool) -> bool:
        """
        Active ou désactive le mode hors ligne.
        
        Args:
            enabled: True pour activer, False pour désactiver
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        return self.set_setting("offline_mode", enabled)
    
    def get_offline_mode(self) -> bool:
        """
        Vérifie si le mode hors ligne est activé.
        
        Returns:
            bool: True si le mode hors ligne est activé
        """
        return self.get_setting("offline_mode", False)
    
    def set_cache_enabled(self, enabled: bool) -> bool:
        """
        Active ou désactive l'utilisation du cache de packages.
        
        Args:
            enabled: True pour activer, False pour désactiver
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        return self.set_setting("use_package_cache", enabled)
    
    def get_cache_enabled(self) -> bool:
        """
        Vérifie si l'utilisation du cache de packages est activée.
        
        Returns:
            bool: True si l'utilisation du cache est activée
        """
        return self.get_setting("use_package_cache", True)

