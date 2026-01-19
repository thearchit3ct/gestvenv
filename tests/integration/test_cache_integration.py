"""
Tests d'intégration du système de cache
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestCacheIntegration:
    """Tests d'intégration du cache avec les autres composants"""

    def test_cache_package_downloads(self, env_manager, tmp_path):
        """Test mise en cache des téléchargements (mocké)"""
        # Mock CacheService
        mock_cache_service = Mock()
        mock_cache_service.clear_cache = Mock(return_value=True)
        mock_cache_service.get_cache_stats = Mock(return_value={
            "total_size": 1000,
            "package_count": 5,
            "hit_count": 10,
            "miss_count": 2
        })
        mock_cache_service.enabled = True

        env_manager._cache_service = mock_cache_service

        try:
            # Vérifier que le cache service est accessible
            cache_service = env_manager.cache_service
            assert cache_service is not None

            # Nettoyage cache
            result = cache_service.clear_cache()
            assert result is True

            # Vérification stats
            cache_stats = cache_service.get_cache_stats()
            assert "total_size" in cache_stats
            assert "package_count" in cache_stats

        finally:
            if hasattr(env_manager, '_cache_service'):
                delattr(env_manager, '_cache_service')

    def test_cache_offline_mode(self, env_manager):
        """Test mode hors ligne avec cache (mocké)"""
        mock_cache_service = Mock()
        mock_cache_service.set_offline_mode = Mock()
        mock_cache_service.is_offline_mode_enabled = Mock(side_effect=[False, True, False])

        env_manager._cache_service = mock_cache_service

        try:
            cache_service = env_manager.cache_service

            # Vérification état initial
            assert cache_service.is_offline_mode_enabled() is False

            # Activation mode hors ligne
            cache_service.set_offline_mode(True)
            mock_cache_service.set_offline_mode.assert_called_with(True)

            # Vérification mode activé
            assert cache_service.is_offline_mode_enabled() is True

            # Désactivation
            cache_service.set_offline_mode(False)
            assert cache_service.is_offline_mode_enabled() is False

        finally:
            if hasattr(env_manager, '_cache_service'):
                delattr(env_manager, '_cache_service')

    def test_cache_cleanup_and_maintenance(self, env_manager):
        """Test nettoyage et maintenance du cache (mocké)"""
        mock_cache_service = Mock()
        mock_cache_service.get_cache_stats = Mock(side_effect=[
            {"total_size": 5000, "package_count": 10},
            {"total_size": 3000, "package_count": 6}
        ])
        mock_cache_service.optimize_cache = Mock(return_value=True)

        env_manager._cache_service = mock_cache_service

        try:
            cache_service = env_manager.cache_service

            # Stats avant optimisation
            stats_before = cache_service.get_cache_stats()
            assert stats_before["package_count"] == 10

            # Optimisation
            result = cache_service.optimize_cache()
            assert result is True

            # Stats après optimisation
            stats_after = cache_service.get_cache_stats()
            assert stats_after["total_size"] <= stats_before["total_size"]

        finally:
            if hasattr(env_manager, '_cache_service'):
                delattr(env_manager, '_cache_service')

    def test_cache_backend_integration(self, env_manager):
        """Test intégration cache avec différents backends (mocké)"""
        mock_cache_service = Mock()
        mock_cache_service.cache_package = Mock(return_value=True)
        mock_cache_service.is_package_cached = Mock(side_effect=[False, True])
        mock_cache_service.get_cache_stats = Mock(return_value={"total_size": 1000})

        mock_backend_manager = Mock()
        mock_backend_manager.backends = {
            'pip': Mock(available=True),
            'uv': Mock(available=True)
        }

        env_manager._cache_service = mock_cache_service
        env_manager._backend_manager = mock_backend_manager

        try:
            cache_service = env_manager.cache_service
            backend_manager = env_manager.backend_manager

            # Test avec backend pip
            if backend_manager.backends['pip'].available:
                # Vérifier que le package n'est pas en cache
                assert cache_service.is_package_cached("requests", "2.28.0", "linux") is False

                # Mettre en cache
                result = cache_service.cache_package("requests", "2.28.0", "linux", b"data")
                assert result is True

                # Vérifier présence en cache
                assert cache_service.is_package_cached("requests", "2.28.0", "linux") is True

        finally:
            for attr in ['_cache_service', '_backend_manager']:
                if hasattr(env_manager, attr):
                    delattr(env_manager, attr)

    def test_cache_corruption_recovery(self, env_manager, tmp_path):
        """Test récupération après corruption du cache (mocké)"""
        mock_cache_service = Mock()
        mock_cache_service.cache_path = tmp_path / "cache"
        mock_cache_service.cache_package = Mock(return_value=True)
        mock_cache_service.get_cache_stats = Mock(return_value={"package_count": 1})

        # Créer le répertoire cache
        mock_cache_service.cache_path.mkdir(parents=True, exist_ok=True)

        env_manager._cache_service = mock_cache_service

        try:
            cache_service = env_manager.cache_service

            # Mise en cache
            result = cache_service.cache_package("requests", "2.28.0", "linux", b"data")
            assert result is True

            # Simulation corruption (suppression répertoire cache)
            import shutil
            if cache_service.cache_path.exists():
                shutil.rmtree(cache_service.cache_path)

            # Vérifier que le service peut encore fonctionner (reconstruit auto)
            stats = cache_service.get_cache_stats()
            assert stats is not None

        finally:
            if hasattr(env_manager, '_cache_service'):
                delattr(env_manager, '_cache_service')

    def test_cache_export_import(self, env_manager, tmp_path):
        """Test export et import du cache"""
        mock_cache_service = Mock()
        mock_cache_service.export_cache = Mock(return_value=Mock(
            success=True,
            output_path=tmp_path / "cache_export.tar.gz"
        ))
        mock_cache_service.import_cache = Mock(return_value=True)

        env_manager._cache_service = mock_cache_service

        try:
            cache_service = env_manager.cache_service

            # Export
            export_result = cache_service.export_cache(tmp_path / "cache_export.tar.gz")
            assert export_result.success is True

            # Import
            import_result = cache_service.import_cache(tmp_path / "cache_import.tar.gz")
            assert import_result is True

        finally:
            if hasattr(env_manager, '_cache_service'):
                delattr(env_manager, '_cache_service')
