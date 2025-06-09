"""
Parser pyproject.toml conforme PEP 621 pour GestVenv v1.1
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from .toml_handler import TomlHandler
from ..core.models import PyProjectInfo
from ..core.exceptions import PyProjectParsingError, ValidationError

import logging
logger = logging.getLogger(__name__)


class PyProjectParser:
    """Parser TOML pour pyproject.toml avec validation PEP 621"""
    
    @staticmethod
    def parse_pyproject_toml(path: Path) -> PyProjectInfo:
        """Parse un fichier pyproject.toml"""
        if not path.exists():
            raise PyProjectParsingError(
                f"Fichier pyproject.toml introuvable",
                file_path=str(path)
            )
        
        try:
            data = TomlHandler.load(path)
            return PyProjectParser._extract_project_info(data, path)
        except Exception as e:
            raise PyProjectParsingError(
                f"Erreur parsing pyproject.toml: {e}",
                file_path=str(path)
            )
    
    @staticmethod
    def validate_pep621(data: Dict[str, Any]) -> bool:
        """Valide la conformité PEP 621"""
        project_section = data.get('project', {})
        
        # Champs requis PEP 621
        required_fields = ['name']
        for field in required_fields:
            if field not in project_section:
                return False
        
        # Validation format nom
        name = project_section.get('name', '')
        if not PyProjectParser._validate_project_name(name):
            return False
        
        # Validation version si présente
        version = project_section.get('version')
        if version and not PyProjectParser._validate_version(version):
            return False
        
        # Validation requires-python si présent
        requires_python = project_section.get('requires-python')
        if requires_python and not PyProjectParser._validate_python_requirement(requires_python):
            return False
        
        return True
    
    @staticmethod
    def convert_requirements_to_pyproject(req_path: Path) -> Dict[str, Any]:
        """Convertit requirements.txt vers structure pyproject.toml"""
        if not req_path.exists():
            raise FileNotFoundError(f"requirements.txt introuvable: {req_path}")
        
        try:
            dependencies = []
            
            with open(req_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Ignorer commentaires et lignes vides
                    if not line or line.startswith('#'):
                        continue
                    
                    # Ignorer options pip
                    if line.startswith('-'):
                        continue
                    
                    # Validation et ajout dépendance
                    if PyProjectParser._validate_dependency_spec(line):
                        dependencies.append(line)
                    else:
                        logger.warning(f"Ligne {line_num} ignorée: {line}")
            
            project_name = req_path.parent.name or "my-project"
            
            return {
                "project": {
                    "name": project_name,
                    "version": "0.1.0",
                    "description": f"Converted from {req_path.name}",
                    "dependencies": dependencies
                },
                "build-system": {
                    "requires": ["setuptools>=45", "wheel"],
                    "build-backend": "setuptools.build_meta"
                }
            }
            
        except Exception as e:
            raise PyProjectParsingError(
                f"Erreur conversion requirements.txt: {e}",
                file_path=str(req_path)
            )
    
    # Méthodes privées
    
    @staticmethod
    def _extract_project_info(data: Dict[str, Any], source_path: Path) -> PyProjectInfo:
        """Extrait les informations projet depuis les données TOML"""
        project_section = data.get('project', {})
        
        if not project_section:
            raise PyProjectParsingError(
                "Section [project] manquante",
                file_path=str(source_path)
            )
        
        # Validation PEP 621
        if not PyProjectParser.validate_pep621(data):
            raise PyProjectParsingError(
                "Fichier non conforme PEP 621",
                file_path=str(source_path)
            )
        
        # Extraction données
        pyproject_info = PyProjectInfo(
            name=project_section['name'],
            version=project_section.get('version', '0.1.0'),
            description=project_section.get('description'),
            readme=project_section.get('readme'),
            requires_python=project_section.get('requires-python'),
            source_path=source_path
        )
        
        # Authors
        if 'authors' in project_section:
            pyproject_info.authors = project_section['authors']
        
        # Keywords
        if 'keywords' in project_section:
            pyproject_info.keywords = project_section['keywords']
        
        # Classifiers
        if 'classifiers' in project_section:
            pyproject_info.classifiers = project_section['classifiers']
        
        # Dependencies
        if 'dependencies' in project_section:
            pyproject_info.dependencies = project_section['dependencies']
        
        # Optional dependencies
        if 'optional-dependencies' in project_section:
            pyproject_info.optional_dependencies = project_section['optional-dependencies']
        
        # URLs
        if 'urls' in project_section:
            pyproject_info.urls = project_section['urls']
        
        # Scripts
        if 'scripts' in project_section:
            pyproject_info.scripts = project_section['scripts']
        
        # Build system
        if 'build-system' in data:
            pyproject_info.build_system = data['build-system']
        
        # Tool sections
        if 'tool' in data:
            pyproject_info.tool_sections = data['tool']
        
        return pyproject_info
    
    @staticmethod
    def _validate_project_name(name: str) -> bool:
        """Valide un nom de projet selon PEP 508"""
        if not name:
            return False
        
        # Regex PEP 508 pour nom projet
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def _validate_version(version: str) -> bool:
        """Valide une version selon PEP 440"""
        if not version:
            return False
        
        # Regex simplifiée PEP 440
        pattern = r'^\d+(\.\d+)*((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?$'
        return bool(re.match(pattern, version))
    
    @staticmethod
    def _validate_python_requirement(requirement: str) -> bool:
        """Valide un requirement Python"""
        if not requirement:
            return False
        
        # Format basique: >=3.8, ~=3.9.0, etc.
        pattern = r'^[><=~!]+\d+(\.\d+)*$'
        return bool(re.match(pattern, requirement.replace(' ', '')))
    
    @staticmethod
    def _validate_dependency_spec(spec: str) -> bool:
        """Valide une spécification de dépendance"""
        if not spec:
            return False
        
        # Éviter caractères dangereux
        dangerous_chars = [';', '|', '&', '`', '$']
        if any(char in spec for char in dangerous_chars):
            return False
        
        # Validation basique format package
        # Nom package + version optionnelle + extras optionnels
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*(\[[a-zA-Z0-9,._-]+\])?(==|>=|<=|>|<|~=|!=)?[a-zA-Z0-9._-]*$'
        return bool(re.match(pattern, spec))
    
    @staticmethod
    def _normalize_dependency_name(dep: str) -> str:
        """Normalise un nom de dépendance"""
        # Extraction nom (avant version/extras)
        name_match = re.match(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*)', dep)
        if name_match:
            return name_match.group(1).lower().replace('_', '-')
        return dep
    
    @staticmethod
    def _parse_dependency_extras(dep: str) -> List[str]:
        """Parse les extras d'une dépendance"""
        extras_match = re.search(r'\[([a-zA-Z0-9,._-]+)\]', dep)
        if extras_match:
            return [extra.strip() for extra in extras_match.group(1).split(',')]
        return []
    
    @staticmethod
    def _parse_dependency_version(dep: str) -> Optional[str]:
        """Parse la contrainte de version d'une dépendance"""
        version_match = re.search(r'(==|>=|<=|>|<|~=|!=)([a-zA-Z0-9._-]+)', dep)
        if version_match:
            return f"{version_match.group(1)}{version_match.group(2)}"
        return None