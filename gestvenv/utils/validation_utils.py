"""
Utilitaires de validation pour GestVenv.

Ce module fournit des fonctions pour valider différentes entrées utilisateur
et vérifier des contraintes.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Union, Pattern

# Configuration du logger
logger = logging.getLogger(__name__)

def is_valid_name(name: str, min_length: int = 1, max_length: int = 50,
                 pattern: str = r'^[a-zA-Z0-9_-]+$') -> Tuple[bool, str]:
    """
    Valide un nom selon des critères donnés.
    
    Args:
        name: Nom à valider
        min_length: Longueur minimale
        max_length: Longueur maximale
        pattern: Expression régulière que le nom doit respecter
        
    Returns:
        Tuple[bool, str]: (validité, message d'erreur si invalide)
    """
    if not name:
        return False, "Le nom ne peut pas être vide"
    
    if len(name) < min_length:
        return False, f"Le nom est trop court (minimum {min_length} caractères)"
    
    if len(name) > max_length:
        return False, f"Le nom est trop long (maximum {max_length} caractères)"
    
    # Vérifier le pattern
    if not re.match(pattern, name):
        return False, f"Le nom doit respecter le format: {pattern}"
    
    return True, ""

def is_valid_path(path: Union[str, Path], must_exist: bool = False,
                 must_be_dir: bool = False, must_be_file: bool = False) -> Tuple[bool, Optional[Path], str]:
    """
    Valide un chemin selon des critères donnés.
    
    Args:
        path: Chemin à valider
        must_exist: Si True, le chemin doit exister
        must_be_dir: Si True, le chemin doit être un répertoire
        must_be_file: Si True, le chemin doit être un fichier
        
    Returns:
        Tuple[bool, Optional[Path], str]: (validité, chemin résolu si valide, message d'erreur sinon)
    """
    if not path:
        return False, None, "Le chemin ne peut pas être vide"
    
    try:
        # Convertir en Path si c'est une chaîne
        if isinstance(path, str):
            # Gérer le cas des chemins utilisateur (~)
            if path.startswith("~"):
                path_obj = Path(os.path.expanduser(path))
            else:
                path_obj = Path(path)
        else:
            path_obj = path
        
        # Convertir en chemin absolu
        if not path_obj.is_absolute():
            path_obj = Path.cwd() / path_obj
        
        # Résoudre le chemin
        resolved_path = path_obj.resolve()
        
        # Vérifier l'existence
        if must_exist and not resolved_path.exists():
            return False, None, f"Le chemin n'existe pas: {resolved_path}"
        
        # Vérifier si c'est un répertoire
        if must_be_dir and not resolved_path.is_dir():
            return False, None, f"Le chemin n'est pas un répertoire: {resolved_path}"
        
        # Vérifier si c'est un fichier
        if must_be_file and not resolved_path.is_file():
            return False, None, f"Le chemin n'est pas un fichier: {resolved_path}"
        
        return True, resolved_path, ""
        
    except Exception as e:
        return False, None, f"Erreur lors de la validation du chemin: {e}"

def is_safe_directory(directory: Union[str, Path], forbidden_paths: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Vérifie si un répertoire est sécuritaire à manipuler (pas un répertoire système critique).
    
    Args:
        directory: Répertoire à vérifier
        forbidden_paths: Liste optionnelle de chemins interdits supplémentaires
        
    Returns:
        Tuple[bool, str]: (sécurité, message d'avertissement si non sécuritaire)
    """
    # Convertir en Path et résoudre
    valid, resolved_path, error = is_valid_path(directory)
    if not valid:
        return False, error
    
    # Chemins système critiques par défaut
    system_paths = [
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/home",
        "/lib",
        "/lib64",
        "/media",
        "/mnt",
        "/opt",
        "/proc",
        "/root",
        "/run",
        "/sbin",
        "/srv",
        "/sys",
        "/tmp",
        "/usr",
        "/var",
        "C:\\",
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\Users"
    ]
    
    # Ajouter les chemins interdits supplémentaires
    if forbidden_paths:
        system_paths.extend(forbidden_paths)
    
    # Vérifier si le répertoire est un chemin système critique
    for sys_path in system_paths:
        # Convertir le chemin système en Path
        try:
            sys_path_obj = Path(sys_path).resolve()
            
            # Vérifier si le répertoire est identique ou contenu dans un chemin système
            if resolved_path == sys_path_obj or str(resolved_path).startswith(str(sys_path_obj) + os.sep):
                # Exception pour les répertoires liés à l'application dans les chemins utilisateur
                if "gestvenv" in str(resolved_path).lower() and (
                    sys_path in ["/home", "C:\\Users"] or str(resolved_path).startswith(str(Path.home()))):
                    continue
                
                return False, f"Opération refusée: '{resolved_path}' est un répertoire système critique"
        except Exception:
            # Ignorer les erreurs de résolution de chemin
            continue
    
    return True, ""

def matches_pattern(text: str, pattern: str) -> bool:
    """
    Vérifie si un texte correspond à un motif d'expression régulière.
    
    Args:
        text: Texte à vérifier
        pattern: Motif d'expression régulière
        
    Returns:
        bool: True si le texte correspond au motif
    """
    try:
        return bool(re.match(pattern, text))
    except re.error:
        logger.error(f"Expression régulière invalide: {pattern}")
        return False

def parse_version_string(version: str) -> Optional[Tuple[int, ...]]:
    """
    Analyse une chaîne de version en ses composants numériques.
    
    Args:
        version: Chaîne de version (ex: '3.9.2')
        
    Returns:
        Tuple d'entiers ou None si la version est invalide
    """
    # Pattern pour une version X.Y.Z...
    match = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?', version)
    
    if not match:
        return None
    
    # Extraire les composants en ignorant les valeurs None
    components = []
    for i in range(1, 5):  # max 4 composants
        if match.group(i) is not None:
            components.append(int(match.group(i)))
    
    return tuple(components) if components else None

def is_valid_python_version(version: str) -> Tuple[bool, str]:
    """
    Valide une spécification de version Python.
    
    Args:
        version: Version Python à valider (ex: 'python3.9', 'python', '3.9')
        
    Returns:
        Tuple[bool, str]: (validité, message d'erreur si invalide)
    """
    if not version:
        return True, ""  # Version vide est valide (utilise la version par défaut)
    
    # Si le format est simplement "python" ou "python3"
    if version in ["python", "python3"]:
        return True, ""
    
    # Si le format est "pythonX.Y" ou "python3.X"
    if matches_pattern(version, r'^python(?:3\.(\d+))?$'):
        return True, ""
    
    # Si le format est simplement "3.X"
    match = re.match(r'^3\.(\d+)$', version)
    if match:
        minor_version = int(match.group(1))
        if minor_version < 6:
            return False, "GestVenv nécessite Python 3.6 ou supérieur"
        return True, ""
    
    # Si sous Windows, vérifier le format "py -3.X"
    if os.name == 'nt':  # Windows
        match = re.match(r'^py -3\.(\d+)$', version)
        if match:
            minor_version = int(match.group(1))
            if minor_version < 6:
                return False, "GestVenv nécessite Python 3.6 ou supérieur"
            return True, ""
    
    return False, "Format de version Python invalide"

def is_valid_package_name(package: str) -> Tuple[bool, str]:
    """
    Valide un nom de package Python, avec éventuellement une version spécifiée.
    
    Args:
        package: Nom du package à valider (ex: 'flask', 'flask==2.0.1')
        
    Returns:
        Tuple[bool, str]: (validité, message d'erreur si invalide)
    """
    if not package:
        return False, "Le nom du package ne peut pas être vide"
    
    # Format de base pour les noms de packages
    # Ce regex permet les formats comme "flask", "flask==2.0.1", "flask>=2.0.1", "flask[extra]"
    pattern = r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])(\[[a-zA-Z0-9._-]+\])?((==|>=|<=|>|<|!=)[0-9]+(\.[0-9]+)*)?$'
    
    if not matches_pattern(package, pattern):
        # Vérifier si c'est un chemin local ou une URL Git
        if package.startswith(("git+", "http://", "https://", "./", "/", "~/")):
            return True, ""
        return False, f"Format de package invalide: {package}"
    
    return True, ""

def validate_packages_list(packages_str: str) -> Tuple[bool, List[str], str]:
    """
    Valide une liste de packages séparés par des virgules.
    
    Args:
        packages_str: Chaîne de packages séparés par des virgules
        
    Returns:
        Tuple[bool, List[str], str]: (validité, liste de packages, message d'erreur si invalide)
    """
    if not packages_str:
        return False, [], "La liste de packages ne peut pas être vide"
    
    # Séparer la chaîne en liste de packages
    package_list = [pkg.strip() for pkg in packages_str.split(",")]
    
    # Valider chaque package individuellement
    invalid_packages = []
    for pkg in package_list:
        valid, message = is_valid_package_name(pkg)
        if not valid:
            invalid_packages.append((pkg, message))
    
    if invalid_packages:
        error_message = "Packages invalides: " + ", ".join([f"{pkg} ({msg})" for pkg, msg in invalid_packages])
        return False, [], error_message
    
    return True, package_list, ""

def parse_key_value_string(kv_string: str, delimiter: str = ",", separator: str = ":") -> Tuple[bool, Dict[str, str], str]:
    """
    Analyse une chaîne au format "clé1:valeur1,clé2:valeur2".
    
    Args:
        kv_string: Chaîne de paires clé-valeur
        delimiter: Délimiteur entre les paires
        separator: Séparateur entre les clés et les valeurs
        
    Returns:
        Tuple[bool, Dict[str, str], str]: (validité, dictionnaire, message d'erreur si invalide)
    """
    if not kv_string:
        return True, {}, ""  # Chaîne vide est valide (pas de paires)
    
    result = {}
    
    try:
        # Séparer les paires
        pairs = kv_string.split(delimiter)
        
        for pair in pairs:
            if separator not in pair:
                return False, {}, f"Format invalide (manque '{separator}') : {pair}"
            
            key, value = pair.split(separator, 1)
            key = key.strip()
            value = value.strip()
            
            if not key:
                return False, {}, "Les clés ne peuvent pas être vides"
            
            result[key] = value
        
        return True, result, ""
    except Exception as e:
        return False, {}, f"Erreur lors de l'analyse: {e}"