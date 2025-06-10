"""
Tests d'intégration de création et gestion des templates
"""

import pytest
from pathlib import Path
import json

class TestTemplateCreation:
    """Tests de création complète de templates"""
    
    def test_create_web_app_template(self, env_manager, tmp_path):
        """Test création template application web"""
        template_service = env_manager.template_service
        
        # Création projet depuis template web
        create_result = template_service.create_from_template(
            template_name="webapp",
            project_path=tmp_path / "my_webapp",
            project_params={
                "project_name": "my-web-app",
                "description": "Application web de test",
                "author": "Test Developer",
                "license": "MIT"
            }
        )
        
        assert create_result.success
        
        project_path = tmp_path / "my_webapp"
        assert project_path.exists()
        assert (project_path / "pyproject.toml").exists()
        
        # Vérification contenu pyproject.toml
        pyproject_content = (project_path / "pyproject.toml").read_text()
        assert "my-web-app" in pyproject_content
        assert "flask" in pyproject_content.lower() or "fastapi" in pyproject_content.lower()
        
        # Création environnement depuis template
        env_result = env_manager.create_from_pyproject(
            pyproject_path=project_path / "pyproject.toml",
            env_name="webapp_env"
        )
        assert env_result.success
        
        # Vérification packages web installés
        env_info = env_result.environment
        package_names = [pkg.name.lower() for pkg in env_info.packages]
        web_packages = ["flask", "fastapi", "django", "requests"]
        assert any(web_pkg in package_names for web_pkg in web_packages)
    
    def test_create_data_science_template(self, env_manager, tmp_path):
        """Test création template data science"""
        template_service = env_manager.template_service
        
        # Création projet data science
        create_result = template_service.create_from_template(
            template_name="datascience",
            project_path=tmp_path / "ml_project",
            project_params={
                "project_name": "ml-analysis",
                "description": "Projet d'analyse ML",
                "author": "Data Scientist"
            }
        )
        
        assert create_result.success
        
        project_path = tmp_path / "ml_project"
        pyproject_content = (project_path / "pyproject.toml").read_text()
        
        # Vérification dépendances data science
        ds_packages = ["pandas", "numpy", "scikit-learn", "matplotlib"]
        for package in ds_packages:
            assert package in pyproject_content
        
        # Test environnement data science
        env_result = env_manager.create_from_pyproject(
            pyproject_path=project_path / "pyproject.toml",
            env_name="datascience_env"
        )
        assert env_result.success
        
        env_info = env_result.environment
        package_names = [pkg.name.lower() for pkg in env_info.packages]
        assert "pandas" in package_names
        assert "numpy" in package_names
    
    def test_create_cli_tool_template(self, env_manager, tmp_path):
        """Test création template outil CLI"""
        template_service = env_manager.template_service
        
        # Création outil CLI
        create_result = template_service.create_from_template(
            template_name="cli",
            project_path=tmp_path / "cli_tool",
            project_params={
                "project_name": "my-cli-tool",
                "description": "Outil CLI de test",
                "entry_point": "mycli"
            }
        )
        
        assert create_result.success
        
        project_path = tmp_path / "cli_tool"
        pyproject_content = (project_path / "pyproject.toml").read_text()
        
        # Vérification configuration CLI
        assert "click" in pyproject_content or "typer" in pyproject_content
        assert "console_scripts" in pyproject_content or "scripts" in pyproject_content
        assert "mycli" in pyproject_content
        
        # Structure CLI typique
        assert (project_path / "src").exists() or (project_path / "my_cli_tool").exists()
    
    def test_custom_template_creation(self, env_manager, tmp_path):
        """Test création template personnalisé"""
        template_service = env_manager.template_service
        
        # Définition template personnalisé
        custom_template = {
            "name": "custom_microservice",
            "description": "Template microservice personnalisé",
            "files": {
                "pyproject.toml": '''[project]
name = "{{project_name}}"
version = "0.1.0"
description = "{{description}}"
dependencies = [
    "fastapi>=0.68.0",
    "uvicorn>=0.15.0",
    "pydantic>=1.8.0"
]

[project.optional-dependencies]
dev = ["pytest>=6.0", "httpx>=0.24.0"]
''',
                "main.py": '''from fastapi import FastAPI

app = FastAPI(title="{{project_name}}")

@app.get("/")
async def root():
    return {"message": "Hello from {{project_name}}"}
''',
                "Dockerfile": '''FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
            }
        }
        
        # Enregistrement template
        register_result = template_service.register_template(custom_template)
        assert register_result.success
        
        # Utilisation template personnalisé
        create_result = template_service.create_from_template(
            template_name="custom_microservice",
            project_path=tmp_path / "my_microservice",
            project_params={
                "project_name": "my-api",
                "description": "API microservice"
            }
        )
        
        assert create_result.success
        
        project_path = tmp_path / "my_microservice"
        assert (project_path / "main.py").exists()
        assert (project_path / "Dockerfile").exists()
        
        # Vérification substitution paramètres
        main_content = (project_path / "main.py").read_text()
        assert "my-api" in main_content
        assert "{{project_name}}" not in main_content
    
    def test_template_with_environment_creation(self, env_manager, tmp_path):
        """Test création template avec environnement associé"""
        template_service = env_manager.template_service
        
        # Création projet avec environnement automatique
        create_result = template_service.create_project_with_environment(
            template_name="webapp",
            project_path=tmp_path / "webapp_with_env",
            env_name="webapp_auto",
            project_params={
                "project_name": "auto-webapp",
                "description": "Webapp avec env auto"
            }
        )
        
        assert create_result.success
        assert create_result.environment is not None
        assert create_result.environment.name == "webapp_auto"
        
        # Vérification projet et environnement
        project_path = tmp_path / "webapp_with_env"
        assert project_path.exists()
        
        env_info = env_manager.get_environment_info("webapp_auto")
        assert env_info is not None
        assert len(env_info.packages) > 0
    
    def test_template_list_and_management(self, env_manager):
        """Test listage et gestion des templates"""
        template_service = env_manager.template_service
        
        # Listage templates disponibles
        templates_list = template_service.list_templates()
        assert templates_list.success
        assert len(templates_list.templates) > 0
        
        # Vérification templates built-in
        template_names = [t.name for t in templates_list.templates]
        builtin_templates = ["webapp", "datascience", "cli"]
        
        for builtin in builtin_templates:
            assert builtin in template_names
        
        # Informations détaillées template
        webapp_info = template_service.get_template_info("webapp")
        assert webapp_info.success
        assert webapp_info.template.name == "webapp"
        assert webapp_info.template.description
        assert len(webapp_info.template.dependencies) > 0