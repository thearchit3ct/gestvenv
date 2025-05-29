"""
Module de gestion de la configuration pour GestVenv v1.1.

Ce module fournit les fonctionnalités pour stocker et récupérer
les configurations des environnements virtuels, avec support étendu
pour pyproject.toml, backends multiples et migration automatique.

Version 1.1 - Nouvelles fonctionnalités:
- Migration automatique v1.0 -> v1.1
- Support backends multiples (pip, uv, poetry, pdm)
- Templates de configuration
- Alias globaux et locaux
- Paramètres par backend
- Sauvegarde et restauration
- Validation et rollback
"""

import os
import json
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from .models import (
    ConfigInfo, EnvironmentInfo, BackendType, SourceFileType,
    PyProjectInfo, ValidationError, MigrationInfo,
    create_default_config_info, validate_environment_name
)

# Configuration du logging
logger = logging.getLogger(__name__)


class ConfigManager:
    """Gestionnaire de configuration pour GestVenv v1.1."""
    
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
            self.config_path = self._get_default_config_path()
        
        # Créer le répertoire de configuration s'il n'existe pas
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Charger ou créer la configuration
        self.config = self._load_config()
        
        # Effectuer la migration si nécessaire
        if self._needs_migration():
            logger.info("Migration de configuration détectée")
            self._perform_migration()
    
    def _get_default_config_path(self) -> Path:
        """
        Obtient le chemin par défaut du fichier de configuration.
        
        Returns:
            Path: Chemin vers le fichier de configuration par défaut.
        """
        from ..utils.path_utils import get_default_data_dir
        
        config_dir = get_default_data_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        
        return config_dir / 'config.json'
    
    def _load_config(self) -> ConfigInfo:
        """
        Charge la configuration depuis le fichier.
        Si le fichier n'existe pas, crée une configuration par défaut.
        
        Returns:
            ConfigInfo: Configuration chargée ou par défaut.
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                
                logger.debug(f"Configuration chargée depuis {self.config_path}")
                return ConfigInfo.from_dict(config_dict)
                
            except json.JSONDecodeError as e:
                logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
                # Créer une sauvegarde du fichier corrompu
                self._create_backup("corrupted")
                logger.warning(f"Sauvegarde du fichier corrompu créée")
                # Créer une nouvelle configuration
                return self._create_default_config()
                
            except Exception as e:
                logger.error(f"Erreur inattendue lors du chargement de la configuration: {str(e)}")
                return self._create_default_config()
        else:
            logger.info("Aucun fichier de configuration trouvé. Création d'une configuration par défaut.")
            return self._create_default_config()
    
    def _create_default_config(self) -> ConfigInfo:
        """
        Crée une configuration par défaut.
        
        Returns:
            ConfigInfo: Configuration par défaut.
        """
        default_config = create_default_config_info()
        default_config.default_python = self._detect_default_python()
        
        # Sauvegarder la configuration par défaut
        self._save_config(default_config)
        
        return default_config
    
    def _detect_default_python(self) -> str:
        """
        Détecte la commande Python par défaut sur le système.
        
        Returns:
            str: Commande Python par défaut.
        """
        from ..services.system_service import SystemService
        
        system_service = SystemService()
        available_versions = system_service.get_available_python_versions()
        
        if available_versions:
            # Préférer python3, puis python, puis la première version disponible
            for preferred in ["python3", "python"]:
                for version_info in available_versions:
                    if version_info["command"] == preferred:
                        return preferred
            
            # Prendre la première version disponible
            return available_versions[0]["command"]
        
        # Retour par défaut si aucune commande n'est trouvée
        return "python3" if os.name != 'nt' else "python"
    
    def _needs_migration(self) -> bool:
        """
        Vérifie si la configuration nécessite une migration.
        
        Returns:
            bool: True si une migration est nécessaire.
        """
        current_version = self.config.config_version
        target_version = "1.1.0"
        
        # Comparaison de versions simple
        if current_version != target_version:
            # Vérifier si c'est une version antérieure
            if not hasattr(self.config, 'preferred_backend') or not hasattr(self.config, 'backend_settings'):
                return True
        
        return False
    
    def _perform_migration(self) -> bool:
        """
        Effectue la migration de configuration v1.0 -> v1.1.
        
        Returns:
            bool: True si la migration réussit.
        """
        migration_info = MigrationInfo(
            from_version=self.config.config_version,
            to_version="1.1.0",
            migration_type="config",
            started_at=datetime.now()
        )
        
        try:
            # Créer une sauvegarde avant migration
            backup_path = self._create_backup("pre_migration")
            migration_info.backup_path = backup_path
            migration_info.rollback_available = True
            
            logger.info(f"Migration de la configuration {migration_info.from_version} -> {migration_info.to_version}")
            
            # Sauvegarder l'ancienne version pour référence
            old_version = self.config.config_version
            self.config.migrated_from_version = old_version
            self.config.migration_date = datetime.now()
            
            # Migrer les paramètres
            self._migrate_settings()
            
            # Migrer les environnements
            self._migrate_environments()
            
            # Initialiser les nouveaux champs
            self._initialize_v11_features()
            
            # Mettre à jour la version
            self.config.config_version = "1.1.0"
            
            # Sauvegarder la configuration migrée
            if not self._save_config():
                raise Exception("Échec de la sauvegarde de la configuration migrée")
            
            migration_info.success = True
            migration_info.completed_at = datetime.now()
            
            logger.info(f"Migration réussie en {migration_info.duration:.2f}s")
            return True
            
        except Exception as e:
            migration_info.success = False
            migration_info.completed_at = datetime.now()
            migration_info.errors.append(ValidationError(
                field="migration",
                message=f"Erreur de migration: {str(e)}",
                severity="error"
            ))
            
            logger.error(f"Échec de la migration: {str(e)}")
            
            # Tentative de rollback
            if migration_info.backup_path and migration_info.backup_path.exists():
                try:
                    self._restore_from_backup(migration_info.backup_path)
                    logger.info("Rollback effectué avec succès")
                except Exception as rollback_error:
                    logger.error(f"Échec du rollback: {str(rollback_error)}")
            
            return False
    
    def _migrate_settings(self) -> None:
        """Migre les paramètres de configuration v1.0 vers v1.1."""
        # Ajouter les nouveaux paramètres par défaut
        new_settings = {
            "preferred_backend": "auto",
            "pyproject_support": True,
            "show_migration_hints": True,
            "auto_detect_project_type": True,
            "performance_monitoring": True,
            "security_scanning": True,
            "cache_optimization": True,
            "parallel_installs": True,
            "max_parallel_jobs": 4,
            "install_timeout": 300,
            "health_check_interval": 86400,
            "auto_cleanup_orphaned": True,
            "backup_on_migration": True
        }
        
        for key, value in new_settings.items():
            if key not in self.config.settings:
                self.config.settings[key] = value
    
    def _migrate_environments(self) -> None:
        """Migre les environnements existants vers le nouveau format."""
        for env_name, env_info in self.config.environments.items():
            # Ajouter les nouveaux champs avec des valeurs par défaut
            if not hasattr(env_info, 'backend_type') or env_info.backend_type is None:
                env_info.backend_type = BackendType.PIP
            
            if not hasattr(env_info, 'source_file_type') or env_info.source_file_type is None:
                env_info.source_file_type = SourceFileType.REQUIREMENTS
            
            if not hasattr(env_info, 'migrated_from_version'):
                env_info.migrated_from_version = "1.0.0"
            
            # Initialiser les nouvelles listes
            if not hasattr(env_info, 'aliases'):
                env_info.aliases = []
            if not hasattr(env_info, 'tags'):
                env_info.tags = []
            if not hasattr(env_info, 'migration_notes'):
                env_info.migration_notes = []
            
            # Initialiser les statistiques
            if not hasattr(env_info, 'usage_count'):
                env_info.usage_count = 0
            if not hasattr(env_info, 'cache_size'):
                env_info.cache_size = 0
    
    def _initialize_v11_features(self) -> None:
        """Initialise les nouvelles fonctionnalités v1.1."""
        # Initialiser le backend préféré
        if not hasattr(self.config, 'preferred_backend'):
            self.config.preferred_backend = BackendType.PIP
        
        # Initialiser les paramètres par backend
        if not hasattr(self.config, 'backend_settings') or not self.config.backend_settings:
            self.config.backend_settings = {
                "pip": {
                    "index_url": None,
                    "extra_index_urls": [],
                    "trusted_hosts": [],
                    "timeout": 60,
                    "retries": 3
                },
                "uv": {
                    "python_preference": "managed",
                    "resolution": "highest",
                    "prerelease": "disallow",
                    "compile_bytecode": True
                },
                "poetry": {
                    "virtualenvs_create": True,
                    "virtualenvs_in_project": False
                }
            }
        
        # Initialiser les alias globaux
        if not hasattr(self.config, 'global_aliases'):
            self.config.global_aliases = {}
        
        # Initialiser les templates
        if not hasattr(self.config, 'templates'):
            self.config.templates = {}
    
    def _create_backup(self, suffix: str = None) -> Path:
        """
        Crée une sauvegarde de la configuration actuelle.
        
        Args:
            suffix: Suffixe à ajouter au nom du fichier de sauvegarde.
            
        Returns:
            Path: Chemin vers le fichier de sauvegarde.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if suffix:
            backup_name = f"config_backup_{suffix}_{timestamp}.json"
        else:
            backup_name = f"config_backup_{timestamp}.json"
        
        backup_path = self.config_path.parent / "backups" / backup_name
        backup_path.parent.mkdir(exist_ok=True)
        
        try:
            shutil.copy2(self.config_path, backup_path)
            logger.debug(f"Sauvegarde créée: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Erreur lors de la création de la sauvegarde: {str(e)}")
            raise
    
    def _restore_from_backup(self, backup_path: Path) -> bool:
        """
        Restaure la configuration depuis une sauvegarde.
        
        Args:
            backup_path: Chemin vers le fichier de sauvegarde.
            
        Returns:
            bool: True si la restauration réussit.
        """
        try:
            if not backup_path.exists():
                raise FileNotFoundError(f"Sauvegarde non trouvée: {backup_path}")
            
            # Sauvegarder la configuration actuelle
            current_backup = self._create_backup("before_restore")
            
            # Restaurer depuis la sauvegarde
            shutil.copy2(backup_path, self.config_path)
            
            # Recharger la configuration
            self.config = self._load_config()
            
            logger.info(f"Configuration restaurée depuis {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la restauration: {str(e)}")
            return False
    
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
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.json.bak')
                shutil.copy2(self.config_path, backup_path)
            
            # Convertir la configuration en dictionnaire
            config_dict = config.to_dict()
            
            # Écrire dans un fichier temporaire d'abord pour éviter la corruption
            with tempfile.NamedTemporaryFile(
                mode='w', 
                encoding='utf-8', 
                dir=self.config_path.parent,
                delete=False
            ) as temp_file:
                json.dump(config_dict, temp_file, indent=2, ensure_ascii=False)
                temp_path = Path(temp_file.name)
            
            # Remplacer le fichier de configuration
            temp_path.replace(self.config_path)
            
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
        # Recherche directe par nom
        if env_name in self.config.environments:
            return self.config.environments[env_name]
        
        # Recherche par alias
        env_by_alias = self.config.get_environment_by_alias(env_name)
        if env_by_alias:
            return env_by_alias
        
        return None
    
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
        # Valider le nom de l'environnement
        validation_errors = validate_environment_name(env_info.name)
        if validation_errors:
            logger.error(f"Nom d'environnement invalide: {validation_errors[0].message}")
            return False
        
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
        
        # Nettoyer les alias globaux qui pointent vers cet environnement
        aliases_to_remove = [
            alias for alias, target in self.config.global_aliases.items() 
            if target == env_name
        ]
        for alias in aliases_to_remove:
            del self.config.global_aliases[alias]
        
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
        return env_name in self.config.environments or self.config.get_environment_by_alias(env_name) is not None
    
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
        
        # Résoudre l'alias si nécessaire
        env_info = self.get_environment(env_name)
        if env_info:
            actual_name = env_info.name
        else:
            actual_name = env_name
        
        # Définir l'environnement actif
        self.config.active_env = actual_name
        
        # Mettre à jour le statut actif dans les environnements
        for name, env in self.config.environments.items():
            env.active = (name == actual_name)
            if env.active:
                env.update_usage_stats()
        
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
    
    # Méthodes pour les paramètres Python et backends
    
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
    
    def get_preferred_backend(self) -> BackendType:
        """
        Récupère le backend préféré.
        
        Returns:
            BackendType: Backend préféré.
        """
        return self.config.preferred_backend
    
    def set_preferred_backend(self, backend: Union[str, BackendType]) -> bool:
        """
        Définit le backend préféré.
        
        Args:
            backend: Backend à utiliser par défaut.
        
        Returns:
            bool: True si l'opération réussit, False sinon.
        """
        if isinstance(backend, str):
            if backend == "auto":
                backend = BackendType.PIP  # Default pour auto
            else:
                try:
                    backend = BackendType(backend)
                except ValueError:
                    logger.error(f"Backend invalide: {backend}")
                    return False
        
        self.config.preferred_backend = backend
        return self._save_config()
    
    def get_backend_setting(self, backend: Union[str, BackendType], setting: str, default: Any = None) -> Any:
        """
        Récupère un paramètre spécifique à un backend.
        
        Args:
            backend: Nom du backend.
            setting: Nom du paramètre.
            default: Valeur par défaut.
        
        Returns:
            Any: Valeur du paramètre.
        """
        return self.config.get_backend_setting(backend, setting, default)
    
    def set_backend_setting(self, backend: Union[str, BackendType], setting: str, value: Any) -> bool:
        """
        Définit un paramètre spécifique à un backend.
        
        Args:
            backend: Nom du backend.
            setting: Nom du paramètre.
            value: Valeur du paramètre.
        
        Returns:
            bool: True si l'opération réussit, False sinon.
        """
        self.config.set_backend_setting(backend, setting, value)
        return self._save_config()
    
    # Méthodes pour les paramètres généraux
    
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
    
    # Méthodes pour le mode hors ligne et le cache
    
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
    
    # Méthodes pour les alias
    
    def add_global_alias(self, alias: str, env_name: str) -> bool:
        """
        Ajoute un alias global.
        
        Args:
            alias: Nom de l'alias.
            env_name: Nom de l'environnement cible.
        
        Returns:
            bool: True si l'ajout réussit.
        """
        if self.config.add_global_alias(alias, env_name):
            return self._save_config()
        return False
    
    def remove_global_alias(self, alias: str) -> bool:
        """
        Supprime un alias global.
        
        Args:
            alias: Nom de l'alias à supprimer.
        
        Returns:
            bool: True si la suppression réussit.
        """
        if self.config.remove_global_alias(alias):
            return self._save_config()
        return False
    
    def get_global_aliases(self) -> Dict[str, str]:
        """
        Récupère tous les alias globaux.
        
        Returns:
            Dict[str, str]: Dictionnaire des alias globaux.
        """
        return self.config.global_aliases.copy()
    
    # Méthodes pour les templates
    
    def add_template(self, name: str, template_data: Dict[str, Any]) -> bool:
        """
        Ajoute un template de configuration.
        
        Args:
            name: Nom du template.
            template_data: Données du template.
        
        Returns:
            bool: True si l'ajout réussit.
        """
        self.config.add_template(name, template_data)
        return self._save_config()
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un template de configuration.
        
        Args:
            name: Nom du template.
        
        Returns:
            Optional[Dict[str, Any]]: Template ou None si non trouvé.
        """
        return self.config.get_template(name)
    
    def list_templates(self) -> List[str]:
        """
        Liste tous les templates disponibles.
        
        Returns:
            List[str]: Noms des templates.
        """
        return list(self.config.templates.keys())
    
    def remove_template(self, name: str) -> bool:
        """
        Supprime un template.
        
        Args:
            name: Nom du template à supprimer.
        
        Returns:
            bool: True si la suppression réussit.
        """
        if name in self.config.templates:
            del self.config.templates[name]
            return self._save_config()
        return False
    
    # Méthodes pour l'export/import
    
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
            "metadata": {
                "gestvenv_version": "1.1.0",
                "export_version": "1.1.0",
                "exported_at": datetime.now().isoformat(),
                "exported_by": os.getlogin() if hasattr(os, 'getlogin') else "unknown",
                "source_environment": env_name
            },
            "environment": env_info.to_dict()
        }
        
        # Ajouter les métadonnées supplémentaires
        if add_metadata:
            export_config["metadata"].update(add_metadata)
        
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
        config_path = Path(config_file)
        if not config_path.exists():
            raise ValueError(f"Le fichier de configuration {config_file} n'existe pas.")
        
        try:
            # Charger la configuration depuis le fichier
            with open(config_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Vérifier le format de la configuration
            if "environment" not in import_data:
                # Format legacy (v1.0) - essayer de convertir
                if "name" in import_data and "python_version" in import_data:
                    import_data = {"environment": import_data}
                else:
                    raise ValueError("Format de configuration invalide.")
            
            env_data = import_data["environment"]
            
            # Déterminer le nom de l'environnement
            original_name = env_data.get("name", "imported_env")
            target_env_name = env_name or original_name
            
            # Vérifier si l'environnement existe déjà
            if self.environment_exists(target_env_name) and not force:
                return {
                    "status": "error",
                    "message": f"L'environnement {target_env_name} existe déjà. Utilisez force=True pour l'écraser."
                }
            
            # Mettre à jour le nom dans les données si nécessaire
            if target_env_name != original_name:
                env_data["name"] = target_env_name
            
            # Créer l'objet EnvironmentInfo depuis les données
            try:
                env_info = EnvironmentInfo.from_dict(env_data)
            except Exception as e:
                raise ValueError(f"Erreur lors de la création de l'environnement: {str(e)}")
            
            # Ajouter ou mettre à jour l'environnement
            if force and self.environment_exists(target_env_name):
                success = self.update_environment(env_info)
            else:
                success = self.add_environment(env_info)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Environnement {target_env_name} importé avec succès",
                    "environment_name": target_env_name,
                    "metadata": import_data.get("metadata", {})
                }
            else:
                return {
                    "status": "error",
                    "message": "Échec de l'ajout de l'environnement à la configuration"
                }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de décodage JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Erreur lors de l'import de la configuration: {str(e)}")
    
    # Méthodes pour les statistiques et monitoring
    
    def get_environment_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques détaillées sur les environnements.
        
        Returns:
            Dict[str, Any]: Statistiques des environnements.
        """
        stats = self.config.get_environment_stats()
        
        # Ajouter des statistiques supplémentaires
        stats.update({
            "configuration_version": self.config.config_version,
            "last_migration": self.config.migration_date.isoformat() if self.config.migration_date else None,
            "migrated_from_version": self.config.migrated_from_version,
            "total_aliases": len(self.config.global_aliases),
            "total_templates": len(self.config.templates),
            "preferred_backend": self.config.preferred_backend.value
        })
        
        return stats
    
    def get_environments_by_backend(self, backend: BackendType) -> List[str]:
        """
        Liste les noms des environnements utilisant un backend spécifique.
        
        Args:
            backend: Type de backend.
        
        Returns:
            List[str]: Noms des environnements.
        """
        environments = self.config.list_environments_by_backend(backend)
        return [env.name for env in environments]
    
    def get_environments_by_tag(self, tag: str) -> List[str]:
        """
        Liste les noms des environnements ayant un tag spécifique.
        
        Args:
            tag: Tag à rechercher.
        
        Returns:
            List[str]: Noms des environnements.
        """
        environments = self.config.list_environments_by_tag(tag)
        return [env.name for env in environments]
    
    def get_unused_environments(self, days: int = 30) -> List[str]:
        """
        Liste les environnements non utilisés depuis un certain nombre de jours.
        
        Args:
            days: Nombre de jours d'inactivité.
        
        Returns:
            List[str]: Noms des environnements non utilisés.
        """
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        unused = []
        for env_name, env_info in self.config.environments.items():
            if not env_info.last_used or env_info.last_used < cutoff_date:
                unused.append(env_name)
        
        return unused
    
    # Méthodes pour la maintenance et nettoyage
    
    def cleanup_orphaned_aliases(self) -> int:
        """
        Nettoie les alias qui pointent vers des environnements inexistants.
        
        Returns:
            int: Nombre d'alias supprimés.
        """
        removed_count = 0
        aliases_to_remove = []
        
        for alias, env_name in self.config.global_aliases.items():
            if env_name not in self.config.environments:
                aliases_to_remove.append(alias)
        
        for alias in aliases_to_remove:
            del self.config.global_aliases[alias]
            removed_count += 1
        
        if removed_count > 0:
            self._save_config()
            logger.info(f"{removed_count} alias orphelins supprimés")
        
        return removed_count
    
    def validate_configuration(self) -> List[ValidationError]:
        """
        Valide la configuration complète et retourne les erreurs trouvées.
        
        Returns:
            List[ValidationError]: Liste des erreurs de validation.
        """
        errors = []
        
        # Valider les environnements
        for env_name, env_info in self.config.environments.items():
            # Valider le nom
            name_errors = validate_environment_name(env_name)
            errors.extend(name_errors)
            
            # Valider la cohérence
            if env_info.name != env_name:
                errors.append(ValidationError(
                    field=f"environments.{env_name}.name",
                    message=f"Incohérence: nom d'environnement '{env_name}' != nom interne '{env_info.name}'",
                    severity="warning"
                ))
            
            # Valider l'existence du chemin
            if not env_info.path.exists():
                errors.append(ValidationError(
                    field=f"environments.{env_name}.path",
                    message=f"Chemin d'environnement inexistant: {env_info.path}",
                    severity="warning"
                ))
        
        # Valider les alias
        for alias, env_name in self.config.global_aliases.items():
            if env_name not in self.config.environments:
                errors.append(ValidationError(
                    field=f"global_aliases.{alias}",
                    message=f"Alias '{alias}' pointe vers l'environnement inexistant '{env_name}'",
                    severity="error"
                ))
        
        # Valider l'environnement actif
        if self.config.active_env and self.config.active_env not in self.config.environments:
            errors.append(ValidationError(
                field="active_env",
                message=f"Environnement actif inexistant: '{self.config.active_env}'",
                severity="error"
            ))
        
        return errors
    
    def repair_configuration(self) -> Tuple[bool, List[str]]:
        """
        Répare automatiquement les problèmes de configuration détectés.
        
        Returns:
            Tuple[bool, List[str]]: (succès, liste des réparations effectuées)
        """
        repairs = []
        
        try:
            # Créer une sauvegarde avant réparation
            backup_path = self._create_backup("before_repair")
            repairs.append(f"Sauvegarde créée: {backup_path}")
            
            # Nettoyer les alias orphelins
            removed_aliases = self.cleanup_orphaned_aliases()
            if removed_aliases > 0:
                repairs.append(f"{removed_aliases} alias orphelins supprimés")
            
            # Réparer l'environnement actif
            if self.config.active_env and self.config.active_env not in self.config.environments:
                self.config.active_env = None
                repairs.append("Environnement actif invalide réinitialisé")
            
            # Réparer les incohérences de noms
            for env_name, env_info in self.config.environments.items():
                if env_info.name != env_name:
                    env_info.name = env_name
                    repairs.append(f"Nom d'environnement réparé: {env_name}")
            
            # Sauvegarder les réparations
            if repairs:
                self._save_config()
                logger.info(f"Configuration réparée: {len(repairs)} réparations effectuées")
            
            return True, repairs
            
        except Exception as e:
            logger.error(f"Erreur lors de la réparation de la configuration: {str(e)}")
            return False, [f"Erreur: {str(e)}"]
    
    # Méthodes pour la sauvegarde et restauration
    
    def get_config_backup_path(self) -> str:
        """
        Obtient le chemin du fichier de sauvegarde de la configuration.
        
        Returns:
            str: Chemin du fichier de sauvegarde.
        """
        return str(self.config_path.with_suffix('.json.bak'))
    
    def restore_config_backup(self) -> bool:
        """
        Restaure la configuration à partir de la sauvegarde automatique.
        
        Returns:
            bool: True si la restauration réussit, False sinon.
        """
        backup_path = Path(self.get_config_backup_path())
        
        if not backup_path.exists():
            logger.error("Aucun fichier de sauvegarde automatique trouvé.")
            return False
        
        return self._restore_from_backup(backup_path)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Liste toutes les sauvegardes disponibles.
        
        Returns:
            List[Dict[str, Any]]: Liste des informations de sauvegarde.
        """
        backups = []
        backup_dir = self.config_path.parent / "backups"
        
        if backup_dir.exists():
            for backup_file in backup_dir.glob("config_backup_*.json"):
                try:
                    stat = backup_file.stat()
                    backups.append({
                        "name": backup_file.name,
                        "path": str(backup_file),
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime),
                        "modified": datetime.fromtimestamp(stat.st_mtime)
                    })
                except Exception as e:
                    logger.warning(f"Erreur lecture sauvegarde {backup_file}: {e}")
        
        # Trier par date de modification (plus récent en premier)
        backups.sort(key=lambda x: x["modified"], reverse=True)
        
        return backups
    
    def restore_from_backup_by_name(self, backup_name: str) -> bool:
        """
        Restaure la configuration depuis une sauvegarde spécifique.
        
        Args:
            backup_name: Nom du fichier de sauvegarde.
        
        Returns:
            bool: True si la restauration réussit.
        """
        backup_dir = self.config_path.parent / "backups"
        backup_path = backup_dir / backup_name
        
        if not backup_path.exists():
            logger.error(f"Sauvegarde non trouvée: {backup_name}")
            return False
        
        return self._restore_from_backup(backup_path)
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Nettoie les anciennes sauvegardes, en gardant seulement un nombre spécifié.
        
        Args:
            keep_count: Nombre de sauvegardes à conserver.
        
        Returns:
            int: Nombre de sauvegardes supprimées.
        """
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            return 0
        
        # Supprimer les sauvegardes les plus anciennes
        to_remove = backups[keep_count:]
        removed_count = 0
        
        for backup in to_remove:
            try:
                Path(backup["path"]).unlink()
                removed_count += 1
            except Exception as e:
                logger.warning(f"Erreur suppression sauvegarde {backup['name']}: {e}")
        
        logger.info(f"{removed_count} anciennes sauvegardes supprimées")
        return removed_count
    
    # Méthodes pour l'intégration avec d'autres composants
    
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Retourne des informations sur les backends disponibles et leur configuration.
        
        Returns:
            Dict[str, Any]: Informations sur les backends.
        """
        from ..services.system_service import SystemService
        
        system_service = SystemService()
        backend_info = {
            "preferred": self.config.preferred_backend.value,
            "available": {},
            "settings": self.config.backend_settings
        }
        
        # Vérifier la disponibilité de chaque backend
        for backend_type in BackendType:
            backend_name = backend_type.value
            
            if backend_name == "pip":
                # pip est toujours disponible
                backend_info["available"][backend_name] = {
                    "available": True,
                    "version": "unknown"
                }
            elif backend_name == "uv":
                # Vérifier si uv est installé
                available = system_service.check_command_exists("uv")
                version = None
                if available:
                    try:
                        import subprocess
                        result = subprocess.run(
                            ["uv", "--version"], 
                            capture_output=True, 
                            text=True, 
                            check=True,
                            timeout=5
                        )
                        version = result.stdout.strip().split()[-1]
                    except Exception:
                        version = "unknown"
                
                backend_info["available"][backend_name] = {
                    "available": available,
                    "version": version
                }
            else:
                # Autres backends - vérification basique
                available = system_service.check_command_exists(backend_name)
                backend_info["available"][backend_name] = {
                    "available": available,
                    "version": "unknown" if available else None
                }
        
        return backend_info
    
    def __str__(self) -> str:
        """Représentation textuelle du gestionnaire de configuration."""
        return f"ConfigManager(config_path={self.config_path}, environments={len(self.config.environments)})"
    
    def __repr__(self) -> str:
        """Représentation détaillée du gestionnaire de configuration."""
        return (f"ConfigManager(config_path={self.config_path!r}, "
                f"version={self.config.config_version}, "
                f"environments={len(self.config.environments)}, "
                f"active_env={self.config.active_env!r})")