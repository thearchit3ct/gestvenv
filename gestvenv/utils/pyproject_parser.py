"""
Parser pyproject.toml conforme PEP 621, 517, 518.
Extraction et validation des métadonnées de projet Python.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import logging
from .toml_utils import TomlUtils
from .validation_utils import ValidationUtils

logger = logging.getLogger(__name__)

@dataclass
class ProjectMetadata:
    """Métadonnées de projet selon PEP 621."""
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    readme: Optional[Union[str, Dict[str, str]]] = None
    requires_python: Optional[str] = None
    license: Optional[Union[str, Dict[str, str]]] = None
    authors: List[Dict[str, str]] = field(default_factory=list)
    maintainers: List[Dict[str, str]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    classifiers: List[str] = field(default_factory=list)
    urls: Dict[str, str] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)
    gui_scripts: Dict[str, str] = field(default_factory=dict)
    entry_points: Dict[str, Dict[str, str]] = field(default_factory=dict)
    dynamic: List[str] = field(default_factory=list)

@dataclass
class BuildSystem:
    """Système de build selon PEP 517/518."""
    requires: List[str] = field(default_factory=list)
    build_backend: Optional[str] = None
    backend_path: List[str] = field(default_factory=list)

@dataclass
class ProjectDependencies:
    """Dépendances de projet."""
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class PyProjectConfig:
    """Configuration complète d'un pyproject.toml."""
    metadata: ProjectMetadata
    dependencies: ProjectDependencies
    build_system: Optional[BuildSystem] = None
    tool_config: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

class PyProjectError(Exception):
    """Exception pour les erreurs de parsing pyproject.toml."""
    pass

class PyProjectParser:
    """Parser pour fichiers pyproject.toml."""
    
    # Schéma de validation PEP 621
    PEP621_SCHEMA = {
        'project': {
            'name': str,
            'version': str,  # Optionnel mais recommandé
            'description': str,
            'readme': (str, dict),
            'requires-python': str,
            'license': (str, dict),
            'authors': [dict],
            'maintainers': [dict],
            'keywords': [str],
            'classifiers': [str],
            'urls': dict,
            'scripts': dict,
            'gui-scripts': dict,
            'entry-points': dict,
            'dependencies': [str],
            'optional-dependencies': dict,
            'dynamic': [str]
        },
        'build-system': {
            'requires': [str],
            'build-backend': str,
            'backend-path': [str]
        }
    }
    
    @staticmethod
    def parse_file(file_path: Union[str, Path]) -> PyProjectConfig:
        """
        Parse un fichier pyproject.toml.
        
        Args:
            file_path: Chemin vers le fichier pyproject.toml
            
        Returns:
            Configuration parsée
            
        Raises:
            PyProjectError: Si erreur de parsing ou validation
        """
        try:
            # Charger le fichier TOML
            raw_data = TomlUtils.load_toml(file_path)
            
            # Valider la structure de base
            errors = PyProjectParser._validate_structure(raw_data)
            if errors:
                raise PyProjectError(f"Structure invalide: {'; '.join(errors)}")
            
            # Parser les métadonnées
            metadata = PyProjectParser._parse_metadata(raw_data.get('project', {}))
            
            # Parser les dépendances
            dependencies = PyProjectParser._parse_dependencies(raw_data.get('project', {}))
            
            # Parser le système de build
            build_system = PyProjectParser._parse_build_system(raw_data.get('build-system'))
            
            # Extraire la configuration des outils
            tool_config = raw_data.get('tool', {})
            
            config = PyProjectConfig(
                metadata=metadata,
                dependencies=dependencies,
                build_system=build_system,
                tool_config=tool_config,
                raw_data=raw_data
            )
            
            logger.debug(f"pyproject.toml parsé: {file_path}")
            return config
            
        except Exception as e:
            raise PyProjectError(f"Erreur parsing {file_path}: {e}")
    
    @staticmethod
    def _validate_structure(data: Dict[str, Any]) -> List[str]:
        """
        Valide la structure du pyproject.toml.
        
        Args:
            data: Données TOML à valider
            
        Returns:
            Liste des erreurs de validation
        """
        errors = []
        
        # Vérifier la présence de la section project
        if 'project' not in data:
            errors.append("Section 'project' manquante")
            return errors
        
        project_data = data['project']
        
        # Vérifier le nom du projet (obligatoire)
        if 'name' not in project_data:
            errors.append("'project.name' est obligatoire")
        else:
            name_valid, name_error = ValidationUtils.validate_package_name(project_data['name'])
            if not name_valid:
                errors.append(f"project.name invalide: {name_error}")
        
        # Valider la version si présente
        if 'version' in project_data:
            version_valid, version_error = ValidationUtils.validate_version(project_data['version'])
            if not version_valid:
                errors.append(f"project.version invalide: {version_error}")
        
        # Valider requires-python si présent
        if 'requires-python' in project_data:
            python_valid, python_error = ValidationUtils.validate_python_version(project_data['requires-python'])
            if not python_valid:
                errors.append(f"project.requires-python invalide: {python_error}")
        
        # Valider les dépendances si présentes
        if 'dependencies' in project_data:
            deps = project_data['dependencies']
            if isinstance(deps, list):
                for i, dep in enumerate(deps):
                    if isinstance(dep, str):
                        dep_valid, dep_error, _ = ValidationUtils.validate_requirement(dep)
                        if not dep_valid:
                            errors.append(f"project.dependencies[{i}] invalide: {dep_error}")
                    else:
                        errors.append(f"project.dependencies[{i}] doit être une chaîne")
            else:
                errors.append("project.dependencies doit être une liste")
        
        # Valider les dépendances optionnelles
        if 'optional-dependencies' in project_data:
            opt_deps = project_data['optional-dependencies']
            if isinstance(opt_deps, dict):
                for group_name, group_deps in opt_deps.items():
                    if isinstance(group_deps, list):
                        for i, dep in enumerate(group_deps):
                            if isinstance(dep, str):
                                dep_valid, dep_error, _ = ValidationUtils.validate_requirement(dep)
                                if not dep_valid:
                                    errors.append(f"project.optional-dependencies.{group_name}[{i}] invalide: {dep_error}")
                            else:
                                errors.append(f"project.optional-dependencies.{group_name}[{i}] doit être une chaîne")
                    else:
                        errors.append(f"project.optional-dependencies.{group_name} doit être une liste")
            else:
                errors.append("project.optional-dependencies doit être un dictionnaire")
        
        return errors
    
    @staticmethod
    def _parse_metadata(project_data: Dict[str, Any]) -> ProjectMetadata:
        """
        Parse les métadonnées de projet.
        
        Args:
            project_data: Section 'project' du pyproject.toml
            
        Returns:
            Métadonnées parsées
        """
        return ProjectMetadata(
            name=project_data['name'],
            version=project_data.get('version'),
            description=project_data.get('description'),
            readme=project_data.get('readme'),
            requires_python=project_data.get('requires-python'),
            license=project_data.get('license'),
            authors=project_data.get('authors', []),
            maintainers=project_data.get('maintainers', []),
            keywords=project_data.get('keywords', []),
            classifiers=project_data.get('classifiers', []),
            urls=project_data.get('urls', {}),
            scripts=project_data.get('scripts', {}),
            gui_scripts=project_data.get('gui-scripts', {}),
            entry_points=project_data.get('entry-points', {}),
            dynamic=project_data.get('dynamic', [])
        )
    
    @staticmethod
    def _parse_dependencies(project_data: Dict[str, Any]) -> ProjectDependencies:
        """
        Parse les dépendances de projet.
        
        Args:
            project_data: Section 'project' du pyproject.toml
            
        Returns:
            Dépendances parsées
        """
        return ProjectDependencies(
            dependencies=project_data.get('dependencies', []),
            optional_dependencies=project_data.get('optional-dependencies', {})
        )
    
    @staticmethod
    def _parse_build_system(build_data: Optional[Dict[str, Any]]) -> Optional[BuildSystem]:
        """
        Parse le système de build.
        
        Args:
            build_data: Section 'build-system' du pyproject.toml
            
        Returns:
            Système de build parsé ou None
        """
        if not build_data:
            return None
        
        return BuildSystem(
            requires=build_data.get('requires', []),
            build_backend=build_data.get('build-backend'),
            backend_path=build_data.get('backend-path', [])
        )
    
    @staticmethod
    def create_template(project_name: str, project_version: str = "0.1.0",
                       description: str = "", python_version: str = ">=3.9",
                       dependencies: Optional[List[str]] = None,
                       template_type: str = "basic") -> PyProjectConfig:
        """
        Crée un template de pyproject.toml.
        
        Args:
            project_name: Nom du projet
            project_version: Version du projet
            description: Description du projet
            python_version: Version Python requise
            dependencies: Dépendances du projet
            template_type: Type de template (basic, web, cli, data_science)
            
        Returns:
            Configuration template
        """
        # Valider les entrées
        name_valid, name_error = ValidationUtils.validate_package_name(project_name)
        if not name_valid:
            raise PyProjectError(f"Nom de projet invalide: {name_error}")
        
        version_valid, version_error = ValidationUtils.validate_version(project_version)
        if not version_valid:
            raise PyProjectError(f"Version de projet invalide: {version_error}")
        
        # Métadonnées de base
        metadata = ProjectMetadata(
            name=project_name,
            version=project_version,
            description=description,
            requires_python=python_version
        )
        
        # Dépendances selon le type de template
        template_dependencies = {
            "basic": dependencies or [],
            "web": (dependencies or []) + ["fastapi", "uvicorn"],
            "cli": (dependencies or []) + ["click", "typer"],
            "data_science": (dependencies or []) + ["pandas", "numpy", "matplotlib", "jupyter"]
        }
        
        project_deps = ProjectDependencies(
            dependencies=template_dependencies.get(template_type, dependencies or [])
        )
        
        # Système de build par défaut
        build_system = BuildSystem(
            requires=["setuptools>=61.0", "wheel"],
            build_backend="setuptools.build_meta"
        )
        
        return PyProjectConfig(
            metadata=metadata,
            dependencies=project_deps,
            build_system=build_system
        )
    
    @staticmethod
    def to_toml_dict(config: PyProjectConfig) -> Dict[str, Any]:
        """
        Convertit une configuration en dictionnaire TOML.
        
        Args:
            config: Configuration à convertir
            
        Returns:
            Dictionnaire TOML
        """
        result = {}
        
        # Section project
        project_section = {
            'name': config.metadata.name,
        }
        
        # Ajouter les champs optionnels s'ils sont définis
        if config.metadata.version:
            project_section['version'] = config.metadata.version
        if config.metadata.description:
            project_section['description'] = config.metadata.description
        if config.metadata.readme:
            project_section['readme'] = config.metadata.readme
        if config.metadata.requires_python:
            project_section['requires-python'] = config.metadata.requires_python
        if config.metadata.license:
            project_section['license'] = config.metadata.license
        if config.metadata.authors:
            project_section['authors'] = config.metadata.authors
        if config.metadata.maintainers:
            project_section['maintainers'] = config.metadata.maintainers
        if config.metadata.keywords:
            project_section['keywords'] = config.metadata.keywords
        if config.metadata.classifiers:
            project_section['classifiers'] = config.metadata.classifiers
        if config.metadata.urls:
            project_section['urls'] = config.metadata.urls
        if config.metadata.scripts:
            project_section['scripts'] = config.metadata.scripts
        if config.metadata.gui_scripts:
            project_section['gui-scripts'] = config.metadata.gui_scripts
        if config.metadata.entry_points:
            project_section['entry-points'] = config.metadata.entry_points
        if config.metadata.dynamic:
            project_section['dynamic'] = config.metadata.dynamic
        
        # Dépendances
        if config.dependencies.dependencies:
            project_section['dependencies'] = config.dependencies.dependencies
        if config.dependencies.optional_dependencies:
            project_section['optional-dependencies'] = config.dependencies.optional_dependencies
        
        result['project'] = project_section
        
        # Section build-system
        if config.build_system:
            build_section = {}
            if config.build_system.requires:
                build_section['requires'] = config.build_system.requires
            if config.build_system.build_backend:
                build_section['build-backend'] = config.build_system.build_backend
            if config.build_system.backend_path:
                build_section['backend-path'] = config.build_system.backend_path
            
            if build_section:
                result['build-system'] = build_section
        
        # Section tool
        if config.tool_config:
            result['tool'] = config.tool_config
        
        return result
    
    @staticmethod
    def save_config(config: PyProjectConfig, file_path: Union[str, Path]) -> None:
        """
        Sauvegarde une configuration dans un fichier pyproject.toml.
        
        Args:
            config: Configuration à sauvegarder
            file_path: Chemin de destination
        """
        toml_dict = PyProjectParser.to_toml_dict(config)
        TomlUtils.save_toml(toml_dict, file_path)
        logger.debug(f"Configuration sauvegardée: {file_path}")
