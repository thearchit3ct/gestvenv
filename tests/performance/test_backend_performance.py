"""
Tests de performance pour les backends GestVenv v2.0
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import asyncio

from gestvenv.backends import BackendType
from gestvenv.backends.backend_manager import BackendManager
from gestvenv.backends.pip_backend import PipBackend
from gestvenv.backends.uv_backend import UvBackend
from gestvenv.core.config_manager import ConfigManager


class TestBackendPerformance:
    """Tests de performance pour les différents backends"""
    
    @pytest.fixture
    def temp_env_path(self):
        """Crée un chemin temporaire pour l'environnement"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def config_manager(self):
        """Configuration manager pour les tests"""
        return ConfigManager()
    
    def measure_time(self, func, *args, **kwargs):
        """Mesure le temps d'exécution d'une fonction"""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return end - start, result
    
    async def measure_async_time(self, func, *args, **kwargs):
        """Mesure le temps d'exécution d'une fonction async"""
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        end = time.perf_counter()
        return end - start, result
    
    @pytest.mark.benchmark
    def test_environment_creation_performance(self, temp_env_path, config_manager):
        """Test de performance pour la création d'environnement"""
        backends = []
        
        # Test avec pip
        pip_backend = PipBackend(config_manager)
        if pip_backend.is_available():
            backends.append(("pip", pip_backend))
        
        # Test avec uv si disponible
        uv_backend = UvBackend(config_manager)
        if uv_backend.is_available():
            backends.append(("uv", uv_backend))
        
        results = {}
        
        for name, backend in backends:
            env_path = temp_env_path / f"env_{name}"
            duration, _ = self.measure_time(
                backend.create_environment,
                str(env_path),
                "3.11"
            )
            results[name] = duration
            
            # Cleanup
            shutil.rmtree(env_path, ignore_errors=True)
        
        # Vérifications de performance
        if "pip" in results:
            assert results["pip"] < 30.0, f"Pip trop lent: {results['pip']}s"
        
        if "uv" in results:
            assert results["uv"] < 5.0, f"UV trop lent: {results['uv']}s"
            
        # Si les deux sont disponibles, uv doit être plus rapide
        if "pip" in results and "uv" in results:
            assert results["uv"] < results["pip"], "UV devrait être plus rapide que pip"
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_package_installation_performance(self, temp_env_path, config_manager):
        """Test de performance pour l'installation de packages"""
        # Packages de test avec différentes tailles
        test_packages = {
            "small": ["requests"],
            "medium": ["django", "flask"],
            "large": ["pandas", "numpy", "matplotlib"]
        }
        
        uv_backend = UvBackend(config_manager)
        if not uv_backend.is_available():
            pytest.skip("UV backend non disponible")
        
        # Créer l'environnement
        env_path = temp_env_path / "test_env"
        uv_backend.create_environment(str(env_path), "3.11")
        
        results = {}
        
        for size, packages in test_packages.items():
            start = time.perf_counter()
            uv_backend.install_packages(str(env_path), packages)
            end = time.perf_counter()
            results[size] = end - start
        
        # Vérifications
        assert results["small"] < 10.0, f"Installation small trop lente: {results['small']}s"
        assert results["medium"] < 20.0, f"Installation medium trop lente: {results['medium']}s"
        assert results["large"] < 60.0, f"Installation large trop lente: {results['large']}s"
    
    @pytest.mark.benchmark
    def test_backend_manager_selection_performance(self, config_manager):
        """Test de performance pour la sélection automatique de backend"""
        manager = BackendManager(config_manager)
        
        # Mesurer le temps de détection
        duration, backend = self.measure_time(
            manager.get_best_backend,
            Path(".")
        )
        
        assert duration < 0.1, f"Détection de backend trop lente: {duration}s"
        assert backend is not None
    
    @pytest.mark.benchmark
    def test_parallel_environment_creation(self, temp_env_path, config_manager):
        """Test de création d'environnements en parallèle"""
        uv_backend = UvBackend(config_manager)
        if not uv_backend.is_available():
            pytest.skip("UV backend non disponible")
        
        num_envs = 5
        
        # Création séquentielle
        seq_start = time.perf_counter()
        for i in range(num_envs):
            env_path = temp_env_path / f"seq_env_{i}"
            uv_backend.create_environment(str(env_path), "3.11")
        seq_duration = time.perf_counter() - seq_start
        
        # Cleanup
        for i in range(num_envs):
            shutil.rmtree(temp_env_path / f"seq_env_{i}", ignore_errors=True)
        
        # Création parallèle avec asyncio
        async def create_env_async(i):
            env_path = temp_env_path / f"par_env_{i}"
            await asyncio.to_thread(
                uv_backend.create_environment,
                str(env_path),
                "3.11"
            )
        
        async def create_all_parallel():
            tasks = [create_env_async(i) for i in range(num_envs)]
            await asyncio.gather(*tasks)
        
        par_start = time.perf_counter()
        asyncio.run(create_all_parallel())
        par_duration = time.perf_counter() - par_start
        
        # Le parallèle devrait être plus rapide
        assert par_duration < seq_duration * 0.7, \
            f"Parallèle pas assez rapide: {par_duration}s vs {seq_duration}s"
    
    @pytest.mark.benchmark
    def test_dependency_resolution_performance(self, temp_env_path, config_manager):
        """Test de performance pour la résolution de dépendances"""
        uv_backend = UvBackend(config_manager)
        if not uv_backend.is_available():
            pytest.skip("UV backend non disponible")
        
        env_path = temp_env_path / "deps_env"
        uv_backend.create_environment(str(env_path), "3.11")
        
        # Package avec beaucoup de dépendances
        complex_packages = ["django[argon2]", "celery[redis]", "pytest-django"]
        
        duration, _ = self.measure_time(
            uv_backend.install_packages,
            str(env_path),
            complex_packages,
            capture_output=True
        )
        
        # Même avec des dépendances complexes, ça devrait être rapide
        assert duration < 30.0, f"Résolution trop lente: {duration}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])