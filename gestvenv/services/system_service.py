"""
SystemService - Service d'interactions avec le système d'exploitation.

Ce service centralise toutes les interactions avec le système :
- Exécution de commandes shell
- Détection et validation des versions Python
- Opérations sur les processus
- Informations système et environnement
- Activation d'environnements virtuels

Il fournit une interface unifiée et sécurisée pour les opérations système
avec gestion d'erreurs, timeouts et logging complet.
"""

import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CommandResult:
    """Résultat d'une commande système."""
    
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "", 
                 duration: float = 0.0, command: List[str] = None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.command = command or []
    
    @property
    def success(self) -> bool:
        """True si la commande a réussi."""
        return self.returncode == 0
    
    @property
    def failed(self) -> bool:
        """True si la commande a échoué."""
        return self.returncode != 0
    
    def __repr__(self) -> str:
        return f"CommandResult(returncode={self.returncode}, duration={self.duration:.2f}s)"


@dataclass
class PythonVersion:
    """Informations sur une version Python détectée."""
    executable: Path
    version: str
    version_info: Tuple[int, int, int]
    is_virtual: bool = False
    location: Optional[Path] = None
    
    @property
    def version_string(self) -> str:
        """Version formatée (ex: '3.11.5')."""
        return self.version
    
    @property
    def major_minor(self) -> str:
        """Version majeure.mineure (ex: '3.11')."""
        return f"{self.version_info[0]}.{self.version_info[1]}"
    
    def is_compatible_with(self, min_version: Tuple[int, int, int]) -> bool:
        """Vérifie la compatibilité avec une version minimum."""
        return self.version_info >= min_version


@dataclass 
class SystemInfo:
    """Informations sur le système."""
    platform: str
    architecture: str
    python_version: str
    python_executable: Path
    shell: Optional[str] = None
    environment_variables: Optional[Dict[str, str]] = None


class SystemService:
    """
    Service pour les interactions avec le système d'exploitation.
    
    Responsabilités:
    - Exécution sécurisée de commandes
    - Détection et validation Python
    - Gestion des processus et environnements
    - Informations système
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le service système.
        
        Args:
            config: Configuration optionnelle du service
        """
        self.config = config or {}
        
        # Configuration par défaut
        self.default_timeout = self.config.get('default_timeout', 30)
        self.max_timeout = self.config.get('max_timeout', 300)
        self.shell_detection = self.config.get('shell_detection', True)
        self.cache_python_versions = self.config.get('cache_python_versions', True)
        
        # Cache pour les versions Python détectées
        self._python_versions_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes
        
        # Détection du shell par défaut
        self.default_shell = self._detect_default_shell()
        
        logger.debug(f"SystemService initialisé avec config: {self.config}")
    
    def run_command(self, command: Union[str, List[str]], 
                   cwd: Optional[Path] = None,
                   env: Optional[Dict[str, str]] = None,
                   timeout: Optional[int] = None,
                   capture_output: bool = True,
                   text: bool = True,
                   shell: bool = False,
                   input_data: Optional[str] = None) -> CommandResult:
        """
        Exécute une commande système avec gestion complète.
        
        Args:
            command: Commande à exécuter (string ou liste)
            cwd: Répertoire de travail
            env: Variables d'environnement supplémentaires
            timeout: Timeout en secondes
            capture_output: Capturer stdout/stderr
            text: Mode texte pour les sorties
            shell: Utiliser le shell système
            input_data: Données à envoyer en entrée
            
        Returns:
            CommandResult: Résultat complet de la commande
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        # Préparation de la commande
        if isinstance(command, str):
            if not shell:
                # Conversion en liste si pas de shell
                command = command.split()
            cmd_for_log = command
        else:
            cmd_for_log = ' '.join(command)
        
        # Préparation de l'environnement
        final_env = os.environ.copy()
        if env:
            final_env.update(env)
        
        logger.debug(f"Exécution commande: {cmd_for_log}")
        logger.debug(f"CWD: {cwd}, Timeout: {timeout}s, Shell: {shell}")
        
        try:
            # Exécution de la commande
            process = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                env=final_env,
                timeout=timeout,
                capture_output=capture_output,
                text=text,
                shell=shell,
                input=input_data
            )
            
            duration = time.time() - start_time
            
            result = CommandResult(
                returncode=process.returncode,
                stdout=process.stdout if capture_output else "",
                stderr=process.stderr if capture_output else "",
                duration=duration,
                command=command if isinstance(command, list) else [command]
            )
            
            if result.success:
                logger.debug(f"Commande réussie en {duration:.2f}s")
            else:
                logger.warning(f"Commande échouée (code {result.returncode}) en {duration:.2f}s")
                if result.stderr:
                    logger.debug(f"Stderr: {result.stderr[:200]}...")
            
            return result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"Timeout de commande après {duration:.2f}s: {cmd_for_log}")
            return CommandResult(
                returncode=-1,
                stderr=f"Timeout après {timeout}s",
                duration=duration,
                command=command if isinstance(command, list) else [command]
            )
            
        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            logger.error(f"Erreur de commande: {e}")
            return CommandResult(
                returncode=e.returncode,
                stdout=e.stdout if hasattr(e, 'stdout') and e.stdout else "",
                stderr=e.stderr if hasattr(e, 'stderr') and e.stderr else str(e),
                duration=duration,
                command=command if isinstance(command, list) else [command]
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Erreur inattendue lors de l'exécution: {e}")
            return CommandResult(
                returncode=-2,
                stderr=f"Erreur interne: {str(e)}",
                duration=duration,
                command=command if isinstance(command, list) else [command]
            )
    
    def check_python_version(self, python_cmd: str) -> Optional[str]:
        """
        Vérifie et retourne la version d'un exécutable Python.
        
        Args:
            python_cmd: Commande Python à tester
            
        Returns:
            Optional[str]: Version Python ou None si invalide
        """
        try:
            result = self.run_command([
                python_cmd, '-c', 
                'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
            ], timeout=10)
            
            if result.success:
                version = result.stdout.strip()
                logger.debug(f"Python {python_cmd} version: {version}")
                return version
            else:
                logger.debug(f"Impossible de déterminer la version de {python_cmd}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.debug(f"Erreur lors de la vérification de {python_cmd}: {e}")
            return None
    
    def get_python_version_info(self, python_cmd: str) -> Optional[PythonVersion]:
        """
        Obtient les informations détaillées sur une version Python.
        
        Args:
            python_cmd: Commande Python à analyser
            
        Returns:
            Optional[PythonVersion]: Informations détaillées ou None
        """
        try:
            # Récupération des informations de base
            result = self.run_command([
                python_cmd, '-c',
                '''
import sys
import os
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print(f"{sys.version_info.major},{sys.version_info.minor},{sys.version_info.micro}")
print("1" if hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix else "0")
print(sys.executable)
'''
            ], timeout=10)
            
            if not result.success:
                return None
            
            lines = result.stdout.strip().split('\n')
            if len(lines) < 4:
                return None
            
            version_str = lines[0]
            version_parts = [int(x) for x in lines[1].split(',')]
            is_virtual = lines[2] == "1"
            executable_path = Path(lines[3])
            
            return PythonVersion(
                executable=executable_path,
                version=version_str,
                version_info=tuple(version_parts),
                is_virtual=is_virtual,
                location=executable_path.parent
            )
            
        except Exception as e:
            logger.debug(f"Erreur lors de l'analyse de {python_cmd}: {e}")
            return None
    
    def get_available_python_versions(self, refresh_cache: bool = False) -> List[PythonVersion]:
        """
        Détecte toutes les versions Python disponibles sur le système.
        
        Args:
            refresh_cache: Forcer le rafraîchissement du cache
            
        Returns:
            List[PythonVersion]: Liste des versions Python trouvées
        """
        # Vérification du cache
        current_time = time.time()
        if (not refresh_cache and self.cache_python_versions and 
            self._python_versions_cache is not None and
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._python_versions_cache
        
        logger.info("Détection des versions Python disponibles...")
        versions = []
        
        # Commandes Python communes à tester
        python_commands = [
            'python', 'python3', 'python3.12', 'python3.11', 'python3.10', 
            'python3.9', 'python3.8', 'python3.7', 'python2', 'python2.7',
            'py'  # Windows Python Launcher
        ]
        
        # Ajout des versions depuis PATH
        if sys.platform.startswith('win'):
            # Windows: chercher dans PATH et répertoires communs
            python_commands.extend(self._find_windows_pythons())
        else:
            # Unix: chercher dans les emplacements standards
            python_commands.extend(self._find_unix_pythons())
        
        # Test de chaque commande
        seen_executables = set()
        for cmd in python_commands:
            try:
                python_info = self.get_python_version_info(cmd)
                if python_info and python_info.executable not in seen_executables:
                    versions.append(python_info)
                    seen_executables.add(python_info.executable)
                    logger.debug(f"Python trouvé: {cmd} -> {python_info.version} ({python_info.executable})")
            except Exception as e:
                logger.debug(f"Erreur lors du test de {cmd}: {e}")
                continue
        
        # Tri par version (plus récente en premier)
        versions.sort(key=lambda v: v.version_info, reverse=True)
        
        # Mise en cache
        if self.cache_python_versions:
            self._python_versions_cache = versions
            self._cache_timestamp = current_time
        
        logger.info(f"Détection terminée: {len(versions)} version(s) Python trouvée(s)")
        return versions
    
    def _find_windows_pythons(self) -> List[str]:
        """Trouve les installations Python sur Windows."""
        commands = []
        
        # Python Launcher
        if shutil.which('py'):
            # Lister les versions disponibles via py
            try:
                result = self.run_command(['py', '-0'], timeout=5)
                if result.success:
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('-'):
                            # Format: -3.11-64 ou -3.11
                            if line.startswith('-'):
                                version = line.split('-')[1].split('-')[0]
                                commands.append(f'py -3.{version}')
            except Exception:
                pass
        
        # Répertoires d'installation communs
        common_paths = [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Python',
            Path('C:/Python*'),
            Path('C:/Program Files/Python*'),
            Path('C:/Program Files (x86)/Python*')
        ]
        
        for path_pattern in common_paths:
            try:
                if '*' in str(path_pattern):
                    # Utilisation de glob pour les patterns
                    parent = path_pattern.parent
                    pattern = path_pattern.name
                    if parent.exists():
                        for python_dir in parent.glob(pattern):
                            python_exe = python_dir / 'python.exe'
                            if python_exe.exists():
                                commands.append(str(python_exe))
                else:
                    python_exe = path_pattern / 'python.exe'
                    if python_exe.exists():
                        commands.append(str(python_exe))
            except Exception:
                continue
        
        return commands
    
    def _find_unix_pythons(self) -> List[str]:
        """Trouve les installations Python sur Unix/Linux/macOS."""
        commands = []
        
        # Répertoires standards
        standard_paths = [
            '/usr/bin',
            '/usr/local/bin',
            '/opt/python*/bin',
            '/opt/local/bin',  # MacPorts
            '/usr/local/Cellar/python*/*/bin',  # Homebrew
            str(Path.home() / '.pyenv' / 'versions' / '*' / 'bin'),  # pyenv
            '/snap/bin',  # Snap packages
        ]
        
        for path_pattern in standard_paths:
            try:
                if '*' in path_pattern:
                    # Utilisation de glob pour les patterns
                    import glob
                    for path_str in glob.glob(path_pattern):
                        path = Path(path_str)
                        if path.exists():
                            for python_exe in path.glob('python*'):
                                if python_exe.is_file() and os.access(python_exe, os.X_OK):
                                    commands.append(str(python_exe))
                else:
                    path = Path(path_pattern)
                    if path.exists():
                        for python_exe in path.glob('python*'):
                            if python_exe.is_file() and os.access(python_exe, os.X_OK):
                                commands.append(str(python_exe))
            except Exception:
                continue
        
        return commands
    
    def run_in_environment(self, env_name: str, env_path: Path, 
                          command: List[str], **kwargs) -> CommandResult:
        """
        Exécute une commande dans un environnement virtuel activé.
        
        Args:
            env_name: Nom de l'environnement
            env_path: Chemin de l'environnement
            command: Commande à exécuter
            **kwargs: Arguments supplémentaires pour run_command
            
        Returns:
            CommandResult: Résultat de la commande
        """
        # Préparation de l'environnement
        activation_env = self._get_environment_variables(env_path)
        
        # Fusion avec l'environnement existant
        final_env = kwargs.get('env', {})
        final_env.update(activation_env)
        kwargs['env'] = final_env
        
        logger.debug(f"Exécution dans l'environnement {env_name}: {' '.join(command)}")
        return self.run_command(command, **kwargs)
    
    def _get_environment_variables(self, env_path: Path) -> Dict[str, str]:
        """
        Calcule les variables d'environnement pour activer un environnement virtuel.
        
        Args:
            env_path: Chemin de l'environnement
            
        Returns:
            Dict[str, str]: Variables d'environnement
        """
        env_vars = {}
        
        if sys.platform.startswith('win'):
            # Windows
            scripts_dir = env_path / 'Scripts'
            python_exe = scripts_dir / 'python.exe'
        else:
            # Unix
            scripts_dir = env_path / 'bin'
            python_exe = scripts_dir / 'python'
        
        if scripts_dir.exists():
            # Modification du PATH
            current_path = os.environ.get('PATH', '')
            env_vars['PATH'] = f"{scripts_dir}{os.pathsep}{current_path}"
            
            # Variables virtuelles
            env_vars['VIRTUAL_ENV'] = str(env_path)
            if python_exe.exists():
                env_vars['PYTHON'] = str(python_exe)
            
            # Suppression de PYTHONHOME si présent
            if 'PYTHONHOME' in os.environ:
                env_vars['PYTHONHOME'] = ''
        
        return env_vars
    
    def get_activation_command(self, env_name: str, env_path: Path) -> Optional[str]:
        """
        Génère la commande d'activation pour un environnement.
        
        Args:
            env_name: Nom de l'environnement
            env_path: Chemin de l'environnement
            
        Returns:
            Optional[str]: Commande d'activation ou None
        """
        if sys.platform.startswith('win'):
            # Windows
            activate_script = env_path / 'Scripts' / 'activate.bat'
            if activate_script.exists():
                return f'"{activate_script}"'
            
            # PowerShell
            ps_script = env_path / 'Scripts' / 'Activate.ps1'
            if ps_script.exists():
                return f'& "{ps_script}"'
        else:
            # Unix
            activate_script = env_path / 'bin' / 'activate'
            if activate_script.exists():
                return f'source "{activate_script}"'
        
        return None
    
    def get_system_info(self) -> SystemInfo:
        """
        Collecte les informations système complètes.
        
        Returns:
            SystemInfo: Informations détaillées du système
        """
        return SystemInfo(
            platform=platform.platform(),
            architecture=platform.architecture()[0],
            python_version=platform.python_version(),
            python_executable=Path(sys.executable),
            shell=self.default_shell,
            environment_variables=dict(os.environ)
        )
    
    def _detect_default_shell(self) -> Optional[str]:
        """Détecte le shell par défaut du système."""
        if not self.shell_detection:
            return None
        
        if sys.platform.startswith('win'):
            # Windows
            return os.environ.get('COMSPEC', 'cmd.exe')
        else:
            # Unix
            return os.environ.get('SHELL', '/bin/bash')
    
    def validate_python_version(self, version: str, min_version: Tuple[int, int, int] = (3, 8, 0)) -> bool:
        """
        Valide qu'une version Python respecte les exigences minimales.
        
        Args:
            version: Version à valider (format "3.11.5")
            min_version: Version minimale requise
            
        Returns:
            bool: True si la version est valide
        """
        try:
            parts = version.split('.')
            if len(parts) < 3:
                return False
            
            version_tuple = tuple(int(part) for part in parts[:3])
            return version_tuple >= min_version
            
        except (ValueError, TypeError):
            return False
    
    def which(self, command: str) -> Optional[Path]:
        """
        Trouve l'emplacement d'une commande dans le PATH.
        
        Args:
            command: Nom de la commande
            
        Returns:
            Optional[Path]: Chemin de la commande ou None
        """
        result = shutil.which(command)
        return Path(result) if result else None
    
    def is_admin(self) -> bool:
        """
        Vérifie si le processus actuel a des privilèges administrateur.
        
        Returns:
            bool: True si administrateur
        """
        try:
            if sys.platform.startswith('win'):
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False