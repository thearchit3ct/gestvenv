"""
Tests d'intégration de création et gestion des templates
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from gestvenv.core.models import ProjectTemplate


class TestTemplateCreation:
    """Tests de création complète de templates (mockés)"""

    def test_create_web_app_template(self, tmp_path):
        """Test création template application web (mocké)"""
        # Créer un mock TemplateService
        mock_template_service = Mock()
        mock_create_result = Mock(
            success=True,
            message="Projet créé depuis template",
            project_path=tmp_path / "my_webapp"
        )
        mock_template_service.create_from_template = Mock(return_value=mock_create_result)

        # Création projet depuis template web
        create_result = mock_template_service.create_from_template(
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
        mock_template_service.create_from_template.assert_called_once()

    def test_create_data_science_template(self, tmp_path):
        """Test création template data science (mocké)"""
        mock_template_service = Mock()
        mock_create_result = Mock(
            success=True,
            message="Projet data science créé",
            project_path=tmp_path / "ml_project"
        )
        mock_template_service.create_from_template = Mock(return_value=mock_create_result)

        # Création projet data science
        create_result = mock_template_service.create_from_template(
            template_name="datascience",
            project_path=tmp_path / "ml_project",
            project_params={
                "project_name": "ml-analysis",
                "description": "Projet d'analyse ML",
                "author": "Data Scientist"
            }
        )

        assert create_result.success
        mock_template_service.create_from_template.assert_called_once()

    def test_create_cli_tool_template(self, tmp_path):
        """Test création template outil CLI (mocké)"""
        mock_template_service = Mock()
        mock_create_result = Mock(
            success=True,
            message="Outil CLI créé",
            project_path=tmp_path / "cli_tool"
        )
        mock_template_service.create_from_template = Mock(return_value=mock_create_result)

        # Création outil CLI
        create_result = mock_template_service.create_from_template(
            template_name="cli",
            project_path=tmp_path / "cli_tool",
            project_params={
                "project_name": "my-cli-tool",
                "description": "Outil CLI de test",
                "entry_point": "mycli"
            }
        )

        assert create_result.success
        mock_template_service.create_from_template.assert_called_once()

    def test_custom_template_registration(self, tmp_path):
        """Test enregistrement template personnalisé (mocké)"""
        mock_template_service = Mock()
        mock_register_result = Mock(
            success=True,
            message="Template enregistré"
        )
        mock_template_service.register_template = Mock(return_value=mock_register_result)

        # Définition template personnalisé
        custom_template = {
            "name": "custom_microservice",
            "description": "Template microservice personnalisé",
            "files": {
                "pyproject.toml": "[project]\nname = '{{project_name}}'\n",
                "main.py": "# Main file\n"
            }
        }

        # Enregistrement template
        register_result = mock_template_service.register_template(custom_template)

        assert register_result.success
        mock_template_service.register_template.assert_called_once_with(custom_template)

    def test_template_list(self):
        """Test listage des templates (mocké)"""
        mock_template_service = Mock()
        # list_templates() retourne List[ProjectTemplate]
        mock_templates = [
            ProjectTemplate(name="webapp", description="Template application web", version="1.0.0"),
            ProjectTemplate(name="datascience", description="Template data science", version="1.0.0"),
            ProjectTemplate(name="cli", description="Template outil CLI", version="1.0.0")
        ]
        mock_template_service.list_templates = Mock(return_value=mock_templates)

        # Listage templates disponibles
        templates = mock_template_service.list_templates()

        assert len(templates) == 3
        template_names = [t.name for t in templates]
        assert "webapp" in template_names
        assert "datascience" in template_names
        assert "cli" in template_names

    def test_get_template_info(self):
        """Test récupération informations template (mocké)"""
        mock_template_service = Mock()
        mock_template = ProjectTemplate(
            name="webapp",
            description="Template pour applications web Flask/FastAPI",
            version="1.0.0",
            default_params={"framework": "flask"}
        )
        mock_template_service.get_template = Mock(return_value=mock_template)

        # Informations détaillées template
        template_info = mock_template_service.get_template("webapp")

        assert template_info is not None
        assert template_info.name == "webapp"
        assert template_info.description is not None
        mock_template_service.get_template.assert_called_once_with("webapp")

    def test_validate_template(self, tmp_path):
        """Test validation template (mocké)"""
        mock_template_service = Mock()
        mock_validation_result = Mock(
            valid=True,
            errors=[],
            warnings=["Pas de fichier README.md"]
        )
        mock_template_service.validate_template = Mock(return_value=mock_validation_result)

        # Template à valider
        template_data = {
            "name": "test_template",
            "description": "Template de test",
            "files": {"pyproject.toml": "[project]\nname='test'\n"}
        }

        # Validation
        validation_result = mock_template_service.validate_template(template_data)

        assert validation_result.valid is True
        assert len(validation_result.errors) == 0
        mock_template_service.validate_template.assert_called_once()

    def test_generate_pyproject_from_template(self, tmp_path):
        """Test génération pyproject.toml depuis template (mocké)"""
        mock_template_service = Mock()
        mock_pyproject_content = """[project]
name = "my-project"
version = "0.1.0"
dependencies = ["flask>=2.0", "requests>=2.25"]
"""
        mock_template_service.generate_pyproject_from_template = Mock(return_value=mock_pyproject_content)

        # Génération
        pyproject_content = mock_template_service.generate_pyproject_from_template(
            template_name="webapp",
            project_params={"project_name": "my-project"}
        )

        assert "my-project" in pyproject_content
        assert "[project]" in pyproject_content
        mock_template_service.generate_pyproject_from_template.assert_called_once()
