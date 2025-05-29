"""
Module de gestion des environnements virtuels pour GestVenv v1.1.

Ce module fournit les fonctionnalités principales pour créer, activer, supprimer
et gérer les environnements virtuels Python avec support étendu pour:
- pyproject.toml (PEP 517/518/621)
- Backends multiples (pip, uv, poetry, pdm)
- Groupes de dépendances avancés
- Lock files et synchronisation
- Migration et compatibilité v1.0
- Monitoring de performance et sécurité

Version 1.1 - Nouvelles fonctionnalités:
- Architecture backend modulaire
- Support pyproject.toml natif
- Détection automatique de type de projet
- Synchronisation intelligente
- Gestion avancée des dépendances
"""

import os
import sys
import json
import platform
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set

# Import des modules internes
from .models import (
    EnvironmentInfo, PackageInfo, EnvironmentHealth, PyProjectInfo,
    LockFileInfo, ConfigInfo, ValidationError, MigrationInfo,
    SecurityIssue, PerformanceMetrics, BackendType, SourceFileType,
    DependencyType, create_default_environment_info, validate_environment_name,
    validate_python_version
)
from .config_manager import ConfigManager

# Configuration du logger
logger = logging.getLogger(__name__)


class EnvironmentManager:
    """
    Classe principale pour la gestion des environnements virtuels Python v1.1.
    
    Cette classe utilise une architecture modulaire avec des backends
    pour effectuer les opérations sur les environnements virtuels et
    maintient l'état de la configuration avec support étendu.
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialise le gestionnaire d'environnements.
        
        Args:
            config_path: Chemin vers le fichier de configuration.
                Si None, utilise le chemin par défaut.
        """
        self.config_manager = ConfigManager(config_path)
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)
        
        # Initialiser les services avec gestion d'erreur
        self._init_services()
        
        # Initialiser les backends
        self._init_backends()
        
        # Métriques de performance
        self.performance_metrics: List[PerformanceMetrics] = []
        
        # Migration automatique si nécessaire
        self._check_and_migrate()
    
    def _init_services(self) -> None:
        """Initialise les services avec gestion d'erreur."""
        try:
            from ..services.environment_service import EnvironmentService
            from ..services.package_service import PackageService
            from ..services.system_service import SystemService
            from ..services.cache_service import CacheService
            
            self.env_service = EnvironmentService()
            self.pkg_service = PackageService()
            self.sys_service = SystemService()
            self.cache_service = CacheService()
            
        except ImportError as e:
            logger.error(f"Erreur lors de l'import des services: {e}")
            raise RuntimeError(f"Services non disponibles: {e}")
    
    def _init_backends(self) -> None:
        """Initialise les backends disponibles."""
        self.available_backends = {}
        
        try:
            # Importer les backends disponibles
            from ..backends.pip_backend import PipBackend
            self.available_backends[BackendType.PIP] = PipBackend()
            
            try:
                from ..backends.uv_backend import UvBackend
                self.available_backends[BackendType.UV] = UvBackend()
            except ImportError:
                logger.debug("Backend uv non disponible")
            
            try:
                from ..backends.poetry_backend import PoetryBackend
                self.available_backends[BackendType.POETRY] = PoetryBackend()
            except ImportError:
                logger.debug("Backend poetry non disponible")
            
            try:
                from ..backends.pdm_backend import PdmBackend
                self.available_backends[BackendType.PDM] = PdmBackend()
            except ImportError:
                logger.debug("Backend pdm non disponible")
                
        except ImportError as e:
            logger.error(f"Erreur lors de l'import des backends: {e}")
            # Au minimum, pip doit être disponible
            if BackendType.PIP not in self.available_backends:
                raise RuntimeError("Backend pip non disponible")
    
    def _check_and_migrate(self) -> None:
        """Vérifie et effectue la migration si nécessaire."""
        try:
            config_version = self.config_manager.config.config_version
            if config_version != "1.1.0":
                logger.info(f"Migration nécessaire de {config_version} vers 1.1.0")
                self._migrate_from_v1_0()
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification de migration: {e}")
    
    def _migrate_from_v1_0(self) -> None:
        """Effectue la migration depuis la version 1.0."""
        try:
            migration_info = MigrationInfo(
                from_version="1.0.0",
                to_version="1.1.0",
                migration_type="config",
                started_at=datetime.now()
            )
            
            # Sauvegarder la configuration actuelle
            backup_path = self.config_manager.config_path.with_suffix('.json.v1.0.backup')
            shutil.copy2(self.config_manager.config_path, backup_path)
            migration_info.backup_path = backup_path
            migration_info.rollback_available = True
            
            # Mettre à jour la version de configuration
            self.config_manager.config.config_version = "1.1.0"
            self.config_manager.config.migrated_from_version = "1.0.0"
            self.config_manager.config.migration_date = datetime.now()
            
            # Migrer les environnements existants
            for env_info in self.config_manager.config.environments.values():
                if not hasattr(env_info, 'backend_type'):
                    env_info.backend_type = BackendType.PIP
                if not hasattr(env_info, 'source_file_type'):
                    env_info.source_file_type = SourceFileType.REQUIREMENTS
            
            # Sauvegarder la configuration migrée
            self.config_manager.save_config()
            
            migration_info.completed_at = datetime.now()
            migration_info.success = True
            
            logger.info("Migration v1.0 → v1.1 terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la migration: {e}")
            migration_info.success = False
            migration_info.errors.append(
                ValidationError("migration", f"Erreur migration: {str(e)}")
            )
    
    def get_optimal_backend(self, env_name: Optional[str] = None, 
                          project_path: Optional[Path] = None) -> BackendType:
        """
        Détermine le backend optimal pour un environnement ou projet.
        
        Args:
            env_name: Nom de l'environnement (optionnel)
            project_path: Chemin du projet (optionnel)
            
        Returns:
            BackendType: Backend optimal à utiliser
        """
        # Préférence utilisateur
        preferred = self.config_manager.config.preferred_backend
        if preferred != BackendType.PIP and preferred in self.available_backends:
            backend = self.available_backends[preferred]
            if backend.is_available():
                return preferred
        
        # Détection basée sur l'environnement existant
        if env_name:
            env_info = self.config_manager.get_environment(env_name)
            if env_info and env_info.backend_type in self.available_backends:
                backend = self.available_backends[env_info.backend_type]
                if backend.is_available():
                    return env_info.backend_type
        
        # Détection basée sur le projet
        if project_path:
            backend_type = self._detect_project_backend(project_path)
            if backend_type and backend_type in self.available_backends:
                backend = self.available_backends[backend_type]
                if backend.is_available():
                    return backend_type
        
        # Ordre de préférence par défaut
        preference_order = [BackendType.UV, BackendType.PIP, BackendType.POETRY, BackendType.PDM]
        
        for backend_type in preference_order:
            if backend_type in self.available_backends:
                backend = self.available_backends[backend_type]
                if backend.is_available():
                    return backend_type
        
        # Fallback ultime
        return BackendType.PIP
    
    def _detect_project_backend(self, project_path: Path) -> Optional[BackendType]:
        """
        Détecte le backend optimal pour un projet basé sur ses fichiers.
        
        Args:
            project_path: Chemin du projet
            
        Returns:
            BackendType ou None: Backend détecté
        """
        try:
            # Vérifier les fichiers indicateurs
            if (project_path / "uv.lock").exists():
                return BackendType.UV
            elif (project_path / "poetry.lock").exists():
                return BackendType.POETRY
            elif (project_path / "pdm.lock").exists():
                return BackendType.PDM
            elif (project_path / "pyproject.toml").exists():
                # Analyser le pyproject.toml pour détecter l'outil
                try:
                    from ..utils.pyproject_parser import PyProjectParser
                    parser = PyProjectParser(project_path / "pyproject.toml")
                    tool_sections = parser.get_tool_sections()
                    
                    if "poetry" in tool_sections:
                        return BackendType.POETRY
                    elif "pdm" in tool_sections:
                        return BackendType.PDM
                    elif "uv" in tool_sections:
                        return BackendType.UV
                    else:
                        return BackendType.UV  # uv supporte les pyproject.toml standards
                except Exception:
                    return BackendType.UV
            elif (project_path / "requirements.txt").exists():
                return BackendType.PIP
                
        except Exception as e:
            logger.debug(f"Erreur détection backend projet: {e}")
        
        return None
    
    def create_environment(self, name: str, python_version: Optional[str] = None,
                          packages: Optional[Union[str, List[str]]] = None, 
                          path: Optional[str] = None, offline: bool = False,
                          backend: Optional[Union[str, BackendType]] = None,
                          groups: Optional[List[str]] = None,
                          from_pyproject: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Crée un nouvel environnement virtuel Python avec support étendu v1.1.
        
        Args:
            name: Nom de l'environnement
            python_version: Version Python à utiliser
            packages: Packages à installer (chaîne ou liste)
            path: Chemin personnalisé pour l'environnement
            offline: Mode hors ligne
            backend: Backend à utiliser
            groups: Groupes de dépendances à installer
            from_pyproject: Chemin vers pyproject.toml
            
        Returns:
            Tuple contenant (succès, message)
        """
        start_time = time.time()
        
        try:
            # Validation du nom
            validation_errors = validate_environment_name(name)
            if validation_errors:
                error_msg = "; ".join([err.message for err in validation_errors])
                return False, f"Nom d'environnement invalide: {error_msg}"
            
            # Vérifier si l'environnement existe déjà
            if self.config_manager.environment_exists(name):
                return False, f"L'environnement '{name}' existe déjà"
            
            # Validation de la version Python
            if python_version:
                python_errors = validate_python_version(python_version)
                if python_errors:
                    error_msg = "; ".join([err.message for err in python_errors])
                    return False, f"Version Python invalide: {error_msg}"
            
            # Déterminer le backend à utiliser
            backend_type = BackendType.PIP
            if backend:
                if isinstance(backend, str):
                    try:
                        backend_type = BackendType(backend)
                    except ValueError:
                        return False, f"Backend '{backend}' non reconnu"
                else:
                    backend_type = backend
            else:
                backend_type = self.get_optimal_backend(project_path=Path.cwd())
            
            # Vérifier que le backend est disponible
            if backend_type not in self.available_backends:
                return False, f"Backend '{backend_type.value}' non disponible"
            
            backend_instance = self.available_backends[backend_type]
            if not backend_instance.is_available():
                return False, f"Backend '{backend_type.value}' non installé"
            
            # Déterminer le chemin de l'environnement
            env_path = self.env_service.get_environment_path(name, path)
            
            # Traitement du pyproject.toml si spécifié
            pyproject_info = None
            if from_pyproject:
                try:
                    from ..utils.pyproject_parser import PyProjectParser
                    parser = PyProjectParser(from_pyproject)
                    pyproject_info = parser.extract_info()
                    
                    # Utiliser les informations du pyproject.toml
                    if not python_version and pyproject_info.requires_python:
                        python_version = pyproject_info.requires_python
                    
                    if not packages and pyproject_info.dependencies:
                        packages = pyproject_info.dependencies
                    
                    # Ajouter les groupes optionnels
                    if groups and pyproject_info.optional_dependencies:
                        if isinstance(packages, str):
                            packages = [pkg.strip() for pkg in packages.split(',')]
                        elif packages is None:
                            packages = []
                        
                        for group in groups:
                            if group in pyproject_info.optional_dependencies:
                                packages.extend(pyproject_info.optional_dependencies[group])
                    
                except Exception as e:
                    return False, f"Erreur lors du parsing du pyproject.toml: {str(e)}"
            
            # Créer l'environnement virtuel
            python_cmd = python_version or self.config_manager.get_default_python()
            success = backend_instance.create_environment(name, python_cmd, env_path)
            
            if not success:
                return False, f"Échec de la création avec le backend {backend_type.value}"
            
            # Déterminer la version Python réelle
            actual_python_version = self.sys_service.check_python_version(python_cmd)
            if not actual_python_version:
                actual_python_version = python_cmd
            
            # Créer l'objet EnvironmentInfo
            env_info = EnvironmentInfo(
                name=name,
                path=env_path,
                python_version=actual_python_version,
                created_at=datetime.now(),
                backend_type=backend_type,
                source_file_type=SourceFileType.PYPROJECT if from_pyproject else SourceFileType.REQUIREMENTS,
                pyproject_info=pyproject_info,
                project_path=from_pyproject.parent if from_pyproject else None
            )
            
            # Installer les packages si spécifiés
            if packages:
                package_list = packages
                if isinstance(packages, str):
                    package_list = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
                
                install_success, install_msg = self._install_packages_in_env(
                    env_info, package_list, offline
                )
                
                if not install_success:
                    # Nettoyer l'environnement en cas d'échec
                    try:
                        shutil.rmtree(env_path)
                    except Exception:
                        pass
                    return False, f"Échec de l'installation des packages: {install_msg}"
                
                # Mettre à jour les packages installés
                env_info.packages = [str(pkg) for pkg in package_list]
            
            # Vérifier la santé de l'environnement
            env_info.health = self.env_service.check_environment_health(name, env_path)
            
            # Ajouter l'environnement à la configuration
            self.config_manager.add_environment(env_info)
            
            # Si c'est le premier environnement, le définir comme actif
            if len(self.config_manager.get_all_environments()) == 1:
                self.config_manager.set_active_environment(name)
            
            # Enregistrer les métriques de performance
            duration = time.time() - start_time
            metrics = PerformanceMetrics(
                environment_name=name,
                backend_type=backend_type.value,
                measurement_type="create",
                duration=duration,
                package_count=len(packages) if packages else 0,
                success=True
            )
            self.performance_metrics.append(metrics)
            
            return True, f"Environnement '{name}' créé avec succès avec {backend_type.value}"
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'environnement: {str(e)}")
            
            # Enregistrer les métriques d'échec
            duration = time.time() - start_time
            metrics = PerformanceMetrics(
                environment_name=name,
                backend_type=backend_type.value if 'backend_type' in locals() else "unknown",
                measurement_type="create",
                duration=duration,
                package_count=0,
                success=False
            )
            self.performance_metrics.append(metrics)
            
            return False, f"Erreur lors de la création de l'environnement: {str(e)}"
    
    def create_from_pyproject(self, pyproject_path: Path, env_name: str,
                             groups: Optional[List[str]] = None,
                             backend: Optional[BackendType] = None) -> Tuple[bool, str]:
        """
        Crée un environnement depuis un fichier pyproject.toml.
        
        Args:
            pyproject_path: Chemin vers le pyproject.toml
            env_name: Nom de l'environnement
            groups: Groupes de dépendances à installer
            backend: Backend à utiliser
            
        Returns:
            Tuple contenant (succès, message)
        """
        return self.create_environment(
            name=env_name,
            from_pyproject=pyproject_path,
            groups=groups,
            backend=backend
        )
    
    def sync_environment(self, env_name: str, groups: Optional[List[str]] = None,
                        strict: bool = False, update_lock: bool = True) -> Tuple[bool, str]:
        """
        Synchronise un environnement avec ses fichiers de configuration.
        
        Args:
            env_name: Nom de l'environnement
            groups: Groupes de dépendances à synchroniser
            strict: Mode strict (supprime les packages non déclarés)
            update_lock: Met à jour le fichier de lock
            
        Returns:
            Tuple contenant (succès, message)
        """
        start_time = time.time()
        
        try:
            # Vérifier si l'environnement existe
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return False, f"L'environnement '{name}' n'existe pas"
            
            # Vérifier s'il est sécuritaire de supprimer l'environnement
            if not force:
                safe, warning = self.env_service.is_safe_to_delete(name, env_info.path)
                if not safe:
                    return False, warning
            
            # Supprimer l'environnement du système de fichiers
            success, message = self.env_service.delete_environment(env_info.path)
            if not success:
                return False, message
            
            # Supprimer l'environnement de la configuration
            try:
                self.config_manager.remove_environment(name)
            except Exception as e:
                logger.error(f"Erreur suppression config: {str(e)}")
                return False, f"Environnement supprimé du disque mais erreur config: {str(e)}"
            
            return True, f"Environnement '{name}' supprimé avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {str(e)}")
            return False, f"Erreur lors de la suppression: {str(e)}"
    
    def list_environments(self, include_health: bool = True,
                         filter_backend: Optional[BackendType] = None,
                         filter_tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Liste tous les environnements disponibles avec leurs informations.
        
        Args:
            include_health: Inclut les informations de santé
            filter_backend: Filtre par backend
            filter_tags: Filtre par tags
            
        Returns:
            Liste des environnements avec leurs détails
        """
        try:
            result = []
            environments = self.config_manager.get_all_environments()
            active_env = self.config_manager.get_active_environment()
            
            for name, env_info in environments.items():
                # Appliquer les filtres
                if filter_backend and env_info.backend_type != filter_backend:
                    continue
                
                if filter_tags and not any(tag in env_info.tags for tag in filter_tags):
                    continue
                
                # Vérifier si l'environnement existe réellement
                exists = self.env_service.check_environment_exists(env_info.path)
                
                # Mettre à jour l'état de santé si demandé
                health = env_info.health
                if include_health and exists:
                    health = self.env_service.check_environment_health(name, env_info.path)
                    env_info.health = health
                
                # Préparer les informations de base
                env_data = {
                    "name": name,
                    "path": str(env_info.path),
                    "python_version": env_info.python_version,
                    "created_at": env_info.created_at.isoformat() if isinstance(env_info.created_at, datetime) else env_info.created_at,
                    "packages_count": len(env_info.packages_installed),
                    "active": name == active_env,
                    "exists": exists,
                    "backend_type": env_info.backend_type.value,
                    "source_file_type": env_info.source_file_type.value,
                    "description": env_info.description,
                    "tags": env_info.tags,
                    "aliases": env_info.aliases,
                    "last_used": env_info.last_used.isoformat() if env_info.last_used else None,
                    "usage_count": env_info.usage_count
                }
                
                # Ajouter les informations de santé
                if include_health:
                    env_data["health"] = health.to_dict()
                    env_data["health_score"] = health.health_score
                
                # Ajouter les informations pyproject.toml
                if env_info.pyproject_info:
                    env_data["has_pyproject"] = True
                    env_data["project_name"] = env_info.pyproject_info.name
                    env_data["project_version"] = env_info.pyproject_info.version
                    env_data["dependency_groups"] = list(env_info.pyproject_info.optional_dependencies.keys())
                else:
                    env_data["has_pyproject"] = False
                
                # Ajouter les informations de lock file
                if env_info.lock_file_info:
                    env_data["has_lock_file"] = True
                    env_data["lock_file_type"] = env_info.lock_file_info.lock_type
                else:
                    env_data["has_lock_file"] = False
                
                result.append(env_data)
            
            # Trier par nom
            result.sort(key=lambda x: x["name"].lower())
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la liste des environnements: {str(e)}")
            return []
    
    def get_environment_info(self, name: str, detailed: bool = True) -> Optional[Dict[str, Any]]:
        """
        Obtient des informations détaillées sur un environnement spécifique.
        
        Args:
            name: Nom de l'environnement
            detailed: Inclut les informations détaillées
            
        Returns:
            Dictionnaire d'informations ou None si non trouvé
        """
        try:
            # Vérifier si l'environnement existe
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                logger.warning(f"L'environnement '{name}' n'existe pas")
                return None
            
            # Vérifier si l'environnement existe physiquement
            exists = self.env_service.check_environment_exists(env_info.path)
            
            # Mettre à jour l'état de santé
            health = env_info.health
            if exists:
                health = self.env_service.check_environment_health(name, env_info.path)
                env_info.health = health
            
            # Obtenir les packages installés si l'environnement existe
            installed_packages = []
            if exists and health.pip_available:
                try:
                    installed_packages = self._get_installed_packages(env_info)
                    # Mettre à jour la liste dans l'environnement
                    env_info.packages_installed = installed_packages
                except Exception as e:
                    logger.debug(f"Erreur récupération packages: {e}")
            
            # Informations de base
            active_env = self.config_manager.get_active_environment()
            result = {
                "name": name,
                "path": str(env_info.path),
                "python_version": env_info.python_version,
                "created_at": env_info.created_at.isoformat() if isinstance(env_info.created_at, datetime) else env_info.created_at,
                "active": name == active_env,
                "exists": exists,
                "backend_type": env_info.backend_type.value,
                "source_file_type": env_info.source_file_type.value,
                "health": health.to_dict(),
                "health_score": health.health_score,
                "description": env_info.description,
                "tags": env_info.tags,
                "aliases": env_info.aliases,
                "last_used": env_info.last_used.isoformat() if env_info.last_used else None,
                "usage_count": env_info.usage_count,
                "packages_configured": env_info.packages,
                "packages_installed": [pkg.to_dict() for pkg in installed_packages],
                "packages_count": len(installed_packages)
            }
            
            # Informations détaillées
            if detailed:
                # Informations pyproject.toml
                if env_info.pyproject_info:
                    result["pyproject_info"] = {
                        "name": env_info.pyproject_info.name,
                        "version": env_info.pyproject_info.version,
                        "description": env_info.pyproject_info.description,
                        "requires_python": env_info.pyproject_info.requires_python,
                        "dependencies": env_info.pyproject_info.dependencies,
                        "optional_dependencies": env_info.pyproject_info.optional_dependencies,
                        "build_backend": env_info.pyproject_info.get_build_backend(),
                        "file_path": str(env_info.pyproject_info.file_path) if env_info.pyproject_info.file_path else None
                    }
                
                # Informations de lock file
                if env_info.lock_file_info:
                    result["lock_file_info"] = env_info.lock_file_info.to_dict()
                
                # Chemins des exécutables
                if exists:
                    result["python_executable"] = str(self.env_service.get_python_executable(name, env_info.path))
                    result["pip_executable"] = str(self.env_service.get_pip_executable(name, env_info.path))
                    result["activation_script"] = str(self.env_service.get_activation_script_path(name, env_info.path))
                
                # Statistiques de performance
                env_metrics = [m for m in self.performance_metrics if m.environment_name == name]
                if env_metrics:
                    result["performance_stats"] = {
                        "average_install_time": sum(m.duration for m in env_metrics if m.measurement_type == "install") / len([m for m in env_metrics if m.measurement_type == "install"]) if any(m.measurement_type == "install" for m in env_metrics) else None,
                        "total_operations": len(env_metrics),
                        "success_rate": sum(1 for m in env_metrics if m.success) / len(env_metrics) if env_metrics else 0
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur récupération infos environnement: {str(e)}")
            return None
    
    def clone_environment(self, source_name: str, target_name: str,
                         copy_config: bool = True, include_packages: bool = True) -> Tuple[bool, str]:
        """
        Clone un environnement existant vers un nouveau.
        
        Args:
            source_name: Nom de l'environnement source
            target_name: Nom du nouvel environnement
            copy_config: Copie la configuration (pyproject.toml, etc.)
            include_packages: Inclut les packages installés
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            # Vérifier l'environnement source
            source_info = self.config_manager.get_environment(source_name)
            if not source_info:
                return False, f"L'environnement source '{source_name}' n'existe pas"
            
            # Valider le nom cible
            validation_errors = validate_environment_name(target_name)
            if validation_errors:
                error_msg = "; ".join([err.message for err in validation_errors])
                return False, f"Nom d'environnement cible invalide: {error_msg}"
            
            # Vérifier que le nom cible n'existe pas
            if self.config_manager.environment_exists(target_name):
                return False, f"L'environnement cible '{target_name}' existe déjà"
            
            # Créer le nouvel environnement avec la même configuration
            packages = None
            if include_packages:
                if source_info.pyproject_info:
                    packages = source_info.pyproject_info.get_all_dependencies()
                else:
                    packages = source_info.packages
            
            success, message = self.create_environment(
                name=target_name,
                python_version=source_info.python_version,
                packages=packages,
                backend=source_info.backend_type
            )
            
            if not success:
                return False, f"Erreur création environnement cible: {message}"
            
            # Copier les métadonnées
            target_info = self.config_manager.get_environment(target_name)
            if target_info:
                target_info.description = f"Clone de {source_name}"
                target_info.tags = source_info.tags.copy()
                target_info.metadata = source_info.metadata.copy()
                
                if copy_config and source_info.pyproject_info:
                    target_info.pyproject_info = source_info.pyproject_info
                    target_info.source_file_type = source_info.source_file_type
                
                self.config_manager.update_environment(target_info)
            
            return True, f"Environnement '{source_name}' cloné avec succès vers '{target_name}'"
            
        except Exception as e:
            logger.error(f"Erreur lors du clonage: {str(e)}")
            return False, f"Erreur lors du clonage: {str(e)}"
    
    def export_environment(self, name: str, output_path: Optional[str] = None,
                          format_type: str = "json", include_metadata: bool = True,
                          include_lock: bool = False) -> Tuple[bool, str]:
        """
        Exporte la configuration d'un environnement.
        
        Args:
            name: Nom de l'environnement à exporter
            output_path: Chemin de sortie
            format_type: Format d'export ('json', 'requirements', 'pyproject')
            include_metadata: Inclut les métadonnées
            include_lock: Inclut les informations de lock
            
        Returns:
            Tuple contenant (succès, message ou chemin du fichier)
        """
        try:
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return False, f"L'environnement '{name}' n'existe pas"
            
            if format_type.lower() == "requirements":
                # Export au format requirements.txt
                output_file = Path(output_path) if output_path else self.env_service.get_requirements_output_path(name)
                success, export_path = self._export_requirements(env_info, output_file)
                if success:
                    return True, f"Export requirements.txt vers {export_path}"
                else:
                    return False, "Erreur lors de l'export requirements.txt"
            
            elif format_type.lower() == "pyproject":
                # Export au format pyproject.toml
                if not env_info.pyproject_info:
                    return False, f"L'environnement '{name}' n'a pas de configuration pyproject.toml"
                
                output_file = Path(output_path) if output_path else Path(f"{name}_pyproject.toml")
                success = self._export_pyproject(env_info, output_file)
                if success:
                    return True, f"Export pyproject.toml vers {output_file}"
                else:
                    return False, "Erreur lors de l'export pyproject.toml"
            
            else:
                # Export au format JSON (par défaut)
                export_data = env_info.to_dict()
                
                if include_metadata:
                    export_data["_export_metadata"] = {
                        "exported_at": datetime.now().isoformat(),
                        "exported_by": "gestvenv",
                        "gestvenv_version": "1.1.0",
                        "format_version": "1.1"
                    }
                
                if include_lock and env_info.lock_file_info:
                    export_data["_lock_file_content"] = self._read_lock_file(env_info.lock_file_info.file_path)
                
                output_file = Path(output_path) if output_path else self.env_service.get_json_output_path(name)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                return True, f"Export JSON vers {output_file}"
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {str(e)}")
            return False, f"Erreur lors de l'export: {str(e)}"
    
    def import_environment(self, input_path: str, name: Optional[str] = None,
                          force: bool = False, update_existing: bool = False) -> Tuple[bool, str]:
        """
        Importe un environnement depuis un fichier de configuration.
        
        Args:
            input_path: Chemin vers le fichier de configuration
            name: Nom pour le nouvel environnement
            force: Force l'import même si l'environnement existe
            update_existing: Met à jour un environnement existant
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            input_file = Path(input_path)
            if not input_file.exists():
                return False, f"Le fichier '{input_path}' n'existe pas"
            
            file_extension = input_file.suffix.lower()
            
            if file_extension == ".json":
                return self._import_from_json(input_file, name, force, update_existing)
            elif file_extension == ".txt":
                return self._import_from_requirements(input_file, name, force)
            elif file_extension == ".toml":
                return self._import_from_pyproject(input_file, name, force)
            else:
                return False, f"Format de fichier non supporté: {file_extension}"
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import: {str(e)}")
            return False, f"Erreur lors de l'import: {str(e)}"
    
    def _import_from_json(self, json_file: Path, name: Optional[str],
                         force: bool, update_existing: bool) -> Tuple[bool, str]:
        """Importe depuis un fichier JSON."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Valider le format
            if "name" not in data or "path" not in data:
                return False, "Format JSON invalide: champs requis manquants"
            
            env_name = name or data["name"]
            
            # Vérifier si l'environnement existe
            if self.config_manager.environment_exists(env_name):
                if not force and not update_existing:
                    return False, f"L'environnement '{env_name}' existe déjà"
                elif update_existing:
                    # Mettre à jour l'environnement existant
                    env_info = EnvironmentInfo.from_dict(data)
                    env_info.name = env_name
                    self.config_manager.update_environment(env_info)
                    return True, f"Environnement '{env_name}' mis à jour"
            
            # Créer le nouvel environnement
            packages = data.get("packages", [])
            python_version = data.get("python_version", "python3")
            backend_type = BackendType.PIP
            
            if "backend_type" in data:
                try:
                    backend_type = BackendType(data["backend_type"])
                except ValueError:
                    backend_type = BackendType.PIP
            
            success, message = self.create_environment(
                name=env_name,
                python_version=python_version,
                packages=packages,
                backend=backend_type
            )
            
            if success:
                # Restaurer les métadonnées supplémentaires
                env_info = self.config_manager.get_environment(env_name)
                if env_info and "description" in data:
                    env_info.description = data["description"]
                    env_info.tags = data.get("tags", [])
                    env_info.aliases = data.get("aliases", [])
                    self.config_manager.update_environment(env_info)
                
                return True, f"Environnement importé avec succès: {env_name}"
            else:
                return False, f"Erreur création environnement: {message}"
            
        except Exception as e:
            return False, f"Erreur import JSON: {str(e)}"
    
    def _import_from_requirements(self, req_file: Path, name: Optional[str],
                                 force: bool) -> Tuple[bool, str]:
        """Importe depuis un fichier requirements.txt."""
        try:
            if not name:
                return False, "Un nom d'environnement doit être spécifié pour l'import requirements.txt"
            
            # Valider le nom
            validation_errors = validate_environment_name(name)
            if validation_errors:
                error_msg = "; ".join([err.message for err in validation_errors])
                return False, f"Nom invalide: {error_msg}"
            
            # Vérifier si l'environnement existe
            if self.config_manager.environment_exists(name) and not force:
                return False, f"L'environnement '{name}' existe déjà"
            
            # Lire les packages
            with open(req_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            packages = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    packages.append(line)
            
            # Créer l'environnement
            success, message = self.create_environment(
                name=name,
                packages=packages
            )
            
            if success:
                return True, f"Environnement importé depuis requirements.txt: {name}"
            else:
                return False, f"Erreur création: {message}"
                
        except Exception as e:
            return False, f"Erreur import requirements.txt: {str(e)}"
    
    def _import_from_pyproject(self, pyproject_file: Path, name: Optional[str],
                              force: bool) -> Tuple[bool, str]:
        """Importe depuis un fichier pyproject.toml."""
        try:
            from ..utils.pyproject_parser import PyProjectParser
            parser = PyProjectParser(pyproject_file)
            pyproject_info = parser.extract_info()
            
            env_name = name or pyproject_info.name or pyproject_file.stem
            
            if self.config_manager.environment_exists(env_name) and not force:
                return False, f"L'environnement '{env_name}' existe déjà"
            
            # Créer l'environnement depuis pyproject.toml
            success, message = self.create_from_pyproject(
                pyproject_path=pyproject_file,
                env_name=env_name
            )
            
            if success:
                return True, f"Environnement importé depuis pyproject.toml: {env_name}"
            else:
                return False, f"Erreur création: {message}"
                
        except Exception as e:
            return False, f"Erreur import pyproject.toml: {str(e)}"
    
    def run_command_in_environment(self, env_name: str, command: List[str]) -> Tuple[int, str, str]:
        """
        Exécute une commande dans un environnement virtuel spécifique.
        
        Args:
            env_name: Nom de l'environnement
            command: Commande à exécuter
            
        Returns:
            Tuple contenant (code de retour, sortie standard, sortie d'erreur)
        """
        try:
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return 1, "", f"L'environnement '{env_name}' n'existe pas"
            
            # Exécuter la commande
            return self.sys_service.run_in_environment(env_name, env_info.path, command)
            
        except Exception as e:
            logger.error(f"Erreur exécution commande: {str(e)}")
            return 1, "", f"Erreur exécution: {str(e)}"
    
    def update_packages(self, env_name: str, packages: Optional[str] = None,
                       all_packages: bool = False, upgrade_strategy: str = "only-if-needed") -> Tuple[bool, str]:
        """
        Met à jour des packages dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement
            packages: Liste de packages à mettre à jour
            all_packages: Met à jour tous les packages
            upgrade_strategy: Stratégie de mise à jour
            
        Returns:
            Tuple contenant (succès, message)
        """
        start_time = time.time()
        
        try:
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return False, f"L'environnement '{env_name}' n'existe pas"
            
            if not self.env_service.check_environment_exists(env_info.path):
                return False, f"L'environnement '{env_name}' n'existe pas physiquement"
            
            # Obtenir le backend
            backend = self.available_backends[env_info.backend_type]
            if not backend.is_available():
                return False, f"Backend '{env_info.backend_type.value}' non disponible"
            
            # Déterminer les packages à mettre à jour
            packages_to_update = []
            if all_packages:
                installed = self._get_installed_packages(env_info)
                packages_to_update = [pkg.name for pkg in installed]
            elif packages:
                packages_to_update = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
            else:
                return False, "Aucun package spécifié et --all non utilisé"
            
            if not packages_to_update:
                return True, "Aucun package à mettre à jour"
            
            # Effectuer la mise à jour
            success = backend.update_packages(env_info.path, packages_to_update, upgrade_strategy)
            
            if success:
                # Mettre à jour les informations de l'environnement
                env_info.packages_installed = self._get_installed_packages(env_info)
                env_info.last_used = datetime.now()
                env_info.usage_count += 1
                self.config_manager.update_environment(env_info)
                
                # Enregistrer les métriques
                duration = time.time() - start_time
                metrics = PerformanceMetrics(
                    environment_name=env_name,
                    backend_type=env_info.backend_type.value,
                    measurement_type="update",
                    duration=duration,
                    package_count=len(packages_to_update),
                    success=True
                )
                self.performance_metrics.append(metrics)
                
                count = len(packages_to_update)
                return True, f"{count} package(s) mis à jour avec succès"
            else:
                return False, "Échec de la mise à jour des packages"
            
        except Exception as e:
            logger.error(f"Erreur mise à jour packages: {str(e)}")
            return False, f"Erreur mise à jour: {str(e)}"
    
    def check_for_updates(self, env_name: str) -> Tuple[bool, List[Dict[str, str]], str]:
        """
        Vérifie les mises à jour disponibles pour les packages d'un environnement.
        
        Args:
            env_name: Nom de l'environnement
            
        Returns:
            Tuple contenant (succès, liste des mises à jour, message)
        """
        try:
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return False, [], f"L'environnement '{env_name}' n'existe pas"
            
            # Obtenir le backend
            backend = self.available_backends[env_info.backend_type]
            if not backend.is_available():
                return False, [], f"Backend '{env_info.backend_type.value}' non disponible"
            
            # Vérifier les mises à jour
            if hasattr(backend, 'check_updates'):
                updates = backend.check_updates(env_info.path)
                
                if not updates:
                    return True, [], "Tous les packages sont à jour"
                
                return True, updates, f"{len(updates)} package(s) peuvent être mis à jour"
            else:
                # Fallback: utiliser le service de packages
                updates = self.pkg_service.check_for_updates(env_name)
                
                if not updates:
                    return True, [], "Tous les packages sont à jour"
                
                return True, updates, f"{len(updates)} package(s) peuvent être mis à jour"
                
        except Exception as e:
            logger.error(f"Erreur vérification mises à jour: {str(e)}")
            return False, [], f"Erreur vérification: {str(e)}"
    
    def get_active_environment(self) -> Optional[str]:
        """
        Retourne le nom de l'environnement actif.
        
        Returns:
            Nom de l'environnement actif ou None
        """
        return self.config_manager.get_active_environment()
    
    def set_default_python(self, python_cmd: str) -> Tuple[bool, str]:
        """
        Définit la commande Python par défaut.
        
        Args:
            python_cmd: Commande Python à utiliser par défaut
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            # Valider la commande Python
            python_errors = validate_python_version(python_cmd)
            if python_errors:
                error_msg = "; ".join([err.message for err in python_errors])
                return False, f"Version Python invalide: {error_msg}"
            
            # Vérifier la disponibilité
            version = self.sys_service.check_python_version(python_cmd)
            if not version:
                return False, f"La commande Python '{python_cmd}' n'est pas disponible"
            
            # Mettre à jour la configuration
            if not self.config_manager.set_default_python(python_cmd):
                return False, "Erreur lors de la sauvegarde de la configuration"
            
            return True, f"Python par défaut défini à '{python_cmd}' (version {version})"
            
        except Exception as e:
            logger.error(f"Erreur définition Python par défaut: {str(e)}")
            return False,"L'environnement '{env_name}' n'existe pas"
            
            # Vérifier si l'environnement a des sources de configuration
            if not env_info.pyproject_info and not env_info.packages:
                return False, f"L'environnement '{env_name}' n'a pas de configuration de packages"
            
            # Obtenir le backend
            backend = self.available_backends[env_info.backend_type]
            if not backend.is_available():
                return False, f"Backend '{env_info.backend_type.value}' non disponible"
            
            success = True
            message = ""
            
            # Synchronisation selon le type de source
            if env_info.pyproject_info and env_info.project_path:
                pyproject_path = env_info.project_path / "pyproject.toml"
                if pyproject_path.exists():
                    # Synchronisation avec pyproject.toml
                    success = backend.sync_from_pyproject(env_info.path, pyproject_path, groups)
                    message = f"Synchronisation avec pyproject.toml"
                    
                    # Mettre à jour le lock file si demandé
                    if update_lock and hasattr(backend, 'update_lock_file'):
                        try:
                            backend.update_lock_file(env_info.path, pyproject_path)
                        except Exception as e:
                            logger.warning(f"Erreur mise à jour lock file: {e}")
                else:
                    return False, f"Fichier pyproject.toml non trouvé à {pyproject_path}"
            else:
                # Synchronisation avec la liste de packages
                if env_info.packages:
                    success = backend.install_packages(env_info.path, env_info.packages)
                    message = f"Synchronisation avec la liste de packages"
            
            if success:
                # Mettre à jour les informations de l'environnement
                env_info.health = self.env_service.check_environment_health(env_name, env_info.path)
                env_info.last_used = datetime.now()
                env_info.usage_count += 1
                
                # Mettre à jour les packages installés
                installed_packages = self._get_installed_packages(env_info)
                env_info.packages_installed = installed_packages
                
                # Sauvegarder la configuration
                self.config_manager.update_environment(env_info)
                
                # Enregistrer les métriques
                duration = time.time() - start_time
                metrics = PerformanceMetrics(
                    environment_name=env_name,
                    backend_type=env_info.backend_type.value,
                    measurement_type="sync",
                    duration=duration,
                    package_count=len(installed_packages),
                    success=True
                )
                self.performance_metrics.append(metrics)
                
                return True, f"Environnement '{env_name}' synchronisé avec succès"
            else:
                return False, f"Échec de la synchronisation de l'environnement '{env_name}'"
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {str(e)}")
            return False, f"Erreur lors de la synchronisation: {str(e)}"
    
    def add_package_to_environment(self, env_name: str, package: str,
                                  group: Optional[str] = None,
                                  update_config: bool = True) -> Tuple[bool, str]:
        """
        Ajoute un package à un environnement avec mise à jour de la configuration.
        
        Args:
            env_name: Nom de l'environnement
            package: Package à ajouter
            group: Groupe de dépendance (dev, test, etc.)
            update_config: Met à jour les fichiers de configuration
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return False, f"L'environnement '{env_name}' n'existe pas"
            
            # Installer le package
            backend = self.available_backends[env_info.backend_type]
            success = backend.install_packages(env_info.path, [package])
            
            if not success:
                return False, f"Échec de l'installation du package '{package}'"
            
            # Mettre à jour la configuration
            if update_config:
                if group and group != "main":
                    # Ajouter au groupe spécifié
                    if group not in env_info.dependency_groups:
                        env_info.dependency_groups[group] = []
                    if package not in env_info.dependency_groups[group]:
                        env_info.dependency_groups[group].append(package)
                else:
                    # Ajouter aux packages principaux
                    if package not in env_info.packages:
                        env_info.packages.append(package)
                
                # Mettre à jour pyproject.toml si présent
                if env_info.pyproject_info and env_info.project_path:
                    self._update_pyproject_dependencies(env_info, package, group)
            
            # Mettre à jour les packages installés
            env_info.packages_installed = self._get_installed_packages(env_info)
            env_info.last_used = datetime.now()
            env_info.usage_count += 1
            
            # Sauvegarder
            self.config_manager.update_environment(env_info)
            
            return True, f"Package '{package}' ajouté avec succès à l'environnement '{env_name}'"
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du package: {str(e)}")
            return False, f"Erreur lors de l'ajout du package: {str(e)}"
    
    def _update_pyproject_dependencies(self, env_info: EnvironmentInfo, 
                                     package: str, group: Optional[str] = None) -> None:
        """Met à jour les dépendances dans pyproject.toml."""
        try:
            if not env_info.project_path:
                return
            
            pyproject_path = env_info.project_path / "pyproject.toml"
            if not pyproject_path.exists():
                return
            
            from ..utils.pyproject_parser import PyProjectParser
            parser = PyProjectParser(pyproject_path)
            
            # Ajouter le package au groupe approprié
            if group and group != "main":
                parser.add_optional_dependency(group, package)
            else:
                parser.add_dependency(package)
            
            # Sauvegarder le fichier
            parser.save()
            
        except Exception as e:
            logger.warning(f"Erreur mise à jour pyproject.toml: {e}")
    
    def activate_environment(self, name: str) -> Tuple[bool, str]:
        """
        Définit un environnement comme actif et retourne la commande pour l'activer.
        
        Args:
            name: Nom de l'environnement à activer
            
        Returns:
            Tuple contenant (succès, message ou commande d'activation)
        """
        try:
            # Vérifier si l'environnement existe
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return False, f"L'environnement '{name}' n'existe pas"
            
            # Vérifier si l'environnement existe physiquement
            if not self.env_service.check_environment_exists(env_info.path):
                return False, f"L'environnement '{name}' n'existe pas physiquement à {env_info.path}"
            
            # Obtenir la commande d'activation
            activation_cmd = self.sys_service.get_activation_command(name, env_info.path)
            if not activation_cmd:
                return False, f"Impossible de générer la commande d'activation pour '{name}'"
            
            # Définir l'environnement comme actif
            self.config_manager.set_active_environment(name)
            
            # Mettre à jour les statistiques d'utilisation
            env_info.last_used = datetime.now()
            env_info.usage_count += 1
            self.config_manager.update_environment(env_info)
            
            # Vérifier les mises à jour si configuré
            if self.config_manager.get_setting("check_updates_on_activate", False):
                try:
                    self._check_updates_async(name)
                except Exception as e:
                    logger.debug(f"Erreur vérification mises à jour: {e}")
            
            return True, activation_cmd
            
        except Exception as e:
            logger.error(f"Erreur lors de l'activation: {str(e)}")
            return False, f"Erreur lors de l'activation: {str(e)}"
    
    def deactivate_environment(self) -> Tuple[bool, str]:
        """
        Désactive l'environnement actif et retourne la commande de désactivation.
        
        Returns:
            Tuple contenant (succès, message ou commande de désactivation)
        """
        try:
            # Vérifier s'il y a un environnement actif
            active_env = self.config_manager.get_active_environment()
            if not active_env:
                return False, "Aucun environnement actif à désactiver"
            
            # Réinitialiser l'environnement actif
            self.config_manager.clear_active_environment()
            
            # Commande de désactivation standard
            deactivate_cmd = "deactivate"
            
            return True, deactivate_cmd
            
        except Exception as e:
            logger.error(f"Erreur lors de la désactivation: {str(e)}")
            return False, f"Erreur lors de la désactivation: {str(e)}"
    
    def delete_environment(self, name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Supprime un environnement virtuel.
        
        Args:
            name: Nom de l'environnement à supprimer
            force: Force la suppression sans vérifications
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            # Vérifier si l'environnement existe
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return False, f"Erreur lors de la définition Python: {str(e)}"
    
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Retourne des informations sur les backends disponibles.
        
        Returns:
            Dict: Informations sur les backends
        """
        try:
            backend_info = {}
            
            for backend_type, backend_instance in self.available_backends.items():
                backend_info[backend_type.value] = {
                    "available": backend_instance.is_available(),
                    "version": backend_instance.version,
                    "name": backend_instance.name,
                    "description": getattr(backend_instance, 'description', ''),
                    "features": getattr(backend_instance, 'supported_features', []),
                    "performance_score": self._calculate_backend_performance(backend_type)
                }
            
            return {
                "available_backends": backend_info,
                "preferred_backend": self.config_manager.config.preferred_backend.value,
                "backend_settings": self.config_manager.config.backend_settings
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération infos backends: {str(e)}")
            return {}
    
    def set_preferred_backend(self, backend: Union[str, BackendType]) -> Tuple[bool, str]:
        """
        Définit le backend préféré.
        
        Args:
            backend: Backend à définir comme préféré
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            backend_type = backend
            if isinstance(backend, str):
                try:
                    backend_type = BackendType(backend)
                except ValueError:
                    return False, f"Backend '{backend}' non reconnu"
            
            # Vérifier que le backend est disponible
            if backend_type not in self.available_backends:
                return False, f"Backend '{backend_type.value}' non disponible"
            
            backend_instance = self.available_backends[backend_type]
            if not backend_instance.is_available():
                return False, f"Backend '{backend_type.value}' non installé"
            
            # Mettre à jour la configuration
            self.config_manager.config.preferred_backend = backend_type
            self.config_manager.save_config()
            
            return True, f"Backend préféré défini à '{backend_type.value}'"
            
        except Exception as e:
            logger.error(f"Erreur définition backend préféré: {str(e)}")
            return False, f"Erreur définition backend: {str(e)}"
    
    def get_environment_statistics(self) -> Dict[str, Any]:
        """
        Retourne des statistiques globales sur les environnements.
        
        Returns:
            Dict: Statistiques des environnements
        """
        try:
            stats = self.config_manager.config.get_environment_stats()
            
            # Ajouter des statistiques de performance
            if self.performance_metrics:
                performance_stats = {
                    "total_operations": len(self.performance_metrics),
                    "average_duration": sum(m.duration for m in self.performance_metrics) / len(self.performance_metrics),
                    "success_rate": sum(1 for m in self.performance_metrics if m.success) / len(self.performance_metrics) * 100,
                    "operations_by_type": {}
                }
                
                # Statistiques par type d'opération
                operation_types = {}
                for metric in self.performance_metrics:
                    op_type = metric.measurement_type
                    if op_type not in operation_types:
                        operation_types[op_type] = {"count": 0, "duration": 0, "success": 0}
                    
                    operation_types[op_type]["count"] += 1
                    operation_types[op_type]["duration"] += metric.duration
                    if metric.success:
                        operation_types[op_type]["success"] += 1
                
                for op_type, data in operation_types.items():
                    performance_stats["operations_by_type"][op_type] = {
                        "count": data["count"],
                        "average_duration": data["duration"] / data["count"],
                        "success_rate": (data["success"] / data["count"]) * 100
                    }
                
                stats["performance"] = performance_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur récupération statistiques: {str(e)}")
            return {}
    
    def cleanup_orphaned_environments(self) -> Tuple[int, List[str]]:
        """
        Nettoie les environnements orphelins (présents en config mais absents sur disque).
        
        Returns:
            Tuple contenant (nombre supprimé, liste des noms supprimés)
        """
        try:
            removed_count = 0
            removed_names = []
            
            environments = self.config_manager.get_all_environments().copy()
            
            for name, env_info in environments.items():
                if not self.env_service.check_environment_exists(env_info.path):
                    logger.info(f"Environnement orphelin détecté: {name}")
                    
                    try:
                        self.config_manager.remove_environment(name)
                        removed_count += 1
                        removed_names.append(name)
                    except Exception as e:
                        logger.warning(f"Erreur suppression environnement orphelin {name}: {e}")
            
            return removed_count, removed_names
            
        except Exception as e:
            logger.error(f"Erreur nettoyage environnements orphelins: {str(e)}")
            return 0, []
    
    def health_check_all_environments(self) -> Dict[str, Dict[str, Any]]:
        """
        Effectue un contrôle de santé sur tous les environnements.
        
        Returns:
            Dict: Résultats du contrôle de santé par environnement
        """
        try:
            results = {}
            environments = self.config_manager.get_all_environments()
            
            for name, env_info in environments.items():
                try:
                    # Vérifier la santé
                    health = self.env_service.check_environment_health(name, env_info.path)
                    
                    # Mettre à jour dans la configuration
                    env_info.health = health
                    env_info.health.last_health_check = datetime.now()
                    
                    results[name] = {
                        "health": health.to_dict(),
                        "health_score": health.health_score,
                        "is_healthy": health.is_healthy,
                        "recommendations": self._get_health_recommendations(health)
                    }
                    
                except Exception as e:
                    logger.warning(f"Erreur contrôle santé {name}: {e}")
                    results[name] = {
                        "error": str(e),
                        "health_score": 0.0,
                        "is_healthy": False
                    }
            
            # Sauvegarder les mises à jour
            self.config_manager.save_config()
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur contrôle santé global: {str(e)}")
            return {}
    
    def _get_health_recommendations(self, health: EnvironmentHealth) -> List[str]:
        """Génère des recommandations basées sur l'état de santé."""
        recommendations = []
        
        if not health.exists:
            recommendations.append("L'environnement n'existe pas sur le disque")
        
        if not health.python_available:
            recommendations.append("L'exécutable Python n'est pas disponible")
        
        if not health.pip_available:
            recommendations.append("Pip n'est pas disponible dans l'environnement")
        
        if not health.activation_script_exists:
            recommendations.append("Le script d'activation est manquant")
        
        if not health.backend_available:
            recommendations.append("Le backend configuré n'est pas disponible")
        
        if not health.lock_file_valid:
            recommendations.append("Le fichier de lock n'est pas valide ou obsolète")
        
        if not health.dependencies_synchronized:
            recommendations.append("Les dépendances ne sont pas synchronisées")
        
        if health.security_issues:
            recommendations.append(f"{len(health.security_issues)} problème(s) de sécurité détecté(s)")
        
        return recommendations
    
    def convert_requirements_to_pyproject(self, requirements_path: Path,
                                        project_name: str, env_name: Optional[str] = None,
                                        create_env: bool = True) -> Tuple[bool, str]:
        """
        Convertit un fichier requirements.txt vers pyproject.toml.
        
        Args:
            requirements_path: Chemin vers requirements.txt
            project_name: Nom du projet
            env_name: Nom de l'environnement à créer (optionnel)
            create_env: Crée un environnement basé sur le pyproject.toml
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            from ..utils.migration_utils import RequirementsConverter
            
            if not requirements_path.exists():
                return False, f"Le fichier requirements.txt n'existe pas: {requirements_path}"
            
            # Convertir vers pyproject.toml
            converter = RequirementsConverter()
            pyproject_path = converter.convert_requirements_to_pyproject(
                requirements_path, project_name
            )
            
            message = f"Conversion réussie: {pyproject_path}"
            
            # Créer un environnement si demandé
            if create_env and env_name:
                success, env_message = self.create_from_pyproject(pyproject_path, env_name)
                if success:
                    message += f"\nEnvironnement '{env_name}' créé avec succès"
                else:
                    message += f"\nErreur création environnement: {env_message}"
            
            return True, message
            
        except Exception as e:
            logger.error(f"Erreur conversion requirements vers pyproject: {str(e)}")
            return False, f"Erreur conversion: {str(e)}"
    
    def migrate_environment_backend(self, env_name: str, 
                                   new_backend: BackendType) -> Tuple[bool, str]:
        """
        Migre un environnement vers un nouveau backend.
        
        Args:
            env_name: Nom de l'environnement
            new_backend: Nouveau backend à utiliser
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return False, f"L'environnement '{env_name}' n'existe pas"
            
            if env_info.backend_type == new_backend:
                return True, f"L'environnement utilise déjà le backend {new_backend.value}"
            
            # Vérifier que le nouveau backend est disponible
            if new_backend not in self.available_backends:
                return False, f"Backend '{new_backend.value}' non disponible"
            
            new_backend_instance = self.available_backends[new_backend]
            if not new_backend_instance.is_available():
                return False, f"Backend '{new_backend.value}' non installé"
            
            # Sauvegarder l'état actuel
            current_packages = self._get_installed_packages(env_info)
            
            # Créer un nouvel environnement avec le nouveau backend
            temp_name = f"{env_name}_migration_temp"
            success, message = self.create_environment(
                name=temp_name,
                python_version=env_info.python_version,
                packages=[pkg.name for pkg in current_packages],
                backend=new_backend
            )
            
            if not success:
                return False, f"Erreur création environnement temporaire: {message}"
            
            try:
                # Supprimer l'ancien environnement
                old_path = env_info.path
                self.config_manager.remove_environment(env_name)
                shutil.rmtree(old_path)
                
                # Renommer l'environnement temporaire
                temp_info = self.config_manager.get_environment(temp_name)
                if temp_info:
                    temp_info.name = env_name
                    temp_info.backend_type = new_backend
                    temp_info.migrated_from_version = env_info.backend_type.value
                    
                    # Déplacer l'environnement temporaire
                    new_path = self.env_service.get_environment_path(env_name)
                    shutil.move(temp_info.path, new_path)
                    temp_info.path = new_path
                    
                    # Mettre à jour la configuration
                    self.config_manager.remove_environment(temp_name)
                    self.config_manager.add_environment(temp_info)
                
                return True, f"Environnement migré vers le backend {new_backend.value}"
                
            except Exception as e:
                # Rollback en cas d'erreur
                try:
                    self.config_manager.remove_environment(temp_name)
                    temp_info = self.config_manager.get_environment(temp_name)
                    if temp_info:
                        shutil.rmtree(temp_info.path)
                except Exception:
                    pass
                
                raise e
            
        except Exception as e:
            logger.error(f"Erreur migration backend: {str(e)}")
            return False, f"Erreur migration: {str(e)}"
    
    # Méthodes utilitaires privées
    
    def _install_packages_in_env(self, env_info: EnvironmentInfo, 
                                packages: List[str], offline: bool = False) -> Tuple[bool, str]:
        """Installe des packages dans un environnement."""
        try:
            backend = self.available_backends[env_info.backend_type]
            
            # Vérifier la disponibilité hors ligne si nécessaire
            if offline:
                missing_packages = self._check_packages_in_cache(packages)
                if missing_packages:
                    return False, f"Packages manquants dans le cache: {', '.join(missing_packages)}"
            
            # Installer les packages
            success = backend.install_packages(env_info.path, packages, offline=offline)
            
            if success:
                return True, f"{len(packages)} package(s) installé(s)"
            else:
                return False, "Échec de l'installation des packages"
                
        except Exception as e:
            logger.error(f"Erreur installation packages: {str(e)}")
            return False, f"Erreur installation: {str(e)}"
    
    def _get_installed_packages(self, env_info: EnvironmentInfo) -> List[PackageInfo]:
        """Récupère la liste des packages installés dans un environnement."""
        try:
            backend = self.available_backends[env_info.backend_type]
            packages_data = backend.get_installed_packages(env_info.path)
            
            packages = []
            for pkg_data in packages_data:
                package_info = PackageInfo(
                    name=pkg_data.get("name", ""),
                    version=pkg_data.get("version", ""),
                    dependencies=pkg_data.get("dependencies", []),
                    source=pkg_data.get("source", "pypi")
                )
                packages.append(package_info)
            
            return packages
            
        except Exception as e:
            logger.error(f"Erreur récupération packages installés: {str(e)}")
            return []
    
    def _check_packages_in_cache(self, packages: List[str]) -> List[str]:
        """Vérifie quels packages manquent dans le cache."""
        missing = []
        
        try:
            for package in packages:
                # Parser le nom et la version
                pkg_name = package.split('==')[0].split('>')[0].split('<')[0].strip()
                pkg_version = None
                
                if '==' in package:
                    pkg_version = package.split('==')[1].strip()
                
                if not self.cache_service.has_package(pkg_name, pkg_version):
                    missing.append(package)
            
        except Exception as e:
            logger.warning(f"Erreur vérification cache: {e}")
            missing = packages  # En cas d'erreur, considérer tous les packages comme manquants
        
        return missing
    
    def _export_requirements(self, env_info: EnvironmentInfo, output_path: Path) -> Tuple[bool, str]:
        """Exporte les packages vers un fichier requirements.txt."""
        try:
            backend = self.available_backends[env_info.backend_type]
            
            if hasattr(backend, 'export_requirements'):
                success = backend.export_requirements(env_info.path, output_path)
            else:
                # Fallback: générer le fichier manuellement
                packages = self._get_installed_packages(env_info)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Requirements for environment: {env_info.name}\n")
                    f.write(f"# Generated on: {datetime.now().isoformat()}\n\n")
                    
                    for pkg in packages:
                        f.write(f"{pkg.name}=={pkg.version}\n")
                
                success = True
            
            return success, str(output_path)
            
        except Exception as e:
            logger.error(f"Erreur export requirements: {str(e)}")
            return False, f"Erreur export: {str(e)}"
    
    def _export_pyproject(self, env_info: EnvironmentInfo, output_path: Path) -> bool:
        """Exporte la configuration vers un fichier pyproject.toml."""
        try:
            if not env_info.pyproject_info:
                return False
            
            from ..utils.toml_utils import TomlHandler
            
            # Préparer les données pour export
            pyproject_data = {
                "project": {
                    "name": env_info.pyproject_info.name,
                    "version": env_info.pyproject_info.version,
                    "description": env_info.pyproject_info.description,
                    "dependencies": env_info.pyproject_info.dependencies,
                    "optional-dependencies": env_info.pyproject_info.optional_dependencies
                }
            }
            
            if env_info.pyproject_info.requires_python:
                pyproject_data["project"]["requires-python"] = env_info.pyproject_info.requires_python
            
            if env_info.pyproject_info.build_system:
                pyproject_data["build-system"] = env_info.pyproject_info.build_system
            
            # Sauvegarder le fichier
            TomlHandler.dump(pyproject_data, output_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur export pyproject: {str(e)}")
            return False
    
    def _read_lock_file(self, lock_path: Path) -> Optional[str]:
        """Lit le contenu d'un fichier de lock."""
        try:
            if not lock_path.exists():
                return None
            
            with open(lock_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            logger.warning(f"Erreur lecture lock file: {e}")
            return None
    
    def _check_updates_async(self, env_name: str) -> None:
        """Vérifie les mises à jour de manière asynchrone."""
        try:
            # Cette méthode sera appelée en arrière-plan
            success, updates, message = self.check_for_updates(env_name)
            
            if success and updates:
                logger.info(f"{len(updates)} mise(s) à jour disponible(s) pour {env_name}")
                
                # Optionnel: notifier l'utilisateur ou enregistrer dans les logs
                self._log_available_updates(env_name, updates)
                
        except Exception as e:
            logger.debug(f"Erreur vérification mises à jour async: {e}")
    
    def _log_available_updates(self, env_name: str, updates: List[Dict[str, str]]) -> None:
        """Enregistre les mises à jour disponibles."""
        try:
            update_log_path = self.config_manager.config_path.parent / "updates.log"
            
            with open(update_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{datetime.now().isoformat()} - {env_name}:\n")
                for update in updates:
                    name = update.get("name", "Unknown")
                    current = update.get("current_version", "?")
                    latest = update.get("latest_version", "?")
                    f.write(f"  {name}: {current} → {latest}\n")
                
        except Exception as e:
            logger.debug(f"Erreur enregistrement log mises à jour: {e}")
    
    def _calculate_backend_performance(self, backend_type: BackendType) -> float:
        """Calcule un score de performance pour un backend."""
        try:
            # Filtrer les métriques pour ce backend
            backend_metrics = [
                m for m in self.performance_metrics 
                if m.backend_type == backend_type.value
            ]
            
            if not backend_metrics:
                return 0.0
            
            # Calculer le score basé sur la vitesse et le taux de succès
            avg_speed = sum(m.packages_per_second for m in backend_metrics) / len(backend_metrics)
            success_rate = sum(1 for m in backend_metrics if m.success) / len(backend_metrics)
            
            # Score normalisé (0.0 - 1.0)
            speed_score = min(1.0, avg_speed / 10.0)  # Normaliser sur 10 packages/sec
            performance_score = (speed_score * 0.7) + (success_rate * 0.3)
            
            return round(performance_score, 2)
            
        except Exception as e:
            logger.debug(f"Erreur calcul performance backend: {e}")
            return 0.0
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Génère un rapport de performance détaillé.
        
        Returns:
            Dict: Rapport de performance
        """
        try:
            if not self.performance_metrics:
                return {"message": "Aucune métrique de performance disponible"}
            
            # Statistiques globales
            total_operations = len(self.performance_metrics)
            successful_operations = sum(1 for m in self.performance_metrics if m.success)
            average_duration = sum(m.duration for m in self.performance_metrics) / total_operations
            
            # Statistiques par backend
            backend_stats = {}
            for backend_type in BackendType:
                backend_metrics = [
                    m for m in self.performance_metrics 
                    if m.backend_type == backend_type.value
                ]
                
                if backend_metrics:
                    backend_stats[backend_type.value] = {
                        "operations": len(backend_metrics),
                        "success_rate": sum(1 for m in backend_metrics if m.success) / len(backend_metrics) * 100,
                        "average_duration": sum(m.duration for m in backend_metrics) / len(backend_metrics),
                        "average_packages_per_second": sum(m.packages_per_second for m in backend_metrics) / len(backend_metrics),
                        "performance_score": self._calculate_backend_performance(backend_type)
                    }
            
            # Statistiques par type d'opération
            operation_stats = {}
            operation_types = set(m.measurement_type for m in self.performance_metrics)
            
            for op_type in operation_types:
                op_metrics = [m for m in self.performance_metrics if m.measurement_type == op_type]
                operation_stats[op_type] = {
                    "count": len(op_metrics),
                    "success_rate": sum(1 for m in op_metrics if m.success) / len(op_metrics) * 100,
                    "average_duration": sum(m.duration for m in op_metrics) / len(op_metrics)
                }
            
            # Recommandations
            recommendations = []
            
            # Recommandation de backend
            if len(backend_stats) > 1:
                best_backend = max(backend_stats.items(), key=lambda x: x[1]["performance_score"])
                recommendations.append(
                    f"Le backend {best_backend[0]} présente les meilleures performances "
                    f"(score: {best_backend[1]['performance_score']})"
                )
            
            # Recommandations d'optimisation
            slow_operations = [m for m in self.performance_metrics if m.duration > 60]  # > 1 minute
            if slow_operations:
                recommendations.append(
                    f"{len(slow_operations)} opération(s) lente(s) détectée(s). "
                    "Considérez l'utilisation du cache ou d'un backend plus rapide."
                )
            
            return {
                "summary": {
                    "total_operations": total_operations,
                    "successful_operations": successful_operations,
                    "success_rate": (successful_operations / total_operations) * 100,
                    "average_duration": round(average_duration, 2)
                },
                "backend_performance": backend_stats,
                "operation_statistics": operation_stats,
                "recommendations": recommendations,
                "report_generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur génération rapport performance: {str(e)}")
            return {"error": f"Erreur génération rapport: {str(e)}"}
    
    def clear_performance_metrics(self) -> None:
        """Efface les métriques de performance."""
        self.performance_metrics.clear()
        logger.info("Métriques de performance effacées")
    
    def __del__(self):
        """Destructeur - sauvegarde les métriques si nécessaire."""
        try:
            # Sauvegarder les métriques de performance si configuré
            if (self.performance_metrics and 
                self.config_manager.get_setting("save_performance_metrics", False)):
                
                metrics_file = self.config_manager.config_path.parent / "performance_metrics.json"
                metrics_data = [m.to_dict() for m in self.performance_metrics]
                
                with open(metrics_file, 'w', encoding='utf-8') as f:
                    json.dump(metrics_data, f, indent=2)
                    
        except Exception as e:
            logger.debug(f"Erreur sauvegarde métriques à la destruction: {e}")


# Fonctions utilitaires du module

def create_environment_manager(config_path: Optional[Union[str, Path]] = None) -> EnvironmentManager:
    """
    Crée une instance d'EnvironmentManager avec gestion d'erreur.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        EnvironmentManager: Instance configurée
        
    Raises:
        RuntimeError: Si l'initialisation échoue
    """
    try:
        return EnvironmentManager(config_path)
    except Exception as e:
        logger.error(f"Erreur création EnvironmentManager: {e}")
        raise RuntimeError(f"Impossible d'initialiser GestVenv: {e}")


def get_default_environment_manager() -> EnvironmentManager:
    """
    Retourne l'instance par défaut d'EnvironmentManager.
    
    Returns:
        EnvironmentManager: Instance par défaut
    """
    global _default_manager
    
    if '_default_manager' not in globals() or _default_manager is None:
        _default_manager = create_environment_manager()
    
    return _default_manager


# Variables globales
_default_manager: Optional[EnvironmentManager] = None