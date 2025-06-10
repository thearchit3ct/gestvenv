"""
Backend pip pour GestVenv v1.1
"""

import logging
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .base import PackageBackend, BackendCapabilities
from ..core.models import PackageInfo, InstallResult
from ..core.exceptions import BackendError, PackageInstallationError

logger = logging.getLogger(__name__)


class PipBackend(PackageBackend):
    """Backend pip classique et compatible"""
    
    def __init__(self):
        super().__init__()
        self._name = "pip"
        
    def _init_capabilities(self) -> BackendCapabilities:
        """Initialise les capacités pip"""
        return BackendCapabilities(
            supports_lock_files=False,
            supports_dependency_groups=False,
            supports_parallel_install=False,
            supports_editable_installs=True,
            supports_workspace=False,
            supports_pyproject_sync=False,
            supported_formats=["requirements.txt", "wheel", "sdist"],
            max_parallel_jobs=1
        )
        
    def _check_availability(self) -> bool:
        """Vérifie la disponibilité de pip"""
        try:
            result = subprocess.run(
                ["pip", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
            
    def _get_version(self) -> Optional[str]:
        """Récupère la version pip"""
        try:
            result = subprocess.run(
                ["pip", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                match = re.search(r'pip (\d+\.\d+\.\d+)', result.stdout)
                return match.group(1) if match else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
        
    def create_environment(self, path: Path, python_version: str) -> bool:
        """Crée un environnement avec venv standard"""
        try:
            python_cmd = self._find_python_executable(python_version)
            if not python_cmd:
                return False
                
            result = subprocess.run(
                [python_cmd, "-m", "venv", str(path)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur création environnement pip: {e}")
            return False
            
    def install_package(self, env_path: Path, package: str, **kwargs) -> InstallResult:
        """Installation avec pip"""
        start_time = time.time()
        
        try:
            if not self.validate_package_spec(package):
                return InstallResult(
                    success=False,
                    message=f"Spécification package invalide: {package}",
                    execution_time=time.time() - start_time
                )
                
            pip_exe = self._get_pip_executable(env_path)
            if not pip_exe.exists():
                return InstallResult(
                    success=False,
                    message="pip non trouvé dans l'environnement",
                    execution_time=time.time() - start_time
                )
                
            cmd = [str(pip_exe), "install"]
            
            # Options
            if kwargs.get('upgrade', False):
                cmd.append("--upgrade")
                
            if kwargs.get('editable', False):
                cmd.append("--editable")
                
            if kwargs.get('no_deps', False):
                cmd.append("--no-deps")
                
            cmd.append(package)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=kwargs.get('timeout', 300)
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Package {package} installé avec succès",
                    packages_installed=[package],
                    backend_used="pip",
                    execution_time=execution_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Erreur installation: {result.stderr}",
                    packages_failed=[package],
                    backend_used="pip",
                    execution_time=execution_time
                )
                
        except subprocess.TimeoutExpired:
            return InstallResult(
                success=False,
                message="Timeout lors de l'installation",
                packages_failed=[package],
                backend_used="pip",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Erreur installation: {e}",
                packages_failed=[package],
                backend_used="pip",
                execution_time=time.time() - start_time
            )
            
    def uninstall_package(self, env_path: Path, package: str) -> bool:
        """Désinstalle un package"""
        try:
            pip_exe = self._get_pip_executable(env_path)
            if not pip_exe.exists():
                return False
                
            result = subprocess.run(
                [str(pip_exe), "uninstall", "-y", package],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur désinstallation {package}: {e}")
            return False
            
    def update_package(self, env_path: Path, package: str) -> bool:
        """Met à jour un package"""
        try:
            pip_exe = self._get_pip_executable(env_path)
            if not pip_exe.exists():
                return False
                
            result = subprocess.run(
                [str(pip_exe), "install", "--upgrade", package],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur mise à jour {package}: {e}")
            return False
            
    def list_packages(self, env_path: Path) -> List[PackageInfo]:
        """Liste les packages installés"""
        try:
            pip_exe = self._get_pip_executable(env_path)
            if not pip_exe.exists():
                return []
                
            # pip list avec format JSON
            result = subprocess.run(
                [str(pip_exe), "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return []
                
            import json
            packages_data = json.loads(result.stdout)
            
            packages = []
            for pkg_data in packages_data:
                packages.append(PackageInfo(
                    name=pkg_data["name"],
                    version=pkg_data["version"],
                    source="pypi",
                    backend_used="pip",
                    installed_at=datetime.now()
                ))
                
            return packages
            
        except Exception as e:
            logger.error(f"Erreur listage packages: {e}")
            return []
            
    def install_from_requirements(self, env_path: Path, req_path: Path) -> bool:
        """Installation depuis requirements.txt"""
        try:
            pip_exe = self._get_pip_executable(env_path)
            if not pip_exe.exists() or not req_path.exists():
                return False
                
            result = subprocess.run(
                [str(pip_exe), "install", "-r", str(req_path)],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur installation requirements: {e}")
            return False
            
    def freeze_requirements(self, env_path: Path) -> str:
        """Génère requirements.txt depuis l'environnement"""
        try:
            pip_exe = self._get_pip_executable(env_path)
            if not pip_exe.exists():
                return ""
                
            result = subprocess.run(
                [str(pip_exe), "freeze"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.stdout if result.returncode == 0 else ""
            
        except Exception as e:
            logger.error(f"Erreur freeze: {e}")
            return ""
            
    def get_performance_score(self) -> int:
        """Score de performance pip"""
        return 5  # Référence baseline
        
    # Méthodes privées
    
    def _get_pip_executable(self, env_path: Path) -> Path:
        """Exécutable pip de l'environnement"""
        if os.name == 'nt':
            return env_path / "Scripts" / "pip.exe"
        else:
            return env_path / "bin" / "pip"
            
    def _find_python_executable(self, version: str) -> Optional[str]:
        """Trouve l'exécutable Python pour une version"""
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
                if result.returncode == 0 and version in result.stdout:
                    return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        return None