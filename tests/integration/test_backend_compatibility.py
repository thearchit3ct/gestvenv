"""
Tests d'intégration de compatibilité entre backends
"""

import pytest
from unittest.mock import patch
from gestvenv.core.models import BackendType

class TestBackendCompatibility:
    """Tests de compatibilité et interopérabilité des backends"""
    
    def test_pip_backend_basic_workflow(self, env_manager):
        """Test workflow complet avec backend pip"""
        # Force utilisation backend pip
        result = env_manager.create_environment(
            name="pip_test",
            python_version="3.11",
            backend="pip"
        )
        
        assert result.success
        assert result.environment.backend_type == BackendType.PIP
        
        # Installation packages
        env_info = result.environment
        install_result = env_manager.package_service.install_package(
            env_info, "requests"
        )
        assert install_result.success
        
        # Mise à jour
        update_result = env_manager.package_service.update_package(
            env_info, "requests"
        )
        assert update_result.success
        
        # Export
        export_result = env_manager.export_environment("pip_test")
        assert export_result.success
    
    @pytest.mark.skipif(
        not pytest.importorskip("uv", reason="uv non disponible"),
        reason="uv backend non disponible"
    )
    def test_uv_backend_performance_workflow(self, env_manager):
        """Test workflow avec backend uv haute performance"""
        backend_manager = env_manager.backend_manager
        
        # Vérification disponibilité uv
        if not backend_manager.backends.get('uv', {}).get('available', False):
            pytest.skip("Backend uv non disponible")
        
        # Création avec uv
        result = env_manager.create_environment(
            name="uv_test",
            python_version="3.11",
            backend="uv"
        )
        
        assert result.success
        assert result.environment.backend_type == BackendType.UV
        
        # Installation rapide packages
        env_info = result.environment
        packages = ["requests", "click", "pytest"]
        
        install_result = env_manager.package_service.install_packages(
            env_info, packages
        )
        assert install_result.success
        assert len(install_result.packages_info) == 3
    
    def test_automatic_backend_selection(self, env_manager):
        """Test sélection automatique du backend optimal"""
        # Création avec auto-sélection
        result = env_manager.create_environment(
            name="auto_backend",
            python_version="3.11",
            backend="auto"
        )
        
        assert result.success
        
        # Vérification backend sélectionné
        env_info = result.environment
        backend_manager = env_manager.backend_manager
        
        # Si uv disponible, doit être sélectionné
        if backend_manager.backends.get('uv', {}).get('available', False):
            assert env_info.backend_type == BackendType.UV
        else:
            # Sinon fallback sur pip
            assert env_info.backend_type == BackendType.PIP
    
    def test_backend_migration_workflow(self, env_manager):
        """Test migration entre backends"""
        # Création avec pip
        result = env_manager.create_environment(
            name="migration_source",
            python_version="3.11", 
            backend="pip"
        )
        env_info = result.environment
        
        # Installation packages
        packages = ["requests", "click"]
        env_manager.package_service.install_packages(env_info, packages)
        
        # Export environnement
        export_result = env_manager.export_environment("migration_source")
        assert export_result.success
        
        # Création nouvel environnement avec backend différent
        backend_manager = env_manager.backend_manager
        target_backend = "uv" if backend_manager.backends.get('uv', {}).get('available', False) else "pip"
        
        if target_backend != "pip":  # Migration seulement si backend différent
            migrate_result = env_manager.migrate_environment_backend(
                source_env="migration_source",
                target_env="migration_target",
                target_backend=target_backend
            )
            
            assert migrate_result.success
            
            # Vérification migration
            target_env_info = env_manager.get_environment_info("migration_target")
            assert target_env_info.backend_type.value == target_backend
            
            # Vérification packages conservés
            source_packages = {pkg.name for pkg in env_info.packages}
            target_packages = {pkg.name for pkg in target_env_info.packages}
            assert source_packages.issubset(target_packages)
    
    def test_backend_fallback_mechanism(self, env_manager):
        """Test mécanisme de fallback entre backends"""
        backend_manager = env_manager.backend_manager
        
        # Simulation échec backend préféré
        with patch.object(backend_manager, 'get_preferred_backend') as mock_preferred:
            # Simulation uv non disponible
            mock_preferred.return_value = None
            
            # Création doit fallback sur pip
            result = env_manager.create_environment(
                name="fallback_test",
                python_version="3.11"
            )
            
            assert result.success
            assert result.environment.backend_type == BackendType.PIP
    
    def test_cross_backend_compatibility(self, env_manager, tmp_path):
        """Test compatibilité croisée formats de sortie"""
        # Création environnements avec backends différents
        environments = []
        
        # Environnement pip
        pip_result = env_manager.create_environment(
            name="cross_pip",
            python_version="3.11",
            backend="pip"
        )
        environments.append(("pip", pip_result.environment))
        
        # Environnement uv si disponible
        backend_manager = env_manager.backend_manager
        if backend_manager.backends.get('uv', {}).get('available', False):
            uv_result = env_manager.create_environment(
                name="cross_uv",
                python_version="3.11",
                backend="uv"
            )
            environments.append(("uv", uv_result.environment))
        
        # Installation packages identiques
        test_packages = ["requests", "click"]
        for backend_name, env_info in environments:
            for package in test_packages:
                install_result = env_manager.package_service.install_package(
                    env_info, package
                )
                assert install_result.success, f"Échec installation {package} avec {backend_name}"
        
        # Export dans formats compatibles
        for backend_name, env_info in environments:
            # Export requirements.txt
            req_export = env_manager.export_environment(
                env_info.name,
                format="requirements"
            )
            assert req_export.success
            
            # Export pyproject.toml
            pyproject_export = env_manager.export_environment(
                env_info.name,
                format="pyproject"
            )
            assert pyproject_export.success
            
            # Vérification contenu cohérent
            assert "requests" in req_export.data
            assert "click" in req_export.data
    
    def test_backend_specific_features(self, env_manager):
        """Test fonctionnalités spécifiques aux backends"""
        backend_manager = env_manager.backend_manager
        
        # Test capacités backend pip
        pip_backend = backend_manager.backends['pip']
        pip_capabilities = pip_backend.get_capabilities()
        
        assert pip_capabilities.supports_install
        assert pip_capabilities.supports_uninstall
        assert pip_capabilities.supports_update
        
        # Test capacités backend uv (si disponible)
        if backend_manager.backends.get('uv', {}).get('available', False):
            uv_backend = backend_manager.backends['uv']
            uv_capabilities = uv_backend.get_capabilities()
            
            assert uv_capabilities.supports_install
            assert uv_capabilities.supports_parallel_install  # Spécifique à uv
            assert uv_capabilities.supports_fast_resolver    # Spécifique à uv
            
            # Test performance comparative
            import time
            
            # Installation avec pip
            pip_env = env_manager.create_environment("perf_pip", backend="pip")
            start_time = time.time()
            env_manager.package_service.install_package(pip_env.environment, "requests")
            pip_time = time.time() - start_time
            
            # Installation avec uv
            uv_env = env_manager.create_environment("perf_uv", backend="uv")
            start_time = time.time()
            env_manager.package_service.install_package(uv_env.environment, "requests")
            uv_time = time.time() - start_time
            
            # uv doit être plus rapide (au moins pour installations répétées)
            assert uv_time <= pip_time * 1.5  # Tolérance pour variations système