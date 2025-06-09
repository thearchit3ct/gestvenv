"""
Module de gestion des environnements virtuels pour GestVenv v1.1.

Ce module fournit les fonctionnalités principales pour créer, activer, supprimer
et gérer les environnements virtuels Python avec support moderne pour pyproject.toml
et backends multiples (pip/uv).

Version: 1.1.0
Compatibilité: 100% compatible avec GestVenv v1.0
Nouvelles fonctionnalités:
- Support pyproject.toml (PEP 621, 517, 518)
- Backends multiples avec auto-détection (pip/uv)
- Groupes de dépendances
- Lock files et synchronisation
- Migration automatique v1.0 → v1.1
"""

import os
import sys
import json
import platform
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set

# Imports des modules internes existants
from .models import EnvironmentInfo, PackageInfo, EnvironmentHealth
from .config_manager import ConfigManager

# Nouveaux imports v1.1
try:
    from .models import PyProjectInfo, BackendType
except ImportError:
    # Fallback pour compatibilité si modèles pas encore étendus
    PyProjectInfo = None
    BackendType = None

# Configuration du logger
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """
    Classe principale pour la gestion des environnements virtuels Python v1.1.
    
    Cette classe orchestrate toutes les opérations sur les environnements virtuels
    en utilisant les services spécialisés et maintient l'état via ConfigManager.
    
    Nouvelles fonctionnalités v1.1:
    - Support pyproject.toml complet
    - Backends multiples (pip/uv) avec auto-détection
    - Groupes de dépendances optionnelles
    - Synchronisation et lock files
    - Compatibilité ascendante 100%
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialise le gestionnaire d'environnements.
        
        Args:
            config_path: Chemin vers le fichier de configuration.
                Si None, utilise le chemin par défaut.
        """
        # Initialisation de base (compatible v1.0)
        self.config_manager = ConfigManager(config_path)
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)
        
        # Services existants v1.0
        from ..services.environment_service import EnvironmentService
        from ..services.package_service import PackageService
        from ..services.system_service import SystemService
        
        self.env_service = EnvironmentService()
        self.pkg_service = PackageService()
        self.sys_service = SystemService()
        
        # Nouveaux services v1.1
        try:
            from ..services.project_service import ProjectService
            self.project_service = ProjectService()
        except ImportError:
            logger.debug("ProjectService non disponible, fonctionnalités pyproject.toml limitées")
            self.project_service = None
            
        try:
            from ..backends import BackendManager
            self.backend_manager = BackendManager()
        except ImportError:
            logger.debug("BackendManager non disponible, utilisation pip uniquement")
            self.backend_manager = None
            
        # Nouveaux parsers v1.1
        try:
            from ..utils.pyproject_parser import PyProjectParser
            self.pyproject_parser = PyProjectParser()
        except ImportError:
            logger.debug("PyProjectParser non disponible")
            self.pyproject_parser = None
    
    # =====================================================================
    # MÉTHODES EXISTANTES V1.0 - PRÉSERVÉES POUR COMPATIBILITÉ
    # =====================================================================
    
    def create_environment(self, name: str, python_version: Optional[str] = None,
                         packages: Optional[str] = None, path: Optional[str] = None,
                         offline: bool = False, requirements_file: Optional[str] = None,
                         description: Optional[str] = None,
                         metadata: Optional[Dict[str, str]] = None,
                         # Nouveaux paramètres v1.1 (optionnels pour compatibilité)
                         backend: Optional[str] = None,
                         from_pyproject: Optional[Union[str, Path]] = None,
                         groups: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Crée un nouvel environnement virtuel Python.
        
        Args:
            name: Nom de l'environnement.
            python_version: Version Python à utiliser.
            packages: Liste de packages à installer, séparés par des virgules.
            path: Chemin personnalisé pour l'environnement.
            offline: Si True, utilise uniquement les packages du cache.
            requirements_file: Chemin vers un fichier requirements.txt.
            description: Description de l'environnement.
            metadata: Métadonnées supplémentaires.
            
            # Nouveaux paramètres v1.1
            backend: Backend à utiliser ('pip', 'uv', 'auto'). Si None, auto-détection.
            from_pyproject: Chemin vers pyproject.toml pour création depuis projet.
            groups: Groupes de dépendances à installer (pour pyproject.toml).
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            logger.info(f"Création de l'environnement '{name}' (v1.1)")
            
            # Validation du nom (logique existante préservée)
            if not self.env_service.validate_environment_name(name):
                return False, f"Nom d'environnement invalide: '{name}'"
            
            # Vérifier si l'environnement existe déjà
            if self.config_manager.get_environment(name):
                return False, f"L'environnement '{name}' existe déjà"
            
            # Déterminer le chemin de l'environnement
            if path:
                env_path = Path(path)
            else:
                env_path = self.config_manager.get_environments_directory() / name
            
            # Déterminer la version Python
            if not python_version:
                python_version = self.sys_service.get_default_python_version()
            
            # Validation de la version Python
            if not self.sys_service.validate_python_version(python_version):
                return False, f"Version Python invalide ou non trouvée: '{python_version}'"
            
            # NOUVEAU v1.1: Déterminer le backend
            selected_backend = self._determine_backend(backend, from_pyproject)
            
            # NOUVEAU v1.1: Gestion création depuis pyproject.toml
            if from_pyproject:
                return self._create_from_pyproject_internal(
                    name, from_pyproject, env_path, python_version, 
                    selected_backend, groups
                )
            
            # Création de l'environnement virtuel (logique existante + backend)
            success, message = self._create_virtual_environment(
                name, env_path, python_version, selected_backend
            )
            if not success:
                return False, message
            
            # Installation des packages
            if packages or requirements_file:
                success, install_message = self._install_initial_packages(
                    name, env_path, packages, requirements_file, offline, selected_backend
                )
                if not success:
                    # Rollback: supprimer l'environnement créé
                    self._cleanup_failed_environment(env_path)
                    return False, f"Création échouée lors de l'installation: {install_message}"
            
            # Création de l'objet EnvironmentInfo (étendu v1.1)
            env_info = self._create_environment_info(
                name, env_path, python_version, selected_backend, 
                description, metadata
            )
            
            # Sauvegarde dans la configuration
            if not self.config_manager.add_environment(env_info):
                self._cleanup_failed_environment(env_path)
                return False, "Impossible de sauvegarder la configuration de l'environnement"
            
            success_message = f"Environnement '{name}' créé avec succès"
            if selected_backend != "pip":
                success_message += f" (backend: {selected_backend})"
                
            logger.info(success_message)
            return True, success_message
            
        except Exception as e:
            error_message = f"Erreur lors de la création de l'environnement '{name}': {str(e)}"
            logger.error(error_message, exc_info=True)
            return False, error_message
    
    def activate_environment(self, name: str) -> Tuple[bool, str]:
        """
        Active un environnement virtuel (compatible v1.0).
        
        Args:
            name: Nom de l'environnement à activer.
            
        Returns:
            Tuple contenant (succès, message d'activation ou script).
        """
        try:
            # Vérifier que l'environnement existe
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return False, f"Environnement '{name}' non trouvé"
            
            # Vérifier l'état de l'environnement
            if not self.env_service.check_environment_exists(Path(env_info.path)):
                return False, f"Environnement '{name}' non trouvé sur le disque"
            
            # Générer le script d'activation
            activation_script = self.env_service.get_activation_script(Path(env_info.path))
            if not activation_script:
                return False, f"Impossible de générer le script d'activation pour '{name}'"
            
            # Marquer comme environnement actif
            self.config_manager.set_active_environment(name)
            
            return True, activation_script
            
        except Exception as e:
            error_message = f"Erreur lors de l'activation de '{name}': {str(e)}"
            logger.error(error_message, exc_info=True)
            return False, error_message
    
    def delete_environment(self, name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Supprime un environnement virtuel (compatible v1.0).
        
        Args:
            name: Nom de l'environnement à supprimer.
            force: Si True, supprime même si des erreurs surviennent.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Vérifier que l'environnement existe
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return False, f"Environnement '{name}' non trouvé"
            
            env_path = Path(env_info.path)
            
            # Vérifier s'il est actif et le désactiver si nécessaire
            active_env = self.config_manager.get_active_environment()
            if active_env == name:
                self.config_manager.set_active_environment(None)
            
            # Supprimer les fichiers de l'environnement
            if env_path.exists():
                success, message = self.env_service.delete_environment(env_path)
                if not success and not force:
                    return False, f"Impossible de supprimer les fichiers: {message}"
            
            # Supprimer de la configuration
            if not self.config_manager.remove_environment(name):
                if not force:
                    return False, "Impossible de supprimer de la configuration"
            
            return True, f"Environnement '{name}' supprimé avec succès"
            
        except Exception as e:
            error_message = f"Erreur lors de la suppression de '{name}': {str(e)}"
            logger.error(error_message, exc_info=True)
            if force:
                return True, f"Suppression forcée de '{name}' (avec erreurs)"
            return False, error_message
    
    def list_environments(self, show_all: bool = False, 
                         filter_backend: Optional[str] = None,
                         filter_pyproject: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Liste tous les environnements disponibles (étendu v1.1).
        
        Args:
            show_all: Si True, affiche tous les environnements, même ceux cassés.
            filter_backend: Filtrer par backend ('pip', 'uv', etc.).
            filter_pyproject: Filtrer par présence pyproject.toml (True/False).
            
        Returns:
            Liste des environnements avec leurs informations.
        """
        try:
            environments = []
            all_envs = self.config_manager.get_all_environments()
            active_env = self.config_manager.get_active_environment()
            
            for env_name, env_info in all_envs.items():
                # Vérifier l'existence
                exists = self.env_service.check_environment_exists(Path(env_info.path))
                
                if not show_all and not exists:
                    continue
                
                # Vérifier la santé de l'environnement
                health = None
                if exists:
                    health = self.env_service.check_environment_health(Path(env_info.path))
                
                # Informations de base (compatible v1.0)
                env_data = {
                    "name": env_name,
                    "path": str(env_info.path),
                    "python_version": env_info.python_version,
                    "active": env_name == active_env,
                    "exists": exists,
                    "healthy": health.is_healthy() if health else False,
                    "packages_count": len(env_info.packages_installed) if hasattr(env_info, 'packages_installed') else 0,
                    "created": env_info.created_at.isoformat() if hasattr(env_info, 'created_at') else None,
                    "description": getattr(env_info, 'description', None),
                }
                
                # Nouvelles informations v1.1
                if hasattr(env_info, 'backend_type'):
                    env_data["backend"] = env_info.backend_type
                if hasattr(env_info, 'pyproject_info'):
                    env_data["has_pyproject"] = env_info.pyproject_info is not None
                    if env_info.pyproject_info:
                        env_data["project_name"] = env_info.pyproject_info.name
                        env_data["dependency_groups"] = list(env_info.pyproject_info.optional_dependencies.keys())
                
                # Appliquer filtres v1.1
                if filter_backend and env_data.get("backend", "pip") != filter_backend:
                    continue
                if filter_pyproject is not None and env_data.get("has_pyproject", False) != filter_pyproject:
                    continue
                
                environments.append(env_data)
            
            # Trier par nom
            environments.sort(key=lambda x: x["name"])
            return environments
            
        except Exception as e:
            logger.error(f"Erreur lors de la liste des environnements: {str(e)}")
            return []
    
    def get_environment_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations détaillées d'un environnement (étendu v1.1).
        
        Args:
            name: Nom de l'environnement.
            
        Returns:
            Dictionnaire avec les informations ou None si non trouvé.
        """
        try:
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return None
            
            env_path = Path(env_info.path)
            exists = self.env_service.check_environment_exists(env_path)
            
            # Informations de base
            info = {
                "name": name,
                "path": str(env_info.path),
                "python_version": env_info.python_version,
                "exists": exists,
                "active": self.config_manager.get_active_environment() == name,
                "created": env_info.created_at.isoformat() if hasattr(env_info, 'created_at') else None,
                "description": getattr(env_info, 'description', None),
            }
            
            if exists:
                # Santé de l'environnement
                health = self.env_service.check_environment_health(env_path)
                info["health"] = {
                    "healthy": health.is_healthy(),
                    "python_available": health.python_available,
                    "pip_available": health.pip_available,
                    "activation_script_exists": health.activation_script_exists,
                }
                
                # Liste des packages installés
                packages = self.pkg_service.list_packages(name)
                info["packages"] = packages
                info["packages_count"] = len(packages)
            
            # Nouvelles informations v1.1
            if hasattr(env_info, 'backend_type'):
                info["backend"] = env_info.backend_type
                
            if hasattr(env_info, 'pyproject_info') and env_info.pyproject_info:
                info["pyproject"] = {
                    "name": env_info.pyproject_info.name,
                    "version": getattr(env_info.pyproject_info, 'version', None),
                    "dependencies": env_info.pyproject_info.dependencies,
                    "optional_dependencies": env_info.pyproject_info.optional_dependencies,
                    "build_system": getattr(env_info.pyproject_info, 'build_system', {}),
                }
            
            return info
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos de '{name}': {str(e)}")
            return None
    
    # =====================================================================
    # NOUVELLES MÉTHODES V1.1 - SUPPORT PYPROJECT.TOML
    # =====================================================================
    
    def create_from_pyproject(self, pyproject_path: Union[str, Path], 
                            env_name: Optional[str] = None,
                            python_version: Optional[str] = None,
                            backend: Optional[str] = None,
                            groups: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Crée un environnement depuis un fichier pyproject.toml.
        
        Args:
            pyproject_path: Chemin vers le fichier pyproject.toml.
            env_name: Nom de l'environnement (auto-généré depuis le projet si None).
            python_version: Version Python (extraite du pyproject.toml si None).
            backend: Backend à utiliser (auto-détection si None).
            groups: Groupes de dépendances optionnelles à installer.
            
        Returns:
            Tuple contenant (succès, message).
        """
        if not self.pyproject_parser:
            return False, "Support pyproject.toml non disponible. Installez les dépendances manquantes."
            
        try:
            pyproject_path = Path(pyproject_path)
            if not pyproject_path.exists():
                return False, f"Fichier pyproject.toml non trouvé: {pyproject_path}"
            
            # Parser le fichier pyproject.toml
            pyproject_info = self.pyproject_parser.parse_file(pyproject_path)
            if not pyproject_info:
                return False, "Impossible de parser le fichier pyproject.toml"
            
            # Déterminer le nom de l'environnement
            if not env_name:
                env_name = pyproject_info.name or pyproject_path.parent.name
            
            # Déterminer la version Python
            if not python_version:
                python_version = self._extract_python_version_from_pyproject(pyproject_info)
            
            # Utiliser la méthode create_environment étendue
            return self.create_environment(
                name=env_name,
                python_version=python_version,
                backend=backend,
                from_pyproject=pyproject_path,
                groups=groups,
                description=f"Environnement créé depuis {pyproject_path.name}"
            )
            
        except Exception as e:
            error_message = f"Erreur lors de la création depuis pyproject.toml: {str(e)}"
            logger.error(error_message, exc_info=True)
            return False, error_message
    
    def sync_environment(self, name: str, 
                        groups: Optional[List[str]] = None,
                        update: bool = False) -> Tuple[bool, str]:
        """
        Synchronise un environnement avec son fichier pyproject.toml.
        
        Args:
            name: Nom de l'environnement.
            groups: Groupes de dépendances à synchroniser (tous si None).
            update: Si True, met à jour les packages vers les dernières versions.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return False, f"Environnement '{name}' non trouvé"
            
            # Vérifier qu'il a une configuration pyproject.toml
            if not hasattr(env_info, 'pyproject_info') or not env_info.pyproject_info:
                return False, f"Environnement '{name}' n'a pas de configuration pyproject.toml"
            
            if not self.project_service:
                return False, "Service pyproject.toml non disponible"
            
            # Synchroniser avec le backend approprié
            backend = getattr(env_info, 'backend_type', 'pip')
            success, message = self.project_service.sync_environment(
                env_info, groups, update, backend
            )
            
            if success:
                # Mettre à jour les informations de l'environnement
                self._update_environment_packages(name)
                logger.info(f"Environnement '{name}' synchronisé avec succès")
            
            return success, message
            
        except Exception as e:
            error_message = f"Erreur lors de la synchronisation de '{name}': {str(e)}"
            logger.error(error_message, exc_info=True)
            return False, error_message
    
    def install_dependency_groups(self, name: str, groups: List[str]) -> Tuple[bool, str]:
        """
        Installe des groupes de dépendances optionnelles.
        
        Args:
            name: Nom de l'environnement.
            groups: Liste des groupes à installer (ex: ['dev', 'test']).
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return False, f"Environnement '{name}' non trouvé"
            
            if not hasattr(env_info, 'pyproject_info') or not env_info.pyproject_info:
                return False, f"Environnement '{name}' n'a pas de configuration pyproject.toml"
            
            # Vérifier que les groupes existent
            available_groups = set(env_info.pyproject_info.optional_dependencies.keys())
            invalid_groups = set(groups) - available_groups
            if invalid_groups:
                return False, f"Groupes non trouvés: {', '.join(invalid_groups)}. Disponibles: {', '.join(available_groups)}"
            
            # Installer les groupes
            if self.project_service:
                backend = getattr(env_info, 'backend_type', 'pip')
                success, message = self.project_service.install_dependency_groups(
                    env_info, groups, backend
                )
            else:
                # Fallback avec PackageService
                packages_to_install = []
                for group in groups:
                    packages_to_install.extend(env_info.pyproject_info.optional_dependencies[group])
                
                success, message = self.pkg_service.install_packages(name, packages_to_install)
            
            if success:
                self._update_environment_packages(name)
                logger.info(f"Groupes {groups} installés dans '{name}'")
            
            return success, message
            
        except Exception as e:
            error_message = f"Erreur lors de l'installation des groupes dans '{name}': {str(e)}"
            logger.error(error_message, exc_info=True)
            return False, error_message
    
    def export_to_pyproject(self, name: str, output_path: Union[str, Path],
                          include_versions: bool = True,
                          groups: Optional[Dict[str, List[str]]] = None) -> Tuple[bool, str]:
        """
        Exporte un environnement vers un fichier pyproject.toml.
        
        Args:
            name: Nom de l'environnement.
            output_path: Chemin de sortie pour pyproject.toml.
            include_versions: Si True, inclut les versions exactes des packages.
            groups: Groupes de dépendances personnalisés.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            env_info = self.config_manager.get_environment(name)
            if not env_info:
                return False, f"Environnement '{name}' non trouvé"
            
            if not self.pyproject_parser:
                return False, "Support pyproject.toml non disponible"
            
            # Récupérer les packages installés
            packages = self.pkg_service.list_packages(name)
            
            # Créer la structure pyproject.toml
            pyproject_data = self._create_pyproject_structure(
                env_info, packages, include_versions, groups
            )
            
            # Écrire le fichier
            output_path = Path(output_path)
            success = self.pyproject_parser.write_file(output_path, pyproject_data)
            
            if success:
                message = f"Environnement '{name}' exporté vers {output_path}"
                logger.info(message)
                return True, message
            else:
                return False, f"Impossible d'écrire le fichier {output_path}"
                
        except Exception as e:
            error_message = f"Erreur lors de l'export de '{name}': {str(e)}"
            logger.error(error_message, exc_info=True)
            return False, error_message
    
    # =====================================================================
    # NOUVELLES MÉTHODES V1.1 - GESTION BACKENDS
    # =====================================================================
    
    def set_preferred_backend(self, backend: str) -> Tuple[bool, str]:
        """
        Définit le backend préféré pour les nouveaux environnements.
        
        Args:
            backend: Nom du backend ('pip', 'uv', 'auto').
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            if not self.backend_manager:
                if backend == "pip":
                    self.config_manager.set_setting("preferred_backend", "pip")
                    return True, "Backend préféré défini à 'pip'"
                else:
                    return False, "Gestion des backends non disponible. Seul 'pip' est supporté."
            
            return self.backend_manager.set_preferred_backend(backend)
            
        except Exception as e:
            error_message = f"Erreur lors de la définition du backend: {str(e)}"
            logger.error(error_message, exc_info=True)
            return False, error_message
    
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur les backends disponibles.
        
        Returns:
            Dictionnaire avec les informations des backends.
        """
        try:
            if self.backend_manager:
                return self.backend_manager.get_backend_info()
            else:
                # Fallback si BackendManager non disponible
                return {
                    "available_backends": {
                        "pip": {
                            "available": True,
                            "version": "default",
                            "performance_tier": "standard"
                        }
                    },
                    "preferred": "pip",
                    "current_selection_logic": "pip-only"
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos backends: {str(e)}")
            return {"error": str(e)}
    
    def check_backend_availability(self) -> Dict[str, bool]:
        """
        Vérifie la disponibilité de tous les backends.
        
        Returns:
            Dictionnaire {backend_name: available}.
        """
        if self.backend_manager:
            try:
                return self.backend_manager.check_all_backends_availability()
            except Exception as e:
                logger.error(f"Erreur vérification backends: {str(e)}")
        
        # Fallback
        return {"pip": True, "uv": False}
    
    # =====================================================================
    # MÉTHODES INTERNES ET UTILITAIRES
    # =====================================================================
    
    def _determine_backend(self, requested_backend: Optional[str], 
                          from_pyproject: Optional[Path] = None) -> str:
        """
        Détermine le backend à utiliser selon la priorité:
        1. Backend explicitement demandé
        2. Backend détecté depuis pyproject.toml
        3. Backend préféré en configuration
        4. Auto-détection (uv > pip)
        """
        # 1. Backend explicitement demandé
        if requested_backend and requested_backend != "auto":
            return requested_backend
        
        # 2. Détection depuis pyproject.toml
        if from_pyproject and self.pyproject_parser:
            try:
                pyproject_info = self.pyproject_parser.parse_file(from_pyproject)
                if pyproject_info and hasattr(pyproject_info, 'build_system'):
                    build_backend = pyproject_info.build_system.get('build-backend', '')
                    if 'uv' in build_backend:
                        return 'uv'
            except Exception:
                pass
        
        # 3. Backend préféré en configuration
        preferred = self.config_manager.get_setting("preferred_backend")
        if preferred and preferred != "auto":
            return preferred
        
        # 4. Auto-détection
        if self.backend_manager:
            availability = self.backend_manager.check_all_backends_availability()
            if availability.get("uv", False):
                return "uv"
        
        return "pip"  # Fallback par défaut
    
    def _create_from_pyproject_internal(self, name: str, pyproject_path: Path,
                                      env_path: Path, python_version: str,
                                      backend: str, groups: Optional[List[str]]) -> Tuple[bool, str]:
        """Logique interne de création depuis pyproject.toml."""
        try:
            # Parser le fichier pyproject.toml
            pyproject_info = self.pyproject_parser.parse_file(pyproject_path)
            if not pyproject_info:
                return False, "Impossible de parser le fichier pyproject.toml"
            
            # Créer l'environnement virtuel de base
            success, message = self._create_virtual_environment(
                name, env_path, python_version, backend
            )
            if not success:
                return False, message
            
            # Installer les dépendances depuis pyproject.toml
            if self.project_service:
                success, install_message = self.project_service.install_from_pyproject(
                    env_path, pyproject_path, groups, backend
                )
            else:
                # Fallback avec PackageService
                packages_to_install = pyproject_info.dependencies[:]
                if groups:
                    for group in groups:
                        if group in pyproject_info.optional_dependencies:
                            packages_to_install.extend(pyproject_info.optional_dependencies[group])
                
                success, install_message = self.pkg_service.install_packages_in_path(
                    env_path, packages_to_install
                )
            
            if not success:
                self._cleanup_failed_environment(env_path)
                return False, f"Installation échouée: {install_message}"
            
            # Créer l'EnvironmentInfo avec informations pyproject.toml
            env_info = self._create_environment_info(
                name, env_path, python_version, backend,
                description=f"Projet {pyproject_info.name}",
                pyproject_info=pyproject_info,
                pyproject_path=pyproject_path
            )
            
            # Sauvegarder
            if not self.config_manager.add_environment(env_info):
                self._cleanup_failed_environment(env_path)
                return False, "Impossible de sauvegarder la configuration"
            
            return True, f"Environnement '{name}' créé depuis pyproject.toml avec succès"
            
        except Exception as e:
            self._cleanup_failed_environment(env_path)
            return False, f"Erreur création depuis pyproject.toml: {str(e)}"
    
    def _create_virtual_environment(self, name: str, env_path: Path, 
                                  python_version: str, backend: str) -> Tuple[bool, str]:
        """Crée l'environnement virtuel avec le backend spécifié."""
        try:
            if backend == "uv" and self.backend_manager:
                uv_backend = self.backend_manager.get_backend("uv")
                if uv_backend and uv_backend.is_available():
                    return uv_backend.create_environment(name, python_version, env_path)
            
            # Fallback ou backend pip
            return self.env_service.create_environment(name, env_path, python_version)
            
        except Exception as e:
            return False, f"Erreur création environnement virtuel: {str(e)}"
    
    def _install_initial_packages(self, name: str, env_path: Path, 
                                packages: Optional[str], requirements_file: Optional[str],
                                offline: bool, backend: str) -> Tuple[bool, str]:
        """Installe les packages initiaux avec le backend spécifié."""
        try:
            if packages:
                package_list = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
            else:
                package_list = []
            
            # Installation avec backend approprié
            if backend == "uv" and self.backend_manager:
                uv_backend = self.backend_manager.get_backend("uv")
                if uv_backend and uv_backend.is_available():
                    if requirements_file:
                        return uv_backend.install_from_requirements(env_path, Path(requirements_file))
                    elif package_list:
                        return uv_backend.install_packages(env_path, package_list)
                    return True, "Aucun package à installer"
            
            # Fallback pip
            if requirements_file:
                return self.pkg_service.install_from_requirements(name, requirements_file, offline)
            elif package_list:
                return self.pkg_service.install_packages(name, package_list, offline)
            
            return True, "Aucun package à installer"
            
        except Exception as e:
            return False, f"Erreur installation packages: {str(e)}"
    
    def _create_environment_info(self, name: str, env_path: Path, python_version: str,
                               backend: str, description: Optional[str] = None,
                               metadata: Optional[Dict[str, str]] = None,
                               pyproject_info: Optional[Any] = None,
                               pyproject_path: Optional[Path] = None) -> EnvironmentInfo:
        """Crée l'objet EnvironmentInfo (étendu v1.1)."""
        # Créer l'objet de base (compatible v1.0)
        env_info = EnvironmentInfo(
            name=name,
            path=env_path,
            python_version=python_version,
        )
        
        # Ajouter les nouveaux champs v1.1 si disponibles
        if hasattr(env_info, 'backend_type'):
            env_info.backend_type = backend
        if hasattr(env_info, 'pyproject_info'):
            env_info.pyproject_info = pyproject_info
        if hasattr(env_info, 'pyproject_path'):
            env_info.pyproject_path = pyproject_path
        if hasattr(env_info, 'description'):
            env_info.description = description
        if hasattr(env_info, 'metadata'):
            env_info.metadata = metadata or {}
        if hasattr(env_info, 'created_at'):
            env_info.created_at = datetime.now()
        
        return env_info
    
    def _cleanup_failed_environment(self, env_path: Path) -> None:
        """Nettoie un environnement en cas d'échec de création."""
        try:
            if env_path.exists():
                self.env_service.delete_environment(env_path)
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de {env_path}: {str(e)}")
    
    def _update_environment_packages(self, name: str) -> None:
        """Met à jour la liste des packages dans la configuration."""
        try:
            env_info = self.config_manager.get_environment(name)
            if env_info and hasattr(env_info, 'packages_installed'):
                packages = self.pkg_service.list_packages(name)
                env_info.packages_installed = [
                    PackageInfo(name=pkg['name'], version=pkg['version'])
                    for pkg in packages
                ]
                self.config_manager.update_environment(env_info)
        except Exception as e:
            logger.error(f"Erreur mise à jour packages de '{name}': {str(e)}")
    
    def _extract_python_version_from_pyproject(self, pyproject_info: Any) -> Optional[str]:
        """Extrait la version Python depuis pyproject.toml."""
        try:
            if hasattr(pyproject_info, 'python_requires'):
                python_requires = pyproject_info.python_requires
                # Simplification: extraction de base (peut être améliorée)
                if ">=" in python_requires:
                    return python_requires.split(">=")[1].strip()
                elif "==" in python_requires:
                    return python_requires.split("==")[1].strip()
        except Exception:
            pass
        return None
    
    def _create_pyproject_structure(self, env_info: EnvironmentInfo, 
                                  packages: List[Dict[str, str]],
                                  include_versions: bool,
                                  groups: Optional[Dict[str, List[str]]]) -> Dict[str, Any]:
        """Crée la structure de données pour pyproject.toml."""
        # Structure de base
        pyproject_data = {
            "project": {
                "name": env_info.name,
                "version": "0.1.0",
                "description": getattr(env_info, 'description', ''),
                "requires-python": f">={env_info.python_version}",
                "dependencies": []
            }
        }
        
        # Ajouter les dépendances
        for pkg in packages:
            if include_versions:
                dependency = f"{pkg['name']}=={pkg['version']}"
            else:
                dependency = pkg['name']
            pyproject_data["project"]["dependencies"].append(dependency)
        
        # Ajouter les groupes optionnels
        if groups:
            pyproject_data["project"]["optional-dependencies"] = groups
        
        return pyproject_data