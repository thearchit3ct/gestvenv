"""
Module pour l'exécution des commandes système dans GestVenv.

Ce module fournit des fonctions pour exécuter des commandes système nécessaires
à la gestion des environnements virtuels Python, notamment la création d'environnements,
l'installation de packages, et l'exécution de commandes dans un environnement spécifique.
"""

import os
import sys
import subprocess
import platform
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union

# Import local pour accéder aux fonctions de gestion des chemins
from .path_handler import (
    get_environment_path,
    get_python_executable,
    get_pip_executable,
    get_activation_script_path,
    is_valid_env_name
)

# Configuration du logger
logger = logging.getLogger(__name__)

def run_command(cmd: List[str], cwd: Optional[Path] = None, 
                capture_output: bool = False, shell: bool = False) -> Tuple[int, str, str]:
    """
    Exécute une commande système et retourne le code de sortie ainsi que les sorties standard et d'erreur.
    
    Args:
        cmd (List[str]): Liste des éléments de la commande à exécuter
        cwd (Optional[Path]): Répertoire de travail pour l'exécution de la commande
        capture_output (bool): Si True, capture la sortie de la commande
        shell (bool): Si True, exécute la commande dans un shell
        
    Returns:
        Tuple[int, str, str]: Tuple contenant (code de retour, sortie standard, sortie d'erreur)
    """
    try:
        logger.debug(f"Exécution de la commande: {' '.join(cmd)}")
        
        # Configuration de l'environnement pour subprocess
        env = os.environ.copy()
        
        process = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            shell=shell,  # nosec B602 - shell est False par défaut, True uniquement pour cas contrôlés
            env=env
        )
        
        stdout = process.stdout if capture_output else ""
        stderr = process.stderr if capture_output else ""
        
        if process.returncode != 0:
            logger.warning(f"Commande terminée avec code de retour non nul: {process.returncode}")
            if stderr:
                logger.warning(f"Erreur: {stderr}")
        else:
            logger.debug("Commande exécutée avec succès")
        
        return process.returncode, stdout, stderr
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la commande: {e}")
        return 1, "", str(e)

def create_virtual_environment(env_name: str, python_version: Optional[str] = None) -> bool:
    """
    Crée un nouvel environnement virtuel Python.
    
    Args:
        env_name (str): Nom de l'environnement virtuel à créer
        python_version (Optional[str]): Version de Python à utiliser
        
    Returns:
        bool: True si la création a réussi, False sinon
    """
    if not is_valid_env_name(env_name):
        logger.error(f"Nom d'environnement invalide: {env_name}")
        return False
    
    # Déterminer le chemin pour le nouvel environnement
    env_path = get_environment_path(env_name)
    
    # Si l'environnement existe déjà, retourner une erreur
    if env_path and env_path.exists():
        logger.error(f"L'environnement '{env_name}' existe déjà à {env_path}")
        return False
    
    # Déterminer quelle version de Python utiliser
    python_cmd = python_version if python_version else "python"
    
    # Vérifier si la commande Python est disponible
    ret_code, _, _ = run_command([python_cmd, "--version"], capture_output=True)
    if ret_code != 0:
        logger.error(f"La commande Python '{python_cmd}' n'est pas disponible")
        return False
    
    # Créer l'environnement virtuel en utilisant le module venv
    cmd = [python_cmd, "-m", "venv", str(env_path)]
    ret_code, stdout, stderr = run_command(cmd, capture_output=True)
    
    # Si la création a échoué avec venv, essayer avec virtualenv
    if ret_code != 0:
        logger.warning("Échec de la création avec venv. Tentative avec virtualenv...")
        
        # Vérifier si virtualenv est installé
        ret_code, _, _ = run_command([python_cmd, "-m", "pip", "show", "virtualenv"], capture_output=True)
        
        if ret_code != 0:
            # Essayer d'installer virtualenv
            logger.info("Installation de virtualenv...")
            ret_code, _, _ = run_command([python_cmd, "-m", "pip", "install", "virtualenv"], capture_output=True)
            
            if ret_code != 0:
                logger.error("Impossible d'installer virtualenv")
                return False
        
        # Créer l'environnement avec virtualenv
        cmd = [python_cmd, "-m", "virtualenv", str(env_path)]
        ret_code, stdout, stderr = run_command(cmd, capture_output=True)
        
        if ret_code != 0:
            logger.error(f"Échec de la création de l'environnement virtuel: {stderr}")
            return False
    
    logger.info(f"Environnement virtuel '{env_name}' créé avec succès à {env_path}")
    return True

def install_packages(env_name: str, packages: List[str], upgrade: bool = False) -> bool:
    """
    Installe des packages dans un environnement virtuel spécifique.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        packages (List[str]): Liste des packages à installer
        upgrade (bool): Si True, met à jour les packages existants
        
    Returns:
        bool: True si l'installation a réussi, False sinon
    """
    # Obtenir le chemin vers l'exécutable pip de l'environnement
    pip_path = get_pip_executable(env_name)
    
    if not pip_path:
        logger.error(f"Impossible de trouver pip pour l'environnement '{env_name}'")
        return False
    
    # Construire la commande d'installation
    cmd = [str(pip_path), "install"]
    
    if upgrade:
        cmd.append("--upgrade")
    
    # Ajouter les packages à la commande
    cmd.extend(packages)
    
    # Exécuter la commande d'installation
    ret_code, stdout, stderr = run_command(cmd, capture_output=True)
    
    if ret_code != 0:
        logger.error(f"Échec de l'installation des packages: {stderr}")
        return False
    
    logger.info(f"Packages installés avec succès dans l'environnement '{env_name}'")
    return True

def uninstall_packages(env_name: str, packages: List[str]) -> bool:
    """
    Désinstalle des packages d'un environnement virtuel spécifique.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        packages (List[str]): Liste des packages à désinstaller
        
    Returns:
        bool: True si la désinstallation a réussi, False sinon
    """
    # Obtenir le chemin vers l'exécutable pip de l'environnement
    pip_path = get_pip_executable(env_name)
    
    if not pip_path:
        logger.error(f"Impossible de trouver pip pour l'environnement '{env_name}'")
        return False
    
    # Construire la commande de désinstallation
    cmd = [str(pip_path), "uninstall", "-y"]
    
    # Ajouter les packages à la commande
    cmd.extend(packages)
    
    # Exécuter la commande de désinstallation
    ret_code, stdout, stderr = run_command(cmd, capture_output=True)
    
    if ret_code != 0:
        logger.error(f"Échec de la désinstallation des packages: {stderr}")
        return False
    
    logger.info(f"Packages désinstallés avec succès de l'environnement '{env_name}'")
    return True

def list_installed_packages(env_name: str) -> Optional[List[Dict[str, str]]]:
    """
    Liste les packages installés dans un environnement virtuel spécifique.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        
    Returns:
        Optional[List[Dict[str, str]]]: Liste des packages installés avec leur version,
                                        ou None en cas d'erreur
    """
    # Obtenir le chemin vers l'exécutable pip de l'environnement
    pip_path = get_pip_executable(env_name)
    
    if not pip_path:
        logger.error(f"Impossible de trouver pip pour l'environnement '{env_name}'")
        return None
    
    # Construire la commande pour lister les packages
    cmd = [str(pip_path), "list", "--format=json"]
    
    # Exécuter la commande
    ret_code, stdout, stderr = run_command(cmd, capture_output=True)
    
    if ret_code != 0:
        logger.error(f"Échec de la récupération des packages installés: {stderr}")
        return None
    
    # Analyser la sortie JSON
    try:
        import json
        packages = json.loads(stdout)
        logger.debug(f"Packages récupérés avec succès: {len(packages)} packages trouvés")
        return packages
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de la liste des packages: {e}")
        return None

def get_activation_command(env_name: str) -> Optional[str]:
    """
    Obtient la commande d'activation d'un environnement virtuel.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        
    Returns:
        Optional[str]: Commande d'activation, ou None si non disponible
    """
    activation_script = get_activation_script_path(env_name)
    
    if not activation_script:
        return None
    
    system = platform.system().lower()
    
    if system == "windows":
        return f'"{activation_script}"'
    else:  # macOS et Linux
        return f'source "{activation_script}"'

def delete_environment(env_name: str) -> bool:
    """
    Supprime un environnement virtuel.
    
    Args:
        env_name (str): Nom de l'environnement virtuel à supprimer
        
    Returns:
        bool: True si la suppression a réussi, False sinon
    """
    env_path = get_environment_path(env_name)
    
    if not env_path or not env_path.exists():
        logger.error(f"L'environnement '{env_name}' n'existe pas ou est introuvable")
        return False
    
    try:
        # Suppression récursive du répertoire de l'environnement
        shutil.rmtree(env_path)
        logger.info(f"Environnement '{env_name}' supprimé avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'environnement '{env_name}': {e}")
        return False

def run_in_environment(env_name: str, cmd: List[str]) -> Tuple[int, str, str]:
    """
    Exécute une commande dans un environnement virtuel spécifique.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        cmd (List[str]): Commande à exécuter
        
    Returns:
        Tuple[int, str, str]: Tuple contenant (code de retour, sortie standard, sortie d'erreur)
    """
    python_exe = get_python_executable(env_name)
    
    if not python_exe:
        logger.error(f"Impossible de trouver l'exécutable Python pour l'environnement '{env_name}'")
        return 1, "", f"Environnement '{env_name}' introuvable ou corrompu"
    
    # Préparer la commande avec l'exécutable Python de l'environnement
    env_cmd = [str(python_exe)] + cmd
    
    # Exécuter la commande
    return run_command(env_cmd, capture_output=True)

def check_python_version(python_cmd: str) -> Optional[str]:
    """
    Vérifie la version de Python pour une commande donnée.
    
    Args:
        python_cmd (str): Commande Python à vérifier (ex: 'python', 'python3.9')
        
    Returns:
        Optional[str]: Version de Python, ou None si non disponible
    """
    try:
        ret_code, stdout, stderr = run_command([python_cmd, "--version"], capture_output=True)
        
        if ret_code != 0:
            logger.warning(f"La commande '{python_cmd}' n'est pas disponible: {stderr}")
            return None
        
        # Extraire la version du format "Python X.Y.Z"
        version = stdout.strip().split(" ")[1] if stdout else None
        logger.debug(f"Version de Python pour '{python_cmd}': {version}")
        return version
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de la version Python: {e}")
        return None

def get_available_python_versions() -> List[Dict[str, str]]:
    """
    Récupère les versions Python disponibles sur le système.
    
    Returns:
        List[Dict[str, str]]: Liste des versions Python disponibles avec commande et version
    """
    python_commands = ["python", "python3"]
    
    # Ajouter des versions spécifiques à vérifier
    for minor in range(9, 14):  # Python 3.9 à 3.13
        python_commands.append(f"python3.{minor}")
    
    # Sous Windows, vérifier aussi 'py' avec différents sélecteurs
    if platform.system().lower() == "windows":
        python_commands.extend(["py", "py -3"])
        for minor in range(7, 13):
            python_commands.append(f"py -3.{minor}")
    
    available_versions = []
    
    for cmd in python_commands:
        version = check_python_version(cmd)
        if version:
            available_versions.append({
                "command": cmd,
                "version": version
            })
    
    return available_versions

def export_requirements(env_name: str, output_path: Path) -> bool:
    """
    Exporte les dépendances d'un environnement dans un fichier requirements.txt.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        output_path (Path): Chemin de sortie pour le fichier requirements.txt
        
    Returns:
        bool: True si l'export a réussi, False sinon
    """
    pip_path = get_pip_executable(env_name)
    
    if not pip_path:
        logger.error(f"Impossible de trouver pip pour l'environnement '{env_name}'")
        return False
    
    # Construire la commande pour générer requirements.txt
    cmd = [str(pip_path), "freeze"]
    
    # Exécuter la commande
    ret_code, stdout, stderr = run_command(cmd, capture_output=True)
    
    if ret_code != 0:
        logger.error(f"Échec de la génération du fichier requirements: {stderr}")
        return False
    
    try:
        # Écrire le contenu dans le fichier requirements.txt
        with open(output_path, "w") as f:
            f.write(stdout)
        
        logger.info(f"Fichier requirements exporté avec succès: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture du fichier requirements: {e}")
        return False

def install_from_requirements(env_name: str, requirements_path: Path) -> bool:
    """
    Installe les packages à partir d'un fichier requirements.txt.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        requirements_path (Path): Chemin vers le fichier requirements.txt
        
    Returns:
        bool: True si l'installation a réussi, False sinon
    """
    pip_path = get_pip_executable(env_name)
    
    if not pip_path:
        logger.error(f"Impossible de trouver pip pour l'environnement '{env_name}'")
        return False
    
    if not requirements_path.exists():
        logger.error(f"Le fichier requirements {requirements_path} n'existe pas")
        return False
    
    # Construire la commande d'installation depuis requirements
    cmd = [str(pip_path), "install", "-r", str(requirements_path)]
    
    # Exécuter la commande
    ret_code, stdout, stderr = run_command(cmd, capture_output=True)
    
    if ret_code != 0:
        logger.error(f"Échec de l'installation depuis requirements: {stderr}")
        return False
    
    logger.info(f"Packages installés avec succès depuis {requirements_path}")
    return True

def check_environment_health(env_name: str) -> Dict[str, bool]:
    """
    Vérifie l'état de santé d'un environnement virtuel.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        
    Returns:
        Dict[str, bool]: Dictionnaire des vérifications avec leur résultat
    """
    results = {
        "exists": False,
        "python_available": False,
        "pip_available": False,
        "activation_script_exists": False
    }
    
    # Vérifier si l'environnement existe
    env_path = get_environment_path(env_name)
    if env_path and env_path.exists():
        results["exists"] = True
    else:
        logger.warning(f"L'environnement '{env_name}' n'existe pas")
        return results
    
    # Vérifier si Python est disponible
    python_exe = get_python_executable(env_name)
    if python_exe and python_exe.exists():
        results["python_available"] = True
    else:
        logger.warning(f"Python introuvable pour l'environnement '{env_name}'")
    
    # Vérifier si pip est disponible
    pip_exe = get_pip_executable(env_name)
    if pip_exe and pip_exe.exists():
        results["pip_available"] = True
    else:
        logger.warning(f"Pip introuvable pour l'environnement '{env_name}'")
    
    # Vérifier si le script d'activation existe
    activation_script = get_activation_script_path(env_name)
    if activation_script and activation_script.exists():
        results["activation_script_exists"] = True
    else:
        logger.warning(f"Script d'activation introuvable pour l'environnement '{env_name}'")
    
    return results