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
from typing import Dict, List, Optional, Tuple, Any, Union, Set

from ..core.models import PackageInfo
from gestvenv.services.environment_service import EnvironmentService
from gestvenv.services.system_service import SystemService
from gestvenv.services.cache_service import CacheService
from gestvenv.core.config_manager import ConfigManager

# Configuration du logger
logger = logging.getLogger(__name__)

class PackageService:
    """Service pour les opérations sur les packages Python."""
    
    def __init__(self) -> None:
        """Initialise le service de gestion des packages."""
        self.env_service = EnvironmentService()
        self.sys_service = SystemService()
        self.cache_service = CacheService()

        # Récupérer le mode hors ligne des paramètres
        config = ConfigManager()
        self.offline_mode = config.get_setting("offline_mode", False)
        self.use_cache = config.get_setting("use_package_cache", True)
    
    def install_packages(self, env_name: str, packages: Union[str, List[str]], 
                        upgrade: bool = False, offline: bool = False,
                        requirements_file: Optional[Path] = None,
                        editable: bool = False, dev: bool = False) -> Tuple[bool, str]:
        """
        Installe des packages dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            packages: Packages à installer (chaîne ou liste).
            upgrade: Si True, met à jour les packages existants.
            offline: Force le mode hors ligne pour cette opération.
            requirements_file: Chemin vers un fichier requirements.txt.
            editable: Si True, installe en mode éditable (-e).
            dev: Si True, installe les dépendances de développement.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Déterminer le mode hors ligne (paramètre ou configuration globale)
            use_offline = offline or self.offline_mode
            
            # Obtenir le chemin de l'environnement
            env_path = self._get_environment_path(env_name)
            if not env_path:
                return False, f"Environnement '{env_name}' non trouvé"
            
            # Obtenir l'exécutable pip
            pip_exe = self.env_service.get_pip_executable(env_name, env_path)
            if not pip_exe:
                return False, f"pip non trouvé dans l'environnement '{env_name}'"
            
            # Traiter l'installation depuis requirements.txt
            if requirements_file:
                return self._install_from_requirements_file(
                    env_name, pip_exe, requirements_file, upgrade, use_offline
                )
            
            # Convertir les packages en liste si c'est une chaîne
            if isinstance(packages, str):
                packages = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
            
            # Vérifier s'il y a des packages à installer
            if not packages:
                return True, "Aucun package à installer"
            
            # Traiter l'installation éditable
            if editable:
                return self._install_editable_packages(
                    env_name, pip_exe, packages, upgrade, use_offline
                )
            
            # Vérifier la disponibilité des packages en mode hors ligne
            if use_offline:
                missing_packages = self._check_packages_availability(packages)
                if missing_packages:
                    return False, f"Mode hors ligne activé mais les packages suivants ne sont pas disponibles dans le cache: {', '.join(missing_packages)}"
            
            # Installer les packages
            return self._install_regular_packages(
                env_name, pip_exe, packages, upgrade, use_offline, dev
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'installation des packages: {str(e)}")
            return False, f"Erreur lors de l'installation des packages: {str(e)}"
    
    def _install_from_requirements_file(self, env_name: str, pip_exe: Path, 
                                       requirements_file: Path, upgrade: bool, 
                                       offline: bool) -> Tuple[bool, str]:
        """Installe des packages depuis un fichier requirements.txt."""
        try:
            if not requirements_file.exists():
                return False, f"Le fichier requirements {requirements_file} n'existe pas"
            
            # Construire la commande d'installation
            cmd = [str(pip_exe), "install", "-r", str(requirements_file)]
            
            if upgrade:
                cmd.append("--upgrade")
            
            if offline:
                cmd.extend(["--no-index", "--find-links", str(self.cache_service.packages_dir)])
            
            # Exécuter la commande
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de l'installation depuis requirements: {result.stderr}")
                return False, f"Échec de l'installation depuis requirements: {result.stderr}"
            
            return True, f"Packages installés avec succès depuis {requirements_file}"
            
        except Exception as e:
            logger.error(f"Erreur lors de l'installation depuis requirements: {str(e)}")
            return False, f"Erreur lors de l'installation depuis requirements: {str(e)}"
    
    def _install_editable_packages(self, env_name: str, pip_exe: Path, 
                                  packages: List[str], upgrade: bool, 
                                  offline: bool) -> Tuple[bool, str]:
        """Installe des packages en mode éditable."""
        try:
            # Construire la commande d'installation éditable
            cmd = [str(pip_exe), "install", "-e"]
            
            if upgrade:
                cmd.append("--upgrade")
            
            if offline:
                cmd.extend(["--no-index", "--find-links", str(self.cache_service.packages_dir)])
            
            # Ajouter les packages (généralement des chemins locaux pour -e)
            cmd.extend(packages)
            
            # Exécuter la commande
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de l'installation éditable: {result.stderr}")
                return False, f"Échec de l'installation éditable: {result.stderr}"
            
            return True, f"Packages installés en mode éditable avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de l'installation éditable: {str(e)}")
            return False, f"Erreur lors de l'installation éditable: {str(e)}"
    
    def _install_regular_packages(self, env_name: str, pip_exe: Path, 
                                 packages: List[str], upgrade: bool, 
                                 offline: bool, dev: bool) -> Tuple[bool, str]:
        """Installe des packages réguliers."""
        try:
            # Si le cache est activé, utiliser les packages du cache si disponibles
            if self.use_cache and not offline:
                cached_packages, non_cached_packages = self._separate_cached_packages(packages)
                
                # Installer d'abord les packages depuis le cache
                if cached_packages:
                    success, message = self._install_from_cache(pip_exe, cached_packages, upgrade)
                    if not success:
                        return False, message
                
                # Continuer avec les packages non mis en cache
                packages = non_cached_packages
                
                # Si tous les packages étaient dans le cache, terminer
                if not packages:
                    return True, f"{len(cached_packages)} package(s) installé(s) avec succès depuis le cache"
            
            # Construire la commande d'installation pour les packages restants
            cmd = [str(pip_exe), "install"]
            
            if upgrade:
                cmd.append("--upgrade")
            
            if offline:
                cmd.extend(["--no-index", "--find-links", str(self.cache_service.packages_dir)])
            
            # Ajouter les packages
            cmd.extend(packages)
            
            # Télécharger et mettre en cache les packages si le cache est activé
            if self.use_cache and not offline:
                self._download_and_cache_packages(packages)
            
            # Exécuter la commande d'installation
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de l'installation des packages: {result.stderr}")
                return False, f"Échec de l'installation des packages: {result.stderr}"
            
            return True, f"{len(packages)} package(s) installé(s) avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de l'installation des packages: {str(e)}")
            return False, f"Erreur lors de l'installation des packages: {str(e)}"
    
    def _check_packages_availability(self, packages: List[str]) -> List[str]:
        """Vérifie la disponibilité des packages dans le cache."""
        missing_packages = []
        
        for pkg in packages:
            # Extraire le nom et la version du package
            pkg_name = pkg.split('==')[0].split('>')[0].split('<')[0].strip()
            pkg_version = None
            
            if '==' in pkg:
                pkg_version = pkg.split('==')[1].strip()
            
            if not self.cache_service.has_package(pkg_name, pkg_version):
                missing_packages.append(pkg)
        
        return missing_packages
    
    def _separate_cached_packages(self, packages: List[str]) -> Tuple[List[str], List[str]]:
        """Sépare les packages disponibles dans le cache de ceux qui ne le sont pas."""
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
        
        return cached_packages, non_cached_packages
    
    def _install_from_cache(self, pip_exe: Path, packages: List[str], 
                           upgrade: bool) -> Tuple[bool, str]:
        """Installe des packages depuis le cache."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copier les fichiers wheel du cache vers le répertoire temporaire
                wheel_files = []
                for pkg in packages:
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
                    
                    return True, f"{len(packages)} package(s) installé(s) depuis le cache"
                
                return True, "Aucun package à installer depuis le cache"
                
        except Exception as e:
            logger.error(f"Erreur lors de l'installation depuis le cache: {str(e)}")
            return False, f"Erreur lors de l'installation depuis le cache: {str(e)}"
    
    def _download_and_cache_packages(self, packages: List[str]) -> None:
        """Télécharge et met en cache des packages."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Télécharger les packages
                cmd = ["pip", "download", "--dest", temp_dir] + packages
                result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
                
                if result.returncode != 0:
                    logger.warning(f"Échec du téléchargement des packages pour le cache: {result.stderr}")
                    return
                
                # Mettre en cache les packages téléchargés
                for file_name in os.listdir(temp_dir):
                    file_path = Path(temp_dir) / file_name
                    if file_path.suffix.lower() in ['.whl', '.tar.gz', '.zip']:
                        # Extraire les informations du package
                        pkg_info = self._extract_package_info(file_name)
                        
                        if pkg_info:
                            # Obtenir les dépendances
                            dependencies = self._get_package_dependencies(pkg_info['name'])
                            
                            # Ajouter le package au cache
                            self.cache_service.add_package(
                                file_path,
                                pkg_info['name'],
                                pkg_info['version'],
                                dependencies
                            )
        except Exception as e:
            logger.warning(f"Erreur lors du téléchargement et de la mise en cache: {str(e)}")
    
    def _extract_package_info(self, filename: str) -> Optional[Dict[str, str]]:
        """Extrait les informations de nom et version d'un fichier de package."""
        try:
            # Supprimer l'extension
            name_without_ext = filename
            for ext in ['.whl', '.tar.gz', '.zip']:
                if filename.endswith(ext):
                    name_without_ext = filename[:-len(ext)]
                    break
            
            # Cas spécial pour .tar.gz
            if filename.endswith('.tar.gz'):
                name_without_ext = filename[:-7]
            
            # Parser le nom
            parts = name_without_ext.split('-')
            
            if len(parts) >= 2:
                package_name = parts[0]
                version = parts[1]
                
                return {
                    'name': package_name,
                    'version': version
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des informations du package {filename}: {e}")
            return {
                'name': filename.split('.')[0],
                'version': 'unknown'
            }
    
    def _get_package_dependencies(self, package_name: str) -> List[str]:
        """Récupère les dépendances d'un package."""
        try:
            cmd = ["pip", "show", package_name]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode == 0:
                # Parser la sortie pour extraire les dépendances
                for line in result.stdout.splitlines():
                    if line.startswith('Requires:'):
                        deps_str = line.split(':', 1)[1].strip()
                        if deps_str and deps_str.lower() != 'none':
                            return [dep.strip() for dep in deps_str.split(',') if dep.strip()]
                        break
            
            return []
        except Exception as e:
            logger.debug(f"Impossible de récupérer les dépendances de {package_name}: {e}")
            return []
    
    def uninstall_packages(self, env_name: str, packages: Union[str, List[str]], 
                          with_dependencies: bool = False, 
                          force: bool = False) -> Tuple[bool, str]:
        """
        Désinstalle des packages d'un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            packages: Packages à désinstaller (chaîne ou liste).
            with_dependencies: Si True, désinstalle aussi les dépendances.
            force: Si True, ne demande pas de confirmation pour les dépendances.
            
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
            
            # Vérifier les dépendances si demandé
            packages_to_uninstall = packages[:]
            
            if with_dependencies:
                dependencies_info = self.check_package_dependencies(env_name, packages)
                
                if dependencies_info and not force:
                    # Afficher les dépendances qui seront affectées
                    dep_message = "Les packages suivants ont des dépendants qui pourraient être affectés:\n"
                    for pkg, dependents in dependencies_info.items():
                        dep_message += f"  {pkg}: {', '.join(dependents)}\n"
                    
                    logger.warning(dep_message)
                    # Note: Dans un vrai CLI, on demanderait confirmation ici
                
                # Ajouter les dépendances à la liste de désinstallation
                for pkg in packages:
                    pkg_name = pkg.split('==')[0].split('>')[0].split('<')[0].strip()
                    deps = self._get_package_dependencies_recursive(env_name, pkg_name)
                    packages_to_uninstall.extend(deps)
                
                # Supprimer les doublons
                packages_to_uninstall = list(set(packages_to_uninstall))
            
            # Construire la commande de désinstallation
            cmd = [str(pip_exe), "uninstall", "-y"]
            cmd.extend(packages_to_uninstall)
            
            # Exécuter la commande de désinstallation
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de la désinstallation des packages: {result.stderr}")
                return False, f"Échec de la désinstallation des packages: {result.stderr}"
            
            count = len(packages_to_uninstall)
            base_count = len(packages)
            
            if with_dependencies and count > base_count:
                return True, f"{base_count} package(s) principal et {count - base_count} dépendance(s) désinstallé(s) avec succès"
            else:
                return True, f"{count} package(s) désinstallé(s) avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de la désinstallation des packages: {str(e)}")
            return False, f"Erreur lors de la désinstallation des packages: {str(e)}"
    
    def _get_package_dependencies_recursive(self, env_name: str, 
                                          package_name: str, 
                                          visited: Optional[Set[str]] = None) -> List[str]:
        """Récupère récursivement toutes les dépendances d'un package."""
        if visited is None:
            visited = set()
        
        if package_name in visited:
            return []
        
        visited.add(package_name)
        dependencies = []
        
        try:
            # Obtenir les informations du package
            package_info = self.show_package_info(package_name, env_name)
            
            if package_info and 'requires' in package_info:
                for dep in package_info['requires']:
                    dep_name = dep.split('==')[0].split('>')[0].split('<')[0].strip()
                    dependencies.append(dep_name)
                    
                    # Récupérer récursivement les dépendances des dépendances
                    sub_deps = self._get_package_dependencies_recursive(env_name, dep_name, visited)
                    dependencies.extend(sub_deps)
            
            return dependencies
            
        except Exception as e:
            logger.debug(f"Erreur lors de la récupération des dépendances de {package_name}: {e}")
            return []
    
    def update_packages(self, env_name: str, packages: Optional[List[str]] = None, 
                       all_packages: bool = False, offline: bool = False) -> Tuple[bool, str]:
        """
        Met à jour des packages dans un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            packages: Liste des packages à mettre à jour.
            all_packages: Si True, met à jour tous les packages.
            offline: Force le mode hors ligne pour cette opération.
            
        Returns:
            Tuple contenant (succès, message).
        """
        try:
            # Déterminer le mode hors ligne
            use_offline = offline or self.offline_mode
            
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
            
            if use_offline:
                cmd.extend(["--no-index", "--find-links", str(self.cache_service.packages_dir)])
            
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
                    if package_info[key] and package_info[key].lower() != 'none':
                        package_info[key] = [item.strip() for item in package_info[key].split(',')]
                    else:
                        package_info[key] = []
                else:
                    # Ajouter la clé si elle n'existe pas
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
    
    def install_from_requirements(self, env_name: str, requirements_path: Path, 
                                 offline: bool = False) -> Tuple[bool, str]:
        """
        Installe les packages à partir d'un fichier requirements.txt.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            requirements_path: Chemin vers le fichier requirements.txt.
            offline: Force le mode hors ligne pour cette opération.
            
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
            
            # Utiliser la méthode helper
            return self._install_from_requirements_file(
                env_name, pip_exe, requirements_path, False, offline or self.offline_mode
            )
            
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
    
    def check_offline_availability(self, packages: Union[str, List[str], Path]) -> Dict[str, bool]:
        """
        Vérifie si des packages sont disponibles hors ligne dans le cache.
        
        Args:
            packages: Liste de packages ou chemin vers requirements.txt
            
        Returns:
            Dictionnaire indiquant la disponibilité de chaque package
        """
        result = {}
        
        try:
            # Si c'est un chemin vers requirements.txt
            if isinstance(packages, Path) and packages.exists():
                with open(packages, 'r') as f:
                    content = f.read()
                
                # Parser le fichier requirements
                package_list = []
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        package_list.append(line)
                
                packages = package_list
            
            # Convertir en liste si c'est une chaîne
            if isinstance(packages, str):
                packages = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
            
            # Vérifier chaque package
            for pkg in packages:
                # Extraire le nom et la version du package
                pkg_name = pkg.split('==')[0].split('>')[0].split('<')[0].strip()
                pkg_version = None
                
                if '==' in pkg:
                    pkg_version = pkg.split('==')[1].strip()
                
                # Vérifier la disponibilité dans le cache
                result[pkg] = self.cache_service.has_package(pkg_name, pkg_version)
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la disponibilité hors ligne: {str(e)}")
            return result
    
    def get_package_size(self, package_name: str, version: Optional[str] = None) -> Optional[int]:
        """
        Récupère la taille d'un package depuis le cache.
        
        Args:
            package_name: Nom du package
            version: Version du package (optionnel)
            
        Returns:
            Taille en octets ou None si non trouvé
        """
        try:
            if package_name in self.cache_service.index:
                versions = self.cache_service.index[package_name]["versions"]
                
                if version and version in versions:
                    return versions[version].get("size", 0)
                elif not version and versions:
                    # Prendre la première version disponible
                    first_version = next(iter(versions.values()))
                    return first_version.get("size", 0)
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la taille du package: {str(e)}")
            return None
    
    def _get_environment_path(self, env_name: str) -> Optional[Path]:
        """
        Obtient le chemin d'un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            
        Returns:
            Path ou None si introuvable.
        """
        try:
            from ..core.config_manager import ConfigManager
            
            # Obtenir le chemin depuis la configuration
            config_manager = ConfigManager()
            env_info = config_manager.get_environment(env_name)
            
            if env_info and hasattr(env_info, 'path'):
                return Path(env_info.path)
        except Exception:
            pass
        
        # Essayer avec le chemin par défaut
        default_path = self.env_service.get_default_venv_dir() / env_name
        if default_path.exists():
            return default_path
        
        return None