"""
Module de gestion des environnements virtuels pour GestVenv.

Ce module fournit les fonctionnalités principales pour créer, activer, supprimer
et gérer les environnements virtuels Python.
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

# Import des modules internes
from .models import EnvironmentInfo, PackageInfo, EnvironmentHealth
from .config_manager import ConfigManager

# Configuration du logger
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """
    Classe principale pour la gestion des environnements virtuels Python.
    
    Cette classe utilise les services pour effectuer les opérations
    sur les environnements virtuels et maintient l'état de la configuration.
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
        
        # Initialiser les services
        from ..services.environment_service import EnvironmentService
        from ..services.package_service import PackageService
        from ..services.system_service import SystemService
        
        self.env_service = EnvironmentService()
        self.pkg_service = PackageService()
        self.sys_service = SystemService()
    
    def create_environment(self, name: str, python_version: Optional[str] = None,
                         packages: Optional[str] = None, path: Optional[str] = None,
                         offline: bool = False, requirements_file: Optional[str] = None,
                         description: Optional[str] = None,
                         metadata: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
        """
        Crée un nouvel environnement virtuel Python.
        
        Args:
            name: Nom de l'environnement.
            python_version: Version Python à utiliser.
            packages: Liste de packages à installer, séparés par des virgules.
            path: Chemin personnalisé pour l'environnement.
            offline: Si True, utilise uniquement les packages du cache (mode hors ligne).
            requirements_file: Chemin vers un fichier requirements.txt.
            description: Description de l'environnement.
            metadata: Métadonnées supplémentaires.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Valider le nom d'environnement avec le service
        valid, error = self.env_service.validate_environment_name(name)
        if not valid:
            return False, error
        
        # Vérifier si l'environnement existe déjà
        if self.config_manager.environment_exists(name):
            return False, f"L'environnement '{name}' existe déjà"
        
        # Valider la version Python avec le service
        if python_version:
            valid, error = self.env_service.validate_python_version(python_version)
            if not valid:
                return False, error
        
        # Si aucune version spécifiée, utiliser la version par défaut
        python_cmd = python_version if python_version else self.config_manager.get_default_python()
        
        # Valider et analyser la liste de packages
        package_list: List[str] = []
        if packages:
            valid, package_list, error = self.env_service.validate_packages_list(packages)
            if not valid:
                return False, error
        
        # Déterminer le chemin de l'environnement
        try:
            env_path = self.env_service.get_environment_path(name, path)
        except Exception as e:
            return False, f"Erreur lors de la détermination du chemin de l'environnement: {str(e)}"
        
        # Créer l'environnement virtuel avec le service
        success, message = self.env_service.create_environment(name, python_cmd, env_path)
        if not success:
            return False, message
        
        # Installer les packages si spécifiés (soit depuis packages, soit depuis requirements.txt)
        if package_list or requirements_file:
            try:
                if requirements_file:
                    requirements_path = Path(requirements_file)
                    if not requirements_path.exists():
                        # Nettoyer en cas d'erreur
                        self.env_service.delete_environment(env_path)
                        return False, f"Le fichier requirements '{requirements_file}' n'existe pas"
                    
                    success, pkg_message = self.pkg_service.install_from_requirements(
                        name, requirements_path, offline=offline
                    )
                else:
                    success, pkg_message = self.pkg_service.install_packages(
                        name, package_list, offline=offline
                    )
                
                if not success:
                    # En cas d'échec, essayer de supprimer l'environnement créé
                    self.env_service.delete_environment(env_path)
                    return False, f"Échec de l'installation des packages: {pkg_message}"
            except Exception as e:
                # En cas d'erreur, essayer de supprimer l'environnement créé
                self.env_service.delete_environment(env_path)
                return False, f"Erreur lors de l'installation des packages: {str(e)}"
        
        # Obtenir la version Python réelle
        python_version_actual = self.sys_service.check_python_version(python_cmd)
        
        # Préparer les métadonnées
        env_metadata = metadata or {}
        if description:
            env_metadata['description'] = description
        env_metadata['created_by'] = 'gestvenv'
        env_metadata['creation_method'] = 'cli'
        
        # Créer l'objet EnvironmentInfo
        env_info = EnvironmentInfo(
            name=name,
            path=env_path,
            python_version=python_version_actual or python_cmd,
            created_at=datetime.now(),
            packages=package_list,
            health=self.env_service.check_environment_health(name, env_path),
            metadata=env_metadata
        )
        
        # Ajouter l'environnement à la configuration
        self.config_manager.add_environment(env_info)
        
        # Si c'est le premier environnement, le définir comme actif
        if len(self.config_manager.get_all_environments()) == 1:
            self.config_manager.set_active_environment(name)
        
        return True, f"Environnement '{name}' créé avec succès"
    
    def activate_environment(self, name: str) -> Tuple[bool, str]:
        """
        Définit un environnement comme actif et retourne la commande pour l'activer.
        
        Args:
            name: Nom de l'environnement à activer.
            
        Returns:
            Tuple contenant (succès, message ou commande d'activation).
        """
        # Vérifier si l'environnement existe
        if not self.config_manager.environment_exists(name):
            return False, f"L'environnement '{name}' n'existe pas"
        
        # Obtenir l'information de l'environnement
        env_info = self.config_manager.get_environment(name)
        if not env_info:
            return False, f"Impossible d'obtenir les informations de l'environnement '{name}'"
        
        # Vérifier si l'environnement existe physiquement
        if not self.env_service.check_environment_exists(env_info.path):
            return False, f"L'environnement '{name}' n'existe pas physiquement à {env_info.path}"
        
        # Obtenir la commande d'activation avec le service
        activation_cmd = self.sys_service.get_activation_command(name, env_info.path)
        if not activation_cmd:
            return False, f"Impossible de générer la commande d'activation pour l'environnement '{name}'"
        
        # Définir l'environnement comme actif dans la configuration
        self.config_manager.set_active_environment(name)
        
        # Vérifier les mises à jour disponibles si cette option est activée
        check_updates = self.config_manager.get_setting("check_updates_on_activate", False)
        if check_updates:
            try:
                updates = self.pkg_service.check_for_updates(name)
                if updates and len(updates) > 0:
                    logger.info(f"{len(updates)} mise(s) à jour disponible(s) pour l'environnement '{name}'")
            except Exception as e:
                logger.warning(f"Impossible de vérifier les mises à jour: {str(e)}")
        
        return True, activation_cmd
    
    def deactivate_environment(self) -> Tuple[bool, str]:
        """
        Désactive l'environnement actif et retourne la commande de désactivation.
        
        Returns:
            Tuple contenant (succès, message ou commande de désactivation).
        """
        # Vérifier s'il y a un environnement actif
        active_env = self.config_manager.get_active_environment()
        if not active_env:
            return False, "Aucun environnement actif à désactiver"
        
        # Réinitialiser l'environnement actif dans la configuration
        self.config_manager.clear_active_environment()
        
        # Obtenir la commande de désactivation appropriée selon le système
        deactivate_cmd = "deactivate"  # Commande standard pour tous les systèmes
        
        return True, deactivate_cmd
    
    def delete_environment(self, name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Supprime un environnement virtuel.
        
        Args:
            name: Nom de l'environnement à supprimer.
            force: Si True, force la suppression sans vérifications supplémentaires.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Vérifier si l'environnement existe dans la configuration
        if not self.config_manager.environment_exists(name):
            return False, f"L'environnement '{name}' n'existe pas"
        
        # Obtenir l'information de l'environnement
        env_info = self.config_manager.get_environment(name)
        if not env_info:
            return False, f"Impossible d'obtenir les informations de l'environnement '{name}'"
        
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
            logger.error(f"Erreur lors de la suppression de l'environnement de la configuration: {str(e)}")
            return False, f"L'environnement a été supprimé du système de fichiers, mais pas de la configuration: {str(e)}"
        
        return True, f"Environnement '{name}' supprimé avec succès"
    
    def list_environments(self) -> List[Dict[str, Any]]:
        """
        Liste tous les environnements disponibles avec leurs informations.
        
        Returns:
            Liste des environnements avec leurs détails.
        """
        result = []
        environments = self.config_manager.get_all_environments()
        active_env = self.config_manager.get_active_environment()
        
        for name, env_info in environments.items():
            # Vérifier si l'environnement existe réellement
            exists = self.env_service.check_environment_exists(env_info.path)
            
            # Mettre à jour l'état de santé de l'environnement
            if exists:
                health = self.env_service.check_environment_health(name, env_info.path)
            else:
                health = EnvironmentHealth(exists=False)
            
            # Ajouter les informations de l'environnement à la liste
            env_data = {
                "name": name,
                "path": str(env_info.path),
                "python_version": env_info.python_version,
                "created_at": env_info.created_at.isoformat() if isinstance(env_info.created_at, datetime) else env_info.created_at,
                "packages_count": len(env_info.packages),
                "active": name == active_env,
                "health": health.to_dict(),
                "exists": exists
            }
            
            # Ajouter la description si disponible
            if hasattr(env_info, 'metadata') and env_info.metadata:
                description = env_info.metadata.get('description')
                if description:
                    env_data['description'] = description
            
            result.append(env_data)
        
        return result
    
    def get_environment_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Obtient des informations détaillées sur un environnement spécifique.
        
        Args:
            name: Nom de l'environnement.
            
        Returns:
            Dictionnaire d'informations ou None si non trouvé.
        """
        # Vérifier si l'environnement existe dans la configuration
        if not self.config_manager.environment_exists(name):
            logger.warning(f"L'environnement '{name}' n'existe pas dans la configuration")
            return None
        
        # Obtenir l'information de l'environnement
        env_info = self.config_manager.get_environment(name)
        if not env_info:
            return None
        
        # Vérifier si l'environnement existe physiquement
        exists = self.env_service.check_environment_exists(env_info.path)
        
        # Mettre à jour l'état de santé de l'environnement
        if exists:
            health = self.env_service.check_environment_health(name, env_info.path)
        else:
            health = EnvironmentHealth(exists=False)
        
        # Obtenir la liste des packages installés
        if exists and health.pip_available:
            try:
                installed_packages = self.pkg_service.list_installed_packages(name)
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des packages installés: {str(e)}")
                installed_packages = []
        else:
            installed_packages = []
        
        # Préparer les informations détaillées
        active_env = self.config_manager.get_active_environment()
        
        result = {
            "name": name,
            "path": str(env_info.path),
            "python_version": env_info.python_version,
            "created_at": env_info.created_at.isoformat() if isinstance(env_info.created_at, datetime) else env_info.created_at,
            "packages_configured": env_info.packages,
            "packages_installed": installed_packages,
            "active": name == active_env,
            "health": health.to_dict(),
            "exists": exists,
        }
        
        # Ajouter les métadonnées si disponibles
        if hasattr(env_info, 'metadata') and env_info.metadata:
            result['metadata'] = env_info.metadata
            
            # Extraire la description pour un accès facile
            description = env_info.metadata.get('description')
            if description:
                result['description'] = description
        
        # Ajouter des informations supplémentaires si l'environnement existe
        if exists:
            result.update({
                "python_executable": str(self.env_service.get_python_executable(name, env_info.path)),
                "pip_executable": str(self.env_service.get_pip_executable(name, env_info.path)),
                "activation_script": str(self.env_service.get_activation_script_path(name, env_info.path))
            })
        
        return result
    
    def install_packages(self, env_name: str, packages: Optional[str] = None,
                        requirements_file: Optional[str] = None,
                        editable: bool = False, dev: bool = False,
                        offline: bool = False) -> Tuple[bool, str]:
        """
        Installe des packages dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement.
            packages: Liste de packages à installer, séparés par des virgules.
            requirements_file: Chemin vers un fichier requirements.txt.
            editable: Si True, installe en mode éditable (-e).
            dev: Si True, installe les dépendances de développement.
            offline: Force le mode hors ligne pour cette opération.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Vérifier si l'environnement existe
        if not self.config_manager.environment_exists(env_name):
            return False, f"L'environnement '{env_name}' n'existe pas"
        
        # Vérifier qu'au moins une source de packages est spécifiée
        if not packages and not requirements_file:
            return False, "Aucun package ou fichier requirements spécifié"
        
        # Préparer le chemin du fichier requirements
        req_path = None
        if requirements_file:
            req_path = Path(requirements_file)
            if not req_path.exists():
                return False, f"Le fichier requirements '{requirements_file}' n'existe pas"
        
        # Installer les packages
        try:
            success, message = self.pkg_service.install_packages(
                env_name, 
                packages if packages else [],
                offline=offline,
                requirements_file=req_path,
                editable=editable,
                dev=dev
            )
            
            if success:
                # Mettre à jour la configuration avec les nouveaux packages
                self._update_environment_packages(env_name)
            
            return success, message
            
        except Exception as e:
            return False, f"Erreur lors de l'installation des packages: {str(e)}"
    
    def uninstall_packages(self, env_name: str, packages: str,
                          with_dependencies: bool = False,
                          force: bool = False) -> Tuple[bool, str]:
        """
        Désinstalle des packages d'un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement.
            packages: Liste de packages à désinstaller, séparés par des virgules.
            with_dependencies: Si True, désinstalle aussi les dépendances.
            force: Si True, ne demande pas de confirmation pour les dépendances.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Vérifier si l'environnement existe
        if not self.config_manager.environment_exists(env_name):
            return False, f"L'environnement '{env_name}' n'existe pas"
        
        # Désinstaller les packages
        try:
            success, message = self.pkg_service.uninstall_packages(
                env_name, 
                packages,
                with_dependencies=with_dependencies,
                force=force
            )
            
            if success:
                # Mettre à jour la configuration
                self._update_environment_packages(env_name)
            
            return success, message
            
        except Exception as e:
            return False, f"Erreur lors de la désinstallation des packages: {str(e)}"
    
    def clone_environment(self, source_name: str, target_name: str,
                         include_packages: bool = True,
                         description: Optional[str] = None) -> Tuple[bool, str]:
        """
        Clone un environnement existant vers un nouveau.
        
        Args:
            source_name: Nom de l'environnement source.
            target_name: Nom du nouvel environnement.
            include_packages: Si True, copie aussi les packages installés.
            description: Description optionnelle pour le nouvel environnement.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Vérifier si l'environnement source existe
        if not self.config_manager.environment_exists(source_name):
            return False, f"L'environnement source '{source_name}' n'existe pas"
        
        # Vérifier si le nom cible est valide
        valid, error = self.env_service.validate_environment_name(target_name)
        if not valid:
            return False, error
        
        # Vérifier si l'environnement cible existe déjà
        if self.config_manager.environment_exists(target_name):
            return False, f"L'environnement cible '{target_name}' existe déjà"
        
        # Obtenir les informations de l'environnement source
        source_info = self.config_manager.get_environment(source_name)
        if not source_info:
            return False, f"Impossible d'obtenir les informations de l'environnement source '{source_name}'"
        
        # Préparer les métadonnées pour le clone
        clone_metadata = {
            'cloned_from': source_name,
            'cloned_at': datetime.now().isoformat()
        }
        if description:
            clone_metadata['description'] = description
        elif hasattr(source_info, 'metadata') and source_info.metadata:
            original_desc = source_info.metadata.get('description')
            if original_desc:
                clone_metadata['description'] = f"Clone de {source_name}: {original_desc}"
        
        # Créer un nouvel environnement avec la même version Python
        success, message = self.create_environment(
            target_name, 
            source_info.python_version,
            metadata=clone_metadata
        )
        if not success:
            return False, f"Erreur lors de la création du nouvel environnement: {message}"
        
        # Installer les mêmes packages que dans l'environnement source si demandé
        if include_packages and source_info.packages:
            try:
                success, pkg_message = self.pkg_service.install_packages(target_name, source_info.packages)
                if not success:
                    # En cas d'échec, essayer de supprimer l'environnement créé
                    self.delete_environment(target_name, force=True)
                    return False, f"Erreur lors de l'installation des packages dans le nouvel environnement: {pkg_message}"
            except Exception as e:
                # En cas d'erreur, essayer de supprimer l'environnement créé
                self.delete_environment(target_name, force=True)
                return False, f"Erreur lors de l'installation des packages: {str(e)}"
        
        return True, f"Environnement '{source_name}' cloné avec succès vers '{target_name}'"
    
    def export_environment(self, name: str, output_path: Optional[str] = None,
                          format_type: str = "json", metadata: Optional[str] = None,
                          include_metadata: bool = False,
                          production_ready: bool = False) -> Tuple[bool, str]:
        """
        Exporte la configuration d'un environnement.
        
        Args:
            name: Nom de l'environnement à exporter.
            output_path: Chemin de sortie pour le fichier d'export.
            format_type: Format d'export ('json' ou 'requirements').
            metadata: Métadonnées supplémentaires à inclure.
            include_metadata: Si True, inclut les métadonnées détaillées.
            production_ready: Si True, optimise l'export pour la production.
            
        Returns:
            Tuple contenant (succès, message ou chemin du fichier).
        """
        # Vérifier si l'environnement existe
        if not self.config_manager.environment_exists(name):
            return False, f"L'environnement '{name}' n'existe pas"
        
        # Valider le format d'export
        valid, error = self.env_service.validate_output_format(format_type)
        if not valid:
            return False, error
        
        # Valider et analyser les métadonnées si spécifiées
        metadata_dict: Dict[str, str] = {}
        if metadata:
            valid, metadata_dict, error = self.env_service.validate_metadata(metadata)
            if not valid:
                return False, error
        
        # Ajouter des métadonnées supplémentaires si demandé
        if include_metadata:
            env_info = self.config_manager.get_environment(name)
            if env_info and hasattr(env_info, 'metadata') and env_info.metadata:
                metadata_dict.update(env_info.metadata)
        
        # Ajouter des métadonnées de production si demandé
        if production_ready:
            metadata_dict.update({
                'production_ready': 'true',
                'exported_for': 'production',
                'environment_type': 'production'
            })
            
            # Pour la production, on peut exclure certains packages de développement
            # Cette logique pourrait être implémentée dans le service de packages
        
        # Déléguer l'export au service approprié selon le format
        if format_type.lower() == "requirements":
            try:
                # Déterminer le chemin de sortie
                output_file = self.env_service.get_requirements_output_path(name, output_path)
                
                # Exporter au format requirements.txt
                success, export_path = self.pkg_service.export_requirements(name, output_file)
                if not success:
                    return False, f"Erreur lors de l'export des requirements pour l'environnement '{name}'"
                
                return True, f"Environnement '{name}' exporté au format requirements.txt vers {export_path}"
            except Exception as e:
                return False, f"Erreur lors de l'export au format requirements: {str(e)}"
        else:
            try:
                # Exporter au format JSON via le gestionnaire de configuration
                output_file = output_path
                if not output_file:
                    output_file = self.env_service.get_json_output_path(name)
                
                result = self.config_manager.export_environment_config(name, output_file, metadata_dict)
                if result is True:
                    return True, f"Environnement '{name}' exporté au format JSON vers {output_file}"
                elif isinstance(result, str):
                    # Si pas de fichier de sortie spécifié, le résultat est le contenu JSON
                    if output_path is None:
                        return True, result
                    return False, "Erreur inattendue lors de l'export JSON"
                else:
                    return False, "Erreur lors de l'export JSON"
            except Exception as e:
                return False, f"Erreur lors de l'export au format JSON: {str(e)}"
    
    def import_environment(self, input_path: str, name: Optional[str] = None,
                          merge: bool = False, resolve_conflicts: bool = False) -> Tuple[bool, str]:
        """
        Importe un environnement depuis un fichier de configuration.
        
        Args:
            input_path: Chemin vers le fichier de configuration.
            name: Nom à utiliser pour le nouvel environnement.
            merge: Si True, fusionne avec un environnement existant.
            resolve_conflicts: Si True, résout automatiquement les conflits.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Valider et résoudre le chemin d'entrée
            resolved_path = self.env_service.resolve_path(input_path)
            if not resolved_path.exists():
                return False, f"Le fichier '{input_path}' n'existe pas"
            
            # Déterminer le type de fichier et déléguer l'import au service approprié
            if resolved_path.suffix.lower() == ".json":
                # Importer depuis un fichier JSON
                result = self.config_manager.import_environment_config(str(resolved_path), name)
                
                if result["status"] == "error":
                    return False, result["message"]
                
                # Créer l'environnement avec les informations importées
                env_name = result["env_name"]
                config = result["config"]
                
                # Vérifier les conflits si l'environnement existe déjà
                if self.config_manager.environment_exists(env_name):
                    if not merge:
                        return False, f"L'environnement '{env_name}' existe déjà. Utilisez --merge pour le fusionner."
                    
                    if merge and not resolve_conflicts:
                        return False, f"L'environnement '{env_name}' existe déjà. Utilisez --resolve-conflicts pour résoudre automatiquement les conflits."
                    
                    # Logique de fusion/résolution de conflits
                    if merge and resolve_conflicts:
                        return self._merge_environment_config(env_name, config)
                
                return self.create_environment(
                    env_name,
                    python_version=config["python_version"],
                    packages=",".join(config["packages"]) if config["packages"] else None
                )
            
            elif resolved_path.suffix.lower() == ".txt":
                # Importer depuis un fichier requirements.txt
                if not name:
                    return False, "Un nom d'environnement doit être spécifié pour l'import depuis requirements.txt"
                
                # Valider le nom d'environnement
                valid, error = self.env_service.validate_environment_name(name)
                if not valid:
                    return False, error
                
                # Vérifier les conflits
                if self.config_manager.environment_exists(name):
                    if not merge:
                        return False, f"L'environnement '{name}' existe déjà"
                    
                    if merge and not resolve_conflicts:
                        return False, f"L'environnement '{name}' existe déjà. Utilisez --resolve-conflicts pour résoudre automatiquement les conflits."
                
                # Créer l'environnement s'il n'existe pas
                if not self.config_manager.environment_exists(name):
                    success, message = self.create_environment(name)
                    if not success:
                        return False, f"Erreur lors de la création de l'environnement: {message}"
                
                # Installer les packages depuis le fichier requirements.txt
                try:
                    success, pkg_message = self.pkg_service.install_from_requirements(name, resolved_path)
                    if not success:
                        # En cas d'échec et si on vient de créer l'environnement, le supprimer
                        if not merge:
                            self.delete_environment(name, force=True)
                        return False, f"Erreur lors de l'installation des packages: {pkg_message}"
                except Exception as e:
                    # En cas d'erreur et si on vient de créer l'environnement, le supprimer
                    if not merge:
                        self.delete_environment(name, force=True)
                    return False, f"Erreur lors de l'installation des packages: {str(e)}"
                
                return True, f"Environnement importé avec succès depuis {resolved_path} sous le nom '{name}'"
            else:
                return False, f"Format de fichier non pris en charge: {resolved_path.suffix}"
        
        except Exception as e:
            return False, f"Erreur lors de l'import de l'environnement: {str(e)}"
    
    def _merge_environment_config(self, env_name: str, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Fusionne une configuration importée avec un environnement existant.
        
        Args:
            env_name: Nom de l'environnement existant.
            config: Configuration à fusionner.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Obtenir l'environnement existant
            existing_env = self.config_manager.get_environment(env_name)
            if not existing_env:
                return False, f"Impossible d'obtenir les informations de l'environnement '{env_name}'"
            
            # Fusionner les packages
            existing_packages = set(existing_env.packages)
            new_packages = set(config.get("packages", []))
            
            # Packages à ajouter
            packages_to_add = new_packages - existing_packages
            
            if packages_to_add:
                # Installer les nouveaux packages
                success, message = self.pkg_service.install_packages(env_name, list(packages_to_add))
                if not success:
                    return False, f"Erreur lors de l'installation des nouveaux packages: {message}"
                
                # Mettre à jour la configuration
                self._update_environment_packages(env_name)
            
            return True, f"Configuration fusionnée avec succès dans l'environnement '{env_name}'"
            
        except Exception as e:
            return False, f"Erreur lors de la fusion de la configuration: {str(e)}"
    
    def set_default_python(self, python_cmd: str) -> Tuple[bool, str]:
        """
        Définit la commande Python par défaut pour les nouveaux environnements.
        
        Args:
            python_cmd: Commande Python à utiliser par défaut.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Valider la commande Python
        valid, error = self.env_service.validate_python_version(python_cmd)
        if not valid:
            return False, error
        
        # Vérifier si la commande Python est disponible
        version = self.sys_service.check_python_version(python_cmd)
        if not version:
            return False, f"La commande Python '{python_cmd}' n'est pas disponible sur le système"
        
        # Mettre à jour la configuration
        if not self.config_manager.set_default_python(python_cmd):
            return False, "Erreur lors de la sauvegarde de la configuration"
        
        return True, f"Commande Python par défaut définie à '{python_cmd}' (version {version})"
    
    def get_active_environment(self) -> Optional[str]:
        """
        Retourne le nom de l'environnement actif, s'il existe.
        
        Returns:
            Nom de l'environnement actif ou None.
        """
        return self.config_manager.get_active_environment()
    
    def run_command_in_environment(self, env_name: str, command: List[str],
                                  env_vars: Optional[Dict[str, str]] = None,
                                  timeout: Optional[int] = None,
                                  background: bool = False) -> Tuple[int, str, str]:
        """
        Exécute une commande dans un environnement virtuel spécifique.
        
        Args:
            env_name: Nom de l'environnement.
            command: Commande à exécuter.
            env_vars: Variables d'environnement supplémentaires.
            timeout: Timeout en secondes.
            background: Si True, exécute en arrière-plan.
            
        Returns:
            Tuple contenant (code de retour, sortie standard, sortie d'erreur).
        """
        # Vérifier si l'environnement existe
        if not self.config_manager.environment_exists(env_name):
            return 1, "", f"L'environnement '{env_name}' n'existe pas"
        
        # Obtenir l'information de l'environnement
        env_info = self.config_manager.get_environment(env_name)
        if not env_info:
            return 1, "", f"Impossible d'obtenir les informations de l'environnement '{env_name}'"
        
        # Préparer l'environnement d'exécution
        if env_vars:
            # Créer une copie de l'environnement actuel et ajouter les nouvelles variables
            execution_env = os.environ.copy()
            execution_env.update(env_vars)
            
            # Exécuter la commande avec les variables d'environnement personnalisées
            return self._run_with_custom_env(env_name, env_info.path, command, execution_env, timeout, background)
        else:
            # Exécuter normalement
            return self.sys_service.run_in_environment(env_name, env_info.path, command)
    
    def _run_with_custom_env(self, env_name: str, env_path: Path, command: List[str],
                            env_vars: Dict[str, str], timeout: Optional[int],
                            background: bool) -> Tuple[int, str, str]:
        """Exécute une commande avec des variables d'environnement personnalisées."""
        import subprocess
        
        try:
            # Obtenir l'exécutable Python de l'environnement
            python_exe = self.env_service.get_python_executable(env_name, env_path)
            
            if not python_exe:
                return 1, "", f"Impossible de trouver l'exécutable Python pour l'environnement '{env_name}'"
            
            # Préparer la commande avec l'exécutable Python de l'environnement
            cmd = [str(python_exe)] + command
            
            # Exécuter la commande
            if background:
                # Exécution en arrière-plan
                process = subprocess.Popen(
                    cmd,
                    env=env_vars,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return 0, f"Processus démarré en arrière-plan (PID: {process.pid})", ""
            else:
                # Exécution normale avec timeout optionnel
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env_vars,
                    timeout=timeout,
                    check=False
                )
                
                return result.returncode, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            return 1, "", f"Commande interrompue après {timeout} secondes"
        except Exception as e:
            return 1, "", f"Erreur lors de l'exécution de la commande: {str(e)}"
    
    def update_packages(self, env_name: str, packages: Optional[str] = None, 
                        all_packages: bool = False, offline: bool = False) -> Tuple[bool, str]:
        """
        Met à jour des packages dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement.
            packages: Liste de packages à mettre à jour séparés par des virgules.
            all_packages: Si True, met à jour tous les packages.
            offline: Force le mode hors ligne pour cette opération.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Vérifier si l'environnement existe
        if not self.config_manager.environment_exists(env_name):
            return False, f"L'environnement '{env_name}' n'existe pas"
        
        # Obtenir l'information de l'environnement
        env_info = self.config_manager.get_environment(env_name)
        if not env_info:
            return False, f"Impossible d'obtenir les informations de l'environnement '{env_name}'"
        
        # Vérifier si l'environnement existe physiquement
        if not self.env_service.check_environment_exists(env_info.path):
            return False, f"L'environnement '{env_name}' n'existe pas physiquement à {env_info.path}"
        
        # Valider et analyser la liste de packages
        package_list = []
        if packages:
            valid, package_list, error = self.env_service.validate_packages_list(packages)
            if not valid:
                return False, error
        elif not all_packages:
            return False, "Aucun package spécifié pour la mise à jour et --all n'est pas utilisé"
        
        # Mettre à jour les packages
        try:
            success, message = self.pkg_service.update_packages(env_name, package_list, all_packages, offline)
            if not success:
                return False, message
        except Exception as e:
            return False, f"Erreur lors de la mise à jour des packages: {str(e)}"
        
        # Mettre à jour la configuration avec les nouveaux packages
        try:
            self._update_environment_packages(env_name)
        except Exception as e:
            logger.warning(f"Erreur lors de la mise à jour de la configuration: {str(e)}")
            # Ne pas échouer complètement, car les packages ont été mis à jour
        
        return True, f"Packages mis à jour avec succès dans l'environnement '{env_name}'"
    
    def check_for_updates(self, env_name: str) -> Tuple[bool, List[Dict[str, str]], str]:
        """
        Vérifie les mises à jour disponibles pour les packages d'un environnement.

        Args:
            env_name (str): Nom de l'environnement.

        Returns:
            Tuple[bool, List[Dict[str, str]], str]: Tuple contenant (succès, liste des mises à jour, message).
        """
        # Vérifier si l'environnement existe
        if not self.config_manager.environment_exists(env_name):
            return False, [], f"L'environnement '{env_name}' n'existe pas"

        try:
            # Appeler le service pour vérifier les mises à jour
            updates = self.pkg_service.check_for_updates(env_name)

            if not updates:
                return True, [], "Tous les packages sont à jour"

            # Formater les résultats en assurant que toutes les clés nécessaires sont présentes
            formatted_updates = []
            for update in updates:
                # S'assurer que toutes les clés nécessaires existent avec des valeurs par défaut
                formatted_update = {
                    "name": update.get("name", "Inconnu"),
                    "current_version": update.get("current_version", update.get("version", "?")),
                    "latest_version": update.get("latest_version", update.get("latest", "?"))
                }
                formatted_updates.append(formatted_update)

            return True, formatted_updates, f"{len(formatted_updates)} package(s) peuvent être mis à jour"
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des mises à jour: {str(e)}")
            return False, [], f"Erreur lors de la vérification des mises à jour: {str(e)}"
    
    def diagnose_environment(self, env_name: str, full_check: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        Diagnostique la santé d'un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement à diagnostiquer.
            full_check: Si True, effectue un diagnostic complet.
            
        Returns:
            Tuple contenant (santé globale, rapport de diagnostic).
        """
        try:
            # Vérifier si l'environnement existe dans la configuration
            if not self.config_manager.environment_exists(env_name):
                return False, {
                    "status": "error",
                    "message": f"L'environnement '{env_name}' n'existe pas dans la configuration",
                    "checks": {}
                }
            
            # Obtenir les informations de l'environnement
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return False, {
                    "status": "error",
                    "message": f"Impossible d'obtenir les informations de l'environnement '{env_name}'",
                    "checks": {}
                }
            
            # Effectuer les vérifications de base
            checks = {}
            overall_health = True
            
            # 1. Vérifier l'existence physique
            exists = self.env_service.check_environment_exists(env_info.path)
            checks["physical_existence"] = {
                "status": "ok" if exists else "error",
                "message": "Environnement physiquement présent" if exists else "Environnement manquant sur le disque"
            }
            if not exists:
                overall_health = False
            
            # 2. Vérifier la santé de l'environnement
            if exists:
                health = self.env_service.check_environment_health(env_name, env_info.path)
                
                checks["python_executable"] = {
                    "status": "ok" if health.python_available else "error",
                    "message": "Exécutable Python disponible" if health.python_available else "Exécutable Python manquant"
                }
                
                checks["pip_executable"] = {
                    "status": "ok" if health.pip_available else "error",
                    "message": "pip disponible" if health.pip_available else "pip manquant"
                }
                
                checks["activation_script"] = {
                    "status": "ok" if health.activation_script_exists else "warning",
                    "message": "Script d'activation présent" if health.activation_script_exists else "Script d'activation manquant"
                }
                
                if not health.python_available or not health.pip_available:
                    overall_health = False
            
            # 3. Vérifications approfondies si demandé
            if full_check and exists:
                # Vérifier les packages installés
                try:
                    installed_packages = self.pkg_service.list_installed_packages(env_name)
                    checks["packages_accessible"] = {
                        "status": "ok",
                        "message": f"{len(installed_packages)} packages installés et accessibles"
                    }
                    
                    # Vérifier les mises à jour disponibles
                    updates = self.pkg_service.check_for_updates(env_name)
                    if updates:
                        checks["package_updates"] = {
                            "status": "info",
                            "message": f"{len(updates)} mise(s) à jour disponible(s)"
                        }
                    else:
                        checks["package_updates"] = {
                            "status": "ok",
                            "message": "Tous les packages sont à jour"
                        }
                        
                except Exception as e:
                    checks["packages_accessible"] = {
                        "status": "warning",
                        "message": f"Erreur lors de la vérification des packages: {str(e)}"
                    }
                
                # Vérifier l'espace disque
                try:
                    free_space = self.sys_service.get_free_disk_space(env_info.path)
                    if free_space < 100 * 1024 * 1024:  # Moins de 100 MB
                        checks["disk_space"] = {
                            "status": "warning",
                            "message": f"Espace disque faible: {free_space // (1024*1024)} MB disponible"
                        }
                    else:
                        checks["disk_space"] = {
                            "status": "ok",
                            "message": f"Espace disque suffisant: {free_space // (1024*1024)} MB disponible"
                        }
                except Exception as e:
                    checks["disk_space"] = {
                        "status": "info",
                        "message": f"Impossible de vérifier l'espace disque: {str(e)}"
                    }
            
            # Préparer le rapport final
            report = {
                "status": "healthy" if overall_health else "unhealthy",
                "environment": env_name,
                "path": str(env_info.path),
                "python_version": env_info.python_version,
                "checks": checks,
                "recommendations": []
            }
            
            # Ajouter des recommandations basées sur les vérifications
            if not overall_health:
                if not exists:
                    report["recommendations"].append("Recréer l'environnement virtuel")
                elif not checks.get("python_executable", {}).get("status") == "ok":
                    report["recommendations"].append("Réinstaller Python dans l'environnement")
                elif not checks.get("pip_executable", {}).get("status") == "ok":
                    report["recommendations"].append("Réinstaller pip dans l'environnement")
            
            if full_check and "package_updates" in checks and checks["package_updates"]["status"] == "info":
                report["recommendations"].append("Mettre à jour les packages obsolètes")
            
            return overall_health, report
            
        except Exception as e:
            logger.error(f"Erreur lors du diagnostic de l'environnement: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Erreur lors du diagnostic: {str(e)}",
                "checks": {}
            }
    
    def repair_environment(self, env_name: str, auto_fix: bool = False) -> Tuple[bool, List[str]]:
        """
        Tente de réparer un environnement virtuel endommagé.
        
        Args:
            env_name: Nom de l'environnement à réparer.
            auto_fix: Si True, applique automatiquement les corrections.
            
        Returns:
            Tuple contenant (succès, liste des actions effectuées).
        """
        actions = []
        
        try:
            # Diagnostiquer d'abord l'environnement
            is_healthy, diagnosis = self.diagnose_environment(env_name, full_check=True)
            
            if is_healthy:
                return True, ["L'environnement est déjà en bonne santé"]
            
            # Obtenir les informations de l'environnement
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return False, ["Impossible d'obtenir les informations de l'environnement"]
            
            # Vérifier les problèmes et les corriger
            checks = diagnosis.get("checks", {})
            
            # 1. Environnement physiquement manquant
            if checks.get("physical_existence", {}).get("status") == "error":
                if auto_fix:
                    # Recréer l'environnement
                    success, message = self.env_service.create_environment(
                        env_name, 
                        env_info.python_version, 
                        env_info.path
                    )
                    if success:
                        actions.append("Environnement recréé")
                    else:
                        actions.append(f"Échec de la recréation: {message}")
                        return False, actions
                else:
                    actions.append("Recommandation: Recréer l'environnement virtuel")
            
            # 2. pip manquant
            if checks.get("pip_executable", {}).get("status") == "error":
                if auto_fix:
                    # Tenter de réinstaller pip
                    python_exe = self.env_service.get_python_executable(env_name, env_info.path)
                    if python_exe:
                        try:
                            import subprocess
                            result = subprocess.run([
                                str(python_exe), "-m", "ensurepip", "--upgrade"
                            ], capture_output=True, text=True, check=False)
                            
                            if result.returncode == 0:
                                actions.append("pip réinstallé avec succès")
                            else:
                                actions.append(f"Échec de la réinstallation de pip: {result.stderr}")
                        except Exception as e:
                            actions.append(f"Erreur lors de la réinstallation de pip: {str(e)}")
                    else:
                        actions.append("Impossible de trouver l'exécutable Python pour réinstaller pip")
                else:
                    actions.append("Recommandation: Réinstaller pip")
            
            # 3. Packages manquants (si spécifiés dans la configuration)
            if env_info.packages and auto_fix:
                try:
                    # Vérifier quels packages sont manquants
                    installed_packages = self.pkg_service.list_installed_packages(env_name)
                    installed_names = {pkg["name"].lower() for pkg in installed_packages}
                    
                    missing_packages = []
                    for pkg_spec in env_info.packages:
                        pkg_name = pkg_spec.split('==')[0].split('>')[0].split('<')[0].strip().lower()
                        if pkg_name not in installed_names:
                            missing_packages.append(pkg_spec)
                    
                    if missing_packages:
                        success, message = self.pkg_service.install_packages(env_name, missing_packages)
                        if success:
                            actions.append(f"Packages manquants réinstallés: {', '.join(missing_packages)}")
                        else:
                            actions.append(f"Échec de la réinstallation des packages: {message}")
                
                except Exception as e:
                    actions.append(f"Erreur lors de la vérification des packages: {str(e)}")
            
            # Vérifier le résultat final
            if auto_fix:
                # Refaire un diagnostic pour vérifier si les problèmes sont résolus
                is_healthy_after, _ = self.diagnose_environment(env_name)
                if is_healthy_after:
                    actions.append("Environnement réparé avec succès")
                    return True, actions
                else:
                    actions.append("Réparation partielle - certains problèmes persistent")
                    return False, actions
            else:
                return True, actions
            
        except Exception as e:
            logger.error(f"Erreur lors de la réparation de l'environnement: {str(e)}")
            actions.append(f"Erreur lors de la réparation: {str(e)}")
            return False, actions
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Récupère des informations détaillées sur le système.
        
        Returns:
            Dictionnaire d'informations système.
        """
        try:
            # Informations de base du système
            system_info = self.sys_service.get_system_info()
            
            # Versions Python disponibles
            python_versions = self.sys_service.get_available_python_versions()
            
            # Configuration GestVenv
            gestvenv_config = {
                "default_python": self.config_manager.get_default_python(),
                "active_environment": self.get_active_environment(),
                "total_environments": len(self.config_manager.get_all_environments()),
                "offline_mode": self.config_manager.get_setting("offline_mode", False),
                "cache_enabled": self.config_manager.get_setting("use_package_cache", True)
            }
            
            # Informations sur les environnements
            environments_info = []
            for env_name, env_info in self.config_manager.get_all_environments().items():
                exists = self.env_service.check_environment_exists(env_info.path)
                health = self.env_service.check_environment_health(env_name, env_info.path) if exists else None
                
                environments_info.append({
                    "name": env_name,
                    "exists": exists,
                    "healthy": health.python_available and health.pip_available if health else False,
                    "python_version": env_info.python_version,
                    "packages_count": len(env_info.packages)
                })
            
            return {
                "system": system_info,
                "python_versions": python_versions,
                "gestvenv_config": gestvenv_config,
                "environments": environments_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations système: {str(e)}")
            return {
                "error": f"Erreur lors de la récupération des informations système: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _update_environment_packages(self, env_name: str) -> None:
        """
        Met à jour la liste des packages dans la configuration d'un environnement.
        
        Args:
            env_name: Nom de l'environnement à mettre à jour.
        """
        try:
            # Récupérer la liste mise à jour des packages installés
            installed_packages = self.pkg_service.list_installed_packages(env_name)
            
            # Obtenir l'environnement
            env_info = self.config_manager.get_environment(env_name)
            if not env_info:
                return
            
            # Mettre à jour les packages installés
            env_info.packages_installed = [
                PackageInfo(name=pkg["name"], version=pkg["version"])
                for pkg in installed_packages
            ]
            
            # Mettre à jour la liste des packages configurés
            env_info.packages = [
                f"{pkg['name']}=={pkg['version']}"
                for pkg in installed_packages
            ]
            
            # Sauvegarder les modifications
            self.config_manager.update_environment(env_info)
            
        except Exception as e:
            logger.warning(f"Erreur lors de la mise à jour des packages de l'environnement {env_name}: {str(e)}")