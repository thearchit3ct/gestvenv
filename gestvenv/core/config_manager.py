"""
Gestionnaire de configuration pour GestVenv v1.1
"""

import json
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .models import Config
from .exceptions import ConfigurationError, ValidationError


class ConfigManager:
    """Gestionnaire de configuration centralisée"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".gestvenv" / "config.json"
        self._config: Optional[Config] = None
        
    @property
    def config(self) -> Config:
        """Configuration chargée"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def load_config(self) -> Config:
        """Charge la configuration depuis le fichier"""
        try:
            if self.config_path.exists():
                return Config.load(self.config_path)
            else:
                # Première utilisation - création config par défaut
                config = Config()
                self.save_config(config)
                return config
        except Exception as e:
            raise ConfigurationError(
                f"Erreur chargement configuration: {e}",
                config_path=str(self.config_path)
            )
    
    def save_config(self, config: Optional[Config] = None) -> bool:
        """Sauvegarde la configuration"""
        config = config or self.config
        try:
            success = config.save(self.config_path)
            if success:
                self._config = config
            return success
        except Exception as e:
            raise ConfigurationError(
                f"Erreur sauvegarde configuration: {e}",
                config_path=str(self.config_path)
            )
    
    def get_environments_path(self) -> Path:
        """Chemin des environnements"""
        path = self.config.environments_path
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_preferred_backend(self) -> str:
        """Backend préféré"""
        return self.config.preferred_backend
    
    def set_backend_preference(self, backend: str) -> bool:
        """Définit le backend préféré"""
        valid_backends = ["auto", "pip", "uv", "poetry", "pdm"]
        if backend not in valid_backends:
            raise ConfigurationError(
                f"Backend invalide: {backend}. Backends valides: {valid_backends}"
            )
        
        self.config.preferred_backend = backend
        return self.save_config()
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Informations sur les backends"""
        return {
            "preferred": self.config.preferred_backend,
            "configs": self.config.backend_configs,
            "available_backends": ["pip", "uv", "poetry", "pdm"]
        }
    
    def update_backend_config(self, backend: str, config: Dict[str, Any]) -> bool:
        """Met à jour la configuration d'un backend"""
        if backend not in self.config.backend_configs:
            self.config.backend_configs[backend] = {}
        
        self.config.backend_configs[backend].update(config)
        return self.save_config()
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Configuration du cache"""
        return self.config.cache_settings
    
    def update_cache_config(self, settings: Dict[str, Any]) -> bool:
        """Met à jour la configuration du cache"""
        self.config.cache_settings.update(settings)
        return self.save_config()
    
    def migrate_from_v1_0(self) -> bool:
        """Migration depuis la configuration v1.0"""
        v1_config_path = Path.home() / ".gestvenv_v1" / "config.json"
        
        if not v1_config_path.exists():
            return True  # Rien à migrer
        
        try:
            # Sauvegarde de la config actuelle
            backup_path = self.backup_config()
            
            # Chargement config v1.0
            with open(v1_config_path, 'r', encoding='utf-8') as f:
                v1_data = json.load(f)
            
            # Migration des paramètres
            migrated_config = Config()
            
            # Mapping des champs v1.0 → v1.1
            if 'environments_path' in v1_data:
                migrated_config.environments_path = Path(v1_data['environments_path'])
            
            if 'default_python' in v1_data:
                migrated_config.default_python_version = v1_data['default_python']
            
            # Nouveaux paramètres v1.1 avec valeurs par défaut
            migrated_config.preferred_backend = "auto"
            migrated_config.auto_migrate = True
            migrated_config.show_migration_hints = True
            
            # Sauvegarde de la nouvelle config
            success = self.save_config(migrated_config)
            
            if success:
                # Marquage de la migration comme effectuée
                migration_marker = self.config_path.parent / ".migration_v1_0_completed"
                migration_marker.touch()
            
            return success
            
        except Exception as e:
            # Restauration en cas d'erreur
            if backup_path and backup_path.exists():
                self.restore_config(backup_path)
            
            raise ConfigurationError(
                f"Erreur migration v1.0: {e}",
                details={"backup_path": str(backup_path) if backup_path else None}
            )
    
    def backup_config(self) -> Optional[Path]:
        """Sauvegarde la configuration actuelle"""
        if not self.config_path.exists():
            return None
        
        try:
            timestamp = str(int(datetime.now().timestamp()))
            backup_path = self.config_path.parent / f"config.json.backup.{timestamp}"
            shutil.copy2(self.config_path, backup_path)
            return backup_path
        except Exception:
            return None
    
    def restore_config(self, backup_path: Path) -> bool:
        """Restaure une configuration depuis sauvegarde"""
        try:
            if backup_path.exists():
                shutil.copy2(backup_path, self.config_path)
                self._config = None  # Force rechargement
                return True
            return False
        except Exception:
            return False
    
    def reset_config(self) -> bool:
        """Remet la configuration par défaut"""
        try:
            # Sauvegarde avant reset
            self.backup_config()
            
            # Création nouvelle config par défaut
            default_config = Config()
            return self.save_config(default_config)
        except Exception as e:
            raise ConfigurationError(f"Erreur reset configuration: {e}")
    
    def validate_config(self) -> List[str]:
        """Valide la configuration et retourne les erreurs"""
        errors = []
        config = self.config
        
        # Validation chemins
        try:
            if not config.environments_path.parent.exists():
                errors.append(f"Répertoire parent inexistant: {config.environments_path.parent}")
        except Exception:
            errors.append("Chemin environnements invalide")
        
        # Validation backend
        valid_backends = ["auto", "pip", "uv", "poetry", "pdm"]
        if config.preferred_backend not in valid_backends:
            errors.append(f"Backend invalide: {config.preferred_backend}")
        
        # Validation cache
        cache_settings = config.cache_settings
        if not isinstance(cache_settings.get('max_size_mb'), (int, float)):
            errors.append("Taille max cache invalide")
        
        if not isinstance(cache_settings.get('cleanup_interval_days'), int):
            errors.append("Intervalle nettoyage cache invalide")
        
        # Validation version Python
        import re
        if not re.match(r'^\d+\.\d+', config.default_python_version):
            errors.append(f"Version Python invalide: {config.default_python_version}")
        
        return errors
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Résumé de la configuration"""
        config = self.config
        return {
            "version": config.version,
            "environments_path": str(config.environments_path),
            "preferred_backend": config.preferred_backend,
            "python_version": config.default_python_version,
            "cache_enabled": config.cache_settings.get("enabled", True),
            "cache_size_mb": config.cache_settings.get("max_size_mb", 1000),
            "auto_migrate": config.auto_migrate,
            "offline_mode": config.offline_mode
        }
    
    def export_config(self, output_path: Path, include_sensitive: bool = False) -> bool:
        """Exporte la configuration"""
        try:
            config_data = self.config.__dict__.copy()
            
            # Conversion des Path en string pour JSON
            config_data['environments_path'] = str(config_data['environments_path'])
            
            if not include_sensitive:
                # Suppression des données sensibles
                sensitive_keys = ['backend_configs']  # Peut contenir tokens/clés
                for key in sensitive_keys:
                    config_data.pop(key, None)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            return True
        except Exception:
            return False
    
    def import_config(self, config_path: Path, merge: bool = True) -> bool:
        """Importe une configuration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)

            if merge:
                # Fusion avec config existante
                current_data = self.config.__dict__.copy()
                current_data.update(imported_data)
                config_data = current_data
            else:
                # Remplacement complet
                config_data = imported_data

            # Reconstruction de la config
            new_config = Config()
            for key, value in config_data.items():
                if hasattr(new_config, key):
                    if key == 'environments_path':
                        setattr(new_config, key, Path(value))
                    else:
                        setattr(new_config, key, value)

            return self.save_config(new_config)
        except Exception:
            return False

    def get_setting(self, name: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration

        Args:
            name: Nom du paramètre à récupérer
            default: Valeur par défaut si le paramètre n'existe pas

        Returns:
            Valeur du paramètre ou default
        """
        if hasattr(self.config, name):
            return getattr(self.config, name)
        return default

    def set_setting(self, name: str, value: Any) -> bool:
        """Définit une valeur de configuration

        Args:
            name: Nom du paramètre à définir
            value: Valeur à attribuer

        Returns:
            True si succès

        Raises:
            ValidationError: Si la valeur est invalide
        """
        if not hasattr(self.config, name):
            # Ignorer silencieusement les paramètres inconnus
            return True

        # Validation spécifique selon le paramètre
        if name == 'default_python_version':
            if not re.match(r'^\d+\.\d+', str(value)):
                raise ValidationError(
                    f"Version Python invalide: {value}",
                    field=name,
                    validation_errors=[f"Valeur invalide: {value}"]
                )

        setattr(self.config, name, value)
        return self.save_config()

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Met à jour plusieurs paramètres de configuration

        Args:
            updates: Dictionnaire des mises à jour

        Returns:
            True si succès

        Raises:
            ValidationError: Si une valeur est invalide
        """
        # Validation préalable
        for name, value in updates.items():
            if name == 'default_python_version':
                if not re.match(r'^\d+\.\d+', str(value)):
                    raise ValidationError(
                        f"Version Python invalide: {value}",
                        field=name,
                        validation_errors=[f"Valeur invalide: {value}"]
                    )
            if name == 'cache_ttl_hours' and isinstance(value, (int, float)) and value < 0:
                raise ValidationError(
                    f"Valeur TTL cache invalide: {value}",
                    field=name,
                    validation_errors=[f"Valeur invalide: {value}"]
                )

        # Application des mises à jour
        for name, value in updates.items():
            if hasattr(self.config, name):
                setattr(self.config, name, value)

        return self.save_config()

    def get_cache_path(self) -> Path:
        """Retourne le chemin du cache

        Returns:
            Chemin vers le répertoire cache
        """
        cache_path = self.config.environments_path.parent / "cache"
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    def ensure_directories(self) -> None:
        """Crée les répertoires nécessaires s'ils n'existent pas"""
        # Répertoire de configuration
        config_dir = self.config_path.parent
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

        # Répertoire des environnements
        env_path = self.config.environments_path
        if not env_path.exists():
            env_path.mkdir(parents=True, exist_ok=True)

        # Répertoire cache
        cache_path = self.config.environments_path.parent / "cache"
        if not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)