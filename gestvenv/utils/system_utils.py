"""
Utilitaires d'interaction système pour GestVenv.

Ce module fournit des fonctions pour interagir avec le système d'exploitation
de manière indépendante de la plateforme.
"""

import os
import sys
import platform
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Union

# Import des utilitaires de chemin sans créer de dépendance circulaire
from .path_utils import get_os_name

# Configuration du logger
logger = logging.getLogger(__name__)

def run_simple_command(cmd: List[str], cwd: Optional[Union[str, Path]] = None,
                       capture_output: bool = True) -> Dict[str, Any]:
    """
    Exécute une commande système simple et retourne les résultats.
    
    Args:
        cmd: Liste des éléments de la commande à exécuter
        cwd: Répertoire de travail pour l'exécution
        capture_output: Si True, capture les sorties standard et d'erreur
        
    Returns:
        Dict: Dictionnaire contenant le code de retour et les sorties
    """
    try:
        logger.debug(f"Exécution de la commande: {' '.join(cmd)}")
        
        # Convertir le répertoire en Path si c'est une chaîne
        if cwd and isinstance(cwd, str):
            cwd = Path(cwd)
        
        # Exécuter la commande
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=False,
            env=os.environ.copy()
        )
        
        # Préparer le résultat
        output = {
            'returncode': result.returncode,
            'stdout': result.stdout if capture_output else "",
            'stderr': result.stderr if capture_output else ""
        }
        
        # Journaliser le résultat si nécessaire
        if result.returncode != 0:
            logger.debug(f"Commande terminée avec code de retour non nul: {result.returncode}")
            if capture_output and result.stderr:
                logger.debug(f"Erreur: {result.stderr}")
        
        return output
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la commande: {e}")
        return {
            'returncode': 1,
            'stdout': "",
            'stderr': str(e)
        }

def get_current_username() -> str:
    """
    Retourne le nom d'utilisateur courant.
    
    Returns:
        str: Nom d'utilisateur courant
    """
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        # Fallback alternatifs selon le système
        try:
            return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'
        except Exception:
            return 'unknown'

def is_command_available(command: str) -> bool:
    """
    Vérifie si une commande est disponible dans le système.
    
    Args:
        command: Nom de la commande à vérifier
        
    Returns:
        bool: True si la commande est disponible
    """
    os_name = get_os_name()
    
    # Construire la commande selon le système
    if os_name == "windows":
        check_cmd = ["where", command]
    else:
        check_cmd = ["which", command]
    
    # Exécuter la commande
    result = run_simple_command(check_cmd)
    
    return result['returncode'] == 0

def get_terminal_size() -> Tuple[int, int]:
    """
    Retourne la taille du terminal (colonnes, lignes).
    
    Returns:
        Tuple[int, int]: (largeur, hauteur) du terminal
    """
    try:
        columns, lines = shutil.get_terminal_size()
        return columns, lines
    except Exception:
        # Valeurs par défaut si impossible de déterminer
        return 80, 24

def get_python_version_info() -> Dict[str, Any]:
    """
    Retourne des informations sur la version Python courante.
    
    Returns:
        Dict: Informations sur la version Python
    """
    return {
        'version': platform.python_version(),
        'implementation': platform.python_implementation(),
        'build': platform.python_build(),
        'compiler': platform.python_compiler(),
        'is_64bit': sys.maxsize > 2**32
    }

def get_system_info() -> Dict[str, str]:
    """
    Retourne des informations sur le système d'exploitation.
    
    Returns:
        Dict: Informations sur le système
    """
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor()
    }

def check_program_version(program: str, args: Optional[List[str]] = None,
                         regex: str = r'(\d+\.\d+\.\d+)') -> Optional[str]:
    """
    Vérifie la version d'un programme en exécutant une commande.
    
    Args:
        program: Nom du programme
        args: Arguments optionnels (par défaut: ['--version'])
        regex: Expression régulière pour extraire la version
        
    Returns:
        str ou None: Version du programme ou None si non trouvée
    """
    import re
    
    if args is None:
        args = ['--version']
    
    # Exécuter la commande
    result = run_simple_command([program] + args)
    
    if result['returncode'] != 0:
        return None
    
    # Rechercher la version dans la sortie
    output = result['stdout'] or result['stderr']
    match = re.search(regex, output)
    
    if match:
        return match.group(1)
    
    return None

def open_file(path: Union[str, Path]) -> bool:
    """
    Ouvre un fichier avec l'application par défaut du système.
    
    Args:
        path: Chemin du fichier à ouvrir
        
    Returns:
        bool: True si l'opération a réussi
    """
    from .path_utils import resolve_path
    path_obj = resolve_path(path)
    
    if not path_obj.exists():
        logger.error(f"Le fichier '{path}' n'existe pas")
        return False
    
    os_name = get_os_name()
    
    try:
        if os_name == "windows":
            # Windows
            os.startfile(str(path_obj))
        elif os_name == "darwin":
            # macOS
            subprocess.run(["open", str(path_obj)], shell=False, check=False)
        else:
            # Linux et autres
            subprocess.run(["xdg-open", str(path_obj)], shell=False, check=False)
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'ouverture du fichier: {e}")
        return False

def get_free_disk_space(path: Union[str, Path]) -> int:
    """
    Retourne l'espace disque libre en octets pour un chemin donné.
    
    Args:
        path: Chemin pour lequel vérifier l'espace disque
        
    Returns:
        int: Espace disque libre en octets
    """
    from .path_utils import resolve_path
    path_obj = resolve_path(path)
    
    try:
        if get_os_name() == "windows":
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(str(path_obj)),
                None, None,
                ctypes.pointer(free_bytes)
            )
            return free_bytes.value
        else:
            # Unix systems
            stats = os.statvfs(path_obj)
            return stats.f_frsize * stats.f_bavail
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'espace disque libre: {e}")
        return 0