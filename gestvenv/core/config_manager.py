"""
GestVenv v1.1 - ConfigManager avec Stratégies Intégrées
======================================================

Module de gestion avancée de la configuration pour GestVenv v1.1.
Étend le ConfigManager existant avec :
- Stratégies intelligentes (migration, backend, cache, templates)
- Migration automatique v1.0 → v1.1
- Support pyproject.toml et backends multiples
- Cache intelligent et templates
- Validation et réparation avancées

Classes principales:
    - ConfigManager: Gestionnaire principal étendu v1.1
    - MigrationHandler: Gestionnaire de migration spécialisé
    - StrategyManager: Gestionnaire des stratégies
    - ConfigValidator: Validateur de configuration

Version: 1.1.0
Auteur: thearchit3ct
Date: 2025-01-27
"""

import os
import json
import logging
import shutil
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import asdict

# Imports des modèles v1.1
from .models import (
    ConfigInfo, EnvironmentInfo, PyProjectInfo, PackageInfo,
    EnvironmentHealth, HealthStatus, BackendType, SourceFileType,
    SCHEMA_VERSION, COMPATIBLE_VERSIONS
)

# Import des stratégies
from .strategies import (
    GestVenvStrategies, MigrationStrategy, BackendStrategy, CacheStrategy,
    MigrationMode, BackendSelectionStrategy, ESSENTIAL_TEMPLATES,
    get_default_strategies, detect_optimal_strategies
)

# Import des exceptions
from .exceptions import (
    GestVenvError, ConfigValidationError, MigrationError, 
    ValidationError, EnvironmentError
)

# Configuration du logging
logger = logging.getLogger(__name__)


# ===== EXCEPTIONS SPÉCIALISÉES =====

class ConfigCorruptedError(GestVenvError):
    """Configuration corrompue nécessitant une restauration."""
    pass


class ConfigBackupError(GestVenvError):
    """Erreur lors des opérations de sauvegarde."""
    pass


class StrategyError(GestVenvError):
    """Erreur liée aux stratégies de configuration."""
    pass


# ===== GESTIONNAIRE DE MIGRATION =====

class MigrationHandler:
    """Gestionnaire spécialisé pour les migrations de configuration."""
    
    MIGRATION_PATHS = {
        "1.0.0": ["1.0.1", "1.1.0"],
        "1.0.1": ["1.1.0"],
        "1.1.0": []  # Version courante
    }
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__ + '.MigrationHandler')
    
    def needs_migration(self, config_dict: Dict[str, Any]) -> bool:
        """Vérifie si une migration est nécessaire."""
        current_version = config_dict.get("config_version", "1.0.0")
        return current_version != SCHEMA_VERSION
    
    def can_migrate(self, from_version: str, to_version: str = None) -> bool:
        """Vérifie si la migration est possible."""
        if to_version is None:
            to_version = SCHEMA_VERSION
        
        # Vérification directe
        if from_version == to_version:
            return True
        
        # Vérification des chemins de migration
        return from_version in self.MIGRATION_PATHS
    
    def migrate_config(self, config_dict: Dict[str, Any], strategy: MigrationStrategy) -> Dict[str, Any]:
        """
        Effectue la migration complète d'une configuration.
        
        Args:
            config_dict: Configuration à migrer
            strategy: Stratégie de migration
            
        Returns:
            Configuration migrée
        """
        current_version = config_dict.get("config_version", "1.0.0")
        
        if current_version == SCHEMA_VERSION:
            return config_dict
        
        self.logger.info(f"Début migration {current_version} → {SCHEMA_VERSION}")
        
        # Créer une sauvegarde si demandé
        if strategy.create_backup:
            self._create_migration_backup(config_dict, current_version)
        
        # Appliquer les migrations étape par étape
        migrated_config = config_dict.copy()
        
        if current_version.startswith("1.0"):
            migrated_config = self._migrate_from_v1_0(migrated_config)
        
        # Finaliser la migration
        migrated_config = self._finalize_migration(migrated_config, current_version)
        
        self.logger.info(f"Migration {current_version} → {SCHEMA_VERSION} terminée")
        return migrated_config
    
    def _migrate_from_v1_0(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Migre depuis la version 1.0.x vers 1.1.0."""
        self.logger.info("Migration v1.0 → v1.1")
        
        # 1. Migrer les environnements
        environments = config_dict.get("environments", {})
        migrated_environments = {}
        
        for env_name, env_data in environments.items():
            migrated_env = self._migrate_environment_v1_0_to_v1_1(env_data)
            migrated_environments[env_name] = migrated_env
        
        config_dict["environments"] = migrated_environments
        
        # 2. Ajouter les nouveaux paramètres v1.1
        config_dict = self._add_v1_1_settings(config_dict)
        
        # 3. Migrer les paramètres existants
        config_dict = self._migrate_settings_v1_0_to_v1_1(config_dict)
        
        return config_dict
    
    def _migrate_environment_v1_0_to_v1_1(self, env_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migre un environnement v1.0 vers v1.1."""
        # Ajouter les nouveaux champs avec valeurs par défaut
        env_data.setdefault("backend_type", "pip")
        env_data.setdefault("source_file_type", "requirements")
        env_data.setdefault("lock_file_path", None)
        env_data.setdefault("dependency_groups", {})
        env_data.setdefault("pyproject_info", None)
        
        # Nouveaux champs métadonnées
        env_data.setdefault("updated_at", datetime.now().isoformat())
        env_data.setdefault("last_used", None)
        env_data.setdefault("usage_count", 0)
        env_data.setdefault("aliases", [])
        env_data.setdefault("tags", [])
        
        # Métadonnées de migration
        env_data["migrated_from_version"] = "1.0.0"
        env_data["_schema_version"] = SCHEMA_VERSION
        
        # Migrer packages vers packages_installed si nécessaire
        if "packages" in env_data and "packages_installed" not in env_data:
            packages_installed = []
            for pkg_name in env_data.get("packages", []):
                packages_installed.append({
                    "name": pkg_name,
                    "version": "unknown",
                    "source": "migration",
                    "backend_used": "pip",
                    "installed_at": datetime.now().isoformat()
                })
            env_data["packages_installed"] = packages_installed
        
        return env_data
    
    def _add_v1_1_settings(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Ajoute les nouveaux paramètres v1.1."""
        # Paramètres backends
        config_dict.setdefault("preferred_backend", "pip")
        config_dict.setdefault("backend_configs", {
            "pip": {
                "index_url": None,
                "extra_index_urls": [],
                "timeout": 60,
                "retries": 3
            },
            "uv": {
                "resolution": "highest",
                "compile_bytecode": True,
                "parallel": True
            }
        })
        
        # Paramètres cache
        config_dict.setdefault("cache_settings", {
            "enabled": True,
            "ttl_seconds": 3600,
            "max_entries": 100,
            "location": None  # Sera défini automatiquement
        })
        
        # Aliases et templates
        config_dict.setdefault("global_aliases", {})
        config_dict.setdefault("templates", {})
        
        # Stratégies
        config_dict.setdefault("migration_settings", {
            "mode": "prompt",
            "create_backup": True,
            "rollback_available": True
        })
        
        return config_dict
    
    def _migrate_settings_v1_0_to_v1_1(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Migre les paramètres existants de v1.0 vers v1.1."""
        settings = config_dict.get("settings", {})
        
        # Mappage des anciens paramètres vers les nouveaux
        migrations_mapping = {
            "auto_activate": "auto_activate",
            "package_cache_enabled": "use_package_cache"
        }
        
        for old_key, new_key in migrations_mapping.items():
            if old_key in settings:
                settings[new_key] = settings.pop(old_key)
        
        # Nouveaux paramètres par défaut
        settings.setdefault("auto_activate", False)
        settings.setdefault("use_package_cache", True)
        settings.setdefault("offline_mode", False)
        settings.setdefault("suggest_optimizations", True)
        settings.setdefault("verbose_operations", False)
        
        config_dict["settings"] = settings
        return config_dict
    
    def _finalize_migration(self, config_dict: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """Finalise la migration avec les métadonnées."""
        config_dict["config_version"] = SCHEMA_VERSION
        config_dict["migrated_from_version"] = from_version
        config_dict["migration_date"] = datetime.now().isoformat()
        config_dict.setdefault("created_at", datetime.now().isoformat())
        config_dict["updated_at"] = datetime.now().isoformat()
        
        return config_dict
    
    def _create_migration_backup(self, config_dict: Dict[str, Any], version: str) -> None:
        """Crée une sauvegarde avant migration."""
        backup_name = f"pre_migration_{version}_to_{SCHEMA_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.config_manager.backup_dir / f"{backup_name}.json"
        
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Sauvegarde de migration créée: {backup_path}")
        except Exception as e:
            self.logger.warning(f"Impossible de créer la sauvegarde de migration: {e}")


# ===== GESTIONNAIRE DES STRATÉGIES =====

class StrategyManager:
    """Gestionnaire des stratégies de configuration."""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__ + '.StrategyManager')
        self._strategies: Optional[GestVenvStrategies] = None
    
    def get_strategies(self) -> GestVenvStrategies:
        """Récupère les stratégies courantes."""
        if self._strategies is None:
            self._strategies = self._load_strategies()
        return self._strategies
    
    def set_strategies(self, strategies: GestVenvStrategies) -> None:
        """Définit les nouvelles stratégies."""
        self._strategies = strategies
        self._save_strategies()
    
    def _load_strategies(self) -> GestVenvStrategies:
        """Charge les stratégies depuis la configuration."""
        config = self.config_manager.config
        
        # Configuration migration
        migration_settings = getattr(config, 'migration_settings', {})
        migration_strategy = MigrationStrategy(
            mode=MigrationMode(migration_settings.get('mode', 'prompt')),
            create_backup=migration_settings.get('create_backup', True),
            rollback_available=migration_settings.get('rollback_available', True)
        )
        
        # Configuration backend
        backend_strategy = BackendStrategy(
            selection_mode=BackendSelectionStrategy(
                getattr(config, 'preferred_backend', 'conservative')
                if getattr(config, 'preferred_backend', 'conservative') != 'pip'
                else 'conservative'
            ),
            fallback_chain=["pip"]
        )
        
        # Configuration cache
        cache_settings = getattr(config, 'cache_settings', {})
        cache_strategy = CacheStrategy(
            enabled=cache_settings.get('enabled', True),
            ttl_seconds=cache_settings.get('ttl_seconds', 3600),
            max_entries=cache_settings.get('max_entries', 100)
        )
        
        return GestVenvStrategies(
            migration=migration_strategy,
            backend=backend_strategy,
            cache=cache_strategy,
            templates=getattr(config, 'templates', ESSENTIAL_TEMPLATES)
        )
    
    def _save_strategies(self) -> None:
        """Sauvegarde les stratégies dans la configuration."""
        if not self._strategies:
            return
        
        config = self.config_manager.config
        
        # Sauvegarder les paramètres de migration
        config.migration_settings = {
            'mode': self._strategies.migration.mode.value,
            'create_backup': self._strategies.migration.create_backup,
            'rollback_available': self._strategies.migration.rollback_available
        }
        
        # Sauvegarder les paramètres de backend
        backend_mode = self._strategies.backend.selection_mode.value
        if backend_mode == 'conservative':
            config.preferred_backend = 'pip'
        elif backend_mode == 'performance':
            config.preferred_backend = 'auto'
        else:
            config.preferred_backend = backend_mode
        
        # Sauvegarder les paramètres de cache
        config.cache_settings = {
            'enabled': self._strategies.cache.enabled,
            'ttl_seconds': self._strategies.cache.ttl_seconds,
            'max_entries': self._strategies.cache.max_entries
        }
        
        # Sauvegarder les templates
        config.templates = self._strategies.templates
        
        # Marquer pour sauvegarde
        config.updated_at = datetime.now()


# ===== VALIDATEUR DE CONFIGURATION =====

class ConfigValidator:
    """Validateur de configuration avec réparation automatique."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.ConfigValidator')
    
    def validate_config(self, config_dict: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Valide une configuration complète.
        
        Returns:
            Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Validation de base
        base_errors, base_warnings = self._validate_basic_structure(config_dict)
        errors.extend(base_errors)
        warnings.extend(base_warnings)
        
        # Validation des environnements
        env_errors, env_warnings = self._validate_environments(config_dict)
        errors.extend(env_errors)
        warnings.extend(env_warnings)
        
        # Validation des paramètres
        settings_errors, settings_warnings = self._validate_settings(config_dict)
        errors.extend(settings_errors)
        warnings.extend(settings_warnings)
        
        return len(errors) == 0, errors, warnings
    
    def _validate_basic_structure(self, config_dict: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Valide la structure de base."""
        errors = []
        warnings = []
        
        # Champs requis
        required_fields = ["environments", "config_version"]
        for field in required_fields:
            if field not in config_dict:
                errors.append(f"Champ requis manquant: {field}")
        
        # Version
        version = config_dict.get("config_version", "unknown")
        if version not in COMPATIBLE_VERSIONS:
            if version == "unknown":
                warnings.append("Version de configuration non spécifiée")
            else:
                warnings.append(f"Version non reconnue: {version}")
        
        return errors, warnings
    
    def _validate_environments(self, config_dict: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Valide les environnements."""
        errors = []
        warnings = []
        
        environments = config_dict.get("environments", {})
        
        for env_name, env_data in environments.items():
            if not isinstance(env_data, dict):
                errors.append(f"Environnement {env_name}: données invalides")
                continue
            
            # Valider les champs requis
            required_env_fields = ["name", "path", "python_version"]
            for field in required_env_fields:
                if field not in env_data:
                    errors.append(f"Environnement {env_name}: champ requis manquant: {field}")
            
            # Valider le chemin
            path = env_data.get("path")
            if path and not Path(path).exists():
                warnings.append(f"Environnement {env_name}: chemin introuvable: {path}")
        
        return errors, warnings
    
    def _validate_settings(self, config_dict: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Valide les paramètres."""
        errors = []
        warnings = []
        
        # Valider backend
        backend = config_dict.get("preferred_backend", "pip")
        valid_backends = ["pip", "uv", "poetry", "pdm", "auto"]
        if backend not in valid_backends:
            errors.append(f"Backend invalide: {backend}")
        
        # Valider cache
        cache_settings = config_dict.get("cache_settings", {})
        if cache_settings:
            ttl = cache_settings.get("ttl_seconds", 3600)
            if not isinstance(ttl, int) or ttl < 0:
                errors.append("cache_settings.ttl_seconds doit être un entier positif")
        
        return errors, warnings
    
    def repair_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Répare automatiquement une configuration."""
        self.logger.info("Début de la réparation de configuration")
        
        repaired = config_dict.copy()
        
        # Réparer la structure de base
        repaired.setdefault("environments", {})
        repaired.setdefault("config_version", SCHEMA_VERSION)
        repaired.setdefault("active_env", None)
        repaired.setdefault("default_python", "python3")
        
        # Réparer les paramètres
        repaired.setdefault("preferred_backend", "pip")
        repaired.setdefault("cache_settings", {
            "enabled": True,
            "ttl_seconds": 3600,
            "max_entries": 100
        })
        
        # Réparer les environnements
        for env_name, env_data in repaired.get("environments", {}).items():
            if isinstance(env_data, dict):
                env_data.setdefault("name", env_name)
                env_data.setdefault("python_version", "python3")
                env_data.setdefault("created_at", datetime.now().isoformat())
        
        self.logger.info("Réparation de configuration terminée")
        return repaired


# ===== GESTIONNAIRE DE CONFIGURATION PRINCIPAL =====

class ConfigManager:
    """
    Gestionnaire de configuration GestVenv v1.1 avec stratégies intégrées.
    
    Fonctionnalités principales:
    - Chargement/sauvegarde configuration avec validation
    - Migration automatique v1.0 → v1.1
    - Gestion des stratégies (migration, backend, cache, templates)
    - Sauvegarde automatique et restauration
    - Import/export avec métadonnées
    """
    
    CONFIG_VERSION = SCHEMA_VERSION
    CONFIG_FILENAME = "config.json"
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialise le gestionnaire de configuration.
        
        Args:
            config_path: Chemin vers le fichier de configuration
        """
        self.config_path = self._resolve_config_path(config_path)
        self.backup_dir = self.config_path.parent / "backups"
        self.cache_dir = self.config_path.parent / "cache"
        
        # Créer les répertoires nécessaires
        self._ensure_directories()
        
        # Gestionnaires spécialisés
        self.migration_handler = MigrationHandler(self)
        self.strategy_manager = StrategyManager(self)
        self.validator = ConfigValidator()
        
        # Charger la configuration
        self.config = self._load_config()
        
        # Créer une sauvegarde initiale
        self._create_auto_backup()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"ConfigManager v{SCHEMA_VERSION} initialisé")
    
    def _resolve_config_path(self, config_path: Optional[Union[str, Path]]) -> Path:
        """Résout le chemin de configuration."""
        if config_path:
            return Path(config_path)
        
        # Chemin par défaut selon l'OS
        if os.name == 'nt':  # Windows
            base_dir = Path(os.environ.get('APPDATA', '')) / 'GestVenv'
        else:  # macOS, Linux
            base_dir = Path.home() / '.config' / 'gestvenv'
        
        return base_dir / self.CONFIG_FILENAME
    
    def _ensure_directories(self) -> None:
        """Crée les répertoires nécessaires."""
        directories = [
            self.config_path.parent,
            self.backup_dir,
            self.cache_dir,
            self.cache_dir / "metadata",
            self.cache_dir / "packages"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> ConfigInfo:
        """Charge la configuration depuis le fichier."""
        if not self.config_path.exists():
            self.logger.info("Création d'une nouvelle configuration")
            return self._create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # Valider la configuration
            is_valid, errors, warnings = self.validator.validate_config(config_dict)
            
            if errors:
                self.logger.warning(f"Configuration invalide: {errors}")
                config_dict = self.validator.repair_config(config_dict)
            
            if warnings:
                for warning in warnings:
                    self.logger.warning(f"Configuration: {warning}")
            
            # Migrer si nécessaire
            if self.migration_handler.needs_migration(config_dict):
                config_dict = self._handle_migration(config_dict)
            
            # Créer l'objet ConfigInfo
            return self._config_dict_to_object(config_dict)
            
        except Exception as e:
            self.logger.error(f"Erreur chargement configuration: {e}")
            return self._handle_corrupted_config()
    
    def _handle_migration(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Gère la migration de configuration."""
        current_version = config_dict.get("config_version", "1.0.0")
        
        # Obtenir la stratégie de migration
        migration_strategy = self._get_migration_strategy(config_dict)
        
        # Vérifier si la migration doit être effectuée
        if not self._should_migrate(current_version, migration_strategy):
            return config_dict
        
        # Effectuer la migration
        try:
            migrated_config = self.migration_handler.migrate_config(config_dict, migration_strategy)
            self.logger.info(f"Migration {current_version} → {SCHEMA_VERSION} réussie")
            return migrated_config
        except Exception as e:
            self.logger.error(f"Échec migration: {e}")
            raise MigrationError(f"Impossible de migrer depuis {current_version}: {e}")
    
    def _get_migration_strategy(self, config_dict: Dict[str, Any]) -> MigrationStrategy:
        """Obtient la stratégie de migration à utiliser."""
        migration_settings = config_dict.get("migration_settings", {})
        
        return MigrationStrategy(
            mode=MigrationMode(migration_settings.get("mode", "prompt")),
            create_backup=migration_settings.get("create_backup", True),
            rollback_available=migration_settings.get("rollback_available", True)
        )
    
    def _should_migrate(self, from_version: str, strategy: MigrationStrategy) -> bool:
        """Détermine si la migration doit être effectuée."""
        if strategy.mode == MigrationMode.NEVER:
            return False
        elif strategy.mode == MigrationMode.AUTO:
            return True
        elif strategy.mode == MigrationMode.PROMPT:
            # Dans un vrai scénario, ceci afficherait une invite utilisateur
            # Pour l'implémentation, on assume "oui"
            self.logger.info(f"Migration {from_version} → {SCHEMA_VERSION} recommandée")
            return True
        elif strategy.mode == MigrationMode.SMART:
            # Migration intelligente : vérifie s'il y a des bénéfices clairs
            return self._has_migration_benefits(from_version)
        
        return False
    
    def _has_migration_benefits(self, from_version: str) -> bool:
        """Vérifie si la migration apporte des bénéfices clairs."""
        # Migration v1.0 → v1.1 apporte toujours des bénéfices
        return from_version.startswith("1.0")
    
    def _config_dict_to_object(self, config_dict: Dict[str, Any]) -> ConfigInfo:
        """Convertit un dictionnaire en objet ConfigInfo."""
        # Convertir les environnements
        environments = {}
        for env_name, env_data in config_dict.get("environments", {}).items():
            environments[env_name] = EnvironmentInfo.from_dict(env_data)
        
        # Créer la configuration
        config = ConfigInfo(
            environments=environments,
            active_env=config_dict.get("active_env"),
            default_python=config_dict.get("default_python", "python3"),
            preferred_backend=config_dict.get("preferred_backend", "pip"),
            auto_activate=config_dict.get("settings", {}).get("auto_activate", False),
            use_package_cache=config_dict.get("settings", {}).get("use_package_cache", True),
            offline_mode=config_dict.get("settings", {}).get("offline_mode", False),
            backend_configs=config_dict.get("backend_configs", {}),
            global_aliases=config_dict.get("global_aliases", {}),
            templates=config_dict.get("templates", {}),
            config_version=config_dict.get("config_version", SCHEMA_VERSION)
        )
        
        # Métadonnées
        if "created_at" in config_dict:
            config.created_at = datetime.fromisoformat(config_dict["created_at"])
        if "updated_at" in config_dict:
            config.updated_at = datetime.fromisoformat(config_dict["updated_at"])
        if "migrated_from_version" in config_dict:
            config.migrated_from_version = config_dict["migrated_from_version"]
        
        return config
    
    def _create_default_config(self) -> ConfigInfo:
        """Crée une configuration par défaut."""
        return ConfigInfo(
            environments={},
            config_version=SCHEMA_VERSION,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _handle_corrupted_config(self) -> ConfigInfo:
        """Gère une configuration corrompue."""
        # Sauvegarder le fichier corrompu
        if self.config_path.exists():
            corrupted_backup = self.backup_dir / f"corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                shutil.copy2(self.config_path, corrupted_backup)
                self.logger.warning(f"Configuration corrompue sauvegardée: {corrupted_backup}")
            except Exception as e:
                self.logger.error(f"Impossible de sauvegarder la configuration corrompue: {e}")
        
        # Essayer de restaurer depuis la dernière sauvegarde
        latest_backup = self._get_latest_backup()
        if latest_backup:
            try:
                return self._restore_from_backup(latest_backup)
            except Exception as e:
                self.logger.error(f"Échec restauration depuis sauvegarde: {e}")
        
        # Créer une nouvelle configuration
        self.logger.info("Création d'une nouvelle configuration par défaut")
        return self._create_default_config()
    
    def save_config(self) -> bool:
        """
        Sauvegarde la configuration courante.
        
        Returns:
            bool: Succès de la sauvegarde
        """
        try:
            # Mettre à jour la date de modification
            self.config.updated_at = datetime.now()
            
            # Convertir en dictionnaire
            config_dict = self.config.to_dict()
            
            # Sauvegarder dans un fichier temporaire puis renommer (atomique)
            temp_path = self.config_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False, default=str)
            
            # Renommer le fichier temporaire (opération atomique)
            temp_path.replace(self.config_path)
            
            self.logger.debug("Configuration sauvegardée")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde configuration: {e}")
            return False
    
    def _create_auto_backup(self) -> None:
        """Crée une sauvegarde automatique."""
        try:
            # Créer seulement si le fichier de config existe
            if not self.config_path.exists():
                return
            
            # Vérifier s'il faut créer une sauvegarde
            if not self._should_create_backup():
                return
            
            backup_name = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / f"{backup_name}.json"
            
            shutil.copy2(self.config_path, backup_path)
            self.logger.debug(f"Sauvegarde automatique créée: {backup_path}")
            
            # Nettoyer les anciennes sauvegardes
            self._cleanup_old_backups()
            
        except Exception as e:
            self.logger.warning(f"Échec création sauvegarde automatique: {e}")
    
    def _should_create_backup(self) -> bool:
        """Vérifie si une sauvegarde automatique est nécessaire."""
        # Vérifier la dernière sauvegarde
        latest_backup = self._get_latest_backup()
        if not latest_backup:
            return True
        
        # Créer une sauvegarde si la dernière date de plus d'une heure
        backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
        return datetime.now() - backup_time > timedelta(hours=1)
    
    def _get_latest_backup(self) -> Optional[Path]:
        """Trouve la sauvegarde la plus récente."""
        if not self.backup_dir.exists():
            return None
        
        backups = list(self.backup_dir.glob("*.json"))
        if not backups:
            return None
        
        return max(backups, key=lambda p: p.stat().st_mtime)
    
    def _cleanup_old_backups(self, keep_count: int = 10) -> None:
        """Nettoie les anciennes sauvegardes."""
        try:
            backups = sorted(
                self.backup_dir.glob("auto_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for backup in backups[keep_count:]:
                backup.unlink()
                self.logger.debug(f"Ancienne sauvegarde supprimée: {backup}")
                
        except Exception as e:
            self.logger.warning(f"Erreur nettoyage sauvegardes: {e}")
    
    def _restore_from_backup(self, backup_path: Path) -> ConfigInfo:
        """Restaure depuis une sauvegarde."""
        with open(backup_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        return self._config_dict_to_object(config_dict)
    
    # ===== API PUBLIQUE =====
    
    def get_environment(self, name: str) -> Optional[EnvironmentInfo]:
        """Récupère un environnement par nom ou alias."""
        return self.config.get_environment(name)
    
    def add_environment(self, env_info: EnvironmentInfo) -> bool:
        """Ajoute un nouvel environnement."""
        success = self.config.add_environment(env_info)
        if success:
            self.save_config()
        return success
    
    def update_environment(self, env_info: EnvironmentInfo) -> bool:
        """Met à jour un environnement existant."""
        if env_info.name in self.config.environments:
            self.config.environments[env_info.name] = env_info
            self.save_config()
            return True
        return False
    
    def remove_environment(self, name: str) -> bool:
        """Supprime un environnement."""
        success = self.config.remove_environment(name)
        if success:
            self.save_config()
        return success
    
    def set_active_environment(self, name: str) -> bool:
        """Définit l'environnement actif."""
        success = self.config.set_active_environment(name)
        if success:
            self.save_config()
        return success
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Récupère un paramètre de configuration."""
        return getattr(self.config, key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Définit un paramètre de configuration."""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self.config.updated_at = datetime.now()
            self.save_config()
            return True
        return False
    
    def get_strategies(self) -> GestVenvStrategies:
        """Récupère les stratégies courantes."""
        return self.strategy_manager.get_strategies()
    
    def set_strategies(self, strategies: GestVenvStrategies) -> None:
        """Définit les nouvelles stratégies."""
        self.strategy_manager.set_strategies(strategies)
        self.save_config()
    
    def export_config(self, output_path: str, include_environments: bool = True) -> bool:
        """
        Exporte la configuration vers un fichier.
        
        Args:
            output_path: Chemin de sortie
            include_environments: Inclure les environnements
            
        Returns:
            bool: Succès de l'export
        """
        try:
            export_data = {
                "export_version": "1.1.0",
                "export_date": datetime.now().isoformat(),
                "source_version": SCHEMA_VERSION,
                "config": self.config.to_dict()
            }
            
            if not include_environments:
                export_data["config"]["environments"] = {}
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Configuration exportée vers: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur export configuration: {e}")
            return False
    
    def import_config(self, input_path: str, merge: bool = False) -> bool:
        """
        Importe une configuration depuis un fichier.
        
        Args:
            input_path: Chemin du fichier à importer
            merge: Fusionner avec la configuration existante
            
        Returns:
            bool: Succès de l'import
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Valider le format d'export
            if "config" not in import_data:
                raise ValueError("Format d'export invalide")
            
            imported_config_dict = import_data["config"]
            
            # Migrer si nécessaire
            if self.migration_handler.needs_migration(imported_config_dict):
                strategy = self._get_migration_strategy(imported_config_dict)
                imported_config_dict = self.migration_handler.migrate_config(
                    imported_config_dict, strategy
                )
            
            if merge:
                # Fusionner avec la configuration existante
                self._merge_config(imported_config_dict)
            else:
                # Remplacer la configuration
                self.config = self._config_dict_to_object(imported_config_dict)
            
            self.save_config()
            self.logger.info(f"Configuration importée depuis: {input_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur import configuration: {e}")
            return False
    
    def _merge_config(self, imported_config_dict: Dict[str, Any]) -> None:
        """Fusionne une configuration importée avec l'existante."""
        # Fusionner les environnements
        imported_environments = imported_config_dict.get("environments", {})
        for env_name, env_data in imported_environments.items():
            env_info = EnvironmentInfo.from_dict(env_data)
            self.config.environments[env_name] = env_info
        
        # Fusionner les templates
        imported_templates = imported_config_dict.get("templates", {})
        self.config.templates.update(imported_templates)
        
        # Fusionner les alias globaux
        imported_aliases = imported_config_dict.get("global_aliases", {})
        self.config.global_aliases.update(imported_aliases)
    
    def create_manual_backup(self, backup_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Crée une sauvegarde manuelle.
        
        Args:
            backup_name: Nom de la sauvegarde
            
        Returns:
            Tuple[bool, str]: (succès, chemin ou message d'erreur)
        """
        try:
            if not backup_name:
                backup_name = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_path = self.backup_dir / f"{backup_name}.json"
            
            backup_data = {
                "backup_version": "1.1.0",
                "created_at": datetime.now().isoformat(),
                "original_config_path": str(self.config_path),
                "config": self.config.to_dict()
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Sauvegarde manuelle créée: {backup_path}")
            return True, str(backup_path)
            
        except Exception as e:
            error_msg = f"Erreur création sauvegarde: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Liste les sauvegardes disponibles."""
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for backup_file in self.backup_dir.glob("*.json"):
            try:
                stat = backup_file.stat()
                backups.append({
                    "name": backup_file.stem,
                    "path": str(backup_file),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "auto" if backup_file.name.startswith("auto_") else "manual"
                })
            except Exception:
                continue
        
        return sorted(backups, key=lambda x: x["created_at"], reverse=True)
    
    def validate_current_config(self) -> Tuple[bool, List[str], List[str]]:
        """
        Valide la configuration courante.
        
        Returns:
            Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
        """
        config_dict = self.config.to_dict()
        return self.validator.validate_config(config_dict)
    
    def repair_config(self) -> bool:
        """
        Répare automatiquement la configuration courante.
        
        Returns:
            bool: Succès de la réparation
        """
        try:
            config_dict = self.config.to_dict()
            repaired_dict = self.validator.repair_config(config_dict)
            self.config = self._config_dict_to_object(repaired_dict)
            self.save_config()
            self.logger.info("Configuration réparée automatiquement")
            return True
        except Exception as e:
            self.logger.error(f"Erreur réparation configuration: {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """Retourne des informations sur la configuration."""
        return {
            "version": self.config.config_version,
            "config_path": str(self.config_path),
            "backup_dir": str(self.backup_dir),
            "cache_dir": str(self.cache_dir),
            "created_at": self.config.created_at.isoformat() if self.config.created_at else None,
            "updated_at": self.config.updated_at.isoformat() if self.config.updated_at else None,
            "migrated_from": self.config.migrated_from_version,
            "environments_count": len(self.config.environments),
            "active_environment": self.config.active_env,
            "strategies": {
                "migration_mode": self.get_strategies().migration.mode.value,
                "preferred_backend": self.config.preferred_backend,
                "cache_enabled": self.get_strategies().cache.enabled
            }
        }


# ===== EXPORTS =====

__all__ = [
    'ConfigManager',
    'MigrationHandler',
    'StrategyManager', 
    'ConfigValidator',
    'ConfigCorruptedError',
    'ConfigBackupError',
    'StrategyError'
]