#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de gestion des packages Python dans les environnements virtuels.

Ce module fournit les fonctionnalités pour installer, mettre à jour,
supprimer et gérer les packages Python dans les environnements virtuels.
"""

import os
import re
import json
import logging
import subprocess
from pathlib import Path

# Imports internes
from ..utils.system_commands import run_command
from ..utils.validators import validate_package_name, validate_environment_exists
from ..core.env_manager import EnvironmentManager

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PackageManager:
    """Gestionnaire de packages pour les environnements virtuels Python."""
    
    def __init__(self, config_path=None):
        """
        Initialiser le gestionnaire de packages.
        
        Args:
            config_path (str, optional): Chemin vers le fichier de configuration.
                Si None, utilise le chemin par défaut.
        """
        self.env_manager = EnvironmentManager(config_path)
    
    def install_packages(self, packages, env_name=None, upgrade=False, 
                         editable=False, requirements=None, index_url=None):
        """
        Installer des packages dans un environnement virtuel.
        
        Args:
            packages (str or list): Packages à installer.
                Peut être une chaîne délimitée par des virgules ou une liste.
            env_name (str, optional): Nom de l'environnement cible.
                Si None, utilise l'environnement actif.
            upgrade (bool, optional): Si True, met à jour les packages s'ils existent déjà.
            editable (bool, optional): Si True, installe les packages en mode éditable (-e).
            requirements (str, optional): Chemin vers un fichier requirements.txt.
            index_url (str, optional): URL d'un index alternatif pour PyPI.
        
        Returns:
            dict: Résultat de l'opération d'installation.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        # Déterminer l'environnement cible
        target_env = self._get_target_environment(env_name)
        
        pip_args = ["install"]
        
        # Ajouter les options
        if upgrade:
            pip_args.append("--upgrade")
        
        if index_url:
            pip_args.extend(["--index-url", index_url])
        
        # Gérer les requirements.txt
        if requirements:
            if not os.path.exists(requirements):
                raise ValueError(f"Le fichier requirements {requirements} n'existe pas.")
            pip_args.extend(["-r", requirements])
        
        # Gérer les packages individuels
        if packages:
            if isinstance(packages, str):
                packages = [pkg.strip() for pkg in packages.split(",") if pkg.strip()]
            
            # Valider les noms de packages
            for pkg in packages:
                pkg_name = pkg.split("==")[0].split(">")[0].split("<")[0].split("@")[0].strip()
                if not validate_package_name(pkg_name):
                    raise ValueError(f"Nom de package invalide: {pkg_name}")
            
            # Ajouter en mode éditable si demandé
            if editable:
                for i, pkg in enumerate(packages):
                    if os.path.isdir(pkg) or pkg.startswith("git+"):
                        packages[i] = f"-e {pkg}"
            
            pip_args.extend(packages)
        
        # Vérifier qu'il y a au moins des packages ou un fichier requirements
        if not (packages or requirements):
            raise ValueError("Aucun package ou fichier requirements spécifié.")
        
        # Exécuter la commande pip
        logger.info(f"Installation de packages dans l'environnement {target_env}...")
        result = self._run_pip_command(target_env, pip_args)
        
        if result['returncode'] == 0:
            # Mettre à jour la liste des packages dans la configuration
            self._update_package_list(target_env)
            return {
                "status": "success",
                "message": f"Packages installés avec succès dans {target_env}",
                "details": result['stdout']
            }
        else:
            return {
                "status": "error",
                "message": f"Échec de l'installation des packages dans {target_env}",
                "details": result['stderr'] or result['stdout']
            }
    
    def uninstall_packages(self, packages, env_name=None, yes=False, dry_run=False):
        """
        Désinstaller des packages d'un environnement virtuel.
        
        Args:
            packages (str or list): Packages à désinstaller.
                Peut être une chaîne délimitée par des virgules ou une liste.
            env_name (str, optional): Nom de l'environnement cible.
                Si None, utilise l'environnement actif.
            yes (bool, optional): Si True, confirme automatiquement la suppression.
            dry_run (bool, optional): Si True, simule l'opération sans l'exécuter.
        
        Returns:
            dict: Résultat de l'opération de désinstallation.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        # Déterminer l'environnement cible
        target_env = self._get_target_environment(env_name)
        
        # Convertir les packages en liste
        if isinstance(packages, str):
            packages = [pkg.strip() for pkg in packages.split(",") if pkg.strip()]
        
        # Vérifier les dépendances avant suppression
        if not dry_run and not yes:
            deps_info = self.check_package_dependencies(packages, target_env)
            if deps_info["dependent_packages"]:
                deps_str = ", ".join([f"{pkg} (requis par {', '.join(deps)})" 
                                    for pkg, deps in deps_info["dependent_packages"].items()])
                print(f"Attention: Les packages suivants ont des dépendances: {deps_str}")
                confirm = input("Voulez-vous continuer? (y/n): ")
                if confirm.lower() != 'y':
                    return {
                        "status": "cancelled",
                        "message": "Désinstallation annulée."
                    }
        
        # Préparer les arguments pip
        pip_args = ["uninstall"]
        
        if yes:
            pip_args.append("-y")
        
        if dry_run:
            pip_args.append("--dry-run")
        
        pip_args.extend(packages)
        
        # Exécuter la commande pip
        logger.info(f"Désinstallation de packages de l'environnement {target_env}...")
        result = self._run_pip_command(target_env, pip_args)
        
        if result['returncode'] == 0 or dry_run:
            # Mettre à jour la liste des packages dans la configuration si ce n'est pas un dry run
            if not dry_run:
                self._update_package_list(target_env)
            
            return {
                "status": "success",
                "message": f"Packages désinstallés avec succès de {target_env}" if not dry_run 
                         else f"Simulation de désinstallation réussie pour {target_env}",
                "details": result['stdout']
            }
        else:
            return {
                "status": "error",
                "message": f"Échec de la désinstallation des packages de {target_env}",
                "details": result['stderr'] or result['stdout']
            }
    
    def update_packages(self, packages=None, env_name=None, all_packages=False):
        """
        Mettre à jour des packages dans un environnement virtuel.
        
        Args:
            packages (str or list, optional): Packages à mettre à jour.
                Si None et all_packages=True, met à jour tous les packages.
            env_name (str, optional): Nom de l'environnement cible.
                Si None, utilise l'environnement actif.
            all_packages (bool, optional): Si True, met à jour tous les packages.
        
        Returns:
            dict: Résultat de l'opération de mise à jour.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        # Déterminer l'environnement cible
        target_env = self._get_target_environment(env_name)
        
        pip_args = ["install", "--upgrade"]
        
        # Déterminer quels packages mettre à jour
        if all_packages:
            # Liste tous les packages installés
            installed_packages = self.list_packages(target_env)
            packages_to_update = [pkg["name"] for pkg in installed_packages]
            
            if not packages_to_update:
                return {
                    "status": "info",
                    "message": f"Aucun package à mettre à jour dans {target_env}."
                }
        else:
            # Utiliser les packages spécifiés
            if not packages:
                raise ValueError("Aucun package spécifié pour la mise à jour.")
            
            if isinstance(packages, str):
                packages_to_update = [pkg.strip() for pkg in packages.split(",") if pkg.strip()]
            else:
                packages_to_update = packages
        
        pip_args.extend(packages_to_update)
        
        # Exécuter la commande pip
        logger.info(f"Mise à jour des packages dans l'environnement {target_env}...")
        result = self._run_pip_command(target_env, pip_args)
        
        if result['returncode'] == 0:
            # Mettre à jour la liste des packages dans la configuration
            self._update_package_list(target_env)
            return {
                "status": "success",
                "message": f"Packages mis à jour avec succès dans {target_env}",
                "details": result['stdout']
            }
        else:
            return {
                "status": "error",
                "message": f"Échec de la mise à jour des packages dans {target_env}",
                "details": result['stderr'] or result['stdout']
            }
    
    def list_packages(self, env_name=None, outdated=False, format="list"):
        """
        Lister les packages installés dans un environnement virtuel.
        
        Args:
            env_name (str, optional): Nom de l'environnement cible.
                Si None, utilise l'environnement actif.
            outdated (bool, optional): Si True, liste uniquement les packages obsolètes.
            format (str, optional): Format de sortie ("list" ou "json").
        
        Returns:
            list: Liste des packages installés ou obsolètes.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        # Déterminer l'environnement cible
        target_env = self._get_target_environment(env_name)
        
        if outdated:
            pip_args = ["list", "--outdated"]
            if format == "json":
                pip_args.append("--format=json")
        else:
            pip_args = ["list"]
            if format == "json":
                pip_args.append("--format=json")
        
        # Exécuter la commande pip
        result = self._run_pip_command(target_env, pip_args)
        
        if result['returncode'] == 0:
            if format == "json":
                try:
                    return json.loads(result['stdout'])
                except json.JSONDecodeError:
                    logger.error(f"Échec du décodage JSON: {result['stdout']}")
                    return []
            else:
                # Parser la sortie de pip list
                packages = []
                lines = result['stdout'].strip().split('\n')
                
                # Ignorer l'en-tête de pip list (les 2 premières lignes)
                for line in lines[2:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        package = {
                            "name": parts[0],
                            "version": parts[1],
                        }
                        
                        # Ajouter la version la plus récente pour les packages obsolètes
                        if outdated and len(parts) >= 3:
                            package["latest"] = parts[2]
                        
                        packages.append(package)
                
                return packages
        else:
            logger.error(f"Échec de l'obtention de la liste des packages: {result['stderr']}")
            return []
    
    def search_packages(self, query):
        """
        Rechercher des packages sur PyPI.
        
        Args:
            query (str): Terme de recherche.
        
        Returns:
            list: Résultats de la recherche.
        """
        cmd = ["pip", "search", query]
        try:
            result = run_command(cmd)
            
            if result['returncode'] == 0:
                # Parser les résultats de recherche
                packages = []
                current_package = {}
                
                for line in result['stdout'].strip().split('\n'):
                    if not line.startswith(' '):
                        # Nouvelle entrée de package
                        if current_package:
                            packages.append(current_package)
                            current_package = {}
                        
                        parts = line.split(' - ', 1)
                        if len(parts) >= 2:
                            current_package = {
                                "name": parts[0].strip(),
                                "summary": parts[1].strip(),
                                "description": ""
                            }
                    else:
                        # Suite de la description
                        if current_package:
                            current_package["description"] += line.strip() + " "
                
                # Ajouter le dernier package
                if current_package:
                    packages.append(current_package)
                
                return packages
            else:
                # Recherche par index pas disponible dans les versions récentes de pip
                logger.warning("La recherche pip n'est plus disponible dans les versions récentes de pip.")
                logger.info("Utilisation de PyPI API pour la recherche (limité)...")
                
                # Alternative: utiliser l'API PyPI JSON
                import requests
                url = f"https://pypi.org/pypi/{query}/json"
                try:
                    response = requests.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        return [{
                            "name": data["info"]["name"],
                            "summary": data["info"]["summary"],
                            "description": data["info"]["description"]
                        }]
                    else:
                        return []
                except Exception as e:
                    logger.error(f"Erreur lors de la recherche sur PyPI: {str(e)}")
                    return []
                
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de packages: {str(e)}")
            return []
    
    def show_package_info(self, package_name, env_name=None):
        """
        Afficher des informations détaillées sur un package.
        
        Args:
            package_name (str): Nom du package.
            env_name (str, optional): Nom de l'environnement.
                Si None, utilise l'environnement actif.
        
        Returns:
            dict: Informations sur le package.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        # Déterminer l'environnement cible
        target_env = self._get_target_environment(env_name)
        
        pip_args = ["show", package_name]
        
        # Exécuter la commande pip
        result = self._run_pip_command(target_env, pip_args)
        
        if result['returncode'] == 0:
            # Parser les informations du package
            package_info = {}
            for line in result['stdout'].strip().split('\n'):
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
        else:
            logger.error(f"Échec de l'obtention des informations sur le package: {result['stderr']}")
            return None
    
    def export_requirements(self, env_name=None, output_file=None, include_versions=True, include_editable=True):
        """
        Exporter les packages installés dans un fichier requirements.txt.
        
        Args:
            env_name (str, optional): Nom de l'environnement.
                Si None, utilise l'environnement actif.
            output_file (str, optional): Chemin du fichier de sortie.
                Si None, affiche les requirements sur la sortie standard.
            include_versions (bool, optional): Si True, inclut les numéros de version.
            include_editable (bool, optional): Si True, inclut les packages installés en mode éditable.
        
        Returns:
            str: Contenu du fichier requirements.txt.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        # Déterminer l'environnement cible
        target_env = self._get_target_environment(env_name)
        
        pip_args = ["freeze"]
        
        # Exécuter la commande pip
        result = self._run_pip_command(target_env, pip_args)
        
        if result['returncode'] == 0:
            requirements = []
            
            for line in result['stdout'].strip().split('\n'):
                # Filtrer selon les options
                if not include_editable and line.startswith('-e '):
                    continue
                
                if not include_versions and '==' in line and not line.startswith('-e '):
                    line = line.split('==')[0]
                
                if line.strip():
                    requirements.append(line)
            
            requirements_content = '\n'.join(requirements)
            
            # Écrire dans un fichier si spécifié
            if output_file:
                try:
                    with open(output_file, 'w') as f:
                        f.write(requirements_content + '\n')
                    logger.info(f"Requirements exportés avec succès dans {output_file}")
                except Exception as e:
                    logger.error(f"Erreur lors de l'écriture du fichier requirements: {str(e)}")
            
            return requirements_content
        else:
            logger.error(f"Échec de l'export des requirements: {result['stderr']}")
            return None
    
    def import_requirements(self, requirements_file, env_name=None, upgrade=False):
        """
        Importer et installer des packages depuis un fichier requirements.txt.
        
        Args:
            requirements_file (str): Chemin vers le fichier requirements.txt.
            env_name (str, optional): Nom de l'environnement cible.
                Si None, utilise l'environnement actif.
            upgrade (bool, optional): Si True, met à jour les packages existants.
        
        Returns:
            dict: Résultat de l'opération d'installation.
        
        Raises:
            ValueError: Si le fichier requirements n'existe pas,
                ou si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        if not os.path.exists(requirements_file):
            raise ValueError(f"Le fichier requirements {requirements_file} n'existe pas.")
        
        return self.install_packages(
            packages=None,
            env_name=env_name,
            upgrade=upgrade,
            requirements=requirements_file
        )
    
    def check_package_dependencies(self, packages, env_name=None):
        """
        Vérifier les dépendances d'un package avant suppression.
        
        Args:
            packages (str or list): Packages à vérifier.
                Peut être une chaîne délimitée par des virgules ou une liste.
            env_name (str, optional): Nom de l'environnement cible.
                Si None, utilise l'environnement actif.
        
        Returns:
            dict: Informations sur les dépendances.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        # Déterminer l'environnement cible
        target_env = self._get_target_environment(env_name)
        
        # Convertir les packages en liste
        if isinstance(packages, str):
            packages = [pkg.strip() for pkg in packages.split(",") if pkg.strip()]
        
        # Vérifier chaque package
        dependent_packages = {}
        
        for package in packages:
            # Récupérer les informations sur le package
            package_info = self.show_package_info(package, target_env)
            
            if package_info and 'required_by' in package_info and package_info['required_by']:
                dependent_packages[package] = package_info['required_by']
        
        return {
            "status": "dependencies_found" if dependent_packages else "no_dependencies",
            "dependent_packages": dependent_packages
        }
    
    def check_outdated_packages(self, env_name=None):
        """
        Vérifier les packages obsolètes dans un environnement.
        
        Args:
            env_name (str, optional): Nom de l'environnement cible.
                Si None, utilise l'environnement actif.
        
        Returns:
            list: Liste des packages obsolètes avec leurs versions.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        return self.list_packages(env_name, outdated=True)
    
    def _get_target_environment(self, env_name=None):
        """
        Déterminer l'environnement cible à utiliser.
        
        Args:
            env_name (str, optional): Nom de l'environnement spécifié.
                Si None, utilise l'environnement actif.
        
        Returns:
            str: Nom de l'environnement cible.
        
        Raises:
            ValueError: Si aucun environnement n'est actif et qu'aucun n'est spécifié,
                ou si l'environnement spécifié n'existe pas.
        """
        if env_name:
            # Vérifier si l'environnement existe
            if not validate_environment_exists(env_name):
                raise ValueError(f"L'environnement {env_name} n'existe pas.")
            return env_name
        else:
            # Utiliser l'environnement actif
            active_env = self.env_manager.get_active_environment()
            if not active_env:
                raise ValueError("Aucun environnement actif et aucun environnement spécifié.")
            return active_env
    
    def _run_pip_command(self, env_name, pip_args):
        """
        Exécuter une commande pip dans l'environnement spécifié.
        
        Args:
            env_name (str): Nom de l'environnement.
            pip_args (list): Arguments pour pip.
        
        Returns:
            dict: Résultat de la commande (stdout, stderr, returncode).
        """
        return self.env_manager._run_pip_command(env_name, pip_args)
    
    def _update_package_list(self, env_name):
        """
        Mettre à jour la liste des packages dans la configuration.
        
        Args:
            env_name (str): Nom de l'environnement.
        
        Returns:
            list: Liste mise à jour des packages.
        """
        return self.env_manager.refresh_environment_packages(env_name)