"""
Outils de migration et conversion v1.0 → v1.1.
Migration automatique des configurations et projets.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import shutil
import json
import logging
from .pyproject_parser import PyProjectParser, PyProjectConfig, ProjectMetadata, ProjectDependencies, BuildSystem
from .toml_utils import TomlUtils
from .validation_utils import ValidationUtils
from .path_utils import PathUtils

logger = logging.getLogger(__name__)

@dataclass
class MigrationSuggestion:
    """Suggestion d'amélioration lors de migration."""
    category: str  # "performance", "modernization", "compatibility"
    description: str
    command: str
    priority: str = "medium"  # "low", "medium", "high"

@dataclass
class MigrationAnalysis:
    """Résultat d'analyse de migration."""
    project_path: Path
    suggestions: List[MigrationSuggestion] = field(default_factory=list)
    compatibility_issues: List[str] = field(default_factory=list)
    performance_gains: Dict[str, str] = field(default_factory=dict)
    migration_feasible: bool = True
    
    def add_suggestion(self, category: str, description: str, command: str, priority: str = "medium") -> None:
        """Ajoute une suggestion de migration."""
        self.suggestions.append(MigrationSuggestion(category, description, command, priority))

class RequirementsConverter:
    """Convertisseur requirements.txt vers pyproject.toml."""
    
    @staticmethod
    def parse_requirements_file(file_path: Path) -> List[str]:
        """
        Parse un fichier requirements.txt.
        
        Args:
            file_path: Chemin vers le fichier requirements.txt
            
        Returns:
            Liste des requirements parsés
        """
        requirements = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # Nettoyer la ligne
                    line = line.strip()
                    
                    # Ignorer les lignes vides et les commentaires
                    if not line or line.startswith('#'):
                        continue
                    
                    # Ignorer les options pip (-r, -f, etc.)
                    if line.startswith('-'):
                        logger.warning(f"Option pip ignorée ligne {line_num}: {line}")
                        continue
                    
                    # Ignorer les URLs Git (pour l'instant)
                    if line.startswith(('git+', 'hg+', 'svn+', 'bzr+')):
                        logger.warning(f"URL VCS ignorée ligne {line_num}: {line}")
                        continue
                    
                    # Valider le requirement
                    req_valid, req_error, _ = ValidationUtils.validate_requirement(line)
                    if req_valid:
                        requirements.append(line)
                    else:
                        logger.warning(f"Requirement invalide ligne {line_num}: {req_error}")
            
            logger.debug(f"Requirements parsés: {len(requirements)} depuis {file_path}")
            return requirements
            
        except Exception as e:
            logger.error(f"Erreur lecture {file_path}: {e}")
            return []
    
    @staticmethod
    def detect_optional_requirements(project_dir: Path) -> Dict[str, List[str]]:
        """
        Détecte les fichiers requirements auxiliaires.
        
        Args:
            project_dir: Répertoire du projet
            
        Returns:
            Dictionnaire des groupes de dépendances optionnelles
        """
        optional_deps = {}
        
        patterns = {
            "dev": ["dev-requirements.txt", "requirements-dev.txt", "requirements_dev.txt"],
            "test": ["test-requirements.txt", "requirements-test.txt", "requirements_test.txt"],
            "docs": ["docs-requirements.txt", "requirements-docs.txt", "requirements_docs.txt"],
            "lint": ["lint-requirements.txt", "requirements-lint.txt"],
            "build": ["build-requirements.txt", "requirements-build.txt"]
        }
        
        for group, filenames in patterns.items():
            for filename in filenames:
                req_file = project_dir / filename
                if req_file.exists():
                    requirements = RequirementsConverter.parse_requirements_file(req_file)
                    if requirements:
                        optional_deps[group] = requirements
                    break
        
        return optional_deps
    
    @staticmethod
    def convert_to_pyproject(requirements_path: Path, project_name: str,
                           project_version: str = "0.1.0",
                           python_version: str = ">=3.9",
                           author_name: Optional[str] = None,
                           author_email: Optional[str] = None,
                           description: str = "") -> PyProjectConfig:
        """
        Convertit un fichier requirements.txt en configuration pyproject.toml.
        
        Args:
            requirements_path: Chemin vers requirements.txt
            project_name: Nom du projet
            project_version: Version du projet
            python_version: Version Python requise
            author_name: Nom de l'auteur
            author_email: Email de l'auteur
            description: Description du projet
            
        Returns:
            Configuration PyProject générée
        """
        # Parser les requirements principaux
        main_requirements = RequirementsConverter.parse_requirements_file(requirements_path)
        
        # Détecter les requirements optionnels
        project_dir = requirements_path.parent
        optional_requirements = RequirementsConverter.detect_optional_requirements(project_dir)
        
        # Créer les métadonnées
        metadata = ProjectMetadata(
            name=project_name,
            version=project_version,
            description=description or f"Project converted from {requirements_path.name}",
            requires_python=python_version
        )
        
        # Ajouter l'auteur si fourni
        if author_name or author_email:
            author_info = {}
            if author_name:
                author_info['name'] = author_name
            if author_email:
                author_info['email'] = author_email
            metadata.authors = [author_info]
        
        # Créer les dépendances
        dependencies = ProjectDependencies(
            dependencies=main_requirements,
            optional_dependencies=optional_requirements
        )
        
        # Système de build par défaut
        build_system = BuildSystem(
            requires=["setuptools>=61.0", "wheel"],
            build_backend="setuptools.build_meta"
        )
        
        # Configuration des outils avec métadonnées de migration
        tool_config = {
            "gestvenv": {
                "migrated_from": str(requirements_path),
                "migration_date": datetime.now().isoformat(),
                "original_format": "requirements.txt",
                "migration_version": "1.1.0"
            }
        }
        
        return PyProjectConfig(
            metadata=metadata,
            dependencies=dependencies,
            build_system=build_system,
            tool_config=tool_config
        )

class ConfigMigrator:
    """Migrateur de configuration GestVenv v1.0 → v1.1."""
    
    @staticmethod
    def migrate_config_v1_0_to_v1_1(config_path: Path) -> bool:
        """
        Migre la configuration v1.0 vers v1.1.
        
        Args:
            config_path: Chemin vers le fichier de configuration
            
        Returns:
            True si migration réussie, False sinon
        """
        try:
            # Charger la configuration actuelle
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Créer une sauvegarde
            backup_path = config_path.with_suffix('.json.v1.0.backup')
            shutil.copy2(config_path, backup_path)
            logger.info(f"Sauvegarde créée: {backup_path}")
            
            # Ajouter les nouveaux champs v1.1
            if "settings" not in config_data:
                config_data["settings"] = {}
            
            # Nouveaux paramètres par défaut
            new_settings = {
                "preferred_backend": "auto",  # auto, pip, uv
                "pyproject_support": True,
                "show_migration_hints": True,
                "auto_detect_project_type": True,
                "enable_cache": True,
                "parallel_installs": True
            }
            
            for key, value in new_settings.items():
                if key not in config_data["settings"]:
                    config_data["settings"][key] = value
            
            # Migrer les environnements existants
            for env_name, env_data in config_data.get("environments", {}).items():
                # Ajouter les nouveaux champs aux environnements
                if "backend_type" not in env_data:
                    env_data["backend_type"] = "pip"  # Préserver comportement actuel
                
                if "source_file_type" not in env_data:
                    env_data["source_file_type"] = "requirements"
                
                if "pyproject_info" not in env_data:
                    env_data["pyproject_info"] = None
                
                if "dependency_groups" not in env_data:
                    env_data["dependency_groups"] = {}
                
                if "lock_file_path" not in env_data:
                    env_data["lock_file_path"] = None
            
            # Ajouter les métadonnées de migration
            config_data["_migration"] = {
                "from_version": "1.0.0",
                "to_version": "1.1.0",
                "migration_date": datetime.now().isoformat(),
                "backup_created": str(backup_path),
                "migrated_environments": len(config_data.get("environments", {}))
            }
            
            # Sauvegarder la configuration migrée
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration migrée vers v1.1: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur migration config: {e}")
            return False

class MigrationService:
    """Service principal de migration."""
    
    def __init__(self) -> None:
        self.converter = RequirementsConverter()
        self.config_migrator = ConfigMigrator()
    
    def analyze_project(self, project_path: Path) -> MigrationAnalysis:
        """
        Analyse un projet et suggère des améliorations.
        
        Args:
            project_path: Chemin du projet à analyser
            
        Returns:
            Analyse de migration avec suggestions
        """
        analysis = MigrationAnalysis(project_path=project_path)
        
        # Détecter les fichiers existants
        has_requirements = (project_path / "requirements.txt").exists()
        has_pyproject = (project_path / "pyproject.toml").exists()
        has_setup_py = (project_path / "setup.py").exists()
        has_setup_cfg = (project_path / "setup.cfg").exists()
        
        # Vérifier la disponibilité d'uv
        from ..utils.system_utils import SystemUtils
        uv_available = SystemUtils.check_command_available('uv').available
        
        # Suggestions de modernisation
        if has_requirements and not has_pyproject:
            analysis.add_suggestion(
                "modernization",
                "Migrer requirements.txt vers pyproject.toml (standard moderne)",
                f"gestvenv convert-to-pyproject {project_path / 'requirements.txt'}",
                "high"
            )
            analysis.performance_gains["migration"] = "Standards Python modernes (PEP 621)"
        
        if has_setup_py and not has_pyproject:
            analysis.add_suggestion(
                "modernization",
                "Migrer setup.py vers pyproject.toml pour compatibilité future",
                "gestvenv modernize-project .",
                "medium"
            )
        
        if has_setup_cfg and not has_pyproject:
            analysis.add_suggestion(
                "modernization",
                "Migrer setup.cfg vers pyproject.toml",
                "gestvenv modernize-project .",
                "medium"
            )
        
        # Suggestions de performance
        if not uv_available:
            analysis.add_suggestion(
                "performance",
                "Installer uv pour performances 10-100x supérieures",
                "pip install uv",
                "high"
            )
            analysis.performance_gains["uv"] = "Installation packages 10-100x plus rapide"
        
        # Vérifier les problèmes de compatibilité
        if has_pyproject:
            try:
                PyProjectParser.parse_file(project_path / "pyproject.toml")
            except Exception as e:
                analysis.compatibility_issues.append(f"pyproject.toml invalide: {e}")
                analysis.migration_feasible = False
        
        # Analyser la structure du projet
        python_files = list(PathUtils.find_files(project_path, "*.py"))
        if len(python_files) > 50:
            analysis.add_suggestion(
                "performance",
                "Projet volumineux détecté, optimiser avec cache et installations parallèles",
                "gestvenv config set enable_cache=true parallel_installs=true",
                "medium"
            )
        
        return analysis
    
    def migrate_project_to_pyproject(self, project_path: Path, project_name: str,
                                   backup: bool = True) -> Tuple[bool, str]:
        """
        Migre un projet complet vers pyproject.toml.
        
        Args:
            project_path: Chemin du projet
            project_name: Nom du projet
            backup: Créer une sauvegarde des fichiers existants
            
        Returns:
            (succès, message)
        """
        try:
            requirements_file = project_path / "requirements.txt"
            pyproject_file = project_path / "pyproject.toml"
            
            # Vérifier les pré-requis
            if not requirements_file.exists():
                return False, "Fichier requirements.txt introuvable"
            
            if pyproject_file.exists():
                return False, "pyproject.toml existe déjà"
            
            # Créer une sauvegarde si demandée
            if backup:
                backup_dir: Path = project_path / ".gestvenv_backup"
                backup_dir.mkdir(exist_ok=True)
                
                for file_to_backup in [requirements_file]:
                    if file_to_backup.exists():
                        backup_file = backup_dir / f"{file_to_backup.name}.backup"
                        shutil.copy2(file_to_backup, backup_file)
                        logger.debug(f"Sauvegarde créée: {backup_file}")
            
            # Convertir vers pyproject.toml
            config = self.converter.convert_to_pyproject(
                requirements_file, project_name
            )
            
            # Sauvegarder le nouveau pyproject.toml
            PyProjectParser.save_config(config, pyproject_file)
            
            message = f"Migration réussie: {pyproject_file} créé"
            if backup:
                message += f" (sauvegarde dans {backup_dir})"
            
            logger.info(message)
            return True, message
            
        except Exception as e:
            logger.error(f"Erreur migration projet: {e}")
            return False, f"Erreur migration: {e}"
    
    def suggest_optimizations(self, project_path: Path) -> List[MigrationSuggestion]:
        """
        Suggère des optimisations pour un projet.
        
        Args:
            project_path: Chemin du projet
            
        Returns:
            Liste de suggestions d'optimisation
        """
        suggestions = []
        
        # Analyser la structure du projet
        analysis = self.analyze_project(project_path)
        suggestions.extend(analysis.suggestions)
        
        # Suggestions spécifiques selon le contenu
        if (project_path / "tests").exists():
            suggestions.append(MigrationSuggestion(
                "quality",
                "Ajouter un groupe de dépendances 'test' dans pyproject.toml",
                "gestvenv add-group test pytest pytest-cov",
                "medium"
            ))
        
        if (project_path / "docs").exists():
            suggestions.append(MigrationSuggestion(
                "quality",
                "Ajouter un groupe de dépendances 'docs' dans pyproject.toml",
                "gestvenv add-group docs sphinx sphinx-rtd-theme",
                "low"
            ))
        
        # Détecter les frameworks web
        web_files = list(PathUtils.find_files(project_path, "*app.py")) + \
                   list(PathUtils.find_files(project_path, "*main.py"))
        
        for file_path in web_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'fastapi' in content.lower() or 'flask' in content.lower():
                        suggestions.append(MigrationSuggestion(
                            "performance",
                            "Application web détectée, considérer uv pour installations rapides",
                            "gestvenv config set preferred_backend=uv",
                            "high"
                        ))
                        break
            except Exception:
                continue
        
        return suggestions
