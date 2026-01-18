"""
Module de validation pour GestVenv.

Ce module fournit des fonctions pour valider différentes entrées utilisateur
et configurations du gestionnaire d'environnements virtuels Python.
"""

import os
import re
import json
import platform
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple

# Configuration du logger
logger = logging.getLogger(__name__)

def validate_env_name(name: str) -> Tuple[bool, str]:
    """
    Valide un nom d'environnement virtuel.
    
    Args:
        name (str): Nom d'environnement à valider
        
    Returns:
        Tuple[bool, str]: Tuple contenant (validité, message d'erreur si invalide)
    """
    if not name:
        return False, "Le nom d'environnement ne peut pas être vide"
    
    if len(name) > 50:
        return False, "Le nom d'environnement est trop long (maximum 50 caractères)"
    
    # Vérifie que le nom contient uniquement des caractères alphanumériques, tirets et soulignés
    pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    if not pattern.match(name):
        return False, "Le nom d'environnement ne peut contenir que des lettres, chiffres, tirets et soulignés"
    
    # Noms réservés à éviter
    reserved_names = ["system", "admin", "config", "test", "venv", "env", "environment"]
    if name.lower() in reserved_names:
        return False, f"'{name}' est un nom réservé. Veuillez choisir un autre nom"
    
    return True, ""

def validate_python_version(version: str) -> Tuple[bool, str]:
    """
    Valide une spécification de version Python.
    
    Args:
        version (str): Version Python à valider (ex: "python3.9", "python", "3.10")
        
    Returns:
        Tuple[bool, str]: Tuple contenant (validité, message d'erreur si invalide)
    """
    if not version:
        return True, ""  # Version vide est valide (utilise la version par défaut)
    
    # Si le format est simplement "python" ou "python3"
    if version in ["python", "python3"]:
        return True, ""
    
    # Si le format est "pythonX.Y" ou "python3.X"
    match = re.match(r'^python(?:3\.(\d+))?$', version)
    if match:
        return True, ""
    
    # Si le format est simplement "3.X"
    match = re.match(r'^3\.(\d+)$', version)
    if match:
        minor_version = int(match.group(1))
        if minor_version < 6:
            return False, "GestVenv nécessite Python 3.6 ou supérieur"
        return True, ""
    
    # Si sous Windows, vérifier le format "py -3.X"
    if platform.system().lower() == "windows":
        match = re.match(r'^py -3\.(\d+)$', version)
        if match:
            minor_version = int(match.group(1))
            if minor_version < 6:
                return False, "GestVenv nécessite Python 3.6 ou supérieur"
            return True, ""
    
    return False, "Format de version Python invalide"

def validate_package_name(package: str) -> Tuple[bool, str]:
    """
    Valide un nom de package Python, avec éventuellement une version spécifiée.
    
    Args:
        package (str): Nom du package à valider (ex: "flask", "flask==2.0.1")
        
    Returns:
        Tuple[bool, str]: Tuple contenant (validité, message d'erreur si invalide)
    """
    if not package:
        return False, "Le nom du package ne peut pas être vide"
    
    # Format de base pour les noms de packages
    # Ce regex permet les formats comme "flask", "flask==2.0.1", "flask>=2.0.1", "flask[extra]"
    pattern = re.compile(r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])(\[[a-zA-Z0-9._-]+\])?((==|>=|<=|>|<|!=)[0-9]+(\.[0-9]+)*)?$')
    
    if not pattern.match(package):
        # Vérifier si c'est un chemin local ou une URL Git
        if package.startswith(("git+", "http://", "https://", "./", "/", "~/")):
            return True, ""
        return False, f"Format de package invalide: {package}"
    
    return True, ""

def validate_packages_list(packages: str) -> Tuple[bool, List[str], str]:
    """
    Valide une liste de packages séparés par des virgules.
    
    Args:
        packages (str): Chaîne de packages séparés par des virgules
        
    Returns:
        Tuple[bool, List[str], str]: Tuple contenant (validité, liste de packages, message d'erreur si invalide)
    """
    if not packages:
        return False, [], "La liste de packages ne peut pas être vide"
    
    # Séparer la chaîne en liste de packages
    package_list = [pkg.strip() for pkg in packages.split(",")]
    
    # Valider chaque package individuellement
    invalid_packages = []
    for pkg in package_list:
        valid, message = validate_package_name(pkg)
        if not valid:
            invalid_packages.append((pkg, message))
    
    if invalid_packages:
        error_message = "Packages invalides: " + ", ".join([f"{pkg} ({msg})" for pkg, msg in invalid_packages])
        return False, [], error_message
    
    return True, package_list, ""

def validate_path_exists(path_str: str, must_exist: bool = True) -> Tuple[bool, Optional[Path], str]:
    """
    Valide qu'un chemin existe ou peut être créé.
    
    Args:
        path_str (str): Chaîne de caractères représentant un chemin
        must_exist (bool): Si True, le chemin doit exister
        
    Returns:
        Tuple[bool, Optional[Path], str]: Tuple contenant (validité, chemin résolu si valide, message d'erreur si invalide)
    """
    if not path_str:
        return False, None, "Le chemin ne peut pas être vide"
    
    try:
        # Résoudre le chemin (~ pour le répertoire utilisateur, chemins relatifs, etc.)
        if path_str.startswith("~"):
            path = Path(os.path.expanduser(path_str))
        else:
            path = Path(path_str)
        
        # Convertir en chemin absolu
        if not path.is_absolute():
            path = Path.cwd() / path
        
        # Vérifier si le chemin existe
        if must_exist and not path.exists():
            return False, None, f"Le chemin n'existe pas: {path}"
        
        return True, path, ""
    except Exception as e:
        return False, None, f"Erreur lors de la validation du chemin: {e}"

def validate_requirements_file(file_path: str) -> Tuple[bool, Optional[Path], str]:
    """
    Valide un fichier requirements.txt.
    
    Args:
        file_path (str): Chemin vers le fichier requirements.txt
        
    Returns:
        Tuple[bool, Optional[Path], str]: Tuple contenant (validité, chemin résolu si valide, message d'erreur si invalide)
    """
    # Vérifier que le chemin existe
    valid, path, error = validate_path_exists(file_path)
    if not valid:
        return False, None, error
    
    # Vérifier que c'est un fichier
    if not path.is_file():
        return False, None, f"Le chemin ne pointe pas vers un fichier: {path}"
    
    # Vérifier l'extension du fichier
    if path.suffix.lower() != ".txt":
        return False, None, f"Le fichier n'a pas l'extension .txt: {path}"
    
    # Vérifier que le fichier est lisible
    try:
        if path is None:
            return False, None, "Invalid path: path is None"
        with open(str(path), "r") as f:
            lines = f.readlines()
        
        # Vérifier le format de base (chaque ligne non vide contient un package valide)
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                valid, _ = validate_package_name(line.split("#")[0].strip())  # Ignorer les commentaires
                if not valid:
                    return False, None, f"Format de package invalide dans requirements.txt: {line}"
        
        return True, path, ""
    except Exception as e:
        return False, None, f"Erreur lors de la lecture du fichier requirements: {e}"

def validate_config_json(file_path: str) -> Tuple[bool, Optional[Dict], str]:
    """
    Valide un fichier de configuration JSON exporté.
    
    Args:
        file_path (str): Chemin vers le fichier JSON
        
    Returns:
        Tuple[bool, Optional[Dict], str]: Tuple contenant (validité, dictionnaire de configuration si valide, message d'erreur si invalide)
    """
    # Vérifier que le chemin existe
    valid, path, error = validate_path_exists(file_path)
    if not valid:
        return False, None, error
    
    # Vérifier que c'est un fichier
    if not path.is_file():
        return False, None, f"Le chemin ne pointe pas vers un fichier: {path}"
    
    # Vérifier l'extension du fichier
    if path.suffix.lower() != ".json":
        return False, None, f"Le fichier n'a pas l'extension .json: {path}"
    
    # Vérifier que le fichier est lisible et contient du JSON valide
    try:
        with open(path, "r") as f:
            config = json.load(f)
        
        # Vérifier la structure minimale requise
        required_keys = ["name", "python_version", "packages"]
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            return False, None, f"Clés manquantes dans le fichier de configuration: {', '.join(missing_keys)}"
        
        # Valider le nom d'environnement
        valid, error = validate_env_name(config["name"])
        if not valid:
            return False, None, f"Configuration invalide: {error}"
        
        # Valider la version Python
        valid, error = validate_python_version(config["python_version"])
        if not valid:
            return False, None, f"Configuration invalide: {error}"
        
        # Valider les packages
        for pkg in config["packages"]:
            valid, error = validate_package_name(pkg)
            if not valid:
                return False, None, f"Package invalide dans la configuration: {pkg} - {error}"
        
        return True, config, ""
    except json.JSONDecodeError as e:
        return False, None, f"Erreur de décodage JSON: {e}"
    except Exception as e:
        return False, None, f"Erreur lors de la validation du fichier de configuration: {e}"

def validate_command_args(args: Dict[str, Any], required_args: List[str], optional_args: List[str]) -> Tuple[bool, str]:
    """
    Valide les arguments d'une commande.
    
    Args:
        args (Dict[str, Any]): Dictionnaire des arguments
        required_args (List[str]): Liste des arguments requis
        optional_args (List[str]): Liste des arguments optionnels
        
    Returns:
        Tuple[bool, str]: Tuple contenant (validité, message d'erreur si invalide)
    """
    # Vérifier les arguments requis
    missing_args = [arg for arg in required_args if arg not in args or args[arg] is None]
    if missing_args:
        return False, f"Arguments requis manquants: {', '.join(missing_args)}"
    
    # Vérifier les arguments non reconnus
    all_valid_args = required_args + optional_args
    unknown_args = [arg for arg in args if arg not in all_valid_args]
    if unknown_args:
        return False, f"Arguments non reconnus: {', '.join(unknown_args)}"
    
    return True, ""

def validate_environment_exists(env_name: str) -> Tuple[bool, str]:
    """
    Valide qu'un environnement virtuel existe.
    
    Args:
        env_name (str): Nom de l'environnement à vérifier
        
    Returns:
        Tuple[bool, str]: Tuple contenant (validité, message d'erreur si invalide)
    """
    # Import local pour éviter l'import circulaire
    from .path_handler import get_environment_path
    
    # Valider d'abord le format du nom
    valid, error = validate_env_name(env_name)
    if not valid:
        return False, error
    
    # Vérifier si l'environnement existe
    env_path = get_environment_path(env_name)
    if not env_path or not env_path.exists():
        return False, f"L'environnement '{env_name}' n'existe pas"
    
    return True, ""

def validate_output_format(format_str: str) -> Tuple[bool, str]:
    """
    Valide un format de sortie spécifié.
    
    Args:
        format_str (str): Format de sortie à valider
        
    Returns:
        Tuple[bool, str]: Tuple contenant (validité, message d'erreur si invalide)
    """
    valid_formats = ["json", "text", "requirements"]
    
    if not format_str:
        return False, "Le format de sortie ne peut pas être vide"
    
    if format_str.lower() not in valid_formats:
        return False, f"Format de sortie invalide. Formats valides: {', '.join(valid_formats)}"
    
    return True, ""

def validate_metadata(metadata_str: str) -> Tuple[bool, Dict[str, str], str]:
    """
    Valide une chaîne de métadonnées au format "clé1:valeur1,clé2:valeur2".
    
    Args:
        metadata_str (str): Chaîne de métadonnées à valider
        
    Returns:
        Tuple[bool, Dict[str, str], str]: Tuple contenant (validité, dictionnaire de métadonnées, message d'erreur si invalide)
    """
    if not metadata_str:
        return True, {}, ""  # Chaîne vide est valide (pas de métadonnées)
    
    metadata = {}
    
    try:
        # Séparer les paires clé:valeur
        pairs = metadata_str.split(",")
        
        for pair in pairs:
            if ":" not in pair:
                return False, {}, f"Format de métadonnées invalide (manque ':') : {pair}"
            
            key, value = pair.split(":", 1)
            key = key.strip()
            value = value.strip()
            
            if not key:
                return False, {}, "Les clés de métadonnées ne peuvent pas être vides"
            
            metadata[key] = value
        
        return True, metadata, ""
    except Exception as e:
        return False, {}, f"Erreur lors de la validation des métadonnées: {e}"

def validate_boolean_flag(flag_value: Any) -> bool:
    """
    Valide et convertit une valeur en booléen.
    
    Args:
        flag_value (Any): Valeur à valider
        
    Returns:
        bool: Valeur booléenne correspondante
    """
    if isinstance(flag_value, bool):
        return flag_value
    
    if isinstance(flag_value, str):
        # Conversion de chaînes couramment utilisées pour représenter des booléens
        true_values = ["true", "yes", "y", "1", "on"]
        false_values = ["false", "no", "n", "0", "off"]
        
        if flag_value.lower() in true_values:
            return True
        if flag_value.lower() in false_values:
            return False
    
    # Convertir en booléen Python standard (0 ou chaîne vide -> False, tout le reste -> True)
    return bool(flag_value)

def is_safe_to_delete(env_name: str) -> Tuple[bool, str]:
    """
    Vérifie s'il est sécuritaire de supprimer un environnement.
    
    Args:
        env_name (str): Nom de l'environnement à vérifier
        
    Returns:
        Tuple[bool, str]: Tuple contenant (sécurité, message d'avertissement si non sécuritaire)
    """
    from .path_handler import get_environment_path
    
    env_path = get_environment_path(env_name)
    if not env_path:
        return False, f"L'environnement '{env_name}' n'existe pas"
    
    # Vérifier si le chemin est sécuritaire (ne contient pas de dossiers système)
    system_directories = [
        os.path.expanduser("~"),
        os.path.expanduser("~/Documents"),
        "/",
        "/usr",
        "/bin",
        "/etc",
        "/var",
        "/home",
        "/tmp",
        "C:\\",
        "C:\\Windows",
        "C:\\Program Files"
    ]
    
    for sys_dir in system_directories:
        if str(env_path) == sys_dir or str(env_path).startswith(f"{sys_dir}/") or str(env_path).startswith(f"{sys_dir}\\"):
            return False, f"Suppression refusée: '{env_path}' semble être un dossier système ou contenu dans un dossier système"
    
    # Vérifier si le chemin ressemble à un environnement virtuel
    venv_indicators = ["bin/python", "bin/activate", "Scripts/python.exe", "Scripts/activate.bat", "pyvenv.cfg"]
    
    any_indicator_found = False
    for indicator in venv_indicators:
        indicator_path = env_path / indicator.replace("/", os.sep)
        if indicator_path.exists():
            any_indicator_found = True
            break
    
    if not any_indicator_found:
        return False, f"Suppression refusée: '{env_path}' ne semble pas être un environnement virtuel"
    
    return True, ""