"""
Service de migration et conversion pour GestVenv v1.1
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass , field

from ..core.models import PyProjectInfo
from ..core.exceptions import MigrationError, ValidationError
from ..utils import TomlHandler, ValidationUtils, PathUtils

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Résultat d'une migration"""
    success: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    backup_path: Optional[Path] = None


@dataclass 
class ConversionResult:
    """Résultat d'une conversion"""
    success: bool
    message: str
    output_path: Optional[Path] = None
    dependencies_converted: int = 0
    optional_groups: List[str] = field(default_factory=list)


class MigrationService:
    """Service de migration automatique et conversion"""
    
    def __init__(self):
        self.backup_dir = Path.home() / ".gestvenv" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def auto_migrate_if_needed(self) -> MigrationResult:
        """Migration automatique si nécessaire"""
        try:
            # Détection v1.0
            v1_config_path = Path.home() / ".gestvenv_v1" / "config.json"
            v1_1_config_path = Path.home() / ".gestvenv" / "config.json"
            
            if v1_config_path.exists() and not v1_1_config_path.exists():
                logger.info("Migration automatique v1.0 → v1.1 détectée")
                return self.migrate_from_v1_0()
                
            return MigrationResult(
                success=True, 
                message="Aucune migration nécessaire"
            )
            
        except Exception as e:
            logger.error(f"Erreur migration automatique: {e}")
            return MigrationResult(
                success=False,
                message=f"Erreur migration automatique: {e}"
            )
    
    def migrate_from_v1_0(self) -> MigrationResult:
        """Migration complète depuis v1.0"""
        migration_steps = [
            ("Sauvegarde données v1.0", self._backup_v1_0_data),
            ("Migration configuration", self._migrate_config_v1_0),
            ("Migration environnements", self._migrate_environments_v1_0),
            ("Validation migration", self._validate_migration),
            ("Nettoyage", self._cleanup_v1_0_data)
        ]
        
        results = []
        backup_path = None
        
        try:
            for step_name, step_function in migration_steps:
                logger.info(f"Exécution: {step_name}")
                
                if step_name == "Sauvegarde données v1.0":
                    backup_path = step_function()
                    step_result = backup_path is not None
                else:
                    step_result = step_function()
                
                results.append((step_name, step_result, None))
                
                if not step_result:
                    raise MigrationError(f"Échec étape: {step_name}")
                    
        except Exception as e:
            logger.error(f"Erreur migration: {e}")
            results.append((step_name, False, str(e)))
            
            # Rollback en cas d'erreur
            if backup_path:
                self._rollback_migration(backup_path)
                
            return MigrationResult(
                success=False,
                message=f"Migration échouée à l'étape: {step_name}",
                details={"error": str(e), "steps": results},
                backup_path=backup_path
            )
            
        return MigrationResult(
            success=True,
            message="Migration v1.0 → v1.1 réussie",
            details={"steps": results},
            backup_path=backup_path
        )
    
    def convert_requirements_to_pyproject(
        self, 
        req_path: Path, 
        output_path: Optional[Path] = None,
        project_name: Optional[str] = None
    ) -> ConversionResult:
        """Conversion requirements.txt → pyproject.toml"""
        if not req_path.exists():
            return ConversionResult(
                success=False,
                message=f"Fichier {req_path} introuvable"
            )
            
        try:
            # Parsing requirements.txt
            main_deps, dev_deps = self._parse_requirements_file(req_path)
            
            # Détection fichiers requirements auxiliaires
            optional_deps = self._detect_optional_requirements(req_path.parent)
            if dev_deps:
                optional_deps["dev"] = dev_deps
                
            # Génération pyproject.toml
            project_name = project_name or req_path.parent.name or "my-project"
            
            pyproject_data = {
                "project": {
                    "name": project_name,
                    "version": "0.1.0",
                    "description": f"Converted from {req_path.name}",
                    "dependencies": main_deps
                },
                "build-system": {
                    "requires": ["setuptools>=45", "wheel"],
                    "build-backend": "setuptools.build_meta"
                }
            }
            
            if optional_deps:
                pyproject_data["project"]["optional-dependencies"] = optional_deps
                
            # Métadonnées conversion
            pyproject_data["tool"] = {
                "gestvenv": {
                    "converted_from": str(req_path),
                    "conversion_date": datetime.now().isoformat(),
                    "original_format": "requirements.txt"
                }
            }
            
            # Sauvegarde
            if not output_path:
                output_path = req_path.parent / "pyproject.toml"
                
            self._save_pyproject_toml(pyproject_data, output_path)
            
            return ConversionResult(
                success=True,
                message=f"Conversion réussie: {output_path}",
                output_path=output_path,
                dependencies_converted=len(main_deps),
                optional_groups=list(optional_deps.keys())
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                message=f"Erreur conversion: {e}"
            )
    
    def detect_migration_candidates(self) -> List[Path]:
        """Détecte les candidats à la migration"""
        candidates = []
        
        # Recherche requirements.txt sans pyproject.toml
        search_paths = [Path.cwd(), Path.home()]
        
        for path in search_paths:
            if path.exists():
                for req_file in path.rglob("requirements*.txt"):
                    pyproject_file = req_file.parent / "pyproject.toml"
                    if not pyproject_file.exists():
                        candidates.append(req_file)
        
        return candidates[:10]  # Limiter à 10 résultats
    
    def backup_environment(self, env_info) -> Path:
        """Sauvegarde un environnement"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{env_info.name}_{timestamp}.json"
            backup_path = self.backup_dir / "environments" / backup_name
            
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(env_info.to_dict(), f, indent=2, default=str)
            
            return backup_path
        except Exception as e:
            logger.error(f"Erreur sauvegarde environnement: {e}")
            raise MigrationError(f"Échec sauvegarde: {e}")
    
    def rollback_migration(self, backup_path: Path, target_path: Path) -> bool:
        """Rollback d'une migration"""
        try:
            if backup_path.exists():
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(backup_path, target_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur rollback: {e}")
            return False
    
    # Méthodes privées
    
    def _backup_v1_0_data(self) -> Optional[Path]:
        """Sauvegarde les données v1.0"""
        try:
            v1_path = Path.home() / ".gestvenv_v1"
            if not v1_path.exists():
                return self.backup_dir / "empty_v1_backup"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"v1_0_backup_{timestamp}"
            
            shutil.copytree(v1_path, backup_path)
            logger.info(f"Données v1.0 sauvegardées dans {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde v1.0: {e}")
            return None
    
    def _migrate_config_v1_0(self) -> bool:
        """Migration de la configuration v1.0"""
        old_config_path = Path.home() / ".gestvenv_v1" / "config.json"
        new_config_path = Path.home() / ".gestvenv" / "config.json"
        
        try:
            # Configuration par défaut v1.1
            new_config = {
                "version": "1.1.0",
                "migration": {
                    "from_version": "1.0.0",
                    "migration_date": datetime.now().isoformat(),
                    "auto_migrate": True
                },
                "paths": {
                    "environments_path": str(Path.home() / ".gestvenv" / "environments"),
                },
                "backends": {
                    "preferred_backend": "auto",
                    "backend_configs": {}
                },
                "cache": {
                    "enabled": True,
                    "max_size_mb": 1000,
                    "cleanup_interval_days": 30,
                    "compression": True,
                    "offline_mode": False
                },
                "interface": {
                    "show_migration_hints": True,
                    "default_format": "table",
                    "emoji_in_output": True
                }
            }
            
            # Migration paramètres v1.0 si le fichier existe
            if old_config_path.exists():
                with open(old_config_path, 'r', encoding='utf-8') as f:
                    old_config = json.load(f)
                
                # Mapping des champs compatibles
                if 'environments_path' in old_config:
                    new_config["paths"]["environments_path"] = old_config['environments_path']
                
                if 'default_python' in old_config:
                    new_config["default_python_version"] = old_config['default_python']
            
            # Sauvegarde nouvelle config
            new_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(new_config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2)
            
            logger.info("✅ Configuration migrée v1.0 → v1.1")
            return True
            
        except Exception as e:
            logger.error(f"Erreur migration config: {e}")
            return False
    
    def _migrate_environments_v1_0(self) -> bool:
        """Migration des environnements v1.0"""
        old_env_path = Path.home() / ".gestvenv_v1" / "environments"
        new_env_path = Path.home() / ".gestvenv" / "environments"
        
        if not old_env_path.exists():
            logger.info("Aucun environnement v1.0 à migrer")
            return True
        
        try:
            new_env_path.mkdir(parents=True, exist_ok=True)
            migrated_count = 0
            
            for env_dir in old_env_path.iterdir():
                if env_dir.is_dir():
                    try:
                        # Copie physique
                        target_dir = new_env_path / env_dir.name
                        if target_dir.exists():
                            shutil.rmtree(target_dir)
                        shutil.copytree(env_dir, target_dir)
                        
                        # Création métadonnées v1.1
                        self._create_v1_1_metadata(target_dir)
                        
                        migrated_count += 1
                        logger.info(f"✅ Environnement migré: {env_dir.name}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️  Échec migration {env_dir.name}: {e}")
                        
            logger.info(f"✅ {migrated_count} environnements migrés")
            return True
            
        except Exception as e:
            logger.error(f"Erreur migration environnements: {e}")
            return False
    
    def _create_v1_1_metadata(self, env_path: Path) -> None:
        """Crée les métadonnées v1.1 pour un environnement"""
        try:
            # Détection version Python
            python_version = self._detect_python_version(env_path)
            
            # Métadonnées basiques
            metadata = {
                "name": env_path.name,
                "path": str(env_path),
                "python_version": python_version,
                "backend_type": "pip",  # Défaut v1.0
                "source_file_type": "requirements.txt",
                "health": "unknown",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "is_active": False,
                "packages": [],
                "dependency_groups": {},
                "metadata": {
                    "migrated_from": "v1.0",
                    "migration_date": datetime.now().isoformat()
                }
            }
            
            # Sauvegarde métadonnées
            metadata_path = env_path / ".gestvenv-metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Erreur création métadonnées v1.1: {e}")
    
    def _detect_python_version(self, env_path: Path) -> str:
        """Détecte la version Python d'un environnement"""
        try:
            # Lecture pyvenv.cfg
            pyvenv_cfg = env_path / "pyvenv.cfg"
            if pyvenv_cfg.exists():
                content = pyvenv_cfg.read_text(encoding='utf-8')
                for line in content.split('\n'):
                    if line.startswith('version'):
                        version = line.split('=')[1].strip()
                        # Extraction version majeure.mineure
                        parts = version.split('.')
                        if len(parts) >= 2:
                            return f"{parts[0]}.{parts[1]}"
            
            # Fallback
            return "3.11"
            
        except Exception:
            return "3.11"
    
    def _validate_migration(self) -> bool:
        """Valide la migration"""
        try:
            # Vérification structure
            gestvenv_path = Path.home() / ".gestvenv"
            required_items = ["config.json", "environments"]
            
            for item in required_items:
                if not (gestvenv_path / item).exists():
                    logger.error(f"Élément manquant après migration: {item}")
                    return False
            
            logger.info("✅ Migration validée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur validation migration: {e}")
            return False
    
    def _cleanup_v1_0_data(self) -> bool:
        """Nettoyage optionnel des données v1.0"""
        try:
            # Ne pas supprimer automatiquement - laisser le choix à l'utilisateur
            logger.info("Données v1.0 conservées pour sécurité")
            return True
        except Exception:
            return True
    
    def _rollback_migration(self, backup_path: Path) -> bool:
        """Rollback en cas d'erreur"""
        try:
            gestvenv_path = Path.home() / ".gestvenv"
            
            if gestvenv_path.exists():
                shutil.rmtree(gestvenv_path)
            
            if backup_path and backup_path.exists():
                # Restauration depuis sauvegarde
                logger.info(f"Rollback depuis {backup_path}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Erreur rollback: {e}")
            return False
    
    def _parse_requirements_file(self, req_path: Path) -> Tuple[List[str], List[str]]:
        """Parse un fichier requirements.txt"""
        main_deps = []
        dev_deps = []
        
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Ignorer commentaires et lignes vides
                    if not line or line.startswith('#'):
                        continue
                    
                    # Ignorer options pip
                    if line.startswith('-'):
                        continue
                    
                    # Classification dev vs main
                    if any(keyword in line.lower() for keyword in 
                          ['test', 'dev', 'debug', 'lint', 'format', 'coverage']):
                        dev_deps.append(line)
                    else:
                        main_deps.append(line)
                        
        except Exception as e:
            raise ValidationError(f"Erreur parsing {req_path}: {e}")
        
        return main_deps, dev_deps
    
    def _detect_optional_requirements(self, directory: Path) -> Dict[str, List[str]]:
        """Détecte les fichiers requirements optionnels"""
        optional_deps = {}
        
        patterns = {
            "dev": ["requirements-dev.txt", "requirements_dev.txt", "dev-requirements.txt"],
            "test": ["requirements-test.txt", "requirements_test.txt", "test-requirements.txt"],
            "docs": ["requirements-docs.txt", "requirements_docs.txt", "docs-requirements.txt"]
        }
        
        for group, filenames in patterns.items():
            for filename in filenames:
                req_file = directory / filename
                if req_file.exists():
                    try:
                        main_deps, _ = self._parse_requirements_file(req_file)
                        if main_deps:
                            optional_deps[group] = main_deps
                            break
                    except Exception:
                        continue
        
        return optional_deps
    
    def _save_pyproject_toml(self, data: Dict[str, Any], output_path: Path) -> None:
        """Sauvegarde un fichier pyproject.toml"""
        try:
            TomlHandler.dump(data, output_path)
        except Exception as e:
            raise MigrationError(f"Erreur sauvegarde pyproject.toml: {e}")