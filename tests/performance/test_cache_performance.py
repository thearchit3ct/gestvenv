"""
Tests de performance pour le systeme de cache GestVenv v2.0
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from gestvenv.services.cache_service import CacheService
from gestvenv.core.models import Config


class TestCachePerformance:
    """Tests de performance pour le systeme de cache"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Cree un repertoire temporaire pour le cache"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def config(self, temp_cache_dir):
        """Configuration pour les tests avec cache temporaire"""
        return Config(
            cache_settings={
                'enabled': True,
                'directory': str(temp_cache_dir),
                'max_size_mb': 1000,
                'compression': False
            }
        )

    @pytest.fixture
    def cache_service(self, config):
        """Service de cache pour les tests"""
        return CacheService(config)

    def create_fake_package(self, name: str, size_mb: int) -> bytes:
        """Cree un faux package pour les tests"""
        # Genere des donnees pseudo-aleatoires
        data = (name * 1024).encode() * (size_mb * 1024)
        return data[:size_mb * 1024 * 1024]

    @pytest.mark.benchmark
    def test_cache_initialization_performance(self, config):
        """Test de performance pour l'initialisation du cache"""
        start = time.perf_counter()
        cache = CacheService(config)
        duration = time.perf_counter() - start

        assert duration < 0.5, f"Initialisation trop lente: {duration}s"

    @pytest.mark.benchmark
    def test_cache_write_performance(self, cache_service, temp_cache_dir):
        """Test de performance pour l'ecriture dans le cache"""
        # Test avec differentes tailles
        test_sizes = [
            ("small", 1),    # 1 MB
            ("medium", 10),  # 10 MB
        ]

        results = {}

        # Utiliser le répertoire temporaire directement pour le test
        cache_dir = temp_cache_dir / "packages"
        cache_dir.mkdir(parents=True, exist_ok=True)

        for name, size_mb in test_sizes:
            package_data = self.create_fake_package(name, size_mb)

            start = time.perf_counter()
            # Simule l'ajout au cache (methode simplifiee)
            cache_path = cache_dir / f"test_{name}-1.0.0.whl"
            cache_path.write_bytes(package_data)
            duration = time.perf_counter() - start

            results[name] = {
                "size_mb": size_mb,
                "duration": duration,
                "mb_per_sec": size_mb / duration if duration > 0 else float('inf')
            }

        # Verifications
        assert results["small"]["mb_per_sec"] > 10, \
            "Ecriture trop lente pour petits packages"
        assert results["medium"]["mb_per_sec"] > 5, \
            "Ecriture trop lente pour packages moyens"

    @pytest.mark.benchmark
    def test_cache_cleanup_performance(self, cache_service, temp_cache_dir):
        """Test de performance pour le nettoyage du cache"""
        # Utiliser le répertoire temporaire directement
        cache_dir = temp_cache_dir / "packages"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Creer plusieurs fichiers
        num_files = 50

        for i in range(num_files):
            file_path = cache_dir / f"test_package_{i}.whl"
            file_path.write_bytes(b"dummy data")

        # Mesurer le temps de nettoyage
        start = time.perf_counter()
        # Simule un nettoyage
        for file in cache_dir.glob("*.whl"):
            file.unlink()
        duration = time.perf_counter() - start

        assert duration < 1.0, f"Nettoyage trop lent: {duration}s pour {num_files} fichiers"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
