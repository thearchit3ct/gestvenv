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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

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
                           packages: Optional[str] = None, path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Crée un nouvel environnement virtuel Python.
        
        Args:
            name: Nom de l'environnement.
            python_version: Version Python à utiliser.
            packages: Liste de packages à installer, séparés par des virgules.
            path: Chemin personnalisé pour l'environnement.
            
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
        package_list = []
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
        
        # Installer les packages si spécifiés
        if package_list:
            try:
                success, pkg_message = self.pkg_service.install_packages(name, package_list)
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
        
        # Créer l'objet EnvironmentInfo
        env_info = EnvironmentInfo(
            name=name,
            path=env_path,
            python_version=python_version_actual or python_cmd,
            created_at=datetime.now(),
            packages=package_list,
            health=self.env_service.check_environment_health(name, env_path)
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
            result.append({
                "name": name,
                "path": str(env_info.path),
                "python_version": env_info.python_version,
                "created_at": env_info.created_at.isoformat() if isinstance(env_info.created_at, datetime) else env_info.created_at,
                "packages_count": len(env_info.packages),
                "active": name == active_env,
                "health": health.to_dict(),
                "exists": exists
            })
        
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
        
        # Ajouter des informations supplémentaires si l'environnement existe
        if exists:
            result.update({
                "python_executable": str(self.env_service.get_python_executable(name, env_info.path)),
                "pip_executable": str(self.env_service.get_pip_executable(name, env_info.path)),
                "activation_script": str(self.env_service.get_activation_script_path(name, env_info.path))
            })
        
        return result
    
    def clone_environment(self, source_name: str, target_name: str) -> Tuple[bool, str]:
        """
        Clone un environnement existant vers un nouveau.
        
        Args:
            source_name: Nom de l'environnement source.
            target_name: Nom du nouvel environnement.
            
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
        
        # Créer un nouvel environnement avec la même version Python
        success, message = self.create_environment(target_name, source_info.python_version)
        if not success:
            return False, f"Erreur lors de la création du nouvel environnement: {message}"
        
        # Installer les mêmes packages que dans l'environnement source
        if source_info.packages:
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
                          format_type: str = "json", metadata: Optional[str] = None) -> Tuple[bool, str]:
        """
        Exporte la configuration d'un environnement.
        
        Args:
            name: Nom de l'environnement à exporter.
            output_path: Chemin de sortie pour le fichier d'export.
            format_type: Format d'export ('json' ou 'requirements').
            metadata: Métadonnées supplémentaires à inclure.
            
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
        metadata_dict = {}
        if metadata:
            valid, metadata_dict, error = self.env_service.validate_metadata(metadata)
            if not valid:
                return False, error
        
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
    
    def import_environment(self, input_path: str, name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Importe un environnement depuis un fichier de configuration.
        
        Args:
            input_path: Chemin vers le fichier de configuration.
            name: Nom à utiliser pour le nouvel environnement.
            
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
                
                # Vérifier si l'environnement existe déjà
                if self.config_manager.environment_exists(name):
                    return False, f"L'environnement '{name}' existe déjà"
                
                # Créer l'environnement
                success, message = self.create_environment(name)
                if not success:
                    return False, f"Erreur lors de la création de l'environnement: {message}"
                
                # Installer les packages depuis le fichier requirements.txt
                try:
                    success, pkg_message = self.pkg_service.install_from_requirements(name, resolved_path)
                    if not success:
                        # En cas d'échec, essayer de supprimer l'environnement créé
                        self.delete_environment(name, force=True)
                        return False, f"Erreur lors de l'installation des packages: {pkg_message}"
                except Exception as e:
                    # En cas d'erreur, essayer de supprimer l'environnement créé
                    self.delete_environment(name, force=True)
                    return False, f"Erreur lors de l'installation des packages: {str(e)}"
                
                return True, f"Environnement importé avec succès depuis {resolved_path} sous le nom '{name}'"
            else:
                return False, f"Format de fichier non pris en charge: {resolved_path.suffix}"
        
        except Exception as e:
            return False, f"Erreur lors de l'import de l'environnement: {str(e)}"
    
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
    
    def run_command_in_environment(self, env_name: str, command: List[str]) -> Tuple[int, str, str]:
        """
        Exécute une commande dans un environnement virtuel spécifique.
        
        Args:
            env_name: Nom de l'environnement.
            command: Commande à exécuter.
            
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
        
        # Exécuter la commande dans l'environnement
        return self.sys_service.run_in_environment(env_name, env_info.path, command)
    
    def update_packages(self, env_name: str, packages: Optional[str] = None, 
                        all_packages: bool = False) -> Tuple[bool, str]:
        """
        Met à jour des packages dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement.
            packages: Liste de packages à mettre à jour séparés par des virgules.
            all_packages: Si True, met à jour tous les packages.
            
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
            success, message = self.pkg_service.update_packages(env_name, package_list, all_packages)
            if not success:
                return False, message
        except Exception as e:
            return False, f"Erreur lors de la mise à jour des packages: {str(e)}"
        
        # Mettre à jour la configuration avec les nouveaux packages
        try:
            # Récupérer la liste mise à jour des packages installés
            installed_packages = self.pkg_service.list_installed_packages(env_name)
            
            # Mettre à jour l'environnement dans la configuration
            env_info.packages_installed = [
                PackageInfo(name=pkg["name"], version=pkg["version"])
                for pkg in installed_packages
            ]
            
            # Mettre à jour les packages configurés si nécessaire
            if all_packages or package_list:
                env_info.packages = [
                    f"{pkg['name']}=={pkg['version']}"
                    for pkg in installed_packages
                ]
            
            # Sauvegarder les modifications
            self.config_manager.update_environment(env_info)
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

