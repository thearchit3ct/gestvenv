"""
Tests d'intégration de la gestion des packages
"""

import pytest
from gestvenv.core.models import PackageInfo, SyncResult

class TestPackageManagement:
    """Tests de gestion complète des packages"""
    
    def test_package_installation_workflow(self, env_manager):
        """Test workflow installation de packages"""
        # Création environnement
        result = env_manager.create_environment("pkg_test", python_version="3.11")
        env_info = result.environment
        
        # Installation package simple
        install_result = env_manager.package_service.install_package(
            env_info, "requests"
        )
        assert install_result.success
        assert install_result.package_info.name == "requests"
        
        # Installation avec version spécifique
        install_result = env_manager.package_service.install_package(
            env_info, "click==8.1.3"
        )
        assert install_result.success
        assert install_result.package_info.version == "8.1.3"
        
        # Installation multiple
        packages = ["pytest", "black", "flake8"]
        install_result = env_manager.package_service.install_packages(
            env_info, packages
        )
        assert install_result.success
        assert len(install_result.packages_info) == 3
    
    def test_package_update_workflow(self, env_manager):
        """Test workflow mise à jour packages"""
        result = env_manager.create_environment("update_test", python_version="3.11")
        env_info = result.environment
        
        # Installation version ancienne
        install_result = env_manager.package_service.install_package(
            env_info, "requests==2.25.0"
        )
        assert install_result.success
        
        # Mise à jour
        update_result = env_manager.package_service.update_package(
            env_info, "requests"
        )
        assert update_result.success
        
        # Vérification version mise à jour
        env_info_updated = env_manager.get_environment_info("update_test")
        requests_pkg = next(
            (pkg for pkg in env_info_updated.packages if pkg.name == "requests"),
            None
        )
        assert requests_pkg
        assert requests_pkg.version != "2.25.0"
    
    def test_package_removal_workflow(self, env_manager):
        """Test workflow suppression packages"""
        result = env_manager.create_environment("remove_test", python_version="3.11")
        env_info = result.environment
        
        # Installation packages
        packages = ["requests", "click", "pytest"]
        env_manager.package_service.install_packages(env_info, packages)
        
        # Suppression package
        remove_result = env_manager.package_service.remove_package(
            env_info, "pytest"
        )
        assert remove_result.success
        
        # Vérification suppression
        env_info_updated = env_manager.get_environment_info("remove_test")
        package_names = [pkg.name for pkg in env_info_updated.packages]
        assert "pytest" not in package_names
        assert "requests" in package_names
        assert "click" in package_names
    
    def test_dependency_resolution(self, env_manager):
        """Test résolution des dépendances"""
        result = env_manager.create_environment("deps_test", python_version="3.11")
        env_info = result.environment
        
        # Installation package avec dépendances
        install_result = env_manager.package_service.install_package(
            env_info, "flask"
        )
        assert install_result.success
        
        # Vérification dépendances installées
        env_info_updated = env_manager.get_environment_info("deps_test")
        package_names = [pkg.name for pkg in env_info_updated.packages]
        
        # Flask a des dépendances comme Werkzeug, Jinja2, etc.
        assert "flask" in package_names
        assert len(package_names) > 1  # Au moins Flask + ses dépendances
    
    def test_package_conflict_resolution(self, env_manager):
        """Test résolution des conflits de versions"""
        result = env_manager.create_environment("conflict_test", python_version="3.11")
        env_info = result.environment
        
        # Installation packages avec versions spécifiques
        env_manager.package_service.install_package(env_info, "requests==2.25.0")
        
        # Tentative installation package nécessitant version différente
        install_result = env_manager.package_service.install_package(
            env_info, "requests==2.28.0"
        )
        
        # Doit soit réussir avec mise à jour, soit échouer proprement
        if install_result.success:
            env_info_updated = env_manager.get_environment_info("conflict_test")
            requests_pkg = next(
                (pkg for pkg in env_info_updated.packages if pkg.name == "requests"),
                None
            )
            assert requests_pkg.version == "2.28.0"
        else:
            assert "conflit" in install_result.message.lower() or "conflict" in install_result.message.lower()
    
    def test_sync_with_pyproject_changes(self, env_manager, tmp_path):
        """Test synchronisation après modification pyproject.toml"""
        # Création pyproject.toml initial
        initial_content = '''[project]
name = "sync-test"
dependencies = ["requests>=2.25.0"]
'''
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(initial_content)
        
        # Création environnement
        result = env_manager.create_from_pyproject(
            pyproject_path=pyproject_path,
            env_name="sync_test"
        )
        env_info = result.environment
        
        # Modification pyproject.toml
        updated_content = '''[project]
name = "sync-test"
dependencies = ["requests>=2.25.0", "click>=8.0"]
'''
        pyproject_path.write_text(updated_content)
        
        # Synchronisation
        sync_result = env_manager.sync_environment("sync_test")
        assert sync_result.success
        
        # Vérification nouveau package installé
        env_info_updated = env_manager.get_environment_info("sync_test")
        package_names = [pkg.name for pkg in env_info_updated.packages]
        assert "click" in package_names