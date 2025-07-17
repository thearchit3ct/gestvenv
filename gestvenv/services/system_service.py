"""
Service système pour GestVenv v1.1
"""

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.models import CommandResult
from ..core.exceptions import ValidationError

import logging
logger = logging.getLogger(__name__)


class SystemService:
    """Service d'intégration système et commandes"""
    
    def detect_python_versions(self) -> List[str]:
        """Détecte les versions Python disponibles"""
        versions = []
        
        # Commandes à tester
        commands = [
            'python3.13', 'python3.12', 'python3.11', 'python3.10', 'python3.9',
            'python3', 'python'
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(
                    [cmd, '--version'], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if result.returncode == 0:
                    version_output = result.stdout.strip()
                    match = re.search(r'Python (\d+\.\d+\.\d+)', version_output)
                    if match:
                        full_version = match.group(1)
                        short_version = '.'.join(full_version.split('.')[:2])
                        if short_version not in versions:
                            versions.append(short_version)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return sorted(versions, reverse=True)
    
    def validate_python_version(self, version: str) -> bool:
        """Valide une version Python"""
        if not re.match(r'^\d+\.\d+', version):
            return False
        
        try:
            major, minor = map(int, version.split('.')[:2])
            return major >= 3 and (major > 3 or minor >= 9)
        except ValueError:
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Informations système"""
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "home_directory": str(Path.home()),
            "current_directory": str(Path.cwd())
        }
    
    def check_backend_availability(self) -> Dict[str, bool]:
        """Vérifie la disponibilité des backends"""
        backends = {}
        
        # pip (toujours disponible avec Python)
        backends['pip'] = self._check_command_availability('pip')
        
        # uv
        backends['uv'] = self._check_command_availability('uv')
        
        # poetry
        backends['poetry'] = self._check_command_availability('poetry')
        
        # pdm
        backends['pdm'] = self._check_command_availability('pdm')
        
        return backends
    
    def get_activation_script(self, env_path: Path) -> Path:
        """Script d'activation pour un environnement"""
        if os.name == 'nt':  # Windows
            return env_path / "Scripts" / "activate.bat"
        else:  # Unix/Linux/macOS
            return env_path / "bin" / "activate"
    
    def detect_python_version(self, env_path: Path) -> str:
        """Détecte la version Python d'un environnement"""
        try:
            # Lecture pyvenv.cfg
            pyvenv_cfg = env_path / "pyvenv.cfg"
            if pyvenv_cfg.exists():
                content = pyvenv_cfg.read_text(encoding='utf-8')
                for line in content.split('\n'):
                    if line.startswith('version'):
                        version = line.split('=')[1].strip()
                        parts = version.split('.')
                        if len(parts) >= 2:
                            return f"{parts[0]}.{parts[1]}"
            
            # Fallback: exécution directe
            python_exe = self._get_python_executable(env_path)
            if python_exe.exists():
                result = subprocess.run(
                    [str(python_exe), '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    match = re.search(r'Python (\d+\.\d+)', result.stdout)
                    if match:
                        return match.group(1)
            
            return "3.11"  # Défaut
            
        except Exception as e:
            logger.error(f"Erreur détection version Python: {e}")
            return "3.11"
    
    def execute_command(
        self, 
        cmd: List[str], 
        env_path: Optional[Path] = None, 
        **kwargs
    ) -> CommandResult:
        """Exécute une commande avec sécurisation"""
        start_time = time.time()
        
        try:
            # Validation commande
            if not cmd or not cmd[0]:
                return CommandResult(
                    return_code=1,
                    stdout="",
                    stderr="Commande vide",
                    execution_time=0.0,
                    success=False
                )
            
            # Environnement sécurisé
            env = self._create_secure_environment(env_path) if env_path else None
            
            # Exécution avec timeout
            timeout = kwargs.get('timeout', 300)  # 5 minutes par défaut
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=env_path or Path.cwd(),
                **{k: v for k, v in kwargs.items() if k != 'timeout'}
            )
            
            execution_time = time.time() - start_time
            
            return CommandResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                success=result.returncode == 0
            )
            
        except subprocess.TimeoutExpired:
            return CommandResult(
                return_code=124,
                stdout="",
                stderr="Timeout de la commande",
                execution_time=time.time() - start_time,
                success=False
            )
        except Exception as e:
            return CommandResult(
                return_code=1,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
                success=False,
                error=e
            )
    
    def get_platform_info(self) -> Dict[str, str]:
        """Informations plateforme"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            platform_tag = f"win_{machine}"
        elif system == "darwin":
            platform_tag = f"macosx_{machine}"
        else:
            platform_tag = f"linux_{machine}"
        
        return {
            "system": system,
            "machine": machine,
            "platform_tag": platform_tag,
            "is_windows": system == "windows",
            "is_macos": system == "darwin",
            "is_linux": system == "linux"
        }
    
    def check_permissions(self, path: Path) -> bool:
        """Vérifie les permissions sur un chemin"""
        try:
            if not path.exists():
                # Vérifier le parent
                return self.check_permissions(path.parent) if path.parent != path else False
            
            # Test lecture/écriture
            return os.access(path, os.R_OK | os.W_OK)
        except Exception:
            return False
    
    def create_virtual_environment(self, path: Path, python_version: str) -> bool:
        """Crée un environnement virtuel avec venv"""
        try:
            # Recherche exécutable Python
            python_cmd = self._find_python_executable(python_version)
            if not python_cmd:
                return False
            
            # Création avec venv
            result = subprocess.run(
                [python_cmd, '-m', 'venv', str(path)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur création environnement virtuel: {e}")
            return False
    
    # Méthodes privées
    
    def _check_command_availability(self, command: str) -> bool:
        """Vérifie la disponibilité d'une commande"""
        try:
            result = subprocess.run(
                [command, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _get_python_executable(self, env_path: Path) -> Path:
        """Exécutable Python d'un environnement"""
        if os.name == 'nt':
            return env_path / "Scripts" / "python.exe"
        else:
            return env_path / "bin" / "python"
    
    def _find_python_executable(self, version: str) -> Optional[str]:
        """Trouve l'exécutable Python pour une version"""
        # Commandes possibles
        candidates = [
            f'python{version}',
            f'python{version.split(".")[0]}.{version.split(".")[1]}',
            'python3',
            'python'
        ]
        
        for cmd in candidates:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Vérifier que la version correspond
                    if version in result.stdout:
                        return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return None
    
    def _create_secure_environment(self, env_path: Path) -> Dict[str, str]:
        """Crée un environnement sécurisé pour l'exécution"""
        # Variables de base
        secure_env = {}
        
        # Variables système essentielles
        essential_vars = ['HOME', 'USER', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR', 'TEMP']
        for var in essential_vars:
            if var in os.environ:
                secure_env[var] = os.environ[var]
        
        # Configuration environnement virtuel
        if env_path:
            if os.name == 'nt':
                scripts_dir = env_path / "Scripts"
                secure_env['PATH'] = f"{scripts_dir};{os.environ.get('PATH', '')}"
            else:
                bin_dir = env_path / "bin"
                secure_env['PATH'] = f"{bin_dir}:{os.environ.get('PATH', '')}"
            
            secure_env['VIRTUAL_ENV'] = str(env_path)
            secure_env['PYTHONHOME'] = ''
            secure_env['PYTHONPATH'] = ''
        else:
            secure_env['PATH'] = os.environ.get('PATH', '')
        
        return secure_env