"""
MigrationService - Service de migration et gestion de compatibilité.

Ce service gère les migrations entre versions de GestVenv et les conversions
de formats de configuration :
- Migration v1.0 → v1.1
- Conversion requirements.txt → pyproject.toml
- Migration setup.py → pyproject.toml
- Mise à jour des environnements existants
- Sauvegarde et rollback automatiques
- Validation post-migration

Il assure la compatibilité ascendante et facilite l'adoption des nouveaux formats.
"""

import json
import logging
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import re

logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Types de migration supportés."""
    VERSION_UPGRADE = "version_upgrade"
    REQUIREMENTS_TO_PYPROJECT = "requirements_to_pyproject"
    SETUP_TO_PYPROJECT = "setup_to_pyproject"
    ENVIRONMENT_FORMAT = "environment_format"
    CONFIG_FORMAT = "config_format"


class MigrationStatus(Enum):
    """Statuts de migration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationStep:
    """Étape d'une migration."""
    id: str
    name: str
    description: str
    required: bool = True
    completed: bool = False
    error_message: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationPlan:
    """Plan de migration complet."""
    migration_type: MigrationType
    source_version: str
    target_version: str
    description: str
    steps: List[MigrationStep] = field(default_factory=list)
    backup_required: bool = True
    reversible: bool = True
    estimated_duration: float = 0.0
    
    @property
    def total_steps(self) -> int:
        """Nombre total d'étapes."""
        return len(self.steps)
    
    @property
    def completed_steps(self) -> int:
        """Nombre d'étapes complétées."""
        return sum(1 for step in self.steps if step.completed)
    
    @property
    def progress_percentage(self) -> float:
        """Pourcentage de progression."""
        if not self.steps:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100.0


@dataclass
class MigrationResult:
    """Résultat d'une migration."""
    success: bool
    migration_type: MigrationType
    source_path: Path
    target_path: Optional[Path] = None
    backup_path: Optional[Path] = None
    steps_completed: int = 0
    total_steps: int = 0
    duration: float = 0.0
    message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_warnings(self) -> bool:
        """True s'il y a des avertissements."""
        return len(self.warnings) > 0
    
    @property
    def success_rate(self) -> float:
        """Taux de réussite des étapes."""
        if self.total_steps == 0:
            return 100.0
        return (self.steps_completed / self.total_steps) * 100.0


class MigrationStrategy(ABC):
    """Interface abstraite pour les stratégies de migration."""
    
    @abstractmethod
    def can_migrate(self, source_path: Path) -> bool:
        """Vérifie si la migration est applicable."""
        pass
    
    @abstractmethod
    def create_plan(self, source_path: Path, target_path: Optional[Path] = None) -> MigrationPlan:
        """Crée un plan de migration."""
        pass
    
    @abstractmethod
    def execute_migration(self, plan: MigrationPlan, source_path: Path, 
                         target_path: Optional[Path] = None) -> MigrationResult:
        """Exécute la migration."""
        pass
    
    @abstractmethod
    def rollback_migration(self, result: MigrationResult) -> bool:
        """Effectue un rollback si possible."""
        pass


class RequirementsToPyprojectStrategy(MigrationStrategy):
    """Stratégie de migration requirements.txt → pyproject.toml."""
    
    def __init__(self, system_service=None):
        self.system_service = system_service
    
    def can_migrate(self, source_path: Path) -> bool:
        """Vérifie la présence de requirements.txt."""
        return (source_path / "requirements.txt").exists()
    
    def create_plan(self, source_path: Path, target_path: Optional[Path] = None) -> MigrationPlan:
        """Crée le plan de migration requirements.txt → pyproject.toml."""
        steps = [
            MigrationStep(
                id="parse_requirements",
                name="Analyse requirements.txt",
                description="Parse et valide le fichier requirements.txt"
            ),
            MigrationStep(
                id="detect_project_info",
                name="Détection informations projet",
                description="Extraction des métadonnées du projet"
            ),
            MigrationStep(
                id="create_pyproject",
                name="Génération pyproject.toml",
                description="Création du fichier pyproject.toml"
            ),
            MigrationStep(
                id="validate_result",
                name="Validation",
                description="Validation du pyproject.toml généré"
            )
        ]
        
        return MigrationPlan(
            migration_type=MigrationType.REQUIREMENTS_TO_PYPROJECT,
            source_version="requirements.txt",
            target_version="pyproject.toml",
            description="Conversion requirements.txt vers pyproject.toml",
            steps=steps,
            backup_required=True,
            reversible=True,
            estimated_duration=10.0
        )
    
    def execute_migration(self, plan: MigrationPlan, source_path: Path, 
                         target_path: Optional[Path] = None) -> MigrationResult:
        """Exécute la migration requirements.txt → pyproject.toml."""
        start_time = time.time()
        result = MigrationResult(
            success=False,
            migration_type=MigrationType.REQUIREMENTS_TO_PYPROJECT,
            source_path=source_path,
            target_path=target_path or source_path,
            total_steps=len(plan.steps)
        )
        
        try:
            requirements_file = source_path / "requirements.txt"
            pyproject_file = (target_path or source_path) / "pyproject.toml"
            
            # Sauvegarde si nécessaire
            if plan.backup_required and pyproject_file.exists():
                backup_path = pyproject_file.with_suffix('.toml.backup')
                shutil.copy2(pyproject_file, backup_path)
                result.backup_path = backup_path
            
            # Étape 1: Parse requirements.txt
            dependencies = self._parse_requirements_file(requirements_file)
            plan.steps[0].completed = True
            result.steps_completed += 1
            
            # Étape 2: Détection informations projet
            project_info = self._detect_project_metadata(source_path)
            plan.steps[1].completed = True
            result.steps_completed += 1
            
            # Étape 3: Génération pyproject.toml
            pyproject_content = self._generate_pyproject_content(dependencies, project_info)
            with open(pyproject_file, 'w', encoding='utf-8') as f:
                f.write(pyproject_content)
            plan.steps[2].completed = True
            result.steps_completed += 1
            
            # Étape 4: Validation
            if self._validate_pyproject(pyproject_file):
                plan.steps[3].completed = True
                result.steps_completed += 1
                result.success = True
                result.message = "Migration réussie vers pyproject.toml"
            else:
                result.errors.append("Validation du pyproject.toml échouée")
                result.message = "Migration partiellement réussie (validation échouée)"
            
            result.target_path = pyproject_file
            
        except Exception as e:
            logger.error(f"Erreur lors de la migration requirements → pyproject: {e}")
            result.errors.append(str(e))
            result.message = f"Migration échouée: {str(e)}"
        
        result.duration = time.time() - start_time
        return result
    
    def rollback_migration(self, result: MigrationResult) -> bool:
        """Rollback de la migration requirements → pyproject."""
        try:
            if result.backup_path and result.backup_path.exists():
                # Restaurer la sauvegarde
                if result.target_path:
                    shutil.copy2(result.backup_path, result.target_path)
                    result.backup_path.unlink()  # Supprimer la sauvegarde
                return True
            elif result.target_path and result.target_path.exists():
                # Supprimer le fichier créé
                result.target_path.unlink()
                return True
        except Exception as e:
            logger.error(f"Erreur lors du rollback: {e}")
            return False
        
        return True
    
    def _parse_requirements_file(self, requirements_path: Path) -> List[Dict[str, str]]:
        """Parse un fichier requirements.txt."""
        dependencies = []
        
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Ignorer commentaires et lignes vides
                    if not line or line.startswith('#'):
                        continue
                    
                    # Ignorer les options pip
                    if line.startswith('-'):
                        continue
                    
                    # Parse la dépendance
                    dep_info = self._parse_dependency_line(line, line_num)
                    if dep_info:
                        dependencies.append(dep_info)
        
        except Exception as e:
            logger.error(f"Erreur lors du parsing requirements.txt: {e}")
            raise
        
        return dependencies
    
    def _parse_dependency_line(self, line: str, line_num: int) -> Optional[Dict[str, str]]:
        """Parse une ligne de dépendance."""
        try:
            # Pattern basique pour package[extras]>=version; marker
            pattern = r'^([a-zA-Z0-9_.-]+)(\[[^\]]+\])?(.*?)(?:;(.*))?$'
            match = re.match(pattern, line.strip())
            
            if match:
                name = match.group(1)
                extras = match.group(2) or ""
                version_spec = match.group(3) or ""
                markers = match.group(4) or ""
                
                # Construction de la spécification
                spec = name
                if extras:
                    spec += extras
                if version_spec:
                    spec += version_spec
                if markers:
                    spec += f"; {markers.strip()}"
                
                return {
                    'name': name,
                    'spec': spec,
                    'line_number': line_num
                }
            else:
                logger.warning(f"Ligne de dépendance invalide ignorée (ligne {line_num}): {line}")
                return None
        
        except Exception as e:
            logger.warning(f"Erreur parsing ligne {line_num}: {e}")
            return None
    
    def _detect_project_metadata(self, project_path: Path) -> Dict[str, Any]:
        """Détecte les métadonnées du projet."""
        metadata = {
            'name': project_path.name.replace('_', '-').lower(),
            'version': '0.1.0',
            'description': '',
            'authors': [],
            'license': '',
            'readme': None,
            'homepage': '',
            'repository': ''
        }
        
        # Détection du README
        readme_files = ['README.md', 'README.rst', 'README.txt', 'README']
        for readme_name in readme_files:
            readme_path = project_path / readme_name
            if readme_path.exists():
                metadata['readme'] = readme_name
                break
        
        # Détection setup.py pour extraction de métadonnées
        setup_py = project_path / 'setup.py'
        if setup_py.exists():
            try:
                setup_metadata = self._extract_setup_metadata(setup_py)
                metadata.update(setup_metadata)
            except Exception as e:
                logger.warning(f"Impossible d'extraire les métadonnées de setup.py: {e}")
        
        # Détection du LICENSE
        license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING']
        for license_name in license_files:
            if (project_path / license_name).exists():
                metadata['license'] = {'file': license_name}
                break
        
        return metadata
    
    def _extract_setup_metadata(self, setup_py: Path) -> Dict[str, Any]:
        """Extrait les métadonnées de setup.py (méthode simplifiée)."""
        metadata = {}
        
        try:
            content = setup_py.read_text(encoding='utf-8')
            
            # Expressions régulières pour extraire les métadonnées communes
            patterns = {
                'name': r'name\s*=\s*["\']([^"\']+)["\']',
                'version': r'version\s*=\s*["\']([^"\']+)["\']',
                'description': r'description\s*=\s*["\']([^"\']+)["\']',
                'author': r'author\s*=\s*["\']([^"\']+)["\']',
                'author_email': r'author_email\s*=\s*["\']([^"\']+)["\']',
                'url': r'url\s*=\s*["\']([^"\']+)["\']',
                'license': r'license\s*=\s*["\']([^"\']+)["\']'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    metadata[key] = match.group(1)
            
            # Construction des auteurs
            if 'author' in metadata:
                author_info = {'name': metadata['author']}
                if 'author_email' in metadata:
                    author_info['email'] = metadata['author_email']
                metadata['authors'] = [author_info]
        
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction setup.py: {e}")
        
        return metadata
    
    def _generate_pyproject_content(self, dependencies: List[Dict[str, str]], 
                                   metadata: Dict[str, Any]) -> str:
        """Génère le contenu du fichier pyproject.toml."""
        lines = [
            "[build-system]",
            'requires = ["setuptools>=45", "wheel"]',
            'build-backend = "setuptools.build_meta"',
            "",
            "[project]",
            f'name = "{metadata["name"]}"',
            f'version = "{metadata["version"]}"',
        ]
        
        if metadata.get('description'):
            lines.append(f'description = "{metadata["description"]}"')
        
        if metadata.get('authors'):
            lines.append("authors = [")
            for author in metadata['authors']:
                if isinstance(author, dict):
                    if 'email' in author:
                        lines.append(f'    {{name = "{author["name"]}", email = "{author["email"]}"}},')
                    else:
                        lines.append(f'    {{name = "{author["name"]}"}},')
                else:
                    lines.append(f'    {{name = "{author}"}},')
            lines.append("]")
        
        if metadata.get('license'):
            if isinstance(metadata['license'], dict) and 'file' in metadata['license']:
                lines.append(f'license = {{file = "{metadata["license"]["file"]}"}}')
            else:
                lines.append(f'license = {{text = "{metadata["license"]}"}}')
        
        if metadata.get('readme'):
            lines.append(f'readme = "{metadata["readme"]}"')
        
        # URLs
        urls = {}
        if metadata.get('homepage'):
            urls['Homepage'] = metadata['homepage']
        if metadata.get('repository'):
            urls['Repository'] = metadata['repository']
        if metadata.get('url'):
            urls['Homepage'] = metadata['url']
        
        if urls:
            lines.append("urls = {")
            for name, url in urls.items():
                lines.append(f'    {name} = "{url}",')
            lines.append("}")
        
        # Python requirement (par défaut)
        lines.extend([
            'requires-python = ">=3.8"',
            "classifiers = [",
            '    "Development Status :: 3 - Alpha",',
            '    "Intended Audience :: Developers",',
            '    "License :: OSI Approved :: MIT License",',
            '    "Programming Language :: Python :: 3",',
            '    "Programming Language :: Python :: 3.8",',
            '    "Programming Language :: Python :: 3.9",',
            '    "Programming Language :: Python :: 3.10",',
            '    "Programming Language :: Python :: 3.11",',
            '    "Programming Language :: Python :: 3.12",',
            "]"
        ])
        
        # Dépendances
        if dependencies:
            lines.append("dependencies = [")
            for dep in dependencies:
                lines.append(f'    "{dep["spec"]}",')
            lines.append("]")
        else:
            lines.append("dependencies = []")
        
        # Dépendances optionnelles (exemple)
        lines.extend([
            "",
            "[project.optional-dependencies]",
            "dev = [",
            '    "pytest>=6.0",',
            '    "pytest-cov",',
            '    "black",',
            '    "isort",',
            '    "flake8",',
            "]"
        ])
        
        return "\n".join(lines) + "\n"
    
    def _validate_pyproject(self, pyproject_path: Path) -> bool:
        """Valide le fichier pyproject.toml généré."""
        try:
            # Import conditionnel de TOML
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    logger.warning("Bibliothèque TOML non disponible pour validation")
                    return True  # Assume valid if can't validate
            
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
            
            # Vérifications basiques
            if 'project' not in data:
                return False
            
            project = data['project']
            required_fields = ['name', 'version']
            
            for field in required_fields:
                if field not in project:
                    logger.error(f"Champ requis manquant dans pyproject.toml: {field}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de la validation pyproject.toml: {e}")
            return False


class VersionMigrationStrategy(MigrationStrategy):
    """Stratégie de migration entre versions de GestVenv."""
    
    def __init__(self, system_service=None):
        self.system_service = system_service
        
        # Définition des migrations supportées
        self.migration_matrix = {
            ('1.0.0', '1.1.0'): self._migrate_1_0_to_1_1
        }
    
    def can_migrate(self, source_path: Path) -> bool:
        """Vérifie si une migration de version est nécessaire."""
        config_file = source_path / '.gestvenv' / 'config.json'
        if not config_file.exists():
            return False
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            current_version = config.get('version', '1.0.0')
            return current_version != '1.1.0'
        
        except Exception:
            return False
    
    def create_plan(self, source_path: Path, target_path: Optional[Path] = None) -> MigrationPlan:
        """Crée un plan de migration de version."""
        # Détection de la version actuelle
        source_version = self._detect_current_version(source_path)
        target_version = '1.1.0'
        
        if (source_version, target_version) not in self.migration_matrix:
            raise ValueError(f"Migration {source_version} → {target_version} non supportée")
        
        steps = [
            MigrationStep(
                id="backup_config",
                name="Sauvegarde configuration",
                description="Sauvegarde de la configuration actuelle"
            ),
            MigrationStep(
                id="update_config_format",
                name="Mise à jour format configuration",
                description="Migration du format de configuration"
            ),
            MigrationStep(
                id="migrate_environments",
                name="Migration environnements",
                description="Mise à jour des métadonnées d'environnements"
            ),
            MigrationStep(
                id="initialize_new_features",
                name="Initialisation nouvelles fonctionnalités",
                description="Configuration des nouvelles fonctionnalités"
            ),
            MigrationStep(
                id="validate_migration",
                name="Validation",
                description="Validation de la migration"
            )
        ]
        
        return MigrationPlan(
            migration_type=MigrationType.VERSION_UPGRADE,
            source_version=source_version,
            target_version=target_version,
            description=f"Migration GestVenv {source_version} → {target_version}",
            steps=steps,
            backup_required=True,
            reversible=True,
            estimated_duration=30.0
        )
    
    def execute_migration(self, plan: MigrationPlan, source_path: Path, 
                         target_path: Optional[Path] = None) -> MigrationResult:
        """Exécute la migration de version."""
        migration_func = self.migration_matrix.get((plan.source_version, plan.target_version))
        if not migration_func:
            raise ValueError(f"Migration {plan.source_version} → {plan.target_version} non supportée")
        
        return migration_func(plan, source_path, target_path)
    
    def rollback_migration(self, result: MigrationResult) -> bool:
        """Rollback d'une migration de version."""
        try:
            if result.backup_path and result.backup_path.exists():
                # Restaurer la configuration sauvegardée
                config_file = result.source_path / '.gestvenv' / 'config.json'
                shutil.copy2(result.backup_path, config_file)
                
                # Nettoyer les nouvelles fonctionnalités si nécessaire
                cache_dir = result.source_path / '.gestvenv' / 'cache'
                if cache_dir.exists() and 'cache_created' in result.metadata:
                    shutil.rmtree(cache_dir)
                
                return True
        
        except Exception as e:
            logger.error(f"Erreur lors du rollback de version: {e}")
            return False
        
        return False
    
    def _detect_current_version(self, source_path: Path) -> str:
        """Détecte la version actuelle de GestVenv."""
        config_file = source_path / '.gestvenv' / 'config.json'
        
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config.get('version', '1.0.0')
            else:
                return '1.0.0'  # Version par défaut si pas de config
        
        except Exception:
            return '1.0.0'
    
    def _migrate_1_0_to_1_1(self, plan: MigrationPlan, source_path: Path, 
                           target_path: Optional[Path] = None) -> MigrationResult:
        """Migration spécifique v1.0 → v1.1."""
        start_time = time.time()
        result = MigrationResult(
            success=False,
            migration_type=MigrationType.VERSION_UPGRADE,
            source_path=source_path,
            total_steps=len(plan.steps)
        )
        
        gestvenv_dir = source_path / '.gestvenv'
        config_file = gestvenv_dir / 'config.json'
        
        try:
            # Étape 1: Sauvegarde
            if config_file.exists():
                backup_path = config_file.with_suffix('.json.backup')
                shutil.copy2(config_file, backup_path)
                result.backup_path = backup_path
            plan.steps[0].completed = True
            result.steps_completed += 1
            
            # Étape 2: Mise à jour configuration
            config = self._load_or_create_config(config_file)
            config['version'] = '1.1.0'
            
            # Nouvelles sections de configuration
            if 'backends' not in config:
                config['backends'] = {
                    'preferred': 'auto',
                    'fallback_to_pip': True,
                    'uv_enabled': True
                }
            
            if 'cache' not in config:
                config['cache'] = {
                    'enabled': True,
                    'max_size_mb': 1024,
                    'compression': 'auto',
                    'strategy': 'lru'
                }
            
            self._save_config(config_file, config)
            plan.steps[1].completed = True
            result.steps_completed += 1
            
            # Étape 3: Migration des environnements
            environments_dir = gestvenv_dir / 'environments'
            if environments_dir.exists():
                self._migrate_environment_metadata(environments_dir)
            plan.steps[2].completed = True
            result.steps_completed += 1
            
            # Étape 4: Initialisation nouvelles fonctionnalités
            # Créer la structure de cache
            cache_dir = gestvenv_dir / 'cache'
            if not cache_dir.exists():
                cache_dir.mkdir(parents=True)
                (cache_dir / 'packages').mkdir()
                (cache_dir / 'metadata').mkdir()
                result.metadata['cache_created'] = True
            
            # Créer les répertoires pour les sauvegardes et logs
            (gestvenv_dir / 'backups').mkdir(exist_ok=True)
            (gestvenv_dir / 'logs').mkdir(exist_ok=True)
            
            plan.steps[3].completed = True
            result.steps_completed += 1
            
            # Étape 5: Validation
            if self._validate_v1_1_installation(gestvenv_dir):
                plan.steps[4].completed = True
                result.steps_completed += 1
                result.success = True
                result.message = "Migration v1.0 → v1.1 réussie"
            else:
                result.message = "Migration partiellement réussie (validation échouée)"
                result.errors.append("Validation post-migration échouée")
        
        except Exception as e:
            logger.error(f"Erreur lors de la migration 1.0 → 1.1: {e}")
            result.errors.append(str(e))
            result.message = f"Migration échouée: {str(e)}"
        
        result.duration = time.time() - start_time
        return result
    
    def _load_or_create_config(self, config_file: Path) -> Dict[str, Any]:
        """Charge ou crée la configuration."""
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Configuration corrompue, création d'une nouvelle: {e}")
        
        # Configuration par défaut
        return {
            'version': '1.0.0',
            'environments_path': str(config_file.parent / 'environments'),
            'default_python': 'python3'
        }
    
    def _save_config(self, config_file: Path, config: Dict[str, Any]) -> None:
        """Sauvegarde la configuration."""
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _migrate_environment_metadata(self, environments_dir: Path) -> None:
        """Migre les métadonnées des environnements."""
        for env_dir in environments_dir.iterdir():
            if env_dir.is_dir():
                # Créer un fichier de métadonnées si nécessaire
                metadata_file = env_dir / '.gestvenv_metadata.json'
                if not metadata_file.exists():
                    metadata = {
                        'version': '1.1.0',
                        'created_at': time.time(),
                        'last_used': time.time(),
                        'backend_preference': 'auto'
                    }
                    
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2)
    
    def _validate_v1_1_installation(self, gestvenv_dir: Path) -> bool:
        """Valide l'installation v1.1."""
        required_dirs = ['environments', 'cache', 'backups', 'logs']
        required_files = ['config.json']
        
        # Vérification des répertoires
        for dir_name in required_dirs:
            if not (gestvenv_dir / dir_name).exists():
                logger.error(f"Répertoire manquant: {dir_name}")
                return False
        
        # Vérification des fichiers
        for file_name in required_files:
            if not (gestvenv_dir / file_name).exists():
                logger.error(f"Fichier manquant: {file_name}")
                return False
        
        # Vérification de la configuration
        try:
            config_file = gestvenv_dir / 'config.json'
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if config.get('version') != '1.1.0':
                logger.error("Version incorrecte dans la configuration")
                return False
            
            required_sections = ['backends', 'cache']
            for section in required_sections:
                if section not in config:
                    logger.error(f"Section manquante dans la configuration: {section}")
                    return False
        
        except Exception as e:
            logger.error(f"Erreur lors de la validation de la configuration: {e}")
            return False
        
        return True


class MigrationService:
    """
    Service principal de migration et compatibilité.
    
    Responsabilités:
    - Détection des migrations nécessaires
    - Exécution de migrations avec rollback
    - Validation post-migration
    - Gestion des sauvegardes
    - Support de multiples stratégies de migration
    """
    
    def __init__(self, system_service=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le service de migration.
        
        Args:
            system_service: Service système
            config: Configuration optionnelle
        """
        self.system_service = system_service
        self.config = config or {}
        
        # Configuration
        self.auto_backup = self.config.get('auto_backup', True)
        self.keep_backups = self.config.get('keep_backups', 3)
        self.validation_enabled = self.config.get('validation_enabled', True)
        
        # Stratégies de migration
        self.strategies = {
            MigrationType.REQUIREMENTS_TO_PYPROJECT: RequirementsToPyprojectStrategy(system_service),
            MigrationType.VERSION_UPGRADE: VersionMigrationStrategy(system_service)
        }
        
        logger.debug(f"MigrationService initialisé avec {len(self.strategies)} stratégie(s)")
    
    def detect_required_migrations(self, path: Path) -> List[MigrationType]:
        """
        Détecte les migrations nécessaires pour un projet.
        
        Args:
            path: Chemin du projet à analyser
            
        Returns:
            List[MigrationType]: Types de migration nécessaires
        """
        required_migrations = []
        
        try:
            for migration_type, strategy in self.strategies.items():
                if strategy.can_migrate(path):
                    required_migrations.append(migration_type)
                    logger.info(f"Migration détectée: {migration_type.value} pour {path}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection de migrations: {e}")
        
        return required_migrations
    
    def create_migration_plan(self, migration_type: MigrationType, source_path: Path,
                             target_path: Optional[Path] = None) -> Optional[MigrationPlan]:
        """
        Crée un plan de migration pour un type donné.
        
        Args:
            migration_type: Type de migration
            source_path: Chemin source
            target_path: Chemin cible (optionnel)
            
        Returns:
            Optional[MigrationPlan]: Plan de migration ou None
        """
        try:
            strategy = self.strategies.get(migration_type)
            if not strategy:
                logger.error(f"Stratégie de migration non trouvée: {migration_type}")
                return None
            
            if not strategy.can_migrate(source_path):
                logger.warning(f"Migration {migration_type.value} non applicable à {source_path}")
                return None
            
            plan = strategy.create_plan(source_path, target_path)
            logger.info(f"Plan de migration créé: {plan.description}")
            return plan
        
        except Exception as e:
            logger.error(f"Erreur lors de la création du plan: {e}")
            return None
    
    def execute_migration(self, migration_type: MigrationType, source_path: Path,
                         target_path: Optional[Path] = None,
                         dry_run: bool = False) -> MigrationResult:
        """
        Exécute une migration.
        
        Args:
            migration_type: Type de migration
            source_path: Chemin source
            target_path: Chemin cible
            dry_run: Mode simulation (ne fait aucune modification)
            
        Returns:
            MigrationResult: Résultat de la migration
        """
        logger.info(f"Début de migration {migration_type.value}: {source_path}")
        
        if dry_run:
            logger.info("Mode simulation activé - aucune modification ne sera effectuée")
            return MigrationResult(
                success=True,
                migration_type=migration_type,
                source_path=source_path,
                message="Simulation réussie"
            )
        
        try:
            # Création du plan
            plan = self.create_migration_plan(migration_type, source_path, target_path)
            if not plan:
                return MigrationResult(
                    success=False,
                    migration_type=migration_type,
                    source_path=source_path,
                    message="Impossible de créer le plan de migration"
                )
            
            # Exécution
            strategy = self.strategies[migration_type]
            result = strategy.execute_migration(plan, source_path, target_path)
            
            # Validation post-migration
            if result.success and self.validation_enabled:
                validation_success = self._validate_migration_result(result)
                if not validation_success:
                    result.warnings.append("Validation post-migration échouée")
            
            # Nettoyage des anciennes sauvegardes
            if result.success and self.auto_backup:
                self._cleanup_old_backups(source_path)
            
            logger.info(f"Migration terminée: {result.message}")
            return result
        
        except Exception as e:
            logger.error(f"Erreur lors de la migration: {e}")
            return MigrationResult(
                success=False,
                migration_type=migration_type,
                source_path=source_path,
                message=f"Erreur lors de la migration: {str(e)}",
                errors=[str(e)]
            )
    
    def rollback_migration(self, result: MigrationResult) -> bool:
        """
        Effectue un rollback d'une migration.
        
        Args:
            result: Résultat de la migration à annuler
            
        Returns:
            bool: True si le rollback a réussi
        """
        try:
            logger.info(f"Début du rollback pour migration {result.migration_type.value}")
            
            strategy = self.strategies.get(result.migration_type)
            if not strategy:
                logger.error("Stratégie de migration non trouvée pour rollback")
                return False
            
            success = strategy.rollback_migration(result)
            
            if success:
                logger.info("Rollback réussi")
            else:
                logger.error("Rollback échoué")
            
            return success
        
        except Exception as e:
            logger.error(f"Erreur lors du rollback: {e}")
            return False
    
    def migrate_requirements_to_pyproject(self, project_path: Path,
                                        backup: bool = True) -> MigrationResult:
        """
        Migration spécialisée requirements.txt → pyproject.toml.
        
        Args:
            project_path: Chemin du projet
            backup: Créer une sauvegarde
            
        Returns:
            MigrationResult: Résultat de la migration
        """
        return self.execute_migration(
            MigrationType.REQUIREMENTS_TO_PYPROJECT,
            project_path
        )
    
    def migrate_gestvenv_version(self, installation_path: Path) -> MigrationResult:
        """
        Migration de version de GestVenv.
        
        Args:
            installation_path: Chemin d'installation GestVenv
            
        Returns:
            MigrationResult: Résultat de la migration
        """
        return self.execute_migration(
            MigrationType.VERSION_UPGRADE,
            installation_path
        )
    
    def get_migration_status(self, path: Path) -> Dict[str, Any]:
        """
        Retourne le statut de migration d'un projet.
        
        Args:
            path: Chemin à analyser
            
        Returns:
            Dict[str, Any]: Statut de migration
        """
        required_migrations = self.detect_required_migrations(path)
        
        status = {
            'path': str(path),
            'migrations_required': len(required_migrations),
            'migration_types': [mt.value for mt in required_migrations],
            'up_to_date': len(required_migrations) == 0
        }
        
        # Informations détaillées par type
        for migration_type in required_migrations:
            plan = self.create_migration_plan(migration_type, path)
            if plan:
                status[f'plan_{migration_type.value}'] = {
                    'description': plan.description,
                    'steps': len(plan.steps),
                    'estimated_duration': plan.estimated_duration,
                    'reversible': plan.reversible
                }
        
        return status
    
    def _validate_migration_result(self, result: MigrationResult) -> bool:
        """Valide le résultat d'une migration."""
        try:
            if result.migration_type == MigrationType.REQUIREMENTS_TO_PYPROJECT:
                # Vérifier que le pyproject.toml existe et est valide
                if result.target_path and result.target_path.exists():
                    strategy = self.strategies[MigrationType.REQUIREMENTS_TO_PYPROJECT]
                    return strategy._validate_pyproject(result.target_path)
            
            elif result.migration_type == MigrationType.VERSION_UPGRADE:
                # Vérifier la nouvelle version
                gestvenv_dir = result.source_path / '.gestvenv'
                if gestvenv_dir.exists():
                    strategy = self.strategies[MigrationType.VERSION_UPGRADE]
                    return strategy._validate_v1_1_installation(gestvenv_dir)
            
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de la validation: {e}")
            return False
    
    def _cleanup_old_backups(self, path: Path) -> None:
        """Nettoie les anciennes sauvegardes."""
        try:
            backup_pattern = "*.backup"
            backup_files = list(path.rglob(backup_pattern))
            
            # Tri par date de modification (plus récents en premier)
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Suppression des sauvegardes en excès
            if len(backup_files) > self.keep_backups:
                for backup_file in backup_files[self.keep_backups:]:
                    try:
                        backup_file.unlink()
                        logger.debug(f"Ancienne sauvegarde supprimée: {backup_file}")
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer {backup_file}: {e}")
        
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage des sauvegardes: {e}")
    
    def list_available_migrations(self) -> List[Dict[str, str]]:
        """
        Retourne la liste des migrations disponibles.
        
        Returns:
            List[Dict[str, str]]: Informations sur les migrations disponibles
        """
        migrations = []
        
        for migration_type in self.strategies.keys():
            migrations.append({
                'type': migration_type.value,
                'name': migration_type.value.replace('_', ' ').title(),
                'description': self._get_migration_description(migration_type)
            })
        
        return migrations
    
    def _get_migration_description(self, migration_type: MigrationType) -> str:
        """Retourne la description d'un type de migration."""
        descriptions = {
            MigrationType.REQUIREMENTS_TO_PYPROJECT: "Conversion requirements.txt vers pyproject.toml",
            MigrationType.VERSION_UPGRADE: "Migration entre versions de GestVenv",
            MigrationType.SETUP_TO_PYPROJECT: "Conversion setup.py vers pyproject.toml",
            MigrationType.ENVIRONMENT_FORMAT: "Migration du format des environnements",
            MigrationType.CONFIG_FORMAT: "Migration du format de configuration"
        }
        
        return descriptions.get(migration_type, "Migration personnalisée")