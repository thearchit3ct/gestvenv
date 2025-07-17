"""
Classes de base pour le système de templates GestVenv v1.1
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import re
import os
import shutil
import subprocess


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
    
    def create_directory_structure(self, base_path: Path, context: Dict[str, Any]) -> None:
        """Crée la structure de répertoires nécessaire"""
        directories = set()
        
        for template_file in self.get_files():
            file_path = Path(self.render_content(template_file.path, context))
            directories.add(file_path.parent)
        
        for directory in directories:
            full_path = base_path / directory
            full_path.mkdir(parents=True, exist_ok=True)
    
    def write_file(self, file_path: Path, template_file: TemplateFile, context: Dict[str, Any]) -> None:
        """Écrit un fichier avec le contenu rendu"""
        if template_file.is_template:
            content = self.render_content(template_file.content, context)
        else:
            content = template_file.content
            
        file_path.write_text(content, encoding=template_file.metadata.encoding)
        
        if template_file.metadata.executable:
            os.chmod(file_path, 0o755)
    
    def generate_project(self, target_path: Path, **params) -> None:
        """Génère le projet complet"""
        project_name = params.get("project_name")
        if not project_name:
            raise ValueError("project_name est requis")
            
        context = self.prepare_context(project_name, **params)
        errors = self.validate_params(context)
        if errors:
            raise ValueError(f"Paramètres invalides: {', '.join(errors)}")
        
        project_path = target_path / project_name
        project_path.mkdir(exist_ok=True)
        
        self.pre_generate_hook(project_path, context)
        self.create_directory_structure(project_path, context)
        
        for template_file in self.get_files():
            file_path = project_path / self.render_content(template_file.path, context)
            self.write_file(file_path, template_file, context)
        
        self.post_generate_hook(project_path, context)
    
    def pre_generate_hook(self, project_path: Path, context: Dict[str, Any]) -> None:
        """Hook exécuté avant la génération des fichiers"""
        pass
    
    def post_generate_hook(self, project_path: Path, context: Dict[str, Any]) -> None:
        """Hook exécuté après la génération des fichiers"""
        pass
    
    def run_command(self, command: List[str], cwd: Path) -> subprocess.CompletedProcess:
        """Exécute une commande dans le répertoire spécifié"""
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
    
    def copy_static_files(self, source_path: Path, target_path: Path, context: Dict[str, Any]) -> None:
        """Copie des fichiers statiques vers le projet"""
        if not source_path.exists():
            return
            
        for item in source_path.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(source_path)
                target_file = target_path / self.render_content(str(relative_path), context)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_file)
    
    def get_post_install_commands(self) -> List[List[str]]:
        """Retourne les commandes à exécuter après l'installation"""
        return []
    
    def execute_post_install(self, project_path: Path) -> None:
        """Exécute les commandes post-installation"""
        for command in self.get_post_install_commands():
            self.run_command(command, project_path)