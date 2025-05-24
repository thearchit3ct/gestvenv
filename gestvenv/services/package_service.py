"""
Service pour la gestion des packages dans les environnements virtuels.

Ce module fournit les fonctionnalités pour installer, mettre à jour,
supprimer et gérer les packages Python dans les environnements virtuels.
"""

import os
import re
import json
import logging
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from ..core.models import PackageInfo
from .cache_service import CacheService

# Configuration du logger
logger = logging.getLogger(__name__)

class PackageService:
    """Service pour les opérations sur les packages Python."""
    
    def __init__(self) -> None:
        """Initialise le service de gestion des packages."""
        from .environment_service import EnvironmentService
        from .system_service import SystemService
        from .cache_service import CacheService
        
        self.env_service = EnvironmentService()
        self.sys_service = SystemService()
        self.cache_service = CacheService()
        
        # Récupérer le mode hors ligne des paramètres
        from ..core.config_manager import ConfigManager
        config = ConfigManager()
        self.offline_mode = config.get_setting("offline_mode", False)
        self.use_cache = config.get_setting("use_package_cache", True)
    
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
            
            # Vérifier si le mode hors ligne est activé et si tous les packages sont disponibles dans le cache
            if self.offline_mode:
                # Vérifier la disponibilité des packages dans le cache
                missing_packages = []
                for pkg in packages:
                    # Extraire le nom et la version du package
                    pkg_name = pkg.split('==')[0].split('>')[0].split('<')[0].strip()
                    pkg_version = None
                    
                    if '==' in pkg:
                        pkg_version = pkg.split('==')[1].strip()
                    
                    if not self.cache_service.has_package(pkg_name, pkg_version):
                        missing_packages.append(pkg)
                
                if missing_packages:
                    return False, f"Mode hors ligne activé mais les packages suivants ne sont pas disponibles dans le cache: {', '.join(missing_packages)}"
            
            # Si le cache est activé, utiliser les packages du cache si disponibles
            if self.use_cache:
                # Filtrer les packages qui sont disponibles dans le cache
                cached_packages = []
                non_cached_packages = []
                
                for pkg in packages:
                    # Extraire le nom et la version du package
                    pkg_name = pkg.split('==')[0].split('>')[0].split('<')[0].strip()
                    pkg_version = None
                    
                    if '==' in pkg:
                        pkg_version = pkg.split('==')[1].strip()
                    
                    if self.cache_service.has_package(pkg_name, pkg_version):
                        cached_packages.append(pkg)
                    else:
                        non_cached_packages.append(pkg)
                
                # Installer les packages depuis le cache
                if cached_packages:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Copier les fichiers wheel du cache vers le répertoire temporaire
                        wheel_files = []
                        for pkg in cached_packages:
                            pkg_name = pkg.split('==')[0].split('>')[0].split('<')[0].strip()
                            pkg_version = None
                            
                            if '==' in pkg:
                                pkg_version = pkg.split('==')[1].strip()
                            
                            # Récupérer le package du cache
                            pkg_path = self.cache_service.get_package(pkg_name, pkg_version)
                            if pkg_path:
                                # Copier le fichier wheel dans le répertoire temporaire
                                dest_path = Path(temp_dir) / pkg_path.name
                                shutil.copy2(pkg_path, dest_path)
                                wheel_files.append(str(dest_path))
                        
                        # Installer les fichiers wheel
                        if wheel_files:
                            cmd = [str(pip_exe), "install"]
                            
                            if upgrade:
                                cmd.append("--upgrade")
                            
                            # Ajouter les chemins des fichiers wheel
                            cmd.extend(wheel_files)
                            
                            # Exécuter la commande d'installation
                            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
                            
                            if result.returncode != 0:
                                logger.error(f"Échec de l'installation des packages depuis le cache: {result.stderr}")
                                return False, f"Échec de l'installation des packages depuis le cache: {result.stderr}"
                
                # Si tous les packages sont installés depuis le cache, terminer
                if not non_cached_packages:
                    return True, f"{len(cached_packages)} package(s) installé(s) avec succès depuis le cache"
                
                # Continuer avec les packages non mis en cache
                packages = non_cached_packages
                
                # Si mode hors ligne mais des packages ne sont pas dans le cache
                if self.offline_mode and packages:
                    return False, f"Mode hors ligne activé mais les packages suivants ne sont pas disponibles dans le cache: {', '.join(packages)}"
            
            # Construire la commande d'installation pour les packages restants
            cmd = [str(pip_exe), "install"]
            
            if upgrade:
                cmd.append("--upgrade")
            
            # Télécharger les packages dans un répertoire temporaire pour mise en cache
            if self.use_cache and not self.offline_mode:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Ajouter l'option pour télécharger les packages sans les installer
                    download_cmd = cmd + ["--dest", temp_dir] + packages
                    
                    # Exécuter la commande de téléchargement
                    result = subprocess.run(download_cmd, capture_output=True, text=True, shell=False, check=False)
                    
                    if result.returncode != 0:
                        logger.error(f"Échec du téléchargement des packages: {result.stderr}")
                    else:
                        # Mettre en cache les packages téléchargés
                        for file_name in os.listdir(temp_dir):
                            file_path = Path(temp_dir) / file_name
                            if file_path.suffix.lower() in ['.whl', '.tar.gz', '.zip']:
                                # Obtenir les informations du package depuis pip show
                                show_cmd = [str(pip_exe), "show", file_path.stem.split('-')[0]]
                                show_result = subprocess.run(show_cmd, capture_output=True, text=True, shell=False, check=False)
                                
                                if show_result.returncode == 0:
                                    # Extraire les informations du package
                                    pkg_info = {}
                                    dependencies = []
                                    
                                    for line in show_result.stdout.splitlines():
                                        if ': ' in line:
                                            key, value = line.split(': ', 1)
                                            pkg_info[key.lower()] = value.strip()
                                            
                                            # Récupérer les dépendances
                                            if key.lower() == 'requires':
                                                dependencies = [dep.strip() for dep in value.split(',') if dep.strip()]
                                    
                                    # Ajouter le package au cache
                                    if 'name' in pkg_info and 'version' in pkg_info:
                                        self.cache_service.add_package(
                                            file_path,
                                            pkg_info['name'],
                                            pkg_info['version'],
                                            dependencies
                                        )
            
            # Installer les packages
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