"""
Service de gestion des packages pour GestVenv v1.1
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from ..core.models import (
    EnvironmentInfo,
    PackageInfo,
    InstallResult,
    SyncResult,
    PyProjectInfo
)
from ..core.exceptions import (
    PackageInstallationError,
    BackendError,
    ValidationError
)
from ..backends.base import PackageBackend
from ..backends.backend_manager import BackendManager

logger = logging.getLogger(__name__)


class PackageService:
    """Service unifié de gestion des packages"""
    
    def __init__(self, backend_manager: BackendManager, cache_service=None):
        self.backend_manager = backend_manager
        self.cache_service = cache_service
        
    def install_package(
        self, 
        env: EnvironmentInfo, 
        package: str, 
        **kwargs
    ) -> InstallResult:
        """Installation avec backend optimal et cache"""
        start_time = time.time()
        
        try:
            # Validation package
            self._validate_package_specification(package)
            
            # Sélection backend
            backend = self._get_backend_for_env(env)
            
            # Tentative cache en mode hors ligne
            if self.cache_service and self.cache_service.is_offline_mode_enabled():
                cache_result = self.cache_service.install_from_cache(env, package)
                if cache_result.success:
                    return InstallResult(
                        success=True,
                        message=f"Package {package} installé depuis le cache",
                        packages_installed=[package],
                        backend_used="cache",
                        execution_time=time.time() - start_time
                    )
            
            # Installation normale
            result = backend.install_package(env.path, package, **kwargs)
            
            if result.success:
                # Mise en cache si activé
                if self.cache_service:
                    self.cache_service.cache_installed_package(env, package)
                
                # Mise à jour environnement
                env.packages = backend.list_packages(env.path)
                env.updated_at = time.time()
                
                return InstallResult(
                    success=True,
                    message=f"Package {package} installé avec succès",
                    packages_installed=[package],
                    backend_used=backend.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Échec installation {package}: {result.message}",
                    packages_failed=[package],
                    backend_used=backend.name,
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Erreur installation {package}: {e}")
            return InstallResult(
                success=False,
                message=f"Erreur installation: {e}",
                packages_failed=[package],
                execution_time=time.time() - start_time
            )
    
    def uninstall_package(self, env: EnvironmentInfo, package: str) -> bool:
        """Désinstalle un package"""
        try:
            backend = self._get_backend_for_env(env)
            success = backend.uninstall_package(env.path, package)
            
            if success:
                # Mise à jour environnement
                env.packages = backend.list_packages(env.path)
                env.updated_at = time.time()
            
            return success
        except Exception as e:
            logger.error(f"Erreur désinstallation {package}: {e}")
            return False
    
    def update_package(self, env: EnvironmentInfo, package: str) -> bool:
        """Met à jour un package"""
        try:
            backend = self._get_backend_for_env(env)
            success = backend.update_package(env.path, package)
            
            if success:
                env.packages = backend.list_packages(env.path)
                env.updated_at = time.time()
            
            return success
        except Exception as e:
            logger.error(f"Erreur mise à jour {package}: {e}")
            return False
    
    def list_packages(self, env: EnvironmentInfo) -> List[PackageInfo]:
        """Liste les packages installés"""
        try:
            backend = self._get_backend_for_env(env)
            return backend.list_packages(env.path)
        except Exception as e:
            logger.error(f"Erreur listage packages: {e}")
            return []
    
    def install_from_requirements(self, env: EnvironmentInfo, req_path: Path) -> bool:
        """Installation depuis requirements.txt"""
        try:
            if not req_path.exists():
                raise FileNotFoundError(f"Fichier requirements.txt introuvable: {req_path}")
            
            backend = self._get_backend_for_env(env)
            
            if hasattr(backend, 'install_from_requirements'):
                success = backend.install_from_requirements(env.path, req_path)
            else:
                # Installation manuelle ligne par ligne
                success = self._manual_requirements_install(env, req_path, backend)
            
            if success:
                env.packages = backend.list_packages(env.path)
                env.updated_at = time.time()
            
            return success
        except Exception as e:
            logger.error(f"Erreur installation requirements: {e}")
            return False
    
    def install_from_pyproject(
        self, 
        env: EnvironmentInfo, 
        pyproject: PyProjectInfo, 
        groups: Optional[List[str]] = None
    ) -> bool:
        """Installation depuis pyproject.toml"""
        try:
            backend = self._get_backend_for_env(env)
            
            # Support natif pyproject.toml
            if hasattr(backend, 'sync_from_pyproject') and pyproject.source_path:
                success = backend.sync_from_pyproject(
                    env.path, 
                    pyproject.source_path, 
                    groups
                )
            else:
                # Installation manuelle des dépendances
                success = self._manual_pyproject_install(env, pyproject, groups, backend)
            
            if success:
                env.packages = backend.list_packages(env.path)
                env.updated_at = time.time()
            
            return success
        except Exception as e:
            logger.error(f"Erreur installation pyproject: {e}")
            return False
    
    def sync_environment(self, env: EnvironmentInfo) -> SyncResult:
        """Synchronise l'environnement avec son pyproject.toml"""
        start_time = time.time()
        
        try:
            if not env.pyproject_info:
                return SyncResult(
                    success=False,
                    message="Aucun pyproject.toml associé",
                    execution_time=time.time() - start_time
                )
            
            backend = self._get_backend_for_env(env)
            
            # Analyse des différences
            current_packages = {pkg.name: pkg.version for pkg in env.packages}
            expected_deps = env.pyproject_info.extract_dependencies()
            expected_packages = {
                dep.split('>=')[0].split('==')[0].split('[')[0]: dep
                for dep in expected_deps
            }
            
            packages_to_add = []
            packages_to_remove = []
            packages_to_update = []
            
            # Packages à ajouter
            for pkg_name, pkg_spec in expected_packages.items():
                if pkg_name not in current_packages:
                    packages_to_add.append(pkg_spec)
            
            # Packages à supprimer (qui ne sont plus dans pyproject.toml)
            for pkg_name in current_packages:
                if pkg_name not in expected_packages:
                    packages_to_remove.append(pkg_name)
            
            # Installation/suppression
            warnings = []
            
            for package in packages_to_add:
                install_result = self.install_package(env, package)
                if not install_result.success:
                    warnings.append(f"Échec installation {package}")
            
            for package in packages_to_remove:
                if not self.uninstall_package(env, package):
                    warnings.append(f"Échec suppression {package}")
            
            return SyncResult(
                success=True,
                message="Synchronisation terminée",
                packages_added=packages_to_add,
                packages_removed=packages_to_remove,
                packages_updated=packages_to_update,
                warnings=warnings,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"Erreur synchronisation: {e}",
                execution_time=time.time() - start_time
            )
    
    def create_lock_file(self, env: EnvironmentInfo) -> Optional[Path]:
        """Crée un fichier de verrouillage"""
        try:
            backend = self._get_backend_for_env(env)
            
            if hasattr(backend, 'create_lock_file') and env.pyproject_info:
                return backend.create_lock_file(env.pyproject_info.source_path)
            
            return None
        except Exception as e:
            logger.error(f"Erreur création lock file: {e}")
            return None
    
    def install_from_lock(self, env: EnvironmentInfo, lock_path: Path) -> bool:
        """Installation depuis fichier de verrouillage"""
        try:
            backend = self._get_backend_for_env(env)
            
            if hasattr(backend, 'install_from_lock'):
                success = backend.install_from_lock(env.path, lock_path)
                
                if success:
                    env.packages = backend.list_packages(env.path)
                    env.updated_at = time.time()
                
                return success
            
            return False
        except Exception as e:
            logger.error(f"Erreur installation lock: {e}")
            return False
    
    def check_outdated_packages(self, env: EnvironmentInfo) -> List[PackageInfo]:
        """Vérifie les packages obsolètes"""
        try:
            # Implémentation simplifiée - peut être améliorée
            # avec vérification réelle des versions sur PyPI
            outdated = []
            
            for package in env.packages:
                # Logique de vérification (à implémenter selon le backend)
                if hasattr(package, 'is_outdated') and package.is_outdated():
                    outdated.append(package)
            
            return outdated
        except Exception as e:
            logger.error(f"Erreur vérification packages obsolètes: {e}")
            return []
    
    def resolve_dependencies(self, packages: List[str]) -> Dict[str, str]:
        """Résout les dépendances"""
        try:
            # Implémentation simplifiée
            # Dans une vraie implémentation, utiliser un resolver de dépendances
            resolved = {}
            for package in packages:
                pkg_name = package.split('>=')[0].split('==')[0].split('[')[0]
                resolved[pkg_name] = package
            
            return resolved
        except Exception as e:
            logger.error(f"Erreur résolution dépendances: {e}")
            return {}
    
    def _get_backend_for_env(self, env: EnvironmentInfo) -> PackageBackend:
        """Récupère le backend pour un environnement"""
        return self.backend_manager.get_backend(env.backend_type.value, env)
    
    def _validate_package_specification(self, package: str) -> None:
        """Valide une spécification de package"""
        if not package or not package.strip():
            raise ValidationError("Spécification de package vide")
        
        # Validation basique pour éviter l'injection de commandes
        dangerous_chars = [';', '|', '&', '`', '$']
        if any(char in package for char in dangerous_chars):
            raise ValidationError(f"Caractères dangereux dans le package: {package}")
    
    def _manual_requirements_install(
        self, 
        env: EnvironmentInfo, 
        req_path: Path, 
        backend: PackageBackend
    ) -> bool:
        """Installation manuelle depuis requirements.txt"""
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    result = backend.install_package(env.path, line)
                    if not result.success:
                        logger.warning(f"Échec installation {line}")
            
            return True
        except Exception as e:
            logger.error(f"Erreur installation manuelle requirements: {e}")
            return False
    
    def _manual_pyproject_install(
        self, 
        env: EnvironmentInfo, 
        pyproject: PyProjectInfo, 
        groups: Optional[List[str]],
        backend: PackageBackend
    ) -> bool:
        """Installation manuelle depuis pyproject.toml"""
        try:
            dependencies = pyproject.extract_dependencies(groups)
            
            for dep in dependencies:
                result = backend.install_package(env.path, dep)
                if not result.success:
                    logger.warning(f"Échec installation {dep}")
            
            return True
        except Exception as e:
            logger.error(f"Erreur installation manuelle pyproject: {e}")
            return False