"""
Utilitaires de gestion des chemins pour GestVenv.

Ce module fournit des fonctions pour manipuler les chemins de fichiers
de manière indépendante du système d'exploitation.
"""

import os
import sys
import platform
import logging
from pathlib import Path
from typing import Optional, Union, List, Tuple

# Configuration du logger
logger = logging.getLogger(__name__)

def get_os_name() -> str:
    """
    Retourne le nom du système d'exploitation en minuscules.
    
    Returns:
        str: Nom du système ('windows', 'linux', 'darwin', etc.)
    """
    return platform.system().lower()

def expand_user_path(path_str: str) -> Path:
    """
    Expande un chemin utilisateur (commençant par ~).
    
    Args:
        path_str: Chaîne représentant un chemin potentiellement relatif à l'utilisateur
        
    Returns:
        Path: Chemin expandé
    """
    return Path(os.path.expanduser(path_str))

def resolve_path(path_str: Union[str, Path]) -> Path:
    """
    Résout un chemin en absolu, en gérant les chemins utilisateur et relatifs.
    
    Args:
        path_str: Chaîne ou objet Path représentant un chemin
        
    Returns:
        Path: Chemin absolu résolu
    """
    # Convertir en Path si c'est une chaîne
    if isinstance(path_str, str):
        path = Path(path_str)
    else:
        path = path_str
    
    # Résoudre les chemins relatifs aux utilisateurs (~)
    if isinstance(path_str, str) and path_str.startswith("~"):
        path = expand_user_path(path_str)
    
    # Rendre absolu si relatif
    if not path.is_absolute():
        path = Path.cwd() / path
    
    return path.resolve()

def ensure_dir_exists(path: Union[str, Path]) -> Path:
    """
    S'assure qu'un répertoire existe, le crée si nécessaire.
    
    Args:
        path: Chemin du répertoire
        
    Returns:
        Path: Chemin du répertoire
        
    Raises:
        OSError: Si le répertoire ne peut pas être créé
    """
    path = resolve_path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_default_data_dir() -> Path:
    """
    Retourne le répertoire par défaut pour stocker les données de l'application
    selon les conventions du système d'exploitation.
    
    Returns:
        Path: Chemin du répertoire de données par défaut
    """
    os_name = get_os_name()
    
    if os_name == "windows":
        # Windows: %APPDATA%\GestVenv
        base_dir = Path(os.environ.get("APPDATA", "")) / "GestVenv"
    elif os_name == "darwin":
        # macOS: ~/Library/Application Support/GestVenv
        base_dir = Path.home() / "Library" / "Application Support" / "GestVenv"
    else:
        # Linux et autres Unix: ~/.config/gestvenv
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            base_dir = Path(xdg_config_home) / "gestvenv"
        else:
            base_dir = Path.home() / ".config" / "gestvenv"
    
    # Créer le répertoire s'il n'existe pas
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Impossible de créer le répertoire de données: {e}")
        # Fallback au répertoire courant
        base_dir = Path.cwd() / ".gestvenv"
        base_dir.mkdir(exist_ok=True)
    
    return base_dir

def get_normalized_path(path: Union[str, Path]) -> str:
    """
    Normalise un chemin et le retourne sous forme de chaîne,
    indépendamment du système d'exploitation.
    
    Args:
        path: Chemin à normaliser
        
    Returns:
        str: Chemin normalisé sous forme de chaîne
    """
    return str(resolve_path(path)).replace("\\", "/")

def get_relative_path(path: Union[str, Path], base: Union[str, Path]) -> Path:
    """
    Calcule le chemin relatif d'un chemin par rapport à une base.
    
    Args:
        path: Chemin à rendre relatif
        base: Chemin de base
        
    Returns:
        Path: Chemin relatif
    """
    path = resolve_path(path)
    base = resolve_path(base)
    
    try:
        return path.relative_to(base)
    except ValueError:
        # Si les chemins n'ont pas de base commune, retourner le chemin absolu
        return path

def is_subpath(parent: Union[str, Path], child: Union[str, Path]) -> bool:
    """
    Vérifie si un chemin est un sous-chemin d'un autre.
    
    Args:
        parent: Chemin parent potentiel
        child: Chemin enfant potentiel
        
    Returns:
        bool: True si child est un sous-chemin de parent
    """
    parent_path = resolve_path(parent)
    child_path = resolve_path(child)
    
    # Convertir en chaîne avec séparateurs normalisés pour la comparaison
    parent_str = str(parent_path).replace("\\", "/")
    child_str = str(child_path).replace("\\", "/")
    
    return child_str.startswith(parent_str + "/")

def find_file_in_parents(filename: str, start_dir: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """
    Cherche un fichier dans le répertoire courant ou spécifié et ses parents.
    
    Args:
        filename: Nom du fichier à chercher
        start_dir: Répertoire de départ (par défaut: répertoire courant)
        
    Returns:
        Path ou None: Chemin du fichier s'il est trouvé, None sinon
    """
    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = resolve_path(start_dir)
    
    current_dir = start_dir
    
    # Remonter les répertoires parents
    while True:
        file_path = current_dir / filename
        if file_path.exists():
            return file_path
        
        # Arrêter à la racine
        if current_dir.parent == current_dir:
            break
        
        current_dir = current_dir.parent
    
    return None

def get_file_extension(path: Union[str, Path]) -> str:
    """
    Retourne l'extension d'un fichier (sans le point).
    
    Args:
        path: Chemin du fichier
        
    Returns:
        str: Extension du fichier (en minuscules)
    """
    if isinstance(path, str):
        path = Path(path)
    
    return path.suffix.lower().lstrip('.')

def get_file_name_without_extension(path: Union[str, Path]) -> str:
    """
    Retourne le nom d'un fichier sans son extension.
    
    Args:
        path: Chemin du fichier
        
    Returns:
        str: Nom du fichier sans extension
    """
    if isinstance(path, str):
        path = Path(path)
    
    return path.stem

def split_path(path: Union[str, Path]) -> Tuple[str, str, str]:
    """
    Divise un chemin en répertoire, nom de fichier sans extension et extension.
    
    Args:
        path: Chemin à diviser
        
    Returns:
        Tuple[str, str, str]: (répertoire, nom sans extension, extension)
    """
    path_obj = resolve_path(path)
    directory = str(path_obj.parent)
    filename = path_obj.stem
    extension = path_obj.suffix.lstrip('.')
    
    return directory, filename, extension