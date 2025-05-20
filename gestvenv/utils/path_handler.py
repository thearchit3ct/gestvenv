"""
Module de gestion des chemins pour GestVenv.

Ce module fournit des fonctions pour gérer les chemins des environnements virtuels,
les fichiers de configuration, et assure la compatibilité entre différentes plateformes.
"""

import os
import sys
import platform
from pathlib import Path
import logging
from typing import Union, Optional, Dict, List

# Configuration du logger
logger = logging.getLogger(__name__)

def get_app_data_dir() -> Path:
    """
    Obtient le répertoire d'application approprié selon le système d'exploitation.
    
    Returns:
        Path: Chemin vers le répertoire d'application
    """
    system = platform.system().lower()
    
    if system == "windows":
        app_data = os.environ.get("APPDATA")
        return Path(app_data) / "GestVenv"
    elif system == "darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "GestVenv"
    else:  # Linux et autres systèmes Unix-like
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            return Path(xdg_config_home) / "gestvenv"
        else:
            return Path.home() / ".config" / "gestvenv"

def get_config_file_path() -> Path:
    """
    Retourne le chemin vers le fichier de configuration principal.
    
    Returns:
        Path: Chemin vers le fichier de configuration
    """
    config_dir = get_app_data_dir()
    config_file = config_dir / "config.json"
    
    # Création du répertoire si nécessaire
    if not config_dir.exists():
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Répertoire de configuration créé: {config_dir}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du répertoire de configuration: {e}")
            raise
    
    return config_file

def get_default_venv_dir() -> Path:
    """
    Obtient le répertoire par défaut pour les environnements virtuels.
    
    Returns:
        Path: Chemin vers le répertoire des environnements virtuels
    """
    return get_app_data_dir() / "environments"

def ensure_venv_dir(name: str = None) -> Path:
    """
    S'assure que le répertoire pour les environnements virtuels existe.
    Si un nom est fourni, retourne le chemin vers cet environnement spécifique.
    
    Args:
        name (str, optional): Nom de l'environnement virtuel
        
    Returns:
        Path: Chemin vers le répertoire des environnements ou d'un environnement spécifique
    """
    venv_dir = get_default_venv_dir()
    
    if not venv_dir.exists():
        try:
            venv_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Répertoire des environnements créé: {venv_dir}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du répertoire des environnements: {e}")
            raise
    
    if name:
        env_dir = venv_dir / name
        return env_dir
    
    return venv_dir

def get_environment_path(env_name: str) -> Optional[Path]:
    """
    Obtient le chemin vers un environnement virtuel spécifique.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        
    Returns:
        Optional[Path]: Chemin vers l'environnement s'il existe, None sinon
    """
    env_path = ensure_venv_dir(env_name)
    
    if env_path.exists():
        return env_path
    
    # Vérifie également le chemin personnalisé dans la configuration
    from ..core.config_manager import ConfigManager  # Import local pour éviter l'import circulaire
    
    config_manager = ConfigManager()
    env_config = config_manager.get_environment(env_name)
    if env_config and "path" in env_config:
        custom_path = Path(env_config["path"])
        if custom_path.exists():
            return custom_path
    
    logger.warning(f"Environnement '{env_name}' non trouvé")
    return None

def get_python_executable(env_name: str) -> Optional[Path]:
    """
    Obtient le chemin vers l'exécutable Python d'un environnement virtuel.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        
    Returns:
        Optional[Path]: Chemin vers l'exécutable Python s'il existe, None sinon
    """
    env_path = get_environment_path(env_name)
    if not env_path:
        return None
    
    system = platform.system().lower()
    
    if system == "windows":
        python_path = env_path / "Scripts" / "python.exe"
    else:  # macOS et Linux
        python_path = env_path / "bin" / "python"
    
    if python_path.exists():
        return python_path
    
    logger.warning(f"Exécutable Python non trouvé pour l'environnement '{env_name}'")
    return None

def get_pip_executable(env_name: str) -> Optional[Path]:
    """
    Obtient le chemin vers l'exécutable pip d'un environnement virtuel.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        
    Returns:
        Optional[Path]: Chemin vers l'exécutable pip s'il existe, None sinon
    """
    env_path = get_environment_path(env_name)
    if not env_path:
        return None
    
    system = platform.system().lower()
    
    if system == "windows":
        pip_path = env_path / "Scripts" / "pip.exe"
    else:  # macOS et Linux
        pip_path = env_path / "bin" / "pip"
    
    if pip_path.exists():
        return pip_path
    
    logger.warning(f"Exécutable pip non trouvé pour l'environnement '{env_name}'")
    return None

def get_activation_script_path(env_name: str) -> Optional[Path]:
    """
    Obtient le chemin vers le script d'activation d'un environnement virtuel.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        
    Returns:
        Optional[Path]: Chemin vers le script d'activation s'il existe, None sinon
    """
    env_path = get_environment_path(env_name)
    if not env_path:
        return None
    
    system = platform.system().lower()
    
    if system == "windows":
        activate_path = env_path / "Scripts" / "activate.bat"
    else:  # macOS et Linux
        activate_path = env_path / "bin" / "activate"
    
    if activate_path.exists():
        return activate_path
    
    logger.warning(f"Script d'activation non trouvé pour l'environnement '{env_name}'")
    return None

def resolve_path(path_str: str) -> Path:
    """
    Résout un chemin relatif ou absolu.
    
    Args:
        path_str (str): Chaîne de caractères représentant un chemin
        
    Returns:
        Path: Chemin absolu résolu
    """
    path = Path(path_str)
    
    # Résout le chemin (~ pour le répertoire utilisateur, chemins relatifs, etc.)
    if not path.is_absolute():
        # Si le chemin commence par ~, résoudre vers le répertoire utilisateur
        if path_str.startswith("~"):
            path = Path(os.path.expanduser(path_str))
        else:
            # Sinon, considérer le chemin comme relatif au répertoire courant
            path = Path.cwd() / path
    
    return path.resolve()

def get_export_directory() -> Path:
    """
    Obtient le répertoire par défaut pour l'exportation des configurations.
    
    Returns:
        Path: Chemin vers le répertoire d'exportation
    """
    export_dir = get_app_data_dir() / "exports"
    
    if not export_dir.exists():
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Répertoire d'exportation créé: {export_dir}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du répertoire d'exportation: {e}")
            raise
    
    return export_dir

def get_default_export_path(env_name: str) -> Path:
    """
    Obtient le chemin par défaut pour l'exportation d'un environnement.
    
    Args:
        env_name (str): Nom de l'environnement virtuel
        
    Returns:
        Path: Chemin par défaut pour l'exportation
    """
    export_dir = get_export_directory()
    timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{env_name}_{timestamp}.json"
    
    return export_dir / filename

def is_valid_env_name(name: str) -> bool:
    """
    Vérifie si un nom d'environnement est valide (sans caractères spéciaux problématiques).
    
    Args:
        name (str): Nom à vérifier
        
    Returns:
        bool: True si le nom est valide, False sinon
    """
    import re
    # Autorise les lettres, chiffres, tirets et soulignés
    pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    return bool(pattern.match(name))