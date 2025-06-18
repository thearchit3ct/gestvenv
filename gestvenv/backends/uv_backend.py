"""
Backend uv pour GestVenv v1.1 - Performance optimisée
"""

import json
import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .base import PackageBackend, BackendCapabilities
from ..core.models import PackageInfo, InstallResult

logger = logging.getLogger(__name__)


class UvBackend(PackageBackend):
    """Backend uv pour performance maximale"""
    
    def __init__(self):
        super().__init__()
        self._name = "uv"
        
    def _init_capabilities(self) -> BackendCapabilities:
        """Initialise les capacités uv"""
        return BackendCapabilities(
            supports_lock_files=True,
            supports_dependency_groups=True,
            supports_parallel_install=True,
            supports_editable_installs=True,
            supports_workspace=True,
            supports_pyproject_sync=True,
            supported_formats=["pyproject.toml", "requirements.txt", "uv.lock"],
            max_parallel_jobs=4
        )
        
    def _check_availability(self) -> bool:
        """Vérifie la disponibilité d'uv"""
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
            
    def _get_version(self) -> Optional[str]:
        """Récupère la version uv"""
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                match = re.search(r'uv (\d+\.\d+\.\d+)', result.stdout)
                return match.group(1) if match else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
        
    def create_environment(self, path: Path, python_version: str) -> bool:
        """Création ultra-rapide avec uv venv"""
        try:
            cmd = ["uv", "venv", str(path), "--python", python_version]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur création environnement uv: {e}")
            return False
            
    def install_package(self, env_path: Path, package: str, **kwargs) -> InstallResult:
        """Installation optimisée avec uv pip install"""
        start_time = time.time()
        
        try:
            if not self.validate_package_spec(package):
                return InstallResult(
                    success=False,
                    message=f"Spécification package invalide: {package}",
                    execution_time=time.time() - start_time
                )
                
            cmd = ["uv", "pip", "install", "--python", str(self._get_python_executable(env_path))]
            
            if kwargs.get('upgrade', False):
                cmd.append("--upgrade")
                
            if kwargs.get('editable', False):
                cmd.append("--editable")
                
            cmd.append(package)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=kwargs.get('timeout', 180)
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Package {package} installé avec succès",
                    packages_installed=[package],
                    backend_used="uv",
                    execution_time=execution_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Erreur installation: {result.stderr}",
                    packages_failed=[package],
                    backend_used="uv",
                    execution_time=execution_time
                )
                
        except subprocess.TimeoutExpired:
            return InstallResult(
                success=False,
                message="Timeout lors de l'installation",
                packages_failed=[package],
                backend_used="uv",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Erreur installation: {e}",
                packages_failed=[package],
                backend_used="uv",
                execution_time=time.time() - start_time
            )
            
    def uninstall_package(self, env_path: Path, package: str) -> bool:
        """Désinstalle un package"""
        try:
            result = subprocess.run(
                ["uv", "pip", "uninstall", "--python", str(self._get_python_executable(env_path)), package],
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
            result = subprocess.run(
                ["uv", "pip", "install", "--upgrade", "--python", str(self._get_python_executable(env_path)), package],
                capture_output=True,
                text=True,
                timeout=180
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erreur mise à jour {package}: {e}")
            return False
            
    def list_packages(self, env_path: Path) -> List[PackageInfo]:
        """Liste les packages installés"""
        try:
            result = subprocess.run(
                ["uv", "pip", "list", "--format", "json", "--python", str(self._get_python_executable(env_path))],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return []
                
            packages_data = json.loads(result.stdout)
            
            packages = []
            for pkg_data in packages_data:
                packages.append(PackageInfo(
                    name=pkg_data["name"],
                    version=pkg_data["version"],
                    source="pypi",
                    backend_used="uv",
                    installed_at=datetime.now()
                ))
                
            return packages
            
        except Exception as e:
            logger.error(f"Erreur listage packages: {e}")
            return []
            
    def sync_from_pyproject(self, env_path: Path, pyproject_path: Path, groups: Optional[List[str]] = None) -> bool:
        """Synchronisation native depuis pyproject.toml"""
        try:
            cmd = ["uv", "pip", "sync", "--python", str(self._get_python_executable(env_path))]
            
            if groups:
                for group in groups:
                    cmd.extend(["--extra", group])
                    
            # uv nécessite un requirements.txt ou pyproject.toml
            # Si pyproject.toml, uv peut le lire directement
            cmd.append(str(pyproject_path))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur sync pyproject: {e}")
            return False
            
    def create_lock_file(self, pyproject_path: Path) -> Optional[Path]:
        """Génération de uv.lock"""
        try:
            lock_path = pyproject_path.parent / "uv.lock"
            
            result = subprocess.run(
                ["uv", "lock", "--project", str(pyproject_path.parent)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and lock_path.exists():
                return lock_path
                
        except Exception as e:
            logger.error(f"Erreur création lock file: {e}")
            
        return None
        
    def install_from_lock(self, env_path: Path, lock_path: Path) -> bool:
        """Installation depuis uv.lock"""
        try:
            result = subprocess.run(
                ["uv", "pip", "install", "--python", str(self._get_python_executable(env_path)), 
                 "--requirement", str(lock_path)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur installation lock: {e}")
            return False
            
    def install_from_requirements(self, env_path: Path, req_path: Path) -> bool:
        """Installation depuis requirements.txt"""
        try:
            result = subprocess.run(
                ["uv", "pip", "install", "--python", str(self._get_python_executable(env_path)),
                 "--requirement", str(req_path)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erreur installation requirements: {e}")
            return False
            
    def get_performance_score(self) -> int:
        """Score de performance uv"""
        return 9  # Très haute performance
        
    # Méthodes privées
    
    def _get_python_executable(self, env_path: Path) -> Path:
        """Exécutable Python de l'environnement"""
        if env_path.name == "Scripts" or env_path.name == "bin":
            # Si on passe directement le répertoire bin/Scripts
            python_name = "python.exe" if env_path.name == "Scripts" else "python"
            return env_path / python_name
        else:
            # Chemin complet vers l'environnement
            if (env_path / "Scripts").exists():
                return env_path / "Scripts" / "python.exe"
            else:
                return env_path / "bin" / "python"