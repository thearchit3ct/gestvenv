"""
Gestionnaire principal d'environnements pour GestVenv v1.1
"""

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import (
    EnvironmentInfo,
    EnvironmentResult,
    ActivationResult,
    SyncResult,
    ExportResult,
    DiagnosticReport,
    BackendType,
    SourceFileType,
    EnvironmentHealth,
    ExportFormat,
    PyProjectInfo
)
from .config_manager import ConfigManager
from .exceptions import (
    EnvironmentError,
    EnvironmentNotFoundError,
    EnvironmentExistsError,
    ValidationError,
    BackendError
)


class EnvironmentManager:
    """Gestionnaire principal des environnements virtuels"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self._service_container = None
        
    @property
    def backend_manager(self):
        """Backend manager lazy loading"""
        if not hasattr(self, '_backend_manager'):
            from ..backends import BackendManager
            self._backend_manager = BackendManager(self.config_manager.config)
        return self._backend_manager
    
    @property
    def package_service(self):
        """Package service lazy loading"""
        if not hasattr(self, '_package_service'):
            from ..services import PackageService
            self._package_service = PackageService(self.backend_manager, self.cache_service)
        return self._package_service
    
    @property
    def cache_service(self):
        """Cache service lazy loading"""
        if not hasattr(self, '_cache_service'):
            from ..services import CacheService
            self._cache_service = CacheService(self.config_manager.config)
        return self._cache_service
    
    @property
    def migration_service(self):
        """Migration service lazy loading"""
        if not hasattr(self, '_migration_service'):
            from ..services import MigrationService
            self._migration_service = MigrationService()
        return self._migration_service
    
    @property
    def diagnostic_service(self):
        """Diagnostic service lazy loading"""
        if not hasattr(self, '_diagnostic_service'):
            from ..services import DiagnosticService
            self._diagnostic_service = DiagnosticService(self)
        return self._diagnostic_service
    
    @property
    def system_service(self):
        """System service lazy loading"""
        if not hasattr(self, '_system_service'):
            from ..services import SystemService
            self._system_service = SystemService()
        return self._system_service
    
    def create_environment(
        self,
        name: str,
        python_version: Optional[str] = None,
        backend: str = "auto",
        initial_packages: Optional[List[str]] = None,
        custom_path: Optional[Path] = None,
        **options
    ) -> EnvironmentResult:
        """Crée un nouvel environnement virtuel"""
        start_time = time.time()
        
        try:
            # Validation du nom
            self._validate_environment_name(name)
            
            # Vérification existence
            if self._environment_exists(name):
                return EnvironmentResult(
                    success=False,
                    message=f"Environnement '{name}' existe déjà",
                    execution_time=time.time() - start_time
                )
            
            # Préparation paramètres
            python_version = python_version or self.config_manager.config.default_python_version
            env_path = custom_path or self._get_environment_path(name)
            
            # Validation version Python
            if not self.system_service.validate_python_version(python_version):
                return EnvironmentResult(
                    success=False,
                    message=f"Version Python invalide: {python_version}",
                    execution_time=time.time() - start_time
                )
            
            # Sélection backend
            backend_instance = self.backend_manager.get_backend(backend)
            
            # Création environnement
            env_path.mkdir(parents=True, exist_ok=True)
            
            success = backend_instance.create_environment(env_path, python_version)
            if not success:
                # Nettoyage en cas d'échec
                if env_path.exists():
                    shutil.rmtree(env_path, ignore_errors=True)
                return EnvironmentResult(
                    success=False,
                    message="Échec création environnement virtuel",
                    execution_time=time.time() - start_time
                )
            
            # Création métadonnées
            env_info = EnvironmentInfo(
                name=name,
                path=env_path,
                python_version=python_version,
                backend_type=BackendType(backend_instance.name.lower()),
                health=EnvironmentHealth.HEALTHY,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_used=datetime.now()
            )
            
            # Installation packages initiaux
            warnings = []
            if initial_packages:
                for package in initial_packages:
                    install_result = self.package_service.install_package(env_info, package)
                    if not install_result.success:
                        warnings.append(f"Échec installation {package}: {install_result.message}")
                
                # Mise à jour liste packages
                env_info.packages = backend_instance.list_packages(env_path)
                env_info.updated_at = datetime.now()
            
            # Sauvegarde métadonnées
            self._save_environment_metadata(env_info)
            
            return EnvironmentResult(
                success=True,
                message=f"Environnement '{name}' créé avec succès",
                environment=env_info,
                warnings=warnings,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            # Nettoyage en cas d'erreur
            env_path = custom_path or self._get_environment_path(name)
            if env_path.exists():
                shutil.rmtree(env_path, ignore_errors=True)
            
            return EnvironmentResult(
                success=False,
                message=f"Erreur création environnement: {e}",
                execution_time=time.time() - start_time
            )
    
    def create_from_pyproject(
        self,
        pyproject_path: Path,
        env_name: Optional[str] = None,
        groups: Optional[List[str]] = None,
        **options
    ) -> EnvironmentResult:
        """Crée un environnement depuis pyproject.toml"""
        start_time = time.time()
        
        try:
            # Parsing pyproject.toml
            from ..utils import PyProjectParser
            pyproject_info = PyProjectParser.parse_pyproject_toml(pyproject_path)
            
            # Nom environnement
            env_name = env_name or pyproject_info.name or pyproject_path.parent.name
            
            # Création environnement de base
            backend = options.get('backend', 'auto')
            python_version = pyproject_info.requires_python or options.get('python_version')
            
            result = self.create_environment(
                name=env_name,
                python_version=python_version,
                backend=backend,
                **options
            )
            
            if not result.success:
                return result
            
            env_info = result.environment
            
            # Mise à jour avec informations pyproject
            env_info.pyproject_info = pyproject_info
            env_info.source_file_type = SourceFileType.PYPROJECT_TOML
            
            # Extraction dépendances
            dependencies = pyproject_info.extract_dependencies(groups)
            
            # Installation dépendances
            warnings = result.warnings.copy()
            if dependencies:
                for dep in dependencies:
                    install_result = self.package_service.install_package(env_info, dep)
                    if not install_result.success:
                        warnings.append(f"Échec installation {dep}: {install_result.message}")
                
                # Mise à jour packages
                backend_instance = self.backend_manager.get_backend(backend, env_info)
                env_info.packages = backend_instance.list_packages(env_info.path)
            
            # Gestion groupes dépendances
            if pyproject_info.optional_dependencies:
                env_info.dependency_groups = pyproject_info.optional_dependencies
            
            # Génération fichier lock si supporté
            backend_instance = self.backend_manager.get_backend(backend, env_info)
            if hasattr(backend_instance, 'create_lock_file'):
                try:
                    lock_path = backend_instance.create_lock_file(pyproject_path)
                    if lock_path:
                        env_info.lock_file_path = lock_path
                except Exception as e:
                    warnings.append(f"Échec génération lock file: {e}")
            
            env_info.updated_at = datetime.now()
            self._save_environment_metadata(env_info)
            
            return EnvironmentResult(
                success=True,
                message=f"Environnement '{env_name}' créé depuis pyproject.toml",
                environment=env_info,
                warnings=warnings,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return EnvironmentResult(
                success=False,
                message=f"Erreur création depuis pyproject.toml: {e}",
                execution_time=time.time() - start_time
            )
    
    def activate_environment(self, name: str) -> ActivationResult:
        """Active un environnement"""
        try:
            env_info = self.get_environment_info(name)
            if not env_info:
                return ActivationResult(
                    success=False,
                    message=f"Environnement '{name}' introuvable",
                    activation_script=Path(),
                    activation_command=""
                )
            
            # Désactivation environnement actuel
            self.deactivate_environment()
            
            # Génération script activation
            activation_script = self.system_service.get_activation_script(env_info.path)
            
            # Commande d'activation selon OS
            if os.name == 'nt':  # Windows
                activation_command = f"call {activation_script}"
            else:  # Unix/Linux/macOS
                activation_command = f"source {activation_script}"
            
            # Variables d'environnement
            env_vars = {
                'VIRTUAL_ENV': str(env_info.path),
                'VIRTUAL_ENV_PROMPT': f"({name})",
                'PATH': f"{env_info.path / 'bin'}:{os.environ.get('PATH', '')}"
            }
            
            # Marquage comme actif
            env_info.is_active = True
            env_info.last_used = datetime.now()
            self._save_environment_metadata(env_info)
            
            return ActivationResult(
                success=True,
                message=f"Environnement '{name}' activé",
                activation_script=activation_script,
                activation_command=activation_command,
                environment_variables=env_vars
            )
            
        except Exception as e:
            return ActivationResult(
                success=False,
                message=f"Erreur activation: {e}",
                activation_script=Path(),
                activation_command=""
            )
    
    def deactivate_environment(self) -> bool:
        """Désactive l'environnement actuel"""
        try:
            # Marquage tous environnements comme inactifs
            for env_info in self.list_environments():
                if env_info.is_active:
                    env_info.is_active = False
                    self._save_environment_metadata(env_info)
            return True
        except Exception:
            return False
    
    def delete_environment(self, name: str, force: bool = False) -> bool:
        """Supprime un environnement"""
        try:
            env_info = self.get_environment_info(name)
            if not env_info:
                raise EnvironmentNotFoundError(f"Environnement '{name}' introuvable")
            
            # Vérification si actif
            if env_info.is_active and not force:
                raise EnvironmentError(
                    f"Environnement '{name}' est actif. Utilisez --force pour forcer la suppression"
                )
            
            # Sauvegarde avant suppression
            backup_path = self._backup_environment(env_info)
            
            # Suppression répertoire
            if env_info.path.exists():
                shutil.rmtree(env_info.path)
            
            # Suppression métadonnées
            metadata_path = self._get_metadata_path(name)
            if metadata_path.exists():
                metadata_path.unlink()
            
            return True
            
        except Exception as e:
            raise EnvironmentError(f"Erreur suppression environnement: {e}")
    
    def list_environments(self, **filters) -> List[EnvironmentInfo]:
        """Liste les environnements avec filtres optionnels"""
        environments = []
        envs_path = self.config_manager.get_environments_path()
        
        if not envs_path.exists():
            return environments
        
        for env_dir in envs_path.iterdir():
            if env_dir.is_dir():
                env_info = self._load_environment_metadata(env_dir.name)
                if env_info and self._match_filters(env_info, filters):
                    environments.append(env_info)
        
        return sorted(environments, key=lambda x: x.last_used, reverse=True)
    
    def sync_environment(self, name: str) -> SyncResult:
        """Synchronise un environnement avec son pyproject.toml"""
        start_time = time.time()
        
        try:
            env_info = self.get_environment_info(name)
            if not env_info:
                return SyncResult(
                    success=False,
                    message=f"Environnement '{name}' introuvable",
                    execution_time=time.time() - start_time
                )
            
            if not env_info.pyproject_info:
                return SyncResult(
                    success=False,
                    message="Aucun pyproject.toml associé",
                    execution_time=time.time() - start_time
                )
            
            # Synchronisation avec service packages
            sync_result = self.package_service.sync_environment(env_info)
            sync_result.execution_time = time.time() - start_time
            
            if sync_result.success:
                env_info.updated_at = datetime.now()
                self._save_environment_metadata(env_info)
            
            return sync_result
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"Erreur synchronisation: {e}",
                execution_time=time.time() - start_time
            )
    
    def clone_environment(self, source: str, target: str) -> EnvironmentResult:
        """Clone un environnement existant"""
        try:
            source_env = self.get_environment_info(source)
            if not source_env:
                raise EnvironmentNotFoundError(f"Environnement source '{source}' introuvable")
            
            # Création nouvel environnement
            result = self.create_environment(
                name=target,
                python_version=source_env.python_version,
                backend=source_env.backend_type.value
            )
            
            if not result.success:
                return result
            
            # Clonage packages
            target_env = result.environment
            warnings = result.warnings.copy()
            
            for package in source_env.packages:
                install_result = self.package_service.install_package(
                    target_env, 
                    package.get_install_command()
                )
                if not install_result.success:
                    warnings.append(f"Échec clonage {package.name}: {install_result.message}")
            
            # Copie métadonnées
            target_env.pyproject_info = source_env.pyproject_info
            target_env.dependency_groups = source_env.dependency_groups.copy()
            target_env.source_file_type = source_env.source_file_type
            
            # Mise à jour packages
            backend = self.backend_manager.get_backend(target_env.backend_type.value, target_env)
            target_env.packages = backend.list_packages(target_env.path)
            target_env.updated_at = datetime.now()
            
            self._save_environment_metadata(target_env)
            
            return EnvironmentResult(
                success=True,
                message=f"Environnement '{target}' cloné depuis '{source}'",
                environment=target_env,
                warnings=warnings
            )
            
        except Exception as e:
            return EnvironmentResult(
                success=False,
                message=f"Erreur clonage: {e}"
            )
    
    def export_environment(self, name: str, format: ExportFormat) -> ExportResult:
        """Exporte un environnement"""
        try:
            env_info = self.get_environment_info(name)
            if not env_info:
                return ExportResult(
                    success=False,
                    message=f"Environnement '{name}' introuvable",
                    output_path=Path(),
                    format=format,
                    items_exported=0
                )
            
            # Génération chemin de sortie
            output_path = Path.cwd() / f"{name}_export.{format.value}"
            
            if format == ExportFormat.JSON:
                # Export JSON complet
                export_data = env_info.to_dict()
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, default=str)
                items_exported = 1
                
            elif format == ExportFormat.REQUIREMENTS:
                # Export requirements.txt
                lines = [pkg.get_install_command() for pkg in env_info.packages]
                output_path = output_path.with_suffix('.txt')
                output_path.write_text('\n'.join(lines), encoding='utf-8')
                items_exported = len(lines)
                
            elif format == ExportFormat.PYPROJECT:
                # Export pyproject.toml
                if env_info.pyproject_info:
                    from ..utils import TomlHandler
                    pyproject_data = {
                        'project': {
                            'name': env_info.pyproject_info.name,
                            'version': env_info.pyproject_info.version,
                            'dependencies': env_info.pyproject_info.dependencies,
                            'optional-dependencies': env_info.pyproject_info.optional_dependencies
                        }
                    }
                    output_path = output_path.with_suffix('.toml')
                    TomlHandler.dump(pyproject_data, output_path)
                    items_exported = 1
                else:
                    return ExportResult(
                        success=False,
                        message="Aucune information pyproject.toml disponible",
                        output_path=Path(),
                        format=format,
                        items_exported=0
                    )
            
            return ExportResult(
                success=True,
                message=f"Environnement exporté vers {output_path}",
                output_path=output_path,
                format=format,
                items_exported=items_exported
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Erreur export: {e}",
                output_path=Path(),
                format=format,
                items_exported=0
            )
    
    def import_environment(self, source: Path, **options) -> EnvironmentResult:
        """Importe un environnement"""
        try:
            if not source.exists():
                return EnvironmentResult(
                    success=False,
                    message=f"Fichier source introuvable: {source}"
                )
            
            env_name = options.get('name') or source.stem
            
            if source.suffix == '.json':
                # Import depuis JSON
                with open(source, 'r', encoding='utf-8') as f:
                    env_data = json.load(f)
                
                env_info = EnvironmentInfo.from_dict(env_data)
                env_info.name = env_name
                env_info.path = self._get_environment_path(env_name)
                
                # Recréation environnement
                result = self.create_environment(
                    name=env_name,
                    python_version=env_info.python_version,
                    backend=env_info.backend_type.value
                )
                
                if result.success:
                    # Restauration packages
                    target_env = result.environment
                    for package in env_info.packages:
                        self.package_service.install_package(
                            target_env, 
                            package.get_install_command()
                        )
                
                return result
            
            else:
                return EnvironmentResult(
                    success=False,
                    message=f"Format non supporté: {source.suffix}"
                )
                
        except Exception as e:
            return EnvironmentResult(
                success=False,
                message=f"Erreur import: {e}"
            )
    
    def doctor_environment(self, name: Optional[str] = None) -> DiagnosticReport:
        """Diagnostic d'un environnement ou du système complet"""
        if name:
            return self.diagnostic_service.diagnose_environment(name)
        else:
            return self.diagnostic_service.run_full_diagnostic()
    
    def get_environment_info(self, name: str) -> Optional[EnvironmentInfo]:
        """Récupère les informations d'un environnement"""
        return self._load_environment_metadata(name)
    
    def auto_migrate_if_needed(self) -> bool:
        """Migration automatique si nécessaire"""
        try:
            return self.migration_service.auto_migrate_if_needed()
        except Exception:
            return False
    
    # Méthodes privées
    
    def _validate_environment_name(self, name: str) -> None:
        """Valide un nom d'environnement"""
        from ..utils import ValidationUtils
        if not ValidationUtils.validate_environment_name(name):
            raise ValidationError(f"Nom d'environnement invalide: {name}")
    
    def _environment_exists(self, name: str) -> bool:
        """Vérifie si un environnement existe"""
        env_path = self._get_environment_path(name)
        return env_path.exists()
    
    def _get_environment_path(self, name: str) -> Path:
        """Chemin d'un environnement"""
        return self.config_manager.get_environments_path() / name
    
    def _get_metadata_path(self, name: str) -> Path:
        """Chemin du fichier métadonnées"""
        return self._get_environment_path(name) / ".gestvenv-metadata.json"
    
    def _save_environment_metadata(self, env_info: EnvironmentInfo) -> None:
        """Sauvegarde les métadonnées d'un environnement"""
        metadata_path = self._get_metadata_path(env_info.name)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(env_info.to_dict(), f, indent=2, default=str)
    
    def _load_environment_metadata(self, name: str) -> Optional[EnvironmentInfo]:
        """Charge les métadonnées d'un environnement"""
        metadata_path = self._get_metadata_path(name)
        
        if not metadata_path.exists():
            # Tentative détection environnement existant sans métadonnées
            env_path = self._get_environment_path(name)
            if env_path.exists():
                return self._detect_existing_environment(name, env_path)
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return EnvironmentInfo.from_dict(data)
        except Exception:
            return None
    
    def _detect_existing_environment(self, name: str, env_path: Path) -> Optional[EnvironmentInfo]:
        """Détecte un environnement existant sans métadonnées"""
        try:
            # Détection version Python
            python_version = self.system_service.detect_python_version(env_path)
            
            # Création info basique
            env_info = EnvironmentInfo(
                name=name,
                path=env_path,
                python_version=python_version,
                health=EnvironmentHealth.UNKNOWN
            )
            
            # Détection packages
            backend = self.backend_manager.get_backend("pip")  # Fallback
            env_info.packages = backend.list_packages(env_path)
            
            # Sauvegarde métadonnées pour usage futur
            self._save_environment_metadata(env_info)
            
            return env_info
        except Exception:
            return None
    
    def _backup_environment(self, env_info: EnvironmentInfo) -> Optional[Path]:
        """Sauvegarde un environnement"""
        try:
            backup_dir = Path.home() / ".gestvenv" / "backups" / "environments"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{env_info.name}_{timestamp}.json"
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(env_info.to_dict(), f, indent=2, default=str)
            
            return backup_path
        except Exception:
            return None
    
    def _match_filters(self, env_info: EnvironmentInfo, filters: Dict[str, Any]) -> bool:
        """Vérifie si un environnement correspond aux filtres"""
        if filters.get('active_only') and not env_info.is_active:
            return False
        
        if filters.get('backend') and env_info.backend_type.value != filters['backend']:
            return False
        
        if filters.get('health') and env_info.health.value != filters['health']:
            return False
        
        return True