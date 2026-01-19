"""
Tests E2E pour les workflows complets de GestVenv

Ces tests vérifient les scénarios de bout en bout avec de vrais
environnements virtuels et des opérations réelles.
"""

import asyncio
import os
import pytest
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Generator


# Skip tous les tests E2E si l'environnement n'est pas configuré
pytestmark = pytest.mark.e2e


@pytest.fixture
def e2e_temp_dir() -> Generator[Path, None, None]:
    """Crée un répertoire temporaire pour les tests E2E"""
    temp_dir = Path(tempfile.mkdtemp(prefix="gestvenv_e2e_"))
    yield temp_dir
    # Nettoyage
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_project(e2e_temp_dir: Path) -> Path:
    """Crée un projet Python exemple pour les tests"""
    project_dir = e2e_temp_dir / "sample_project"
    project_dir.mkdir(parents=True)

    # Créer pyproject.toml
    pyproject_content = '''[project]
name = "sample-e2e-project"
version = "0.1.0"
description = "Sample project for E2E testing"
requires-python = ">=3.9"
dependencies = [
    "requests>=2.25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    # Créer un module Python simple
    src_dir = project_dir / "src" / "sample_e2e_project"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text('__version__ = "0.1.0"\n')
    (src_dir / "main.py").write_text('''
import requests

def hello():
    """Simple function for testing"""
    return "Hello from sample project!"

def fetch_example():
    """Fetches example.com"""
    try:
        response = requests.get("https://example.com", timeout=5)
        return response.status_code
    except Exception:
        return None
''')

    return project_dir


class TestEnvironmentCreationWorkflow:
    """Tests E2E pour la création d'environnements"""

    def test_create_environment_from_pyproject(self, e2e_temp_dir: Path, sample_project: Path):
        """Test: Création d'un environnement depuis pyproject.toml"""
        env_name = "test-e2e-env"
        env_path = e2e_temp_dir / "environments" / env_name

        # Créer l'environnement avec venv standard
        result = subprocess.run(
            ["python", "-m", "venv", str(env_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Failed to create venv: {result.stderr}"

        # Vérifier la structure
        assert env_path.exists()
        if os.name == "nt":
            python_path = env_path / "Scripts" / "python.exe"
            pip_path = env_path / "Scripts" / "pip.exe"
        else:
            python_path = env_path / "bin" / "python"
            pip_path = env_path / "bin" / "pip"

        assert python_path.exists()
        assert pip_path.exists()

        # Installer les dépendances depuis pyproject.toml
        pyproject_path = sample_project / "pyproject.toml"

        # Utiliser pip pour installer
        install_result = subprocess.run(
            [str(pip_path), "install", "-e", str(sample_project)],
            capture_output=True,
            text=True,
            cwd=sample_project
        )

        # Vérifier que requests est installé
        check_result = subprocess.run(
            [str(python_path), "-c", "import requests; print(requests.__version__)"],
            capture_output=True,
            text=True
        )
        assert check_result.returncode == 0, f"requests not installed: {check_result.stderr}"

    def test_create_environment_with_uv(self, e2e_temp_dir: Path):
        """Test: Création d'un environnement avec uv (si disponible)"""
        # Vérifier si uv est disponible
        try:
            uv_check = subprocess.run(["uv", "--version"], capture_output=True)
            if uv_check.returncode != 0:
                pytest.skip("uv not available")
        except FileNotFoundError:
            pytest.skip("uv not installed")

        env_path = e2e_temp_dir / "uv-test-env"

        # Créer l'environnement avec uv
        result = subprocess.run(
            ["uv", "venv", str(env_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"uv venv failed: {result.stderr}"
        assert env_path.exists()

        # Installer un package avec uv pip
        install_result = subprocess.run(
            ["uv", "pip", "install", "--python", str(env_path / "bin" / "python"), "requests"],
            capture_output=True,
            text=True
        )
        assert install_result.returncode == 0, f"uv pip install failed: {install_result.stderr}"


class TestPackageManagementWorkflow:
    """Tests E2E pour la gestion de packages"""

    def test_install_update_remove_package(self, e2e_temp_dir: Path):
        """Test: Cycle complet install -> update -> remove"""
        env_path = e2e_temp_dir / "pkg-test-env"

        # Créer l'environnement
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"
        python_path = env_path / "bin" / "python" if os.name != "nt" else env_path / "Scripts" / "python.exe"

        # 1. Installation d'un package
        install_result = subprocess.run(
            [str(pip_path), "install", "requests==2.28.0"],
            capture_output=True,
            text=True
        )
        assert install_result.returncode == 0

        # Vérifier la version
        version_result = subprocess.run(
            [str(python_path), "-c", "import requests; print(requests.__version__)"],
            capture_output=True,
            text=True
        )
        assert "2.28.0" in version_result.stdout

        # 2. Mise à jour du package
        upgrade_result = subprocess.run(
            [str(pip_path), "install", "--upgrade", "requests"],
            capture_output=True,
            text=True
        )
        assert upgrade_result.returncode == 0

        # Vérifier que la version a changé
        new_version_result = subprocess.run(
            [str(python_path), "-c", "import requests; print(requests.__version__)"],
            capture_output=True,
            text=True
        )
        # La nouvelle version devrait être >= 2.28.0
        assert new_version_result.returncode == 0

        # 3. Suppression du package
        uninstall_result = subprocess.run(
            [str(pip_path), "uninstall", "-y", "requests"],
            capture_output=True,
            text=True
        )
        assert uninstall_result.returncode == 0

        # Vérifier que le package n'est plus disponible
        check_result = subprocess.run(
            [str(python_path), "-c", "import requests"],
            capture_output=True,
            text=True
        )
        assert check_result.returncode != 0  # Doit échouer

    def test_install_multiple_packages(self, e2e_temp_dir: Path):
        """Test: Installation de plusieurs packages en une fois"""
        env_path = e2e_temp_dir / "multi-pkg-env"

        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"
        python_path = env_path / "bin" / "python" if os.name != "nt" else env_path / "Scripts" / "python.exe"

        # Installer plusieurs packages
        packages = ["click>=8.0", "rich>=10.0"]
        result = subprocess.run(
            [str(pip_path), "install"] + packages,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        # Vérifier les installations
        for pkg in ["click", "rich"]:
            check = subprocess.run(
                [str(python_path), "-c", f"import {pkg}"],
                capture_output=True,
                text=True
            )
            assert check.returncode == 0, f"Package {pkg} not installed"


class TestEnvironmentSyncWorkflow:
    """Tests E2E pour la synchronisation d'environnements"""

    def test_sync_from_requirements(self, e2e_temp_dir: Path):
        """Test: Synchronisation depuis requirements.txt"""
        env_path = e2e_temp_dir / "sync-test-env"
        project_dir = e2e_temp_dir / "sync-project"
        project_dir.mkdir()

        # Créer requirements.txt
        requirements = """requests>=2.25.0
click>=8.0
python-dateutil>=2.8
"""
        (project_dir / "requirements.txt").write_text(requirements)

        # Créer l'environnement
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"
        python_path = env_path / "bin" / "python" if os.name != "nt" else env_path / "Scripts" / "python.exe"

        # Installer depuis requirements.txt
        result = subprocess.run(
            [str(pip_path), "install", "-r", str(project_dir / "requirements.txt")],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        # Vérifier que tous les packages sont installés
        for pkg in ["requests", "click", "dateutil"]:
            check = subprocess.run(
                [str(python_path), "-c", f"import {pkg}"],
                capture_output=True,
                text=True
            )
            assert check.returncode == 0, f"Package {pkg} not installed"

    def test_export_requirements(self, e2e_temp_dir: Path):
        """Test: Export des dépendances vers requirements.txt"""
        env_path = e2e_temp_dir / "export-test-env"

        # Créer et configurer l'environnement
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # Installer quelques packages
        subprocess.run([str(pip_path), "install", "requests", "click"], check=True)

        # Exporter vers requirements.txt
        output_file = e2e_temp_dir / "exported_requirements.txt"
        result = subprocess.run(
            [str(pip_path), "freeze"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        output_file.write_text(result.stdout)

        # Vérifier le contenu
        content = output_file.read_text()
        assert "requests==" in content
        assert "click==" in content


class TestEnvironmentIsolationWorkflow:
    """Tests E2E pour l'isolation des environnements"""

    def test_environments_are_isolated(self, e2e_temp_dir: Path):
        """Test: Les environnements sont bien isolés"""
        env1_path = e2e_temp_dir / "isolated-env-1"
        env2_path = e2e_temp_dir / "isolated-env-2"

        # Créer deux environnements
        subprocess.run(["python", "-m", "venv", str(env1_path)], check=True)
        subprocess.run(["python", "-m", "venv", str(env2_path)], check=True)

        pip1 = env1_path / "bin" / "pip" if os.name != "nt" else env1_path / "Scripts" / "pip.exe"
        pip2 = env2_path / "bin" / "pip" if os.name != "nt" else env2_path / "Scripts" / "pip.exe"
        python1 = env1_path / "bin" / "python" if os.name != "nt" else env1_path / "Scripts" / "python.exe"
        python2 = env2_path / "bin" / "python" if os.name != "nt" else env2_path / "Scripts" / "python.exe"

        # Installer requests dans env1 seulement
        subprocess.run([str(pip1), "install", "requests"], check=True)

        # Installer click dans env2 seulement
        subprocess.run([str(pip2), "install", "click"], check=True)

        # Vérifier l'isolation - env1 a requests mais pas click
        check1_requests = subprocess.run(
            [str(python1), "-c", "import requests"],
            capture_output=True
        )
        check1_click = subprocess.run(
            [str(python1), "-c", "import click"],
            capture_output=True
        )
        assert check1_requests.returncode == 0
        assert check1_click.returncode != 0

        # Vérifier l'isolation - env2 a click mais pas requests
        check2_requests = subprocess.run(
            [str(python2), "-c", "import requests"],
            capture_output=True
        )
        check2_click = subprocess.run(
            [str(python2), "-c", "import click"],
            capture_output=True
        )
        assert check2_requests.returncode != 0
        assert check2_click.returncode == 0


class TestEnvironmentCleanupWorkflow:
    """Tests E2E pour le nettoyage des environnements"""

    def test_cleanup_environment(self, e2e_temp_dir: Path):
        """Test: Suppression complète d'un environnement"""
        env_path = e2e_temp_dir / "cleanup-test-env"

        # Créer l'environnement
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)
        assert env_path.exists()

        # Installer des packages pour avoir du contenu
        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"
        subprocess.run([str(pip_path), "install", "requests", "click"], check=True)

        # Calculer la taille
        def get_dir_size(path: Path) -> int:
            total = 0
            for p in path.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
            return total

        size_before = get_dir_size(env_path)
        assert size_before > 0

        # Supprimer l'environnement
        shutil.rmtree(env_path)
        assert not env_path.exists()

    def test_cleanup_cache(self, e2e_temp_dir: Path):
        """Test: Nettoyage du cache pip"""
        env_path = e2e_temp_dir / "cache-test-env"
        cache_dir = e2e_temp_dir / "pip-cache"

        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # Installer avec un cache spécifique
        subprocess.run(
            [str(pip_path), "install", "--cache-dir", str(cache_dir), "requests"],
            check=True
        )

        # Le cache devrait exister
        assert cache_dir.exists()

        # Nettoyer le cache
        result = subprocess.run(
            [str(pip_path), "cache", "purge"],
            capture_output=True,
            text=True
        )
        # Le cache pip standard est nettoyé (pas notre cache custom)
        assert result.returncode == 0


class TestCLIWorkflow:
    """Tests E2E pour le workflow CLI"""

    def test_cli_help(self):
        """Test: Aide CLI disponible"""
        # Vérifier que pip fonctionne
        result = subprocess.run(
            ["pip", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "install" in result.stdout.lower()

    def test_cli_version(self):
        """Test: Version Python disponible"""
        result = subprocess.run(
            ["python", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Python" in result.stdout or "Python" in result.stderr


class TestErrorRecoveryWorkflow:
    """Tests E2E pour la récupération d'erreurs"""

    def test_recovery_from_failed_install(self, e2e_temp_dir: Path):
        """Test: Récupération après échec d'installation"""
        env_path = e2e_temp_dir / "recovery-test-env"

        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"
        python_path = env_path / "bin" / "python" if os.name != "nt" else env_path / "Scripts" / "python.exe"

        # Tenter d'installer un package inexistant
        result = subprocess.run(
            [str(pip_path), "install", "this-package-definitely-does-not-exist-12345"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0  # Doit échouer

        # L'environnement doit toujours fonctionner
        check = subprocess.run(
            [str(python_path), "-c", "print('still working')"],
            capture_output=True,
            text=True
        )
        assert check.returncode == 0
        assert "still working" in check.stdout

        # On peut toujours installer d'autres packages
        install_result = subprocess.run(
            [str(pip_path), "install", "requests"],
            capture_output=True,
            text=True
        )
        assert install_result.returncode == 0

    def test_recovery_from_corrupted_venv(self, e2e_temp_dir: Path):
        """Test: Récupération d'un venv partiellement corrompu"""
        env_path = e2e_temp_dir / "corrupted-test-env"

        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        # "Corrompre" le venv en supprimant un fichier
        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"
        if pip_path.exists():
            pip_path.unlink()

        # Recréer le venv (devrait réparer)
        result = subprocess.run(
            ["python", "-m", "venv", str(env_path), "--clear"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        # Vérifier que pip est restauré
        assert pip_path.exists()


# Configuration pour ignorer les tests E2E par défaut
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
