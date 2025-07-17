"""
Tests de performance pour le système de cache GestVenv v2.0
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from gestvenv.services.cache_service import CacheService
from gestvenv.core.config_manager import ConfigManager


class TestCachePerformance:
    """Tests de performance pour le système de cache"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Crée un répertoire temporaire pour le cache"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def config_manager(self, temp_cache_dir):
        """Configuration manager pour les tests"""
        config = ConfigManager()
        config._config['cache_directory'] = str(temp_cache_dir)
        config._config['cache_enabled'] = True
        return config
    
    @pytest.fixture
    def cache_service(self, config_manager):
        """Service de cache pour les tests"""
        return CacheService(config_manager)
    
    def create_fake_package(self, name: str, size_mb: int) -> bytes:
        """Crée un faux package pour les tests"""
        # Génère des données pseudo-aléatoires
        data = (name * 1024).encode() * (size_mb * 1024)
        return data[:size_mb * 1024 * 1024]
    
    @pytest.mark.benchmark
    def test_cache_initialization_performance(self, config_manager):
        """Test de performance pour l'initialisation du cache"""
        start = time.perf_counter()
        cache = CacheService(config_manager)
        duration = time.perf_counter() - start
        
        assert duration < 0.1, f"Initialisation trop lente: {duration}s"
    
    @pytest.mark.benchmark
    def test_cache_write_performance(self, cache_service):
        """Test de performance pour l'écriture dans le cache"""
        # Test avec différentes tailles
        test_sizes = [
            ("small", 1),    # 1 MB
            ("medium", 10),  # 10 MB
        ]
        
        results = {}
        
        for name, size_mb in test_sizes:
            package_data = self.create_fake_package(name, size_mb)
            package_info = {
                "name": f"test_{name}",
                "version": "1.0.0",
                "size": len(package_data),
                "python_version": "3.11"
            }
            
            start = time.perf_counter()
            # Simule l'ajout au cache (méthode simplifiée)
            cache_path = cache_service.cache_dir / f"test_{name}-1.0.0.whl"
            cache_path.write_bytes(package_data)
            duration = time.perf_counter() - start
            
            results[name] = {
                "size_mb": size_mb,
                "duration": duration,
                "mb_per_sec": size_mb / duration if duration > 0 else float('inf')
            }
        
        # Vérifications
        assert results["small"]["mb_per_sec"] > 10, \
            "Écriture trop lente pour petits packages"
        assert results["medium"]["mb_per_sec"] > 5, \
            "Écriture trop lente pour packages moyens"
    
    @pytest.mark.benchmark
    def test_cache_cleanup_performance(self, cache_service):
        """Test de performance pour le nettoyage du cache"""
        # Créer plusieurs fichiers
        num_files = 50
        
        for i in range(num_files):
            file_path = cache_service.cache_dir / f"test_package_{i}.whl"
            file_path.write_bytes(b"dummy data")
        
        # Mesurer le temps de nettoyage
        start = time.perf_counter()
        # Simule un nettoyage
        for file in cache_service.cache_dir.glob("*.whl"):
            file.unlink()
        duration = time.perf_counter() - start
        
        assert duration < 1.0, f"Nettoyage trop lent: {duration}s pour {num_files} fichiers"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])