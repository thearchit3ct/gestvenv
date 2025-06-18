"""
Service de gestion des templates pour GestVenv v1.1
"""

from dataclasses import dataclass, field
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.models import (
    ProjectTemplate,
    TemplateFile,
    PyProjectInfo
)
from ..core.exceptions import TemplateError, ValidationError
from ..utils import TomlHandler

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """Informations sur un template"""
    name: str
    description: str
    category: str
    python_version: str
    dependencies: int
    is_builtin: bool


@dataclass
class TemplateCreationResult:
    """Résultat de création depuis template"""
    success: bool
    message: str
    project_path: Optional[Path] = None
    files_created: List[str] = field(default_factory=list)
    template_used: Optional[str] = None


@dataclass
class ValidationResult:
    """Résultat de validation"""
    valid: bool
    errors: List[str] = field(default_factory=list)


class TemplateService:
    """Service de gestion des templates de projets"""
    
    def __init__(self):
        self.templates_path = Path.home() / ".gestvenv" / "templates"
        self.builtin_templates_path = self.templates_path / "builtin"
        self.user_templates_path = self.templates_path / "user"
        
        self.templates = {}
        self._load_templates()
        
    def list_templates(self) -> List[TemplateInfo]:
        """Liste tous les templates disponibles"""
        template_infos = []
        
        for name, template in self.templates.items():
            template_infos.append(TemplateInfo(
                name=name,
                description=template.description,
                category=getattr(template, 'category', 'general'),
                python_version=getattr(template, 'default_python_version', '3.11'),
                dependencies=len(getattr(template, 'default_dependencies', [])),
                is_builtin=getattr(template, '_builtin', False)
            ))
            
        return sorted(template_infos, key=lambda x: (x.category, x.name))
        
    def get_template(self, name: str) -> Optional[ProjectTemplate]:
        """Récupère un template par nom"""
        return self.templates.get(name)
        
    def create_from_template(
        self, 
        template_name: str, 
        project_name: str, 
        output_path: Path, 
        **params
    ) -> TemplateCreationResult:
        """Crée un projet depuis un template"""
        if template_name not in self.templates:
            return TemplateCreationResult(
                success=False,
                message=f"Template '{template_name}' introuvable"
            )
            
        template = self.templates[template_name]
        
        try:
            validation_result = self._validate_parameters(template, params)
            if not validation_result.valid:
                return TemplateCreationResult(
                    success=False,
                    message=f"Paramètres invalides: {validation_result.errors}"
                )
                
            context = self._prepare_context(template, project_name, **params)
            
            project_path = output_path / project_name
            project_path.mkdir(parents=True, exist_ok=True)
            
            files_created = []
            
            # Génération fichiers template
            for template_file in template.files:
                file_path = project_path / template_file.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                if template_file.is_template:
                    content = self._render_content(template_file.content, context)
                else:
                    content = template_file.content
                    
                file_path.write_text(content, encoding='utf-8')
                files_created.append(str(file_path.relative_to(project_path)))
                
            # Génération pyproject.toml
            pyproject_content = self._generate_pyproject_toml(template, context)
            pyproject_path = project_path / "pyproject.toml"
            pyproject_path.write_text(pyproject_content, encoding='utf-8')
            files_created.append("pyproject.toml")
            
            return TemplateCreationResult(
                success=True,
                message=f"Projet '{project_name}' créé depuis template '{template_name}'",
                project_path=project_path,
                files_created=files_created,
                template_used=template_name
            )
            
        except Exception as e:
            return TemplateCreationResult(
                success=False,
                message=f"Erreur création projet: {e}"
            )
            
    def register_template(self, template: ProjectTemplate) -> bool:
        """Enregistre un template utilisateur"""
        try:
            validation_errors = self._validate_template(template)
            if validation_errors:
                logger.error(f"Template invalide: {validation_errors}")
                return False
                
            template_path = self.user_templates_path / f"{template.name}.json"
            template_path.parent.mkdir(parents=True, exist_ok=True)
            
            template_data = self._template_to_dict(template)
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2)
                
            self.templates[template.name] = template
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur enregistrement template: {e}")
            return False
            
    def validate_template(self, template_path: Path) -> List[ValidationError]:
        """Valide un fichier template"""
        errors = []
        
        try:
            if not template_path.exists():
                errors.append(ValidationError(f"Fichier template introuvable: {template_path}"))
                return errors
                
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
                
            required_fields = ['name', 'description', 'files']
            for field in required_fields:
                if field not in template_data:
                    errors.append(ValidationError(f"Champ requis manquant: {field}"))
                    
        except json.JSONDecodeError as e:
            errors.append(ValidationError(f"JSON invalide: {e}"))
        except Exception as e:
            errors.append(ValidationError(f"Erreur validation: {e}"))
            
        return errors
        
    def generate_pyproject_from_template(self, template_name: str, **params) -> Optional[PyProjectInfo]:
        """Génère un PyProjectInfo depuis un template"""
        template = self.templates.get(template_name)
        if not template:
            return None
            
        try:
            context = self._prepare_context(template, params.get('name', 'my-project'), **params)
            pyproject_content = self._generate_pyproject_toml(template, context)
            
            # Parsing du contenu généré
            from ..utils import PyProjectParser
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
                f.write(pyproject_content)
                temp_path = Path(f.name)
                
            try:
                return PyProjectParser.parse_pyproject_toml(temp_path)
            finally:
                temp_path.unlink()
                
        except Exception as e:
            logger.error(f"Erreur génération PyProjectInfo: {e}")
            return None
    
    # Méthodes privées
    
    def _load_templates(self):
        """Charge tous les templates disponibles"""
        self._load_builtin_templates()
        self._load_user_templates()
        
    def _load_builtin_templates(self):
        """Charge les templates intégrés"""
        builtin_templates = {
            "basic": self._create_basic_template(),
            "web": self._create_web_template(),
            "data": self._create_data_science_template(),
            "cli": self._create_cli_template(),
            "package": self._create_package_template(),
            "fastapi": self._create_fastapi_template(),
            "flask": self._create_flask_template()
        }
        
        for name, template in builtin_templates.items():
            template._builtin = True
            self.templates[name] = template
            
    def _load_user_templates(self):
        """Charge les templates utilisateur"""
        if not self.user_templates_path.exists():
            return
            
        for template_file in self.user_templates_path.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                template = self._dict_to_template(template_data)
                self.templates[template.name] = template
                
            except Exception as e:
                logger.warning(f"Erreur chargement template {template_file}: {e}")
                
    def _create_basic_template(self) -> ProjectTemplate:
        """Template basique"""
        return ProjectTemplate(
            name="basic",
            description="Projet Python basique",
            version="1.0.0",
            default_params={
                "author": "Développeur",
                "email": "dev@example.com",
                "python_version": "3.11"
            },
            files=[
                TemplateFile(
                    path="src/__init__.py",
                    content="",
                    is_template=False
                ),
                TemplateFile(
                    path="src/main.py",
                    content='"""Module principal de {{project_name}}"""\n\ndef main():\n    print("Hello, {{project_name}}!")\n\nif __name__ == "__main__":\n    main()\n',
                    is_template=True
                ),
                TemplateFile(
                    path="README.md",
                    content="# {{project_name}}\n\n{{description}}\n\n## Installation\n\n```bash\npip install -e .\n```\n\n## Usage\n\n```bash\npython -m src.main\n```\n",
                    is_template=True
                ),
                TemplateFile(
                    path=".gitignore",
                    content="__pycache__/\n*.py[cod]\n*$py.class\n*.so\ndist/\nbuild/\n*.egg-info/\n.pytest_cache/\n.coverage\n.env\n.venv/\n",
                    is_template=False
                )
            ]
        )
        
    def _create_web_template(self) -> ProjectTemplate:
        """Template application web"""
        return ProjectTemplate(
            name="web",
            description="Application web moderne avec FastAPI",
            version="1.0.0",
            default_params={
                "author": "Développeur",
                "framework": "fastapi"
            },
            files=[
                TemplateFile(
                    path="app/__init__.py",
                    content="",
                    is_template=False
                ),
                TemplateFile(
                    path="app/main.py",
                    content='"""Application {{project_name}} avec FastAPI"""\n\nfrom fastapi import FastAPI\n\napp = FastAPI(\n    title="{{project_name}}",\n    description="{{description}}",\n    version="{{version}}"\n)\n\n@app.get("/")\nasync def root():\n    return {"message": "{{project_name}} API", "status": "running"}\n\n@app.get("/health")\nasync def health():\n    return {"status": "healthy"}\n',
                    is_template=True
                ),
                TemplateFile(
                    path="app/api/__init__.py",
                    content="",
                    is_template=False
                ),
                TemplateFile(
                    path="requirements.txt",
                    content="fastapi>=0.100.0\nuvicorn[standard]>=0.20.0\npydantic>=2.0.0\n",
                    is_template=False
                ),
                TemplateFile(
                    path="Dockerfile",
                    content='FROM python:3.11-slim\n\nWORKDIR /app\n\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\nCOPY app/ ./app/\n\nEXPOSE 8000\n\nCMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]\n',
                    is_template=False
                )
            ]
        )
        
    def _create_data_science_template(self) -> ProjectTemplate:
        """Template data science"""
        return ProjectTemplate(
            name="data",
            description="Projet de science des données",
            version="1.0.0",
            files=[
                TemplateFile(
                    path="notebooks/01_exploration.ipynb",
                    content='{\n "cells": [],\n "metadata": {\n  "kernelspec": {\n   "display_name": "Python 3",\n   "language": "python",\n   "name": "python3"\n  }\n },\n "nbformat": 4,\n "nbformat_minor": 4\n}',
                    is_template=False
                ),
                TemplateFile(
                    path="src/data/__init__.py",
                    content="",
                    is_template=False
                ),
                TemplateFile(
                    path="src/models/__init__.py",
                    content="",
                    is_template=False
                ),
                TemplateFile(
                    path="data/raw/.gitkeep",
                    content="",
                    is_template=False
                ),
                TemplateFile(
                    path="data/processed/.gitkeep",
                    content="",
                    is_template=False
                )
            ]
        )
        
    def _create_cli_template(self) -> ProjectTemplate:
        """Template CLI"""
        return ProjectTemplate(
            name="cli",
            description="Application en ligne de commande",
            version="1.0.0"
        )
        
    def _create_package_template(self) -> ProjectTemplate:
        """Template package Python"""
        return ProjectTemplate(
            name="package",
            description="Package Python distributable",
            version="1.0.0"
        )
        
    def _create_fastapi_template(self) -> ProjectTemplate:
        """Template FastAPI avancé"""
        return self._create_web_template()  # Même base pour l'instant
        
    def _create_flask_template(self) -> ProjectTemplate:
        """Template Flask"""
        return ProjectTemplate(
            name="flask",
            description="Application Flask",
            version="1.0.0"
        )
        
    def _validate_parameters(self, template: ProjectTemplate, params: Dict[str, Any]) -> ValidationResult:
        """Valide les paramètres pour un template"""
        errors = []
        
        # Validation basique
        required_params = getattr(template, 'required_params', [])
        for param in required_params:
            if param not in params:
                errors.append(f"Paramètre requis manquant: {param}")
                
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
        
    def _prepare_context(self, template: ProjectTemplate, project_name: str, **params) -> Dict[str, Any]:
        """Prépare le contexte pour le rendu"""
        context = template.default_params.copy()
        context.update(params)
        context.update({
            "project_name": project_name,
            "creation_date": datetime.now().isoformat(),
            "version": context.get("version", "0.1.0"),
            "description": context.get("description", f"Projet {project_name}")
        })
        return context
        
    def _render_content(self, content: str, context: Dict[str, Any]) -> str:
        """Rend le contenu avec le contexte"""
        # Rendu simple avec replacement
        rendered = content
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        return rendered
        
    def _generate_pyproject_toml(self, template: ProjectTemplate, context: Dict[str, Any]) -> str:
        """Génère le contenu pyproject.toml"""
        pyproject_data = {
            "project": {
                "name": context["project_name"],
                "version": context.get("version", "0.1.0"),
                "description": context.get("description", ""),
                "authors": [
                    {"name": context.get("author", "Développeur"), 
                     "email": context.get("email", "dev@example.com")}
                ],
                "readme": "README.md",
                "requires-python": f">={context.get('python_version', '3.11')}",
                "dependencies": getattr(template, 'default_dependencies', [])
            },
            "build-system": {
                "requires": ["setuptools>=68.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            },
            "tool": {
                "gestvenv": {
                    "created_from_template": template.name,
                    "template_version": template.version,
                    "creation_date": context["creation_date"]
                }
            }
        }
        
        # Ajout dépendances optionnelles si définies
        optional_deps = getattr(template, 'optional_dependencies', {})
        if optional_deps:
            pyproject_data["project"]["optional-dependencies"] = optional_deps
            
        return TomlHandler.dumps(pyproject_data)
        
    def _validate_template(self, template: ProjectTemplate) -> List[str]:
        """Valide un template"""
        errors = []
        
        if not template.name:
            errors.append("Nom du template requis")
            
        if not template.description:
            errors.append("Description du template requise")
            
        if not template.files:
            errors.append("Au moins un fichier requis")
            
        return errors
        
    def _template_to_dict(self, template: ProjectTemplate) -> Dict[str, Any]:
        """Convertit un template en dictionnaire"""
        return {
            "name": template.name,
            "description": template.description,
            "version": template.version,
            "default_params": template.default_params,
            "files": [
                {
                    "path": f.path,
                    "content": f.content,
                    "is_template": f.is_template,
                    "metadata": f.metadata
                }
                for f in template.files
            ]
        }
        
    def _dict_to_template(self, data: Dict[str, Any]) -> ProjectTemplate:
        """Convertit un dictionnaire en template"""
        files = [
            TemplateFile(
                path=f["path"],
                content=f["content"],
                is_template=f["is_template"],
                metadata=f.get("metadata", {})
            )
            for f in data.get("files", [])
        ]
        
        return ProjectTemplate(
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            default_params=data.get("default_params", {}),
            files=files
        )