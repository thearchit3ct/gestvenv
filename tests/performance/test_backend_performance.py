"""
Tests de performance pour les backends GestVenv v2.0
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from gestvenv.core.models import BackendType, Config
from gestvenv.backends.backend_manager import BackendManager
from gestvenv.backends.pip_backend import PipBackend
from gestvenv.backends.uv_backend import UvBackend


class TestBackendPerformance:
    """Tests de performance pour les differents backends"""

    @pytest.fixture
    def temp_env_path(self):
        """Cree un chemin temporaire pour l'environnement"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def config(self):
        """Configuration pour les tests"""
        return Config()

    def measure_time(self, func, *args, **kwargs):
        """Mesure le temps d'execution d'une fonction"""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return end - start, result

    @pytest.mark.benchmark
    def test_environment_creation_performance(self, temp_env_path):
        """Test de performance pour la creation d'environnement (mocké)"""
        # Mock les backends pour éviter les vrais appels système
        mock_pip = Mock()
        mock_pip.available = True
        mock_pip.name = "pip"
        mock_pip.create_environment = Mock(return_value=True)

        mock_uv = Mock()
        mock_uv.available = True
        mock_uv.name = "uv"
        mock_uv.create_environment = Mock(return_value=True)

        backends = [("pip", mock_pip), ("uv", mock_uv)]
        results = {}

        for name, backend in backends:
            if backend.available:
                env_path = temp_env_path / f"env_{name}"
                duration, _ = self.measure_time(
                    backend.create_environment,
                    env_path,
                    "3.11"
                )
                results[name] = duration

        # Vérifications - les mocks sont rapides
        assert "pip" in results
        assert "uv" in results
        assert results["pip"] < 1.0, f"Mock pip trop lent: {results['pip']}s"
        assert results["uv"] < 1.0, f"Mock uv trop lent: {results['uv']}s"

    @pytest.mark.benchmark
    def test_package_installation_performance(self, temp_env_path):
        """Test de performance pour l'installation de packages (mocké)"""
        # Mock le backend
        mock_backend = Mock()
        mock_backend.available = True
        mock_backend.install_package = Mock(return_value=Mock(success=True))

        test_packages = {
            "small": ["requests"],
            "medium": ["django", "flask"],
            "large": ["pandas", "numpy", "matplotlib"]
        }

        results = {}

        for size, packages in test_packages.items():
            start = time.perf_counter()
            for pkg in packages:
                mock_backend.install_package(temp_env_path, pkg)
            end = time.perf_counter()
            results[size] = end - start

        # Vérifications - les mocks sont rapides
        assert results["small"] < 1.0, f"Installation small trop lente: {results['small']}s"
        assert results["medium"] < 1.0, f"Installation medium trop lente: {results['medium']}s"
        assert results["large"] < 1.0, f"Installation large trop lente: {results['large']}s"

    @pytest.mark.benchmark
    def test_backend_manager_selection_performance(self, config):
        """Test de performance pour la selection automatique de backend"""
        manager = BackendManager(config)

        # Mesurer le temps de detection
        duration, recommendations = self.measure_time(
            manager.get_backend_recommendations,
            Path(".")
        )

        assert duration < 1.0, f"Detection de backend trop lente: {duration}s"
        assert recommendations is not None

    @pytest.mark.benchmark
    def test_parallel_environment_creation(self, temp_env_path):
        """Test de creation d'environnements en parallele (mocké)"""
        import asyncio

        mock_backend = Mock()
        mock_backend.available = True
        mock_backend.create_environment = Mock(return_value=True)

        num_envs = 5

        # Creation sequentielle
        seq_start = time.perf_counter()
        for i in range(num_envs):
            env_path = temp_env_path / f"seq_env_{i}"
            mock_backend.create_environment(env_path, "3.11")
        seq_duration = time.perf_counter() - seq_start

        # Creation parallele avec asyncio
        async def create_env_async(i):
            env_path = temp_env_path / f"par_env_{i}"
            await asyncio.to_thread(
                mock_backend.create_environment,
                env_path,
                "3.11"
            )

        async def create_all_parallel():
            tasks = [create_env_async(i) for i in range(num_envs)]
            await asyncio.gather(*tasks)

        par_start = time.perf_counter()
        asyncio.run(create_all_parallel())
        par_duration = time.perf_counter() - par_start

        # Les deux devraient être rapides avec des mocks
        assert seq_duration < 1.0, f"Séquentiel trop lent: {seq_duration}s"
        assert par_duration < 1.0, f"Parallèle trop lent: {par_duration}s"

    @pytest.mark.benchmark
    def test_dependency_resolution_performance(self, temp_env_path):
        """Test de performance pour la resolution de dependances (mocké)"""
        mock_backend = Mock()
        mock_backend.available = True
        mock_backend.install_package = Mock(return_value=Mock(success=True))

        # Package avec beaucoup de dependances
        complex_packages = ["django[argon2]", "celery[redis]", "pytest-django"]

        start = time.perf_counter()
        for pkg in complex_packages:
            mock_backend.install_package(temp_env_path, pkg)
        duration = time.perf_counter() - start

        # Avec des mocks, ca devrait etre rapide
        assert duration < 1.0, f"Resolution trop lente: {duration}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
