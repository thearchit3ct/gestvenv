"""
Tests d'intégration du système de cache
"""

import pytest
import time
from pathlib import Path

class TestCacheIntegration:
    """Tests d'intégration du cache avec les autres composants"""
    
    def test_cache_package_downloads(self, env_manager):
        """Test mise en cache des téléchargements"""
        cache_service = env_manager.cache_service
        
        # Nettoyage cache initial
        cache_service.clear_cache()
        
        # Première installation (téléchargement)
        result = env_manager.create_environment("cache_test1", python_version="3.11")
        env_info = result.environment
        
        start_time = time.time()
        install_result = env_manager.package_service.install_package(
            env_info, "requests"
        )
        first_install_time = time.time() - start_time
        
        assert install_result.success
        
        # Vérification présence en cache
        cache_info = cache_service.get_cache_info()
        assert cache_info.total_size > 0
        assert cache_info.package_count > 0
        
        # Deuxième installation (depuis cache)
        result2 = env_manager.create_environment("cache_test2", python_version="3.11")
        env_info2 = result2.environment
        
        start_time = time.time()
        install_result2 = env_manager.package_service.install_package(
            env_info2, "requests"
        )
        second_install_time = time.time() - start_time
        
        assert install_result2.success
        # Deuxième installation doit être plus rapide (cache hit)
        assert second_install_time < first_install_time * 0.8
    
    def test_cache_offline_mode(self, env_manager):
        """Test mode hors ligne avec cache"""
        cache_service = env_manager.cache_service
        
        # Installation avec connexion
        result = env_manager.create_environment("offline_prep", python_version="3.11")
        env_info = result.environment
        
        install_result = env_manager.package_service.install_package(
            env_info, "click"
        )
        assert install_result.success
        
        # Activation mode hors ligne
        cache_service.enable_offline_mode()
        
        try:
            # Création nouvel environnement en mode hors ligne
            result2 = env_manager.create_environment("offline_test", python_version="3.11")
            env_info2 = result2.environment
            
            # Installation depuis cache
            install_result2 = env_manager.package_service.install_package(
                env_info2, "click"
            )
            assert install_result2.success
            
        finally:
            cache_service.disable_offline_mode()
    
    def test_cache_cleanup_and_maintenance(self, env_manager):
        """Test nettoyage et maintenance du cache"""
        cache_service = env_manager.cache_service
        
        # Installation plusieurs packages pour remplir cache
        result = env_manager.create_environment("cleanup_test", python_version="3.11")
        env_info = result.environment
        
        packages = ["requests", "click", "pytest", "black"]
        for package in packages:
            env_manager.package_service.install_package(env_info, package)
        
        # Vérification cache rempli
        cache_info_before = cache_service.get_cache_info()
        assert cache_info_before.package_count >= 4
        
        # Nettoyage partiel (anciens packages)
        cleanup_result = cache_service.cleanup_old_packages(days=0)
        assert cleanup_result.success
        
        # Vérification cache partiellement nettoyé
        cache_info_after = cache_service.get_cache_info()
        assert cache_info_after.total_size <= cache_info_before.total_size
    
    def test_cache_backend_integration(self, env_manager):
        """Test intégration cache avec différents backends"""
        cache_service = env_manager.cache_service
        backend_manager = env_manager.backend_manager
        
        # Test avec backend pip
        if backend_manager.backends['pip'].available:
            result = env_manager.create_environment(
                "cache_pip", 
                python_version="3.11",
                backend="pip"
            )
            env_info = result.environment
            
            install_result = env_manager.package_service.install_package(
                env_info, "requests"
            )
            assert install_result.success
            
            cache_info_pip = cache_service.get_cache_info()
            assert cache_info_pip.total_size > 0
        
        # Test avec backend uv (si disponible)
        if backend_manager.backends.get('uv', {}).get('available', False):
            result = env_manager.create_environment(
                "cache_uv",
                python_version="3.11", 
                backend="uv"
            )
            env_info = result.environment
            
            install_result = env_manager.package_service.install_package(
                env_info, "click"
            )
            assert install_result.success
            
            cache_info_uv = cache_service.get_cache_info()
            assert cache_info_uv.total_size > cache_info_pip.total_size
    
    def test_cache_corruption_recovery(self, env_manager):
        """Test récupération après corruption du cache"""
        cache_service = env_manager.cache_service
        
        # Installation normale
        result = env_manager.create_environment("corruption_test", python_version="3.11")
        env_info = result.environment
        
        install_result = env_manager.package_service.install_package(
            env_info, "requests"
        )
        assert install_result.success
        
        # Simulation corruption cache (suppression fichiers)
        cache_dir = cache_service.cache_path
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
        
        # Tentative utilisation avec cache corrompu
        result2 = env_manager.create_environment("recovery_test", python_version="3.11")
        env_info2 = result2.environment
        
        # Doit récupérer automatiquement
        install_result2 = env_manager.package_service.install_package(
            env_info2, "requests"
        )
        assert install_result2.success
        
        # Vérification cache reconstruit
        cache_info = cache_service.get_cache_info()
        assert cache_info.package_count > 0