"""
Utilitaires système pour GestVenv v1.1.
Détection plateforme, commandes, ressources système.
"""

import os
import sys
import platform
import subprocess
import shutil
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class SystemInfo:
    """Informations système complètes."""
    platform: str
    architecture: str
    python_version: str
    python_executable: str
    cpu_count: int
    memory_total: int  # en bytes
    memory_available: int  # en bytes
    disk_free: int  # en bytes
    home_directory: Path
    temp_directory: Path
    is_virtual_env: bool
    is_conda_env: bool
    shell: str
    terminal: str

@dataclass
class CommandInfo:
    """Informations sur une commande système."""
    name: str
    path: Optional[Path]
    version: Optional[str]
    available: bool
    error_message: Optional[str] = None

class SystemUtils:
    """Utilitaires système avancés."""
    
    @staticmethod
    def get_system_info() -> SystemInfo:
        """
        Collecte les informations système complètes.
        
        Returns:
            Objet SystemInfo avec toutes les informations système
        """
        try:
            # Informations de base
            system_platform = platform.system().lower()
            architecture = platform.machine()
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            python_executable = Path(sys.executable)
            
            # Ressources système
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Répertoires système
            home_dir = Path.home()
            temp_dir = Path(os.environ.get('TMPDIR', '/tmp'))
            
            # Détection environnements virtuels
            is_virtual_env = hasattr(sys, 'real_prefix') or (
                hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
            )
            is_conda_env = 'CONDA_DEFAULT_ENV' in os.environ
            
            # Shell et terminal
            shell = os.environ.get('SHELL', 'unknown')
            terminal = os.environ.get('TERM', 'unknown')
            
            return SystemInfo(
                platform=system_platform,
                architecture=architecture,
                python_version=python_version,
                python_executable=python_executable,
                cpu_count=cpu_count,
                memory_total=memory.total,
                memory_available=memory.available,
                disk_free=disk.free,
                home_directory=home_dir,
                temp_directory=temp_dir,
                is_virtual_env=is_virtual_env,
                is_conda_env=is_conda_env,
                shell=shell,
                terminal=terminal
            )
            
        except Exception as e:
            logger.error(f"Erreur collecte informations système: {e}")
            raise
    
    @staticmethod
    def check_command_available(command: str, check_version: bool = True) -> CommandInfo:
        """
        Vérifie la disponibilité d'une commande système.
        
        Args:
            command: Nom de la commande
            check_version: Vérifier la version si possible
            
        Returns:
            Informations sur la commande
        """
        try:
            # Rechercher la commande
            command_path = shutil.which(command)
            
            if not command_path:
                return CommandInfo(
                    name=command,
                    path=None,
                    version=None,
                    available=False,
                    error_message=f"Commande '{command}' introuvable"
                )
            
            # Obtenir la version si demandée
            version = None
            if check_version:
                version = SystemUtils._get_command_version(command)
            
            return CommandInfo(
                name=command,
                path=Path(command_path),
                version=version,
                available=True
            )
            
        except Exception as e:
            logger.error(f"Erreur vérification commande {command}: {e}")
            return CommandInfo(
                name=command,
                path=None,
                version=None,
                available=False,
                error_message=str(e)
            )
    
    @staticmethod
    def _get_command_version(command: str) -> Optional[str]:
        """
        Tente d'obtenir la version d'une commande.
        
        Args:
            command: Nom de la commande
            
        Returns:
            Version de la commande ou None
        """
        version_flags = ['--version', '-v', '-V', 'version']
        
        for flag in version_flags:
            try:
                result = subprocess.run(
                    [command, flag],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    # Parser la sortie pour extraire la version
                    output = result.stdout.strip()
                    if output:
                        # Rechercher un motif de version (x.y.z)
                        import re
                        version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', output)
                        if version_match:
                            return version_match.group(1)
                        return output.split('\n')[0]  # Première ligne
                        
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                continue
        
        return None
    
    @staticmethod
    def run_command(command: List[str], cwd: Optional[Path] = None, 
                    timeout: int = 30, capture_output: bool = True) -> Tuple[bool, str, str]:
        """
        Exécute une commande système de manière sécurisée.
        
        Args:
            command: Liste des arguments de la commande
            cwd: Répertoire de travail
            timeout: Timeout en secondes
            capture_output: Capturer stdout/stderr
            
        Returns:
            (succès, stdout, stderr)
        """
        try:
            logger.debug(f"Exécution commande: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                check=False
            )
            
            success = result.returncode == 0
            stdout = result.stdout if capture_output else ""
            stderr = result.stderr if capture_output else ""
            
            if not success:
                logger.warning(f"Commande échouée (code {result.returncode}): {' '.join(command)}")
                logger.warning(f"stderr: {stderr}")
            
            return success, stdout, stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout commande: {' '.join(command)}")
            return False, "", f"Timeout après {timeout}s"
        except Exception as e:
            logger.error(f"Erreur exécution commande {command}: {e}")
            return False, "", str(e)
    
    @staticmethod
    def get_environment_variables(filter_prefix: Optional[str] = None) -> Dict[str, str]:
        """
        Récupère les variables d'environnement avec filtrage optionnel.
        
        Args:
            filter_prefix: Préfixe pour filtrer les variables
            
        Returns:
            Dictionnaire des variables d'environnement
        """
        env_vars = dict(os.environ)
        
        if filter_prefix:
            env_vars = {
                key: value for key, value in env_vars.items()
                if key.startswith(filter_prefix)
            }
        
        return env_vars
    
    @staticmethod
    def is_admin() -> bool:
        """
        Vérifie si l'utilisateur a les privilèges administrateur.
        
        Returns:
            True si administrateur, False sinon
        """
        try:
            if sys.platform == "win32":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False
    
    @staticmethod
    def get_python_installations() -> List[Dict[str, Any]]:
        """
        Détecte les installations Python disponibles.
        
        Returns:
            Liste des installations Python trouvées
        """
        installations = []
        
        # Python actuel
        current_python = {
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "executable": str(Path(sys.executable)),
            "is_current": True,
            "is_virtual_env": hasattr(sys, 'real_prefix') or (
                hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
            )
        }
        installations.append(current_python)
        
        # Rechercher d'autres installations
        python_commands = ['python', 'python3', 'python3.9', 'python3.10', 'python3.11', 'python3.12']
        
        for cmd in python_commands:
            cmd_info = SystemUtils.check_command_available(cmd)
            if cmd_info.available and cmd_info.path != Path(sys.executable):
                # Obtenir la version complète
                success, stdout, _ = SystemUtils.run_command([cmd, '--version'])
                if success and stdout:
                    version_str = stdout.strip().split()[-1]
                    installations.append({
                        "version": version_str,
                        "executable": str(cmd_info.path),
                        "is_current": False,
                        "is_virtual_env": False
                    })
        
        # Éliminer les doublons
        seen_paths = set()
        unique_installations = []
        for install in installations:
            if install["executable"] not in seen_paths:
                seen_paths.add(install["executable"])
                unique_installations.append(install)
        
        return unique_installations
    
    @staticmethod
    def get_disk_usage(path: Union[str, Path]) -> Dict[str, int]:
        """
        Obtient l'utilisation disque pour un chemin.
        
        Args:
            path: Chemin à analyser
            
        Returns:
            Dictionnaire avec total, used, free en bytes
        """
        try:
            usage = psutil.disk_usage(str(path))
            return {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free
            }
        except Exception as e:
            logger.error(f"Erreur analyse disque {path}: {e}")
            return {"total": 0, "used": 0, "free": 0}

# Fonctions utilitaires pour compatibilité
def get_system_info() -> SystemInfo:
    """Fonction utilitaire pour obtenir les informations système."""
    return SystemUtils.get_system_info()

def check_command_available(command: str) -> CommandInfo:
    """Fonction utilitaire pour vérifier une commande."""
    return SystemUtils.check_command_available(command)
