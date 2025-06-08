"""
GestVenv v1.1 - Gestionnaire de Configuration Centralisé
=======================================================

Module principal pour la gestion de configuration de GestVenv v1.1.
Fournit une interface centralisée pour :
- Configuration système et utilisateur
- Gestion des environnements virtuels 
- Migration automatique v1.0 → v1.1
- Sauvegarde et restauration
- Templates et alias
- Validation et réparation

Architecture:
    ConfigManager -> Configuration JSON -> FileSystem
    
Auteur: GestVenv Core Team
Version: 1.1.0
Licence: MIT
"""

import os
import json
import logging
import shutil
import hashlib
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from functools import wraps
import tempfile

# Configuration du logging
logger = logging.getLogger(__name__)

# ================================
# EXCEPTIONS PERSONNALISÉES
# ================================

class ConfigError(Exception):
    """Exception de base pour les erreurs de configuration."""
    pass

class ConfigValidationError(ConfigError):
    """Exception pour les erreurs de validation de configuration."""
    def __init__(self, message: str, field: str = None, details: Dict = None):
        super().__init__(message)
        self.field = field
        self.details = details or {}

class ConfigMigrationError(ConfigError):
    """Exception pour les erreurs de migration de configuration."""
    pass

class ConfigBackupError(ConfigError):
    """Exception pour les erreurs de sauvegarde/restauration."""
    pass

class ConfigLockError(ConfigError):
    """Exception pour les conflits de verrouillage de configuration."""
    pass

# ================================
# MODÈLES DE DONNÉES
# ================================

@dataclass
class EnvironmentInfo:
    """Informations d'un environnement virtuel."""
    name: str
    path: str
    python_version: str
    backend_type: str = "pip"
    source_file_type: str = "requirements"
    created_at: str = None
    last_updated: str = None
    packages: List[Dict[str, str]] = None
    pyproject_info: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    health_status: str = "unknown"
    tags: List[str] = None
    alias: str = None
    
    def __post_init__(self):
        """Initialisation post-création avec valeurs par défaut."""
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.last_updated is None:
            self.last_updated = self.created_at
        if self.packages is None:
            self.packages = []
        if self.pyproject_info is None:
            self.pyproject_info = {}
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sérialisation JSON."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentInfo':
        """Crée une instance depuis un dictionnaire."""
        return cls(**data)

@dataclass
class ConfigSettings:
    """Paramètres de configuration système."""
    preferred_backend: str = "auto"
    default_python: str = "python3"
    environments_path: str = None
    pyproject_support: bool = True
    auto_detect_project_type: bool = True
    show_migration_hints: bool = True
    cache_enabled: bool = True
    cache_ttl_days: int = 7
    backup_enabled: bool = True
    backup_retention_days: int = 30
    max_backups: int = 10
    parallel_operations: bool = True
    verbose_output: bool = False
    confirm_destructive: bool = True
    
    def __post_init__(self):
        """Initialisation avec valeurs par défaut intelligentes."""
        if self.environments_path is None:
            self.environments_path = str(self._get_default_envs_path())
    
    def _get_default_envs_path(self) -> Path:
        """Chemin par défaut des environnements selon l'OS."""
        if platform.system() == "Windows":
            return Path.home() / "GestVenv" / "environments"
        else:
            return Path.home() / ".local" / "share" / "gestvenv" / "environments"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigSettings':
        """Crée depuis un dictionnaire."""
        return cls(**data)

# ================================
# GESTIONNAIRE PRINCIPAL
# ================================

class ConfigManager:
    """
    Gestionnaire de configuration centralisé pour GestVenv v1.1.
    
    Responsabilités:
    - Chargement/sauvegarde configuration JSON
    - Migration transparente v1.0 → v1.1
    - CRUD environnements virtuels
    - Validation et réparation des données
    - Sauvegarde automatique et restauration
    - Gestion des templates et alias
    - Cache et optimisations
    """
    
    # Constantes de configuration
    CONFIG_VERSION = "1.1.0"
    SUPPORTED_VERSIONS = ["1.0.0", "1.1.0"]
    CONFIG_SCHEMA_VERSION = 2
    
    # Validation
    VALID_BACKENDS = {"pip", "uv", "poetry", "pdm", "auto"}
    VALID_SOURCE_TYPES = {"requirements", "pyproject", "pipfile", "environment.yml"}
    VALID_HEALTH_STATUS = {"healthy", "corrupted", "missing", "unknown"}
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None, 
                 auto_migrate: bool = True, create_backup: bool = True):
        """
        Initialise le gestionnaire de configuration.
        
        Args:
            config_path: Chemin personnalisé vers la configuration
            auto_migrate: Migration automatique si nécessaire
            create_backup: Création automatique de sauvegardes
        """
        # Chemins et répertoires
        self.config_path = Path(config_path) if config_path else self._get_default_config_path()
        self.config_dir = self.config_path.parent
        self.backup_dir = self.config_dir / "backups"
        self.lock_file = self.config_dir / ".config.lock"
        
        # Options
        self.auto_migrate = auto_migrate
        self.create_backup = create_backup
        
        # État interne
        self._config_data: Dict[str, Any] = {}
        self._settings: ConfigSettings = ConfigSettings()
        self._environments: Dict[str, EnvironmentInfo] = {}
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._aliases: Dict[str, str] = {}
        self._lock_acquired = False
        
        # Initialisation
        self._ensure_directories()
        self._load_configuration()
        
        logger.info(f"ConfigManager initialisé - Version {self.CONFIG_VERSION}")
    
    def __enter__(self):
        """Context manager pour verrouillage automatique."""
        self.acquire_lock()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Libération automatique du verrou."""
        self.release_lock()
    
    # ================================
    # CONFIGURATION DES CHEMINS
    # ================================
    
    def _get_default_config_path(self) -> Path:
        """
        Détermine le chemin de configuration par défaut selon l'OS.
        
        Returns:
            Path: Chemin vers le fichier de configuration
        """
        system = platform.system()
        
        if system == "Windows":
            # Windows: %APPDATA%\GestVenv\config.json
            base_dir = Path(os.environ.get('APPDATA', Path.home() / "AppData" / "Roaming"))
            config_dir = base_dir / "GestVenv"
        elif system == "Darwin":
            # macOS: ~/Library/Application Support/GestVenv/config.json
            config_dir = Path.home() / "Library" / "Application Support" / "GestVenv"
        else:
            # Linux/Unix: ~/.config/gestvenv/config.json
            config_dir = Path.home() / ".config" / "gestvenv"
        
        return config_dir / "config.json"
    
    def _ensure_directories(self):
        """Crée les répertoires nécessaires."""
        for directory in [self.config_dir, self.backup_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Permissions sécurisées sur Unix/Linux
        if platform.system() != "Windows":
            os.chmod(self.config_dir, 0o700)
            os.chmod(self.backup_dir, 0o700)
    
    # ================================
    # VERROUILLAGE ET CONCURRENCE
    # ================================
    
    def acquire_lock(self, timeout: int = 30) -> bool:
        """
        Acquiert un verrou exclusif sur la configuration.
        
        Args:
            timeout: Timeout en secondes
            
        Returns:
            bool: True si le verrou a été acquis
            
        Raises:
            ConfigLockError: Si impossible d'acquérir le verrou
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            try:
                if not self.lock_file.exists():
                    # Créer le fichier de verrou
                    with open(self.lock_file, 'w') as f:
                        f.write(f"{os.getpid()}|{datetime.now().isoformat()}")
                    
                    self._lock_acquired = True
                    logger.debug("Verrou de configuration acquis")
                    return True
                else:
                    # Vérifier si le processus est encore actif
                    try:
                        with open(self.lock_file, 'r') as f:
                            content = f.read().strip()
                            if '|' in content:
                                pid_str, _ = content.split('|', 1)
                                pid = int(pid_str)
                                
                                # Vérifier si le processus existe encore
                                if not self._process_exists(pid):
                                    logger.warning(f"Verrou orphelin détecté (PID {pid}), suppression")
                                    self.lock_file.unlink()
                                    continue
                    except (ValueError, OSError):
                        # Fichier de verrou corrompu
                        logger.warning("Fichier de verrou corrompu, suppression")
                        self.lock_file.unlink()
                        continue
                
                # Attendre avant nouvelle tentative
                import time
                time.sleep(0.1)
                
            except OSError as e:
                logger.error(f"Erreur lors de l'acquisition du verrou: {e}")
                break
        
        raise ConfigLockError(f"Impossible d'acquérir le verrou dans les {timeout}s")
    
    def release_lock(self):
        """Libère le verrou de configuration."""
        if self._lock_acquired and self.lock_file.exists():
            try:
                self.lock_file.unlink()
                self._lock_acquired = False
                logger.debug("Verrou de configuration libéré")
            except OSError as e:
                logger.error(f"Erreur lors de la libération du verrou: {e}")
    
    def _process_exists(self, pid: int) -> bool:
        """Vérifie si un processus existe."""
        try:
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                      capture_output=True, text=True)
                return str(pid) in result.stdout
            else:
                os.kill(pid, 0)  # Signal 0 ne tue pas mais teste l'existence
                return True
        except (OSError, subprocess.SubprocessError):
            return False
    
    # ================================
    # CHARGEMENT ET SAUVEGARDE
    # ================================
    
    def _load_configuration(self):
        """Charge la configuration depuis le fichier JSON."""
        try:
            if not self.config_path.exists():
                logger.info("Fichier de configuration inexistant, création d'une nouvelle configuration")
                self._create_default_config()
                return
            
            # Chargement avec gestion d'erreurs
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
            
            # Validation et migration si nécessaire
            self._validate_and_migrate()
            
            # Extraction des sections
            self._extract_config_sections()
            
            logger.info(f"Configuration chargée: {len(self._environments)} environnements")
            
        except json.JSONDecodeError as e:
            logger.error(f"Configuration JSON corrompue: {e}")
            self._handle_corrupted_config()
        except Exception as e:
            logger.error(f"Erreur lors du chargement: {e}")
            raise ConfigError(f"Impossible de charger la configuration: {e}")
    
    def _create_default_config(self):
        """Crée une configuration par défaut."""
        self._config_data = {
            "version": self.CONFIG_VERSION,
            "schema_version": self.CONFIG_SCHEMA_VERSION,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "migration_from": None,
            "settings": self._settings.to_dict(),
            "environments": {},
            "templates": {},
            "aliases": {},
            "active_environment": None
        }
        
        # Sauvegarde immédiate
        self.save_configuration()
        logger.info("Configuration par défaut créée")
    
    def _validate_and_migrate(self):
        """Valide et migre la configuration si nécessaire."""
        # Vérification de la version
        config_version = self._config_data.get("version", "1.0.0")
        
        if config_version not in self.SUPPORTED_VERSIONS:
            raise ConfigValidationError(f"Version non supportée: {config_version}")
        
        # Migration automatique si activée
        if config_version != self.CONFIG_VERSION and self.auto_migrate:
            self._migrate_configuration(config_version)
        
        # Validation du schéma
        self._validate_config_schema()
    
    def _migrate_configuration(self, from_version: str):
        """
        Migre la configuration depuis une version antérieure.
        
        Args:
            from_version: Version source de la migration
        """
        logger.info(f"Migration de configuration {from_version} → {self.CONFIG_VERSION}")
        
        try:
            # Sauvegarde avant migration
            if self.create_backup:
                backup_path = self._create_migration_backup(from_version)
                logger.info(f"Sauvegarde pré-migration: {backup_path}")
            
            # Migration spécifique selon la version
            if from_version == "1.0.0":
                self._migrate_from_v1_0()
            
            # Mise à jour des métadonnées
            self._config_data["version"] = self.CONFIG_VERSION
            self._config_data["schema_version"] = self.CONFIG_SCHEMA_VERSION
            self._config_data["last_updated"] = datetime.now().isoformat()
            self._config_data["migration_from"] = from_version
            
            # Sauvegarde post-migration
            self.save_configuration()
            
            logger.info("Migration terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la migration: {e}")
            raise ConfigMigrationError(f"Échec de migration depuis {from_version}: {e}")
    
    def _migrate_from_v1_0(self):
        """Migration spécifique depuis la version 1.0."""
        # Ajout des nouveaux champs de configuration
        if "settings" not in self._config_data:
            self._config_data["settings"] = {}
        
        # Paramètres par défaut v1.1
        default_settings = self._settings.to_dict()
        settings = self._config_data["settings"]
        
        for key, value in default_settings.items():
            if key not in settings:
                settings[key] = value
        
        # Migration des environnements
        environments = self._config_data.get("environments", {})
        for env_name, env_data in environments.items():
            # Ajout des nouveaux champs
            env_data.setdefault("backend_type", "pip")
            env_data.setdefault("source_file_type", "requirements")
            env_data.setdefault("created_at", datetime.now().isoformat())
            env_data.setdefault("last_updated", datetime.now().isoformat())
            env_data.setdefault("pyproject_info", {})
            env_data.setdefault("metadata", {})
            env_data.setdefault("health_status", "unknown")
            env_data.setdefault("tags", [])
            env_data.setdefault("alias", None)
        
        # Ajout des nouvelles sections
        self._config_data.setdefault("templates", {})
        self._config_data.setdefault("aliases", {})
        
        logger.info(f"Migration v1.0: {len(environments)} environnements migrés")
    
    def _validate_config_schema(self):
        """Valide le schéma de configuration."""
        required_keys = {"version", "settings", "environments"}
        missing_keys = required_keys - set(self._config_data.keys())
        
        if missing_keys:
            raise ConfigValidationError(f"Clés manquantes: {missing_keys}")
        
        # Validation des environnements
        environments = self._config_data.get("environments", {})
        for env_name, env_data in environments.items():
            self._validate_environment_data(env_name, env_data)
    
    def _validate_environment_data(self, name: str, data: Dict[str, Any]):
        """
        Valide les données d'un environnement.
        
        Args:
            name: Nom de l'environnement
            data: Données à valider
        """
        required_fields = {"name", "path", "python_version"}
        missing_fields = required_fields - set(data.keys())
        
        if missing_fields:
            raise ConfigValidationError(
                f"Environnement {name}: champs manquants {missing_fields}",
                field=name
            )
        
        # Validation backend
        backend = data.get("backend_type", "pip")
        if backend not in self.VALID_BACKENDS:
            logger.warning(f"Backend inconnu pour {name}: {backend}")
        
        # Validation type de source
        source_type = data.get("source_file_type", "requirements")
        if source_type not in self.VALID_SOURCE_TYPES:
            logger.warning(f"Type de source inconnu pour {name}: {source_type}")
    
    def _extract_config_sections(self):
        """Extrait les sections de configuration dans les attributs."""
        # Paramètres
        settings_data = self._config_data.get("settings", {})
        self._settings = ConfigSettings.from_dict(settings_data)
        
        # Environnements
        self._environments = {}
        environments_data = self._config_data.get("environments", {})
        for env_name, env_data in environments_data.items():
            try:
                self._environments[env_name] = EnvironmentInfo.from_dict(env_data)
            except Exception as e:
                logger.error(f"Erreur environnement {env_name}: {e}")
        
        # Templates et alias
        self._templates = self._config_data.get("templates", {})
        self._aliases = self._config_data.get("aliases", {})
    
    def save_configuration(self, create_backup: bool = None) -> bool:
        """
        Sauvegarde la configuration dans le fichier JSON.
        
        Args:
            create_backup: Force la création d'une sauvegarde
            
        Returns:
            bool: True si la sauvegarde a réussi
        """
        if create_backup is None:
            create_backup = self.create_backup
        
        try:
            # Sauvegarde préventive
            if create_backup and self.config_path.exists():
                self._create_backup()
            
            # Préparation des données
            self._prepare_config_for_save()
            
            # Écriture atomique
            temp_path = self.config_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=2, ensure_ascii=False)
            
            # Remplacement atomique
            if platform.system() == "Windows":
                if self.config_path.exists():
                    self.config_path.unlink()
            temp_path.replace(self.config_path)
            
            # Permissions sécurisées
            if platform.system() != "Windows":
                os.chmod(self.config_path, 0o600)
            
            logger.debug("Configuration sauvegardée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            # Nettoyage du fichier temporaire
            temp_path = self.config_path.with_suffix('.tmp')
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    def _prepare_config_for_save(self):
        """Prépare les données de configuration pour la sauvegarde."""
        # Mise à jour timestamp
        self._config_data["last_updated"] = datetime.now().isoformat()
        
        # Synchronisation des sections
        self._config_data["settings"] = self._settings.to_dict()
        
        # Environnements
        environments_data = {}
        for name, env_info in self._environments.items():
            environments_data[name] = env_info.to_dict()
        self._config_data["environments"] = environments_data
        
        # Templates et alias
        self._config_data["templates"] = self._templates
        self._config_data["aliases"] = self._aliases
    
    def _handle_corrupted_config(self):
        """Gère une configuration corrompue."""
        logger.warning("Configuration corrompue détectée")
        
        # Tentative de restauration depuis sauvegarde
        if self._restore_from_backup():
            logger.info("Configuration restaurée depuis sauvegarde")
            return
        
        # Création d'une nouvelle configuration
        logger.warning("Création d'une nouvelle configuration")
        backup_corrupted = self.config_path.with_suffix('.corrupted')
        shutil.move(self.config_path, backup_corrupted)
        
        self._create_default_config()
    
    # ================================
    # GESTION DES SAUVEGARDES
    # ================================
    
    def _create_backup(self, suffix: str = None) -> Path:
        """
        Crée une sauvegarde de la configuration.
        
        Args:
            suffix: Suffixe optionnel pour le nom de fichier
            
        Returns:
            Path: Chemin vers la sauvegarde créée
        """
        if not self.config_path.exists():
            raise ConfigBackupError("Aucune configuration à sauvegarder")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            filename = f"config_{timestamp}_{suffix}.json"
        else:
            filename = f"config_{timestamp}.json"
        
        backup_path = self.backup_dir / filename
        
        try:
            shutil.copy2(self.config_path, backup_path)
            logger.debug(f"Sauvegarde créée: {backup_path}")
            
            # Nettoyage des anciennes sauvegardes
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            raise ConfigBackupError(f"Échec de sauvegarde: {e}")
    
    def _create_migration_backup(self, from_version: str) -> Path:
        """Crée une sauvegarde spéciale pour migration."""
        return self._create_backup(f"migration_from_v{from_version}")
    
    def _cleanup_old_backups(self):
        """Nettoie les anciennes sauvegardes."""
        try:
            backup_files = list(self.backup_dir.glob("config_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Supprimer les sauvegardes excédentaires
            max_backups = self._settings.max_backups
            for backup_file in backup_files[max_backups:]:
                backup_file.unlink()
                logger.debug(f"Ancienne sauvegarde supprimée: {backup_file}")
            
            # Supprimer les sauvegardes expirées
            retention_days = self._settings.backup_retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for backup_file in backup_files:
                if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                    backup_file.unlink()
                    logger.debug(f"Sauvegarde expirée supprimée: {backup_file}")
                    
        except Exception as e:
            logger.error(f"Erreur nettoyage sauvegardes: {e}")
    
    def _restore_from_backup(self, backup_path: Path = None) -> bool:
        """
        Restaure la configuration depuis une sauvegarde.
        
        Args:
            backup_path: Chemin spécifique, sinon dernière sauvegarde
            
        Returns:
            bool: True si la restauration a réussi
        """
        try:
            if backup_path is None:
                # Trouver la dernière sauvegarde
                backup_files = list(self.backup_dir.glob("config_*.json"))
                if not backup_files:
                    return False
                
                backup_path = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            # Validation de la sauvegarde
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Restauration
            shutil.copy2(backup_path, self.config_path)
            self._load_configuration()
            
            logger.info(f"Configuration restaurée depuis: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur restauration: {e}")
            return False
    
    # ================================
    # API PUBLIQUE - ENVIRONNEMENTS
    # ================================
    
    def get_environment(self, name: str) -> Optional[EnvironmentInfo]:
        """
        Récupère les informations d'un environnement.
        
        Args:
            name: Nom de l'environnement
            
        Returns:
            EnvironmentInfo ou None si inexistant
        """
        return self._environments.get(name)
    
    def add_environment(self, env_info: EnvironmentInfo) -> bool:
        """
        Ajoute un nouvel environnement.
        
        Args:
            env_info: Informations de l'environnement
            
        Returns:
            bool: True si ajouté avec succès
        """
        try:
            # Validation
            if env_info.name in self._environments:
                raise ConfigValidationError(f"Environnement {env_info.name} existe déjà")
            
            self._validate_environment_info(env_info)
            
            # Ajout
            env_info.last_updated = datetime.now().isoformat()
            self._environments[env_info.name] = env_info
            
            # Sauvegarde
            return self.save_configuration()
            
        except Exception as e:
            logger.error(f"Erreur ajout environnement {env_info.name}: {e}")
            return False
    
    def update_environment(self, env_info: EnvironmentInfo) -> bool:
        """
        Met à jour un environnement existant.
        
        Args:
            env_info: Nouvelles informations
            
        Returns:
            bool: True si mis à jour avec succès
        """
        try:
            if env_info.name not in self._environments:
                raise ConfigValidationError(f"Environnement {env_info.name} inexistant")
            
            self._validate_environment_info(env_info)
            
            # Mise à jour
            env_info.last_updated = datetime.now().isoformat()
            self._environments[env_info.name] = env_info
            
            return self.save_configuration()
            
        except Exception as e:
            logger.error(f"Erreur mise à jour environnement {env_info.name}: {e}")
            return False
    
    def remove_environment(self, name: str) -> bool:
        """
        Supprime un environnement de la configuration.
        
        Args:
            name: Nom de l'environnement
            
        Returns:
            bool: True si supprimé avec succès
        """
        try:
            if name not in self._environments:
                logger.warning(f"Environnement {name} inexistant")
                return True
            
            # Suppression
            del self._environments[name]
            
            # Mise à jour environnement actif si nécessaire
            if self._config_data.get("active_environment") == name:
                self._config_data["active_environment"] = None
            
            return self.save_configuration()
            
        except Exception as e:
            logger.error(f"Erreur suppression environnement {name}: {e}")
            return False
    
    def list_environments(self, filters: Dict[str, Any] = None) -> List[EnvironmentInfo]:
        """
        Liste les environnements avec filtres optionnels.
        
        Args:
            filters: Filtres à appliquer
            
        Returns:
            List[EnvironmentInfo]: Liste des environnements
        """
        environments = list(self._environments.values())
        
        if not filters:
            return environments
        
        # Application des filtres
        filtered = []
        for env in environments:
            if self._match_filters(env, filters):
                filtered.append(env)
        
        return filtered
    
    def _match_filters(self, env: EnvironmentInfo, filters: Dict[str, Any]) -> bool:
        """Vérifie si un environnement correspond aux filtres."""
        for key, value in filters.items():
            if key == "backend_type" and env.backend_type != value:
                return False
            elif key == "python_version" and env.python_version != value:
                return False
            elif key == "tags" and not set(value).issubset(set(env.tags)):
                return False
            elif key == "health_status" and env.health_status != value:
                return False
        
        return True
    
    def _validate_environment_info(self, env_info: EnvironmentInfo):
        """Valide les informations d'un environnement."""
        if not env_info.name or not env_info.name.strip():
            raise ConfigValidationError("Nom d'environnement requis")
        
        if not env_info.path:
            raise ConfigValidationError("Chemin d'environnement requis")
        
        if env_info.backend_type not in self.VALID_BACKENDS:
            raise ConfigValidationError(f"Backend invalide: {env_info.backend_type}")
    
    # ================================
    # API PUBLIQUE - PARAMÈTRES
    # ================================
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de paramètre.
        
        Args:
            key: Clé du paramètre
            default: Valeur par défaut
            
        Returns:
            Valeur du paramètre
        """
        return getattr(self._settings, key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Définit une valeur de paramètre.
        
        Args:
            key: Clé du paramètre
            value: Nouvelle valeur
            
        Returns:
            bool: True si défini avec succès
        """
        try:
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
                return self.save_configuration()
            else:
                logger.warning(f"Paramètre inconnu: {key}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur définition paramètre {key}: {e}")
            return False
    
    def get_settings(self) -> ConfigSettings:
        """Retourne une copie des paramètres."""
        return ConfigSettings.from_dict(self._settings.to_dict())
    
    def update_settings(self, **kwargs) -> bool:
        """
        Met à jour plusieurs paramètres.
        
        Args:
            **kwargs: Paramètres à mettre à jour
            
        Returns:
            bool: True si mis à jour avec succès
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self._settings, key):
                    setattr(self._settings, key, value)
                else:
                    logger.warning(f"Paramètre ignoré: {key}")
            
            return self.save_configuration()
            
        except Exception as e:
            logger.error(f"Erreur mise à jour paramètres: {e}")
            return False
    
    # ================================
    # API PUBLIQUE - ENVIRONNEMENT ACTIF
    # ================================
    
    def get_active_environment(self) -> Optional[str]:
        """Retourne le nom de l'environnement actif."""
        return self._config_data.get("active_environment")
    
    def set_active_environment(self, name: str = None) -> bool:
        """
        Définit l'environnement actif.
        
        Args:
            name: Nom de l'environnement ou None pour désactiver
            
        Returns:
            bool: True si défini avec succès
        """
        try:
            if name is not None and name not in self._environments:
                raise ConfigValidationError(f"Environnement {name} inexistant")
            
            self._config_data["active_environment"] = name
            return self.save_configuration()
            
        except Exception as e:
            logger.error(f"Erreur définition environnement actif: {e}")
            return False
    
    # ================================
    # API PUBLIQUE - TEMPLATES ET ALIAS
    # ================================
    
    def add_template(self, name: str, template_data: Dict[str, Any]) -> bool:
        """Ajoute un template d'environnement."""
        try:
            self._templates[name] = template_data
            return self.save_configuration()
        except Exception as e:
            logger.error(f"Erreur ajout template {name}: {e}")
            return False
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Récupère un template."""
        return self._templates.get(name)
    
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """Liste tous les templates."""
        return self._templates.copy()
    
    def add_alias(self, alias: str, environment_name: str) -> bool:
        """Ajoute un alias pour un environnement."""
        try:
            if environment_name not in self._environments:
                raise ConfigValidationError(f"Environnement {environment_name} inexistant")
            
            self._aliases[alias] = environment_name
            return self.save_configuration()
        except Exception as e:
            logger.error(f"Erreur ajout alias {alias}: {e}")
            return False
    
    def resolve_alias(self, name_or_alias: str) -> str:
        """Résout un alias vers le nom d'environnement."""
        return self._aliases.get(name_or_alias, name_or_alias)
    
    # ================================
    # API PUBLIQUE - UTILITAIRES
    # ================================
    
    def get_environments_path(self) -> Path:
        """Retourne le chemin des environnements."""
        return Path(self._settings.environments_path)
    
    def export_config(self, output_path: Union[str, Path], 
                     include_templates: bool = True, 
                     include_aliases: bool = True) -> bool:
        """
        Exporte la configuration vers un fichier.
        
        Args:
            output_path: Chemin de sortie
            include_templates: Inclure les templates
            include_aliases: Inclure les alias
            
        Returns:
            bool: True si exporté avec succès
        """
        try:
            export_data = {
                "version": self.CONFIG_VERSION,
                "exported_at": datetime.now().isoformat(),
                "settings": self._settings.to_dict(),
                "environments": {name: env.to_dict() 
                               for name, env in self._environments.items()}
            }
            
            if include_templates:
                export_data["templates"] = self._templates
            
            if include_aliases:
                export_data["aliases"] = self._aliases
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration exportée: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")
            return False
    
    def import_config(self, input_path: Union[str, Path], 
                     merge: bool = False) -> bool:
        """
        Importe une configuration depuis un fichier.
        
        Args:
            input_path: Chemin du fichier à importer
            merge: True pour fusionner, False pour remplacer
            
        Returns:
            bool: True si importé avec succès
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Sauvegarde préventive
            if self.create_backup:
                self._create_backup("pre_import")
            
            if merge:
                self._merge_config(import_data)
            else:
                self._replace_config(import_data)
            
            return self.save_configuration()
            
        except Exception as e:
            logger.error(f"Erreur import: {e}")
            return False
    
    def _merge_config(self, import_data: Dict[str, Any]) -> None:
        """Fusionne une configuration importée."""
        # Fusion des environnements
        for name, env_data in import_data.get("environments", {}).items():
            if name not in self._environments:
                self._environments[name] = EnvironmentInfo.from_dict(env_data)
        
        # Fusion des templates et alias
        self._templates.update(import_data.get("templates", {}))
        self._aliases.update(import_data.get("aliases", {}))
    
    def _replace_config(self, import_data: Dict[str, Any]) -> None:
        """Remplace la configuration par celle importée."""
        # Remplacement des environnements
        self._environments = {}
        for name, env_data in import_data.get("environments", {}).items():
            self._environments[name] = EnvironmentInfo.from_dict(env_data)
        
        # Remplacement templates et alias
        self._templates = import_data.get("templates", {})
        self._aliases = import_data.get("aliases", {})
        
        # Fusion des paramètres (préservation des valeurs locales)
        imported_settings = import_data.get("settings", {})
        current_settings = self._settings.to_dict()
        current_settings.update(imported_settings)
        self._settings = ConfigSettings.from_dict(current_settings)
    
    def repair_config(self) -> Tuple[bool, List[str]]:
        """
        Répare la configuration en corrigeant les erreurs détectées.
        
        Returns:
            Tuple[bool, List[str]]: (Succès, Liste des réparations)
        """
        repairs = []
        
        try:
            # Sauvegarde préventive
            self._create_backup("pre_repair")
            
            # Vérification et réparation des environnements
            corrupted_envs = []
            for name, env in self._environments.items():
                if not Path(env.path).exists():
                    corrupted_envs.append(name)
                    repairs.append(f"Environnement {name}: chemin inexistant")
            
            # Suppression des environnements corrompus
            for name in corrupted_envs:
                del self._environments[name]
                repairs.append(f"Environnement {name}: supprimé (corrompu)")
            
            # Réparation environnement actif
            active_env = self._config_data.get("active_environment")
            if active_env and active_env not in self._environments:
                self._config_data["active_environment"] = None
                repairs.append("Environnement actif: réinitialisé (inexistant)")
            
            # Sauvegarde des réparations
            success = self.save_configuration()
            
            logger.info(f"Réparation terminée: {len(repairs)} corrections")
            return success, repairs
            
        except Exception as e:
            logger.error(f"Erreur réparation: {e}")
            return False, [f"Erreur: {e}"]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la configuration."""
        try:
            stats = {
                "version": self.CONFIG_VERSION,
                "total_environments": len(self._environments),
                "active_environment": self._config_data.get("active_environment"),
                "templates_count": len(self._templates),
                "aliases_count": len(self._aliases),
                "config_size_bytes": self.config_path.stat().st_size if self.config_path.exists() else 0,
                "last_updated": self._config_data.get("last_updated"),
                "backends_used": list(set(env.backend_type for env in self._environments.values())),
                "python_versions": list(set(env.python_version for env in self._environments.values())),
                "health_summary": self._get_health_summary()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques: {e}")
            return {}
    
    def _get_health_summary(self) -> Dict[str, int]:
        """Résumé de l'état de santé des environnements."""
        summary = {}
        for env in self._environments.values():
            status = env.health_status
            summary[status] = summary.get(status, 0) + 1
        return summary


# ================================
# UTILITAIRES DE DÉCORATION
# ================================

def require_lock(func):
    """Décorateur pour s'assurer qu'un verrou est acquis."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._lock_acquired:
            raise ConfigLockError("Opération nécessite un verrou de configuration")
        return func(self, *args, **kwargs)
    return wrapper


# ================================
# GESTIONNAIRE DE CONTEXTE
# ================================

@contextmanager
def config_transaction(config_manager: ConfigManager) -> Generator[ConfigManager, Any, None]:
    """
    Gestionnaire de contexte pour les transactions de configuration.
    Acquiert un verrou et crée une sauvegarde automatique.
    """
    config_manager.acquire_lock()
    try:
        # Sauvegarde automatique au début de la transaction
        backup_path = config_manager._create_backup("transaction_start")
        
        yield config_manager
        
        # Sauvegarde de fin de transaction
        config_manager.save_configuration()
        
    except Exception as e:
        # Restauration en cas d'erreur
        logger.error(f"Erreur transaction, restauration: {e}")
        config_manager._restore_from_backup(backup_path)
        raise
    finally:
        config_manager.release_lock()


# ================================
# EXPORT PUBLIC
# ================================

__all__ = [
    'ConfigManager',
    'EnvironmentInfo', 
    'ConfigSettings',
    'ConfigError',
    'ConfigValidationError',
    'ConfigMigrationError', 
    'ConfigBackupError',
    'ConfigLockError',
    'config_transaction'
]