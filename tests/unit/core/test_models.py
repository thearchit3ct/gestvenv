"""
Tests unitaires pour les modèles de données
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from gestvenv.core.models import (
    EnvironmentInfo,
    PyProjectInfo,
    PackageInfo,
    Config,
    EnvironmentResult,
    InstallResult,
    SyncResult,
    DiagnosticReport,
    DiagnosticIssue,
    OptimizationSuggestion,
    EnvironmentHealth,
    BackendType,
    SourceFileType,
    ExportFormat,
    IssueLevel,
)


class TestEnvironmentInfo:
    """Tests pour EnvironmentInfo"""

    def test_creation_basique(self):
        """Test création environnement basique"""
        env = EnvironmentInfo(
            name="test_env",
            path=Path("/tmp/test_env"),
            python_version="3.11"
        )

        assert env.name == "test_env"
        assert env.path == Path("/tmp/test_env")
        assert env.python_version == "3.11"
        assert env.backend_type == BackendType.AUTO
        assert env.health == EnvironmentHealth.UNKNOWN
        assert isinstance(env.created_at, datetime)
        assert len(env.packages) == 0
        assert len(env.dependency_groups) == 0

    def test_validation_valide(self, tmp_path):
        """Test validation environnement valide"""
        env = EnvironmentInfo(
            name="valid_env",
            path=tmp_path,  # Utiliser un chemin qui existe
            python_version="3.11"
        )

        # validate() returns truthy value when valid
        assert env.validate()

    def test_validation_invalide(self):
        """Test validation environnement invalide"""
        env = EnvironmentInfo(
            name="",  # Nom vide
            path=Path("/invalid"),
            python_version="3.11"
        )

        # validate() returns falsy value when invalid
        assert not env.validate()

    def test_serialisation_deserialisation(self, tmp_path):
        """Test sérialisation/désérialisation"""
        original = EnvironmentInfo(
            name="test_env",
            path=tmp_path,
            python_version="3.11",
            backend_type=BackendType.UV,
            health=EnvironmentHealth.HEALTHY,
            is_active=True
        )

        data = original.to_dict()
        restored = EnvironmentInfo.from_dict(data)

        assert restored.name == original.name
        assert restored.path == original.path
        assert restored.python_version == original.python_version
        assert restored.backend_type == original.backend_type
        assert restored.health == original.health
        assert restored.is_active == original.is_active

    def test_get_package_count(self):
        """Test comptage packages"""
        env = EnvironmentInfo(
            name="test",
            path=Path("/test"),
            python_version="3.11"
        )

        env.packages = [
            PackageInfo("requests", "2.25.0"),
            PackageInfo("flask", "2.0.0")
        ]

        assert env.get_package_count() == 2

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.rglob')
    def test_get_size_mb(self, mock_rglob, mock_exists):
        """Test calcul taille"""
        mock_exists.return_value = True

        # Mock fichiers
        mock_file1 = MagicMock()
        mock_file1.is_file.return_value = True
        mock_file1.stat.return_value.st_size = 1024 * 1024  # 1MB

        mock_file2 = MagicMock()
        mock_file2.is_file.return_value = True
        mock_file2.stat.return_value.st_size = 512 * 1024  # 0.5MB

        mock_rglob.return_value = [mock_file1, mock_file2]

        env = EnvironmentInfo(
            name="test",
            path=Path("/test"),
            python_version="3.11"
        )

        size = env.get_size_mb()
        assert size == 1.5

    def test_needs_sync_true(self):
        """Test détection besoin sync"""
        pyproject = PyProjectInfo(
            name="test",
            dependencies=["requests>=2.25.0", "flask==2.0.0"]
        )

        env = EnvironmentInfo(
            name="test",
            path=Path("/test"),
            python_version="3.11",
            pyproject_info=pyproject
        )

        env.packages = [PackageInfo("requests", "2.25.0")]

        assert env.needs_sync() is True

    def test_needs_sync_false(self):
        """Test pas besoin sync"""
        pyproject = PyProjectInfo(
            name="test",
            dependencies=["requests>=2.25.0"]
        )

        env = EnvironmentInfo(
            name="test",
            path=Path("/test"),
            python_version="3.11",
            pyproject_info=pyproject
        )

        env.packages = [PackageInfo("requests", "2.25.0")]

        assert env.needs_sync() is False


class TestPyProjectInfo:
    """Tests pour PyProjectInfo"""

    def test_creation_basique(self):
        """Test création PyProjectInfo"""
        pyproject = PyProjectInfo(
            name="test-project",
            version="1.0.0",
            description="Test project"
        )

        assert pyproject.name == "test-project"
        assert pyproject.version == "1.0.0"
        assert pyproject.description == "Test project"
        assert len(pyproject.dependencies) == 0

    def test_validation_pep621_valide(self):
        """Test validation PEP 621 valide"""
        pyproject = PyProjectInfo(
            name="valid-project",
            version="1.0.0",
            dependencies=["requests>=2.25.0"]
        )

        assert pyproject.validate_pep621() is True

    def test_validation_pep621_invalide(self):
        """Test validation PEP 621 invalide"""
        pyproject = PyProjectInfo(
            name="",  # Nom vide
            version="1.0.0"
        )

        assert pyproject.validate_pep621() is False

    def test_extract_dependencies_basique(self):
        """Test extraction dépendances"""
        pyproject = PyProjectInfo(
            name="test",
            dependencies=["requests>=2.25.0", "flask==2.0.0"],
            optional_dependencies={
                "dev": ["pytest>=6.0", "black"],
                "docs": ["sphinx"]
            }
        )

        deps = pyproject.extract_dependencies()
        assert "requests>=2.25.0" in deps
        assert "flask==2.0.0" in deps
        assert len(deps) == 2

    def test_extract_dependencies_avec_groupes(self):
        """Test extraction avec groupes optionnels"""
        pyproject = PyProjectInfo(
            name="test",
            dependencies=["requests>=2.25.0"],
            optional_dependencies={
                "dev": ["pytest>=6.0"],
                "docs": ["sphinx"]
            }
        )

        deps = pyproject.extract_dependencies(groups=["dev"])
        assert "requests>=2.25.0" in deps
        assert "pytest>=6.0" in deps
        assert len(deps) == 2

    def test_to_requirements_txt(self):
        """Test conversion requirements.txt"""
        pyproject = PyProjectInfo(
            name="test",
            dependencies=["requests>=2.25.0", "flask==2.0.0"],
            optional_dependencies={"dev": ["pytest>=6.0"]}
        )

        requirements = pyproject.to_requirements_txt()
        lines = requirements.strip().split('\n')

        assert "requests>=2.25.0" in lines
        assert "flask==2.0.0" in lines
        assert len(lines) == 2

    def test_to_requirements_txt_avec_optionnel(self):
        """Test conversion avec dépendances optionnelles"""
        pyproject = PyProjectInfo(
            name="test",
            dependencies=["requests>=2.25.0"],
            optional_dependencies={"dev": ["pytest>=6.0"]}
        )

        requirements = pyproject.to_requirements_txt(include_optional=True)
        lines = requirements.strip().split('\n')

        assert "requests>=2.25.0" in lines
        assert "pytest>=6.0" in lines

    def test_get_dependency_groups(self):
        """Test récupération groupes dépendances"""
        pyproject = PyProjectInfo(
            name="test",
            optional_dependencies={
                "dev": ["pytest"],
                "docs": ["sphinx"],
                "test": ["coverage"]
            }
        )

        groups = pyproject.get_dependency_groups()
        assert "dev" in groups
        assert "docs" in groups
        assert "test" in groups
        assert len(groups) == 3


class TestPackageInfo:
    """Tests pour PackageInfo"""

    def test_creation_basique(self):
        """Test création PackageInfo"""
        package = PackageInfo(
            name="requests",
            version="2.25.0"
        )

        assert package.name == "requests"
        assert package.version == "2.25.0"
        assert package.source == "pypi"
        assert package.is_editable is False
        assert package.backend_used == "pip"

    def test_compare_version(self):
        """Test comparaison versions"""
        package = PackageInfo("test", "2.0.0")

        assert package.compare_version("1.9.0") == 1
        assert package.compare_version("2.0.0") == 0
        assert package.compare_version("2.1.0") == -1

    def test_compare_version_invalide(self):
        """Test comparaison version invalide"""
        package = PackageInfo("test", "invalid")

        assert package.compare_version("1.0.0") == 0

    def test_is_compatible(self):
        """Test compatibilité Python"""
        package = PackageInfo("test", "1.0.0")

        assert package.is_compatible("3.11") is True
        assert package.is_compatible("3.8") is True

    def test_get_install_command_normal(self):
        """Test commande installation normale"""
        package = PackageInfo("requests", "2.25.0")

        assert package.get_install_command() == "requests==2.25.0"

    def test_get_install_command_editable(self):
        """Test commande installation éditable"""
        package = PackageInfo(
            name="mypackage",
            version="1.0.0",
            is_editable=True,
            local_path=Path("/path/to/package")
        )

        assert package.get_install_command() == "-e /path/to/package"

    def test_is_development_package(self):
        """Test détection package dev"""
        dev_packages = ["pytest", "coverage", "mock"]

        for pkg_name in dev_packages:
            package = PackageInfo(pkg_name, "1.0.0")
            assert package.is_development_package() is True

        prod_package = PackageInfo("requests", "2.25.0")
        assert prod_package.is_development_package() is False


class TestResultModels:
    """Tests pour les modèles de résultats"""

    def test_environment_result_success(self):
        """Test EnvironmentResult succès"""
        env = EnvironmentInfo("test", Path("/test"), "3.11")
        result = EnvironmentResult(
            success=True,
            message="Environnement créé",
            environment=env
        )

        assert result.success is True
        assert result.message == "Environnement créé"
        assert result.environment == env

    def test_environment_result_echec(self):
        """Test EnvironmentResult échec"""
        result = EnvironmentResult(
            success=False,
            message="Erreur création"
        )

        assert result.success is False
        assert result.message == "Erreur création"
        assert result.environment is None

    def test_install_result(self):
        """Test InstallResult"""
        result = InstallResult(
            success=True,
            message="Installation réussie",
            packages_installed=["requests"],
            backend_used="uv"
        )

        assert result.success is True
        assert "requests" in result.packages_installed
        assert result.backend_used == "uv"

    def test_sync_result(self):
        """Test SyncResult"""
        result = SyncResult(
            success=True,
            message="Synchronisation réussie",
            packages_added=["flask", "requests"],
            packages_updated=["django"],
            packages_removed=["old-package"]
        )

        assert result.success is True
        assert len(result.packages_added) == 2
        assert len(result.packages_updated) == 1
        assert len(result.packages_removed) == 1


class TestDiagnosticModels:
    """Tests pour les modèles de diagnostic"""

    def test_diagnostic_issue(self):
        """Test DiagnosticIssue"""
        issue = DiagnosticIssue(
            level=IssueLevel.WARNING,
            category="packages",
            description="Package obsolète",
            metadata={"package": "requests", "version": "1.0.0"}
        )

        assert issue.level == IssueLevel.WARNING
        assert issue.description == "Package obsolète"
        assert issue.category == "packages"
        assert issue.metadata["package"] == "requests"

    def test_optimization_suggestion(self):
        """Test OptimizationSuggestion"""
        suggestion = OptimizationSuggestion(
            category="performance",
            description="Migration vers uv recommandée",
            command="gestvenv migrate --backend uv",
            impact_score=0.8,
            safe_to_apply=True
        )

        assert suggestion.category == "performance"
        assert suggestion.description == "Migration vers uv recommandée"
        assert suggestion.command == "gestvenv migrate --backend uv"
        assert suggestion.impact_score == 0.8
        assert suggestion.safe_to_apply is True

    def test_diagnostic_report(self):
        """Test DiagnosticReport"""
        issues = [
            DiagnosticIssue(
                level=IssueLevel.WARNING,
                category="test",
                description="Test warning"
            )
        ]
        suggestions = [
            OptimizationSuggestion(
                category="test",
                description="Test desc",
                command="test_cmd",
                impact_score=0.5,
                safe_to_apply=True
            )
        ]

        report = DiagnosticReport(
            overall_status=EnvironmentHealth.HAS_WARNINGS,
            issues=issues,
            recommendations=suggestions
        )

        assert report.overall_status == EnvironmentHealth.HAS_WARNINGS
        assert len(report.issues) == 1
        assert len(report.recommendations) == 1
        assert len(report.get_critical_issues()) == 0


class TestConfig:
    """Tests pour Config"""

    def test_creation_defaut(self):
        """Test création configuration par défaut"""
        config = Config()

        assert config.version == "1.1.0"
        assert config.auto_migrate is True
        assert config.default_python_version == "3.11"
        assert config.cache_enabled is True

    def test_validation_valide(self):
        """Test validation configuration valide"""
        config = Config(
            default_python_version="3.11"
        )

        config.cache_settings["cleanup_interval_days"] = 24
        assert config.default_python_version == "3.11"

    def test_cache_enabled_property(self):
        """Test propriété cache_enabled"""
        config = Config()
        config.cache_enabled = False

        assert config.cache_enabled is False
        assert config.cache_settings["enabled"] is False

    def test_save_and_load(self, tmp_path):
        """Test sauvegarde et chargement config"""
        config = Config(
            default_python_version="3.10"
        )
        config.cache_enabled = False

        config_path = tmp_path / "config.json"
        config.save(config_path)

        loaded = Config.load(config_path)
        assert loaded.default_python_version == "3.10"
        assert loaded.cache_enabled is False
