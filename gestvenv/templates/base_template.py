"""
Classes de base pour le système de templates GestVenv v1.1
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


@dataclass
class TemplateMetadata:
    """Métadonnées d'un fichier template"""
    encoding: str = "utf-8"
    executable: bool = False
    create_if_missing: bool = True


@dataclass 
class TemplateFile:
    """Représente un fichier dans un template"""
    path: str
    content: str
    is_template: bool = True
    metadata: TemplateMetadata = field(default_factory=TemplateMetadata)


class ProjectTemplate(ABC):
    """Classe de base pour tous les templates de projet"""
    
    def __init__(
        self,
        name: str,
        description: str,
        category: str = "general",
        version: str = "1.0.0",
        python_version: str = "3.11",
        dependencies: Optional[List[str]] = None,
        dev_dependencies: Optional[List[str]] = None,
        optional_dependencies: Optional[Dict[str, List[str]]] = None
    ):
        self.name = name
        self.description = description
        self.category = category
        self.version = version
        self.python_version = python_version
        self.dependencies = dependencies or []
        self.dev_dependencies = dev_dependencies or []
        self.optional_dependencies = optional_dependencies or {}
        
    @abstractmethod
    def get_files(self) -> List[TemplateFile]:
        """Retourne la liste des fichiers du template"""
        pass
        
    @abstractmethod 
    def get_pyproject_config(self) -> Dict[str, Any]:
        """Retourne la configuration pyproject.toml"""
        pass
        
    def get_default_params(self) -> Dict[str, Any]:
        """Paramètres par défaut du template"""
        return {
            "author": "Développeur",
            "email": "dev@example.com",
            "license": "MIT",
            "python_version": self.python_version
        }
        
    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """Valide les paramètres fournis"""
        errors = []
        
        if not params.get("project_name"):
            errors.append("project_name est requis")
            
        project_name = params.get("project_name", "")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", project_name):
            errors.append("project_name doit être un nom Python valide")
            
        return errors
        
    def render_content(self, content: str, context: Dict[str, Any]) -> str:
        """Rend le contenu avec les variables de contexte"""
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
        return content
        
    def prepare_context(self, project_name: str, **params) -> Dict[str, Any]:
        """Prépare le contexte pour le rendu"""
        defaults = self.get_default_params()
        defaults.update(params)
        defaults["project_name"] = project_name
        defaults["package_name"] = project_name.lower().replace("-", "_")
        return defaults