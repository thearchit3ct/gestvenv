"""
Templates pour GestVenv.

Ce package contient les modèles et fichiers de configuration par défaut utilisés par GestVenv.
"""

import os
import json
from pathlib import Path

def get_default_config():
    """
    Charge et retourne la configuration par défaut.
    
    Returns:
        dict: Configuration par défaut
    """
    template_dir = Path(__file__).parent
    config_path = template_dir / "default_config.json"
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Remplacer les chemins génériques par les chemins spécifiques au système
        if "environments" in config:
            for env_name, env_info in config["environments"].items():
                if "path" in env_info and "PLACEHOLDER_PATH" in env_info["path"]:
                    from ..utils.path_handler import get_default_venv_dir
                    env_info["path"] = str(get_default_venv_dir() / env_name)
        
        return config
    except Exception as e:
        # En cas d'erreur, retourner une configuration minimale
        return {
            "environments": {},
            "active_env": None,
            "default_python": "python3" if os.name != "nt" else "python",
            "settings": {
                "auto_activate": True,
                "package_cache_enabled": True,
                "check_updates_on_activate": True,
                "default_export_format": "json",
                "show_virtual_env_in_prompt": True
            }
        }