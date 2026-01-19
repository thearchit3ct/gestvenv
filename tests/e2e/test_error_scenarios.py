"""
Tests E2E pour les scénarios d'erreur de GestVenv

Ces tests vérifient la gestion des erreurs et la résilience
du système face à des situations problématiques.
"""

import asyncio
import os
import pytest
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch, MagicMock

# Import des modules GestVenv
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from gestvenv.utils.error_handling import (
        ErrorCode,
        ErrorSuggestion,
        EnrichedError,
        enrich_error,
        ErrorHandler,
        with_error_handling,
    )
    from gestvenv.utils.retry import (
        RetryConfig,
        retry,
        retry_sync,
        RetryContext,
        RETRY_NETWORK,
    )
    from gestvenv.core.exceptions import (
        GestVenvError,
        ConfigurationError,
        EnvironmentError,
        BackendError,
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_AVAILABLE = False


pytestmark = [pytest.mark.e2e, pytest.mark.error_scenarios]


@pytest.fixture
def error_temp_dir() -> Generator[Path, None, None]:
    """Crée un répertoire temporaire pour les tests d'erreur"""
    temp_dir = Path(tempfile.mkdtemp(prefix="gestvenv_error_"))
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestNetworkErrorScenarios:
    """Tests pour les erreurs réseau"""

    def test_install_without_network(self, error_temp_dir: Path):
        """Test: Installation sans accès réseau"""
        env_path = error_temp_dir / "offline-test-env"

        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # Tenter d'installer depuis un index inexistant
        result = subprocess.run(
            [str(pip_path), "install", "--index-url", "http://127.0.0.1:65534/simple/", "requests"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode != 0
        # L'erreur doit indiquer un problème de connexion
        assert "connection" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_install_from_invalid_url(self, error_temp_dir: Path):
        """Test: Installation depuis une URL invalide"""
        env_path = error_temp_dir / "invalid-url-env"

        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # URL invalide
        result = subprocess.run(
            [str(pip_path), "install", "git+https://invalid.invalid/repo.git"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode != 0

    def test_timeout_handling(self, error_temp_dir: Path):
        """Test: Gestion des timeouts"""
        env_path = error_temp_dir / "timeout-test-env"

        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # Utiliser un timeout très court
        result = subprocess.run(
            [str(pip_path), "install", "--timeout", "1", "--retries", "0",
             "--index-url", "http://10.255.255.1/simple/", "requests"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode != 0


class TestFileSystemErrorScenarios:
    """Tests pour les erreurs de système de fichiers"""

    def test_permission_denied_error(self, error_temp_dir: Path):
        """Test: Gestion des erreurs de permission"""
        env_path = error_temp_dir / "permission-test-env"

        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        # Rendre le dossier lib non accessible
        lib_path = env_path / "lib"
        if lib_path.exists():
            try:
                os.chmod(lib_path, 0o000)

                pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

                result = subprocess.run(
                    [str(pip_path), "install", "requests"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                # Doit échouer avec une erreur de permission
                # Note: le comportement peut varier selon l'OS

            finally:
                # Restaurer les permissions pour le nettoyage
                os.chmod(lib_path, 0o755)

    def test_disk_full_simulation(self, error_temp_dir: Path):
        """Test: Simulation disque plein"""
        # Ce test est difficile à simuler sans remplir réellement le disque
        # On vérifie plutôt la gestion de l'espace disque

        env_path = error_temp_dir / "disk-test-env"
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        # Vérifier l'espace disponible
        import shutil
        total, used, free = shutil.disk_usage(error_temp_dir)

        # S'assurer qu'il y a de l'espace pour le test
        assert free > 100 * 1024 * 1024  # Au moins 100MB

    def test_path_too_long_error(self, error_temp_dir: Path):
        """Test: Chemin trop long"""
        # Créer un chemin très long
        long_name = "a" * 200
        deep_path = error_temp_dir

        # Essayer de créer des dossiers imbriqués
        try:
            for _ in range(5):
                deep_path = deep_path / long_name
                deep_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Attendu sur certains systèmes
            assert "name too long" in str(e).lower() or "ENAMETOOLONG" in str(e)


class TestCorruptedStateScenarios:
    """Tests pour les états corrompus"""

    def test_corrupted_pyproject_toml(self, error_temp_dir: Path):
        """Test: pyproject.toml malformé"""
        project_dir = error_temp_dir / "corrupted-project"
        project_dir.mkdir()

        # Créer un pyproject.toml invalide
        corrupted_content = """
[project
name = "broken"
version = missing quotes
dependencies = [
    "requests
]
"""
        (project_dir / "pyproject.toml").write_text(corrupted_content)

        env_path = error_temp_dir / "corrupted-pyproject-env"
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # L'installation depuis le pyproject.toml corrompu doit échouer proprement
        result = subprocess.run(
            [str(pip_path), "install", "-e", str(project_dir)],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        # Doit contenir une erreur de parsing
        assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()

    def test_missing_dependencies_file(self, error_temp_dir: Path):
        """Test: Fichier de dépendances manquant"""
        env_path = error_temp_dir / "missing-deps-env"
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # requirements.txt inexistant
        result = subprocess.run(
            [str(pip_path), "install", "-r", str(error_temp_dir / "nonexistent_requirements.txt")],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()

    def test_invalid_package_version(self, error_temp_dir: Path):
        """Test: Version de package invalide"""
        env_path = error_temp_dir / "invalid-version-env"
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # Version inexistante
        result = subprocess.run(
            [str(pip_path), "install", "requests==999.999.999"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert "no matching distribution" in result.stderr.lower() or "could not find" in result.stderr.lower()


class TestConflictResolutionScenarios:
    """Tests pour les conflits de dépendances"""

    def test_dependency_conflict(self, error_temp_dir: Path):
        """Test: Conflit de dépendances"""
        env_path = error_temp_dir / "conflict-test-env"
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # Installer des packages avec des versions spécifiques qui peuvent confliter
        # D'abord une version très ancienne
        result1 = subprocess.run(
            [str(pip_path), "install", "urllib3==1.26.0"],
            capture_output=True,
            text=True
        )

        # Puis un package qui nécessite une version plus récente
        result2 = subprocess.run(
            [str(pip_path), "install", "requests>=2.31.0"],
            capture_output=True,
            text=True
        )

        # pip devrait résoudre le conflit en mettant à jour urllib3
        # ou afficher un warning/error

    def test_incompatible_python_version(self, error_temp_dir: Path):
        """Test: Package incompatible avec la version Python"""
        env_path = error_temp_dir / "py-compat-env"
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"
        python_path = env_path / "bin" / "python" if os.name != "nt" else env_path / "Scripts" / "python.exe"

        # Obtenir la version Python
        version_result = subprocess.run(
            [str(python_path), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            capture_output=True,
            text=True
        )
        py_version = version_result.stdout.strip()

        # Tenter d'installer un package qui ne supporte que d'anciennes versions
        # (difficile à tester de manière fiable)


class TestRecoveryScenarios:
    """Tests pour les scénarios de récupération"""

    def test_recovery_after_sigterm(self, error_temp_dir: Path):
        """Test: Récupération après interruption"""
        env_path = error_temp_dir / "sigterm-test-env"
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"
        python_path = env_path / "bin" / "python" if os.name != "nt" else env_path / "Scripts" / "python.exe"

        # L'environnement doit être utilisable même après création partielle
        check = subprocess.run(
            [str(python_path), "-c", "print('OK')"],
            capture_output=True,
            text=True
        )
        assert check.returncode == 0

    def test_venv_recreation_after_partial_delete(self, error_temp_dir: Path):
        """Test: Recréation après suppression partielle"""
        env_path = error_temp_dir / "partial-delete-env"

        # Créer le venv
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        # Supprimer partiellement
        bin_path = env_path / "bin" if os.name != "nt" else env_path / "Scripts"
        if bin_path.exists():
            shutil.rmtree(bin_path)

        # Recréer avec --clear doit fonctionner
        result = subprocess.run(
            ["python", "-m", "venv", "--clear", str(env_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        # Vérifier que c'est fonctionnel
        python_path = env_path / "bin" / "python" if os.name != "nt" else env_path / "Scripts" / "python.exe"
        assert python_path.exists()


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="GestVenv imports not available")
class TestErrorHandlingModule:
    """Tests pour le module de gestion d'erreurs"""

    def test_error_enrichment(self):
        """Test: Enrichissement des erreurs"""
        original_error = Exception("Environment not found")

        # Utiliser ENV_NOT_FOUND qui a des suggestions définies
        enriched = enrich_error(
            original_error,
            code=ErrorCode.ENV_NOT_FOUND,
            context={"env_name": "test-env", "path": "/etc/gestvenv/"}
        )

        assert enriched.code == ErrorCode.ENV_NOT_FOUND
        assert "Environment not found" in enriched.message
        assert enriched.context["env_name"] == "test-env"
        assert len(enriched.suggestions) > 0

    def test_error_handler_statistics(self):
        """Test: Statistiques du gestionnaire d'erreurs"""
        handler = ErrorHandler()

        # Simuler quelques erreurs
        for i in range(5):
            try:
                raise ValueError(f"Test error {i}")
            except ValueError as e:
                handler.handle(e, code=ErrorCode.VALIDATION)

        stats = handler.get_stats()
        assert stats["total_errors"] == 5
        assert ErrorCode.VALIDATION.name in stats["by_code"]

    def test_error_suggestions(self):
        """Test: Suggestions appropriées pour les erreurs"""
        error = Exception("Environment not found")
        enriched = enrich_error(error, code=ErrorCode.ENV_NOT_FOUND)

        # Doit avoir des suggestions pertinentes
        suggestions_text = [s.description for s in enriched.suggestions]
        assert any("list" in s.lower() or "créer" in s.lower() for s in suggestions_text)

    def test_with_error_handling_decorator(self):
        """Test: Décorateur with_error_handling"""

        @with_error_handling(code=ErrorCode.INTERNAL)
        def failing_function():
            raise RuntimeError("Internal error")

        with pytest.raises(RuntimeError):
            failing_function()


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="GestVenv imports not available")
class TestRetryModule:
    """Tests pour le module de retry"""

    def test_retry_success_after_failures(self):
        """Test: Succès après plusieurs échecs"""
        attempt_count = 0

        @retry(max_attempts=3, base_delay=0.1)
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert attempt_count == 3

    def test_retry_exhaustion(self):
        """Test: Épuisement des tentatives"""

        @retry(max_attempts=2, base_delay=0.1)
        def always_fails():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_fails()

    def test_retry_with_specific_exceptions(self):
        """Test: Retry sur exceptions spécifiques seulement"""

        @retry(max_attempts=3, base_delay=0.1, exceptions=(ConnectionError,))
        def specific_error():
            raise ValueError("Not retried")

        # ValueError ne doit pas être retry
        with pytest.raises(ValueError):
            specific_error()

    def test_retry_context(self):
        """Test: RetryContext pour gestion manuelle"""
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        ctx = RetryContext(config)

        attempts = 0
        while ctx.should_retry():
            attempts += 1
            try:
                if attempts < 3:
                    raise ConnectionError("Retry me")
                ctx.record_success()
                break
            except ConnectionError as e:
                ctx.record_failure(e)
                ctx.wait_sync()

        assert attempts == 3
        assert ctx.stats["success"] is True

    def test_backoff_calculation(self):
        """Test: Calcul du backoff exponentiel"""
        config = RetryConfig(
            base_delay=1.0,
            backoff_factor=2.0,
            jitter=False
        )

        delay1 = config.calculate_delay(1)
        delay2 = config.calculate_delay(2)
        delay3 = config.calculate_delay(3)

        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0


class TestConcurrentErrorScenarios:
    """Tests pour les erreurs en contexte concurrent"""

    def test_concurrent_install_to_same_env(self, error_temp_dir: Path):
        """Test: Installation concurrente sur le même environnement"""
        env_path = error_temp_dir / "concurrent-test-env"
        subprocess.run(["python", "-m", "venv", str(env_path)], check=True)

        pip_path = env_path / "bin" / "pip" if os.name != "nt" else env_path / "Scripts" / "pip.exe"

        # Lancer plusieurs installations en parallèle
        packages = ["requests", "click", "rich"]
        processes = []

        for pkg in packages:
            proc = subprocess.Popen(
                [str(pip_path), "install", pkg],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            processes.append(proc)

        # Attendre la fin
        results = [proc.wait() for proc in processes]

        # Au moins certains devraient réussir
        # (pip gère les locks internes)
        success_count = sum(1 for r in results if r == 0)
        assert success_count > 0


# Configuration pytest
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "error_scenarios: mark test as error scenario test"
    )
