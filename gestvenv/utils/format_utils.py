"""
Utilitaires de formatage pour GestVenv.

Ce module fournit des fonctions pour formater et afficher des données
de manière cohérente et lisible.
"""

import os
import time
import datetime
import logging
from typing import List, Dict, Any, Optional, Union, Tuple

# Configuration du logger
logger = logging.getLogger(__name__)

# Définition des couleurs pour le terminal
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "underline": "\033[4m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bg_black": "\033[40m",
    "bg_red": "\033[41m",
    "bg_green": "\033[42m",
    "bg_yellow": "\033[43m",
    "bg_blue": "\033[44m",
    "bg_magenta": "\033[45m",
    "bg_cyan": "\033[46m",
    "bg_white": "\033[47m"
}

def format_timestamp(timestamp: Union[float, int, str, datetime.datetime],
                    format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Formate un timestamp en chaîne de date lisible.
    
    Args:
        timestamp: Timestamp à formater (float, int, chaîne ISO ou datetime)
        format_str: Format de sortie
        
    Returns:
        str: Timestamp formaté
    """
    try:
        if isinstance(timestamp, (float, int)):
            dt = datetime.datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            # Essayer d'analyser une chaîne ISO
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, datetime.datetime):
            dt = timestamp
        else:
            raise ValueError(f"Type de timestamp non pris en charge: {type(timestamp)}")
        
        return dt.strftime(format_str)
    except Exception as e:
        logger.error(f"Erreur lors du formatage du timestamp: {e}")
        return str(timestamp)

def truncate_string(s: str, max_length: int = 80, suffix: str = "...") -> str:
    """
    Tronque une chaîne si elle dépasse une longueur maximale.
    
    Args:
        s: Chaîne à tronquer
        max_length: Longueur maximale
        suffix: Suffixe à ajouter si la chaîne est tronquée
        
    Returns:
        str: Chaîne tronquée
    """
    if len(s) <= max_length:
        return s
    
    return s[:max_length - len(suffix)] + suffix

def format_list_as_table(data: List[Dict[str, Any]], columns: Optional[List[str]] = None,
                        header: bool = True, padding: int = 2) -> List[str]:
    """
    Formate une liste de dictionnaires en tableau textuel.
    
    Args:
        data: Liste de dictionnaires à formater
        columns: Liste des colonnes à inclure (par défaut: toutes)
        header: Si True, inclut une ligne d'en-tête
        padding: Nombre d'espaces de remplissage entre les colonnes
        
    Returns:
        List[str]: Liste de lignes formatées
    """
    if not data:
        return []
    
    # Déterminer les colonnes
    if not columns:
        # Utiliser toutes les clés uniques des dictionnaires
        columns = sorted(set(key for item in data for key in item.keys()))
    
    # Déterminer la largeur de chaque colonne
    col_widths = {col: len(col) for col in columns}
    for item in data:
        for col in columns:
            if col in item:
                col_widths[col] = max(col_widths[col], len(str(item[col])))
    
    # Générer les lignes du tableau
    lines = []
    
    # Ajouter l'en-tête
    if header:
        header_line = "".join(f"{col:{col_widths[col] + padding}}" for col in columns)
        lines.append(header_line)
        separator = "".join("-" * (col_widths[col] + padding) for col in columns)
        lines.append(separator)
    
    # Ajouter les lignes de données
    for item in data:
        line = "".join(f"{str(item.get(col, '')):{col_widths[col] + padding}}" for col in columns)
        lines.append(line)
    
    return lines

def get_color_for_terminal(color_name: str) -> str:
    """
    Retourne le code ANSI pour une couleur donnée.
    
    Args:
        color_name: Nom de la couleur
        
    Returns:
        str: Code ANSI pour la couleur ou chaîne vide si non disponible
    """
    # Vérifier si les couleurs sont supportées
    if not _supports_color():
        return ""
    
    return COLORS.get(color_name.lower(), "")

def _supports_color() -> bool:
    """
    Vérifie si le terminal supporte les couleurs.
    
    Returns:
        bool: True si le terminal supporte les couleurs
    """
    # Vérifier les variables d'environnement
    if os.environ.get("TERM") == "dumb":
        return False
    
    # Vérifier si la sortie est redirigée
    if not os.isatty(1):  # 1 = stdout
        return False
    
    # Vérifier le système d'exploitation
    plat = os.environ.get("TERM") or os.name
    
    # ANSI est supporté sur la plupart des Unix et Windows 10+
    if plat in ("linux", "cygwin", "xterm", "xterm-color", "xterm-256color"):
        return True
    
    # Windows 10 build 16257+ supporte ANSI nativement
    if os.name == "nt":
        try:
            import ctypes
            version = ctypes.windll.ntdll.RtlGetVersion
            version.argtypes = [ctypes.POINTER(ctypes.c_ulong)]
            version.restype = ctypes.c_ulong
            
            class OSVERSIONINFO(ctypes.Structure):
                _fields_ = [
                    ("dwOSVersionInfoSize", ctypes.c_ulong),
                    ("dwMajorVersion", ctypes.c_ulong),
                    ("dwMinorVersion", ctypes.c_ulong),
                    ("dwBuildNumber", ctypes.c_ulong),
                    ("dwPlatformId", ctypes.c_ulong),
                    ("szCSDVersion", ctypes.c_wchar * 128)
                ]
            
            os_version = OSVERSIONINFO()
            os_version.dwOSVersionInfoSize = ctypes.sizeof(OSVERSIONINFO)
            version(ctypes.byref(os_version))
            
            # Windows 10 build 16257+ supporte ANSI
            if os_version.dwMajorVersion >= 10 and os_version.dwBuildNumber >= 16257:
                return True
        except Exception:
            pass
    
    return False

def format_size(size_bytes: int) -> str:
    """
    Formate une taille en octets en une chaîne lisible (KiB, MiB, GiB).
    
    Args:
        size_bytes: Taille en octets
        
    Returns:
        str: Taille formatée
    """
    if size_bytes < 0:
        raise ValueError("La taille ne peut pas être négative")
    
    if size_bytes < 1024:
        return f"{size_bytes} B"
    
    size_kb = size_bytes / 1024.0
    if size_kb < 1024:
        return f"{size_kb:.2f} KiB"
    
    size_mb = size_kb / 1024.0
    if size_mb < 1024:
        return f"{size_mb:.2f} MiB"
    
    size_gb = size_mb / 1024.0
    return f"{size_gb:.2f} GiB"

def format_duration(seconds: float) -> str:
    """
    Formate une durée en secondes en une chaîne lisible.
    
    Args:
        seconds: Durée en secondes
        
    Returns:
        str: Durée formatée
    """
    if seconds < 0:
        raise ValueError("La durée ne peut pas être négative")
    
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    
    if seconds < 60:
        return f"{seconds:.1f} s"
    
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)}m {int(seconds % 60)}s"
    
    hours = minutes / 60
    return f"{int(hours)}h {int(minutes % 60)}m {int(seconds % 60)}s"