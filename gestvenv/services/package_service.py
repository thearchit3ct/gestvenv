"""
Service pour la gestion des packages dans les environnements virtuels.

Ce module fournit les fonctionnalités pour installer, mettre à jour,
supprimer et gérer les packages Python dans les environnements virtuels.
"""

import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from ..core.models import PackageInfo

# Configuration du logger
logger = logging.getLogger(__name__)

class PackageService:
    """Service pour les opérations sur les packages Python."""
    
    def __init__(self) -> None:
        """Initialise le service de gestion des packages."""
        from .environment_service import EnvironmentService
        from .system_service import SystemService
        
        self.env_service = EnvironmentService()
        self.sys_service = SystemService()
    
    def install_packages(self, env_name: str, packages: Union[str, List[str]], 
                        upgrade: bool = False) -> Tuple[bool, str]:
        """
        Installe des packages dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            packages: Packages à installer (chaîne ou liste).
            upgrade: Si True, met à jour les packages existants.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Convertir les packages en liste si c'est une chaîne
            if isinstance(packages, str):
                packages = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
            
            # Vérifier s'il y a des packages à installer
            if not packages:
                return True, "Aucun package à installer"
            
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                return False, f"Environnement '{env_name}' non trouvé"
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                return False, f"pip non trouvé dans l'environnement '{env_name}'"
            
            # Construire la commande d'installation
            cmd = [str(pip_exe), "install"]
            
            if upgrade:
                cmd.append("--upgrade")
            
            # Ajouter les packages à la commande
            cmd.extend(packages)
            
            # Exécuter la commande d'installation
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de l'installation des packages: {result.stderr}")
                return False, f"Échec de l'installation des packages: {result.stderr}"
            
            return True, f"{len(packages)} package(s) installé(s) avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de l'installation des packages: {str(e)}")
            return False, f"Erreur lors de l'installation des packages: {str(e)}"
    
    def uninstall_packages(self, env_name: str, packages: Union[str, List[str]]) -> Tuple[bool, str]:
        """
        Désinstalle des packages d'un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            packages: Packages à désinstaller (chaîne ou liste).
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Convertir les packages en liste si c'est une chaîne
            if isinstance(packages, str):
                packages = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
            
            # Vérifier s'il y a des packages à désinstaller
            if not packages:
                return True, "Aucun package à désinstaller"
            
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                return False, f"Environnement '{env_name}' non trouvé"
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                return False, f"pip non trouvé dans l'environnement '{env_name}'"
            
            # Construire la commande de désinstallation
            cmd = [str(pip_exe), "uninstall", "-y"]
            cmd.extend(packages)
            
            # Exécuter la commande de désinstallation
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de la désinstallation des packages: {result.stderr}")
                return False, f"Échec de la désinstallation des packages: {result.stderr}"
            
            return True, f"{len(packages)} package(s) désinstallé(s) avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de la désinstallation des packages: {str(e)}")
            return False, f"Erreur lors de la désinstallation des packages: {str(e)}"
    
    def update_packages(self, env_name: str, packages: Optional[List[str]] = None, 
                       all_packages: bool = False) -> Tuple[bool, str]:
        """
        Met à jour des packages dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            packages: Liste des packages à mettre à jour.
            all_packages: Si True, met à jour tous les packages.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                return False, f"Environnement '{env_name}' non trouvé"
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                return False, f"pip non trouvé dans l'environnement '{env_name}'"
            
            # Déterminer quels packages mettre à jour
            if all_packages:
                # Obtenir la liste de tous les packages installés
                installed = self.list_installed_packages(env_name)
                if not installed:
                    return False, f"Impossible d'obtenir la liste des packages installés dans '{env_name}'"
                
                packages_to_update = [pkg["name"] for pkg in installed]
                
                if not packages_to_update:
                    return True, "Aucun package à mettre à jour"
            elif packages:
                packages_to_update = packages
            else:
                return False, "Aucun package spécifié et --all n'est pas utilisé"
            
            # Construire la commande de mise à jour
            cmd = [str(pip_exe), "install", "--upgrade"]
            cmd.extend(packages_to_update)
            
            # Exécuter la commande de mise à jour
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de la mise à jour des packages: {result.stderr}")
                return False, f"Échec de la mise à jour des packages: {result.stderr}"
            
            return True, f"{len(packages_to_update)} package(s) mis à jour avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des packages: {str(e)}")
            return False, f"Erreur lors de la mise à jour des packages: {str(e)}"
    
    def list_installed_packages(self, env_name: str) -> List[Dict[str, str]]:
        """
        Liste les packages installés dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            
        Returns:
            Liste des packages installés avec leur version.
        """
        try:
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                logger.error(f"Environnement '{env_name}' non trouvé")
                return []
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                logger.error(f"pip non trouvé dans l'environnement '{env_name}'")
                return []
            
            # Exécuter la commande pour lister les packages au format JSON
            cmd = [str(pip_exe), "list", "--format=json"]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de la récupération des packages installés: {result.stderr}")
                return []
            
            # Analyser la sortie JSON
            try:
                packages = json.loads(result.stdout)
                return packages
            except json.JSONDecodeError as e:
                logger.error(f"Erreur lors de l'analyse de la liste des packages: {str(e)}")
                return []
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des packages installés: {str(e)}")
            return []
    
    def show_package_info(self, package_name: str, env_name: str) -> Optional[Dict[str, Any]]:
        """
        Affiche des informations détaillées sur un package.
        
        Args:
            package_name: Nom du package.
            env_name: Nom de l'environnement virtuel.
            
        Returns:
            Dictionnaire d'informations sur le package ou None si erreur.
        """
        try:
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                logger.error(f"Environnement '{env_name}' non trouvé")
                return None
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                logger.error(f"pip non trouvé dans l'environnement '{env_name}'")
                return None
            
            # Exécuter la commande pour afficher les informations du package
            cmd = [str(pip_exe), "show", package_name]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de la récupération des informations sur '{package_name}': {result.stderr}")
                return None
            
            # Analyser les informations du package
            package_info = {}
            for line in result.stdout.strip().split('\n'):
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    package_info[key.strip().lower().replace('-', '_')] = value.strip()
            
            # Convertir les listes
            for key in ['requires', 'required_by']:
                if key in package_info:
                    if package_info[key]:
                        package_info[key] = [item.strip() for item in package_info[key].split(',')]
                    else:
                        package_info[key] = []
            
            return package_info
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations sur '{package_name}': {str(e)}")
            return None
    
    def export_requirements(self, env_name: str, output_path: Path) -> Tuple[bool, str]:
        """
        Exporte les packages installés dans un fichier requirements.txt.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            output_path: Chemin du fichier de sortie.
            
        Returns:
            Tuple contenant (succès, chemin du fichier).
        """
        try:
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                return False, f"Environnement '{env_name}' non trouvé"
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                return False, f"pip non trouvé dans l'environnement '{env_name}'"
            
            # Créer le répertoire parent si nécessaire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Exécuter la commande pour générer requirements.txt
            cmd = [str(pip_exe), "freeze"]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de la génération du fichier requirements: {result.stderr}")
                return False, f"Échec de la génération du fichier requirements: {result.stderr}"
            
            # Écrire le contenu dans le fichier requirements.txt
            with open(output_path, "w") as f:
                f.write(result.stdout)
            
            logger.info(f"Fichier requirements exporté avec succès vers {output_path}")
            return True, str(output_path)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export des requirements: {str(e)}")
            return False, f"Erreur lors de l'export des requirements: {str(e)}"
    
    def install_from_requirements(self, env_name: str, requirements_path: Path) -> Tuple[bool, str]:
        """
        Installe les packages à partir d'un fichier requirements.txt.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            requirements_path: Chemin vers le fichier requirements.txt.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Vérifier que le fichier requirements.txt existe
            if not requirements_path.exists():
                return False, f"Le fichier requirements {requirements_path} n'existe pas"
            
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                return False, f"Environnement '{env_name}' non trouvé"
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                return False, f"pip non trouvé dans l'environnement '{env_name}'"
            
            # Construire la commande d'installation depuis requirements
            cmd = [str(pip_exe), "install", "-r", str(requirements_path)]
            
            # Exécuter la commande
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de l'installation depuis requirements: {result.stderr}")
                return False, f"Échec de l'installation depuis requirements: {result.stderr}"
            
            logger.info(f"Packages installés avec succès depuis {requirements_path}")
            return True, f"Packages installés avec succès depuis {requirements_path}"
            
        except Exception as e:
            logger.error(f"Erreur lors de l'installation depuis requirements: {str(e)}")
            return False, f"Erreur lors de l'installation depuis requirements: {str(e)}"
    
    def check_for_updates(self, env_name: str) -> List[Dict[str, str]]:
        """
        Vérifie les mises à jour disponibles pour les packages d'un environnement.
        
        Args:
            env_name: Nom de l'environnement.
            
        Returns:
            Liste des packages pouvant être mis à jour.
        """
        try:
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                logger.error(f"Environnement '{env_name}' non trouvé")
                return []
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                logger.error(f"pip non trouvé dans l'environnement '{env_name}'")
                return []
            
            # Exécuter la commande pour vérifier les mises à jour
            cmd = [str(pip_exe), "list", "--outdated", "--format=json"]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de la vérification des mises à jour: {result.stderr}")
                return []
            
            # Analyser la sortie JSON
            try:
                raw_updates = json.loads(result.stdout)
                
                # Normaliser la structure pour s'assurer que toutes les clés nécessaires existent
                updates = []
                for pkg in raw_updates:
                    updates.append({
                        "name": pkg.get("name", ""),
                        "current_version": pkg.get("version", ""),
                        "latest_version": pkg.get("latest_version", "")
                    })
                
                return updates
            except json.JSONDecodeError as e:
                logger.error(f"Erreur lors de l'analyse des mises à jour: {str(e)}")
                return []
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des mises à jour: {str(e)}")
            return []
    
    def check_package_dependencies(self, env_name: str, packages: Union[str, List[str]]) -> Dict[str, List[str]]:
        """
        Vérifie les dépendances d'un package avant suppression.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            packages: Packages à vérifier (chaîne ou liste).
            
        Returns:
            Dictionnaire des packages et leurs dépendants.
        """
        result = {}
        
        try:
            # Convertir les packages en liste si c'est une chaîne
            if isinstance(packages, str):
                packages = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
            
            # Vérifier chaque package
            for package in packages:
                # Extraire le nom du package (sans la version)
                package_name = package.split('==')[0].split('>')[0].split('<')[0].strip()
                
                # Obtenir les informations sur le package
                package_info = self.show_package_info(package_name, env_name)
                
                if package_info and 'required_by' in package_info and package_info['required_by']:
                    result[package_name] = package_info['required_by']
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des dépendances: {str(e)}")
            return result
    
    def _get_environment_path(self, env_name: str) -> Optional[Path]:
        """
        Obtient le chemin d'un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            
        Returns:
            Path ou None si introuvable.
        """
        from ..core.config_manager import ConfigManager
        
        # Obtenir le chemin depuis la configuration
        config_manager = ConfigManager()
        env_info = config_manager.get_environment(env_name)
        
        if env_info:
            return Path(env_info.path)
        
        # Essayer avec le chemin par défaut
        default_path: Path = self.env_service.get_default_venv_dir() / env_name
        if default_path.exists():
            return default_path
        
        return None