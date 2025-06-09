"""
Backend uv pour GestVenv - Gestionnaire de packages haute performance.

uv est un gestionnaire de packages Python ultra-rapide écrit en Rust,
compatible avec pip mais offrant des performances 5-10x supérieures.
Il supporte nativement pyproject.toml et génère des lock files pour
la reproductibilité.

Caractéristiques:
- Performances 5-10x supérieures à pip
- Support pyproject.toml natif avec PEP 621
- Génération automatique uv.lock
- Installation parallèle de packages
- Cache intelligent et mode offline
- Résolution de dépendances avancée
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base_backend import PackageBackend, BackendCapabilities, InstallResult


class UvBackend(PackageBackend):
    """
    Backend uv - Gestionnaire haute performance pour Python.
    
    Ce backend utilise uv pour toutes les opérations de packages, offrant
    des performances exceptionnelles et un support moderne des standards Python.
    """
    
    def __init__(self):
        super().__init__()
        self._uv_version = None
        self._uv_executable = None
    
    @property
    def name(self) -> str:
        """Nom du backend."""
        return "uv"
    
    @property
    def capabilities(self) -> BackendCapabilities:
        """Capacités du backend uv."""
        return BackendCapabilities(
            supports_requirements_txt=True,
            supports_pyproject_toml=True,
            supports_lock_files=True,
            supports_dependency_groups=True,
            supports_editable_installs=True,
            supports_parallel_installs=True,
            supports_offline_mode=True,
            supports_caching=True,
            supports_incremental_installs=True,
            can_create_environments=True,
            preferred_venv_tool="uv"
        )
    
    @property
    def version(self) -> Optional[str]:
        """Version de uv."""
        if self._uv_version is None:
            self._uv_version = self._detect_uv_version()
        return self._uv_version
    
    def _detect_uv_version(self) -> Optional[str]:
        """Détecte la version de uv."""
        uv_cmd = self._find_uv_executable()
        if not uv_cmd:
            return None
        
        try:
            returncode, stdout, _ = self._run_command([uv_cmd, "--version"])
            if returncode == 0:
                # Format: "uv 0.1.15"
                parts = stdout.strip().split()
                if len(parts) >= 2:
                    return parts[1]
            return "unknown"
        except Exception:
            return None
    
    def _find_uv_executable(self) -> Optional[str]:
        """Trouve l'exécutable uv."""
        if self._uv_executable is None:
            # Chercher uv dans le PATH
            uv_path = shutil.which("uv")
            if uv_path:
                self._uv_executable = uv_path
            else:
                # Essayer des emplacements communs
                common_paths = [
                    Path.home() / ".cargo" / "bin" / "uv",
                    Path("/usr/local/bin/uv"),
                    Path("/opt/homebrew/bin/uv"),
                ]
                
                for path in common_paths:
                    if path.exists():
                        self._uv_executable = str(path)
                        break
        
        return self._uv_executable
    
    def is_available(self) -> bool:
        """Vérifie si uv est disponible."""
        uv_cmd = self._find_uv_executable()
        if not uv_cmd:
            return False
        
        try:
            returncode, _, _ = self._run_command([uv_cmd, "--version"], timeout=10)
            return returncode == 0
        except Exception:
            return False
    
    # ========== GESTION DES ENVIRONNEMENTS ==========
    
    def create_environment(self, 
                          name: str, 
                          python_version: str, 
                          path: Path,
                          **kwargs) -> InstallResult:
        """
        Crée un environnement virtuel avec uv.
        
        Args:
            name: Nom de l'environnement
            python_version: Version Python (ex: "3.11", "python3.11")
            path: Chemin où créer l'environnement
            **kwargs: Options uv
                - seed: bool = True (installer pip, setuptools, wheel)
                - system_site_packages: bool = False
        """
        start_time = time.time()
        uv_cmd = self._find_uv_executable()
        
        if not uv_cmd:
            return InstallResult(
                success=False,
                message="uv executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            # Construire la commande uv venv
            cmd = [uv_cmd, "venv"]
            
            # Spécifier la version Python
            if python_version and python_version != "python":
                # Normaliser la version
                if not python_version.startswith("python"):
                    python_version = f"python{python_version}"
                cmd.extend(["--python", python_version])
            
            # Options
            if not kwargs.get("seed", True):
                cmd.append("--no-seed")
            
            if kwargs.get("system_site_packages", False):
                cmd.append("--system-site-packages")
            
            # Chemin de l'environnement
            cmd.append(str(path))
            
            # Créer l'environnement
            self._logger.info(f"Creating uv environment '{name}' at {path}")
            returncode, stdout, stderr = self._run_command(cmd)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"uv environment '{name}' created successfully",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                # Fallback: essayer avec python -m venv si uv venv échoue
                if "python version" in stderr.lower() or "not found" in stderr.lower():
                    self._logger.warning(f"uv venv failed, falling back to venv: {stderr}")
                    return self._create_with_venv_fallback(name, python_version, path, **kwargs)
                
                return InstallResult(
                    success=False,
                    message=f"Failed to create uv environment: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error creating uv environment: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def _create_with_venv_fallback(self, name: str, python_version: str, path: Path, **kwargs) -> InstallResult:
        """Fallback vers venv standard si uv venv échoue."""
        try:
            import subprocess
            
            python_cmd = self._resolve_python_command(python_version)
            if not python_cmd:
                return InstallResult(
                    success=False,
                    message=f"Python version '{python_version}' not found for fallback",
                    backend_used=self.name
                )
            
            cmd = [python_cmd, "-m", "venv", str(path)]
            
            if kwargs.get("system_site_packages", False):
                cmd.append("--system-site-packages")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Environment '{name}' created with venv fallback",
                    backend_used=self.name,
                    warnings=["Used venv fallback instead of uv venv"]
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Fallback creation failed: {result.stderr}",
                    backend_used=self.name
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Fallback creation error: {e}",
                backend_used=self.name
            )
    
    def _resolve_python_command(self, python_version: str) -> Optional[str]:
        """Résout la commande Python à utiliser."""
        candidates = []
        
        if python_version.startswith("python"):
            candidates.append(python_version)
        else:
            candidates.extend([
                f"python{python_version}",
                f"python{python_version.split('.')[0]}",
                "python3",
                "python"
            ])
        
        for cmd in candidates:
            try:
                returncode, _, _ = self._run_command([cmd, "--version"])
                if returncode == 0:
                    return cmd
            except Exception:
                continue
        
        return None
    
    # ========== GESTION DES PACKAGES ==========
    
    def install_packages(self, 
                        env_path: Path, 
                        packages: List[str],
                        **kwargs) -> InstallResult:
        """
        Installe des packages avec uv.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à installer
            **kwargs: Options uv
                - upgrade: bool = False
                - no_deps: bool = False
                - editable: bool = False
                - index_url: str = None
                - extra_index_url: str = None
                - offline: bool = False
                - no_cache: bool = False
        """
        if not packages:
            return InstallResult(
                success=True,
                message="No packages to install",
                backend_used=self.name
            )
        
        start_time = time.time()
        uv_cmd = self._find_uv_executable()
        
        if not uv_cmd:
            return InstallResult(
                success=False,
                message="uv executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            is_valid, error = self.validate_environment(env_path)
            if not is_valid:
                return InstallResult(
                    success=False,
                    message=error,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande uv pip install
            cmd = [uv_cmd, "pip", "install"]
            
            # Options
            if kwargs.get("upgrade", False):
                cmd.append("--upgrade")
            
            if kwargs.get("no_deps", False):
                cmd.append("--no-deps")
            
            if kwargs.get("offline", False):
                cmd.append("--offline")
            
            if kwargs.get("no_cache", False):
                cmd.append("--no-cache")
            
            # Index URLs
            if kwargs.get("index_url"):
                cmd.extend(["--index-url", kwargs["index_url"]])
            
            if kwargs.get("extra_index_url"):
                cmd.extend(["--extra-index-url", kwargs["extra_index_url"]])
            
            # Packages (gérer les packages editables)
            if kwargs.get("editable", False):
                for package in packages:
                    cmd.extend(["-e", package])
            else:
                cmd.extend(packages)
            
            # Exécuter dans l'environnement
            self._logger.info(f"Installing packages with uv: {', '.join(packages)}")
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                # Parser la sortie uv
                installed = self._parse_uv_install_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully installed {len(installed)} packages with uv",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"uv installation failed: {stderr}",
                    packages_failed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during uv installation: {e}",
                packages_failed=packages,
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def uninstall_packages(self, 
                          env_path: Path, 
                          packages: List[str],
                          **kwargs) -> InstallResult:
        """
        Désinstalle des packages avec uv.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à désinstaller
            **kwargs: Options uv
        """
        if not packages:
            return InstallResult(
                success=True,
                message="No packages to uninstall",
                backend_used=self.name
            )
        
        start_time = time.time()
        uv_cmd = self._find_uv_executable()
        
        if not uv_cmd:
            return InstallResult(
                success=False,
                message="uv executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            is_valid, error = self.validate_environment(env_path)
            if not is_valid:
                return InstallResult(
                    success=False,
                    message=error,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande uv pip uninstall
            cmd = [uv_cmd, "pip", "uninstall", "-y"]
            cmd.extend(packages)
            
            # Exécuter la désinstallation
            self._logger.info(f"Uninstalling packages with uv: {', '.join(packages)}")
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Successfully uninstalled {len(packages)} packages with uv",
                    packages_installed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"uv uninstallation failed: {stderr}",
                    packages_failed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during uv uninstallation: {e}",
                packages_failed=packages,
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def update_packages(self, 
                       env_path: Path, 
                       packages: Optional[List[str]] = None,
                       **kwargs) -> InstallResult:
        """
        Met à jour des packages avec uv.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à mettre à jour (None = tous)
            **kwargs: Options uv
        """
        start_time = time.time()
        
        try:
            is_valid, error = self.validate_environment(env_path)
            if not is_valid:
                return InstallResult(
                    success=False,
                    message=error,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Si aucun package spécifié, mettre à jour tous
            if packages is None:
                installed_packages = self.get_installed_packages(env_path)
                packages = [pkg["name"] for pkg in installed_packages if pkg["name"] not in ["pip", "setuptools", "wheel"]]
            
            if not packages:
                return InstallResult(
                    success=True,
                    message="No packages to update",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Utiliser install avec --upgrade
            return self.install_packages(env_path, packages, upgrade=True, **kwargs)
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during uv update: {e}",
                packages_failed=packages or [],
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def get_installed_packages(self, env_path: Path) -> List[Dict[str, str]]:
        """
        Liste les packages installés avec uv.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            Liste de dictionnaires {name, version, source}
        """
        uv_cmd = self._find_uv_executable()
        if not uv_cmd:
            return []
        
        try:
            is_valid, _ = self.validate_environment(env_path)
            if not is_valid:
                return []
            
            cmd = [uv_cmd, "pip", "list", "--format", "json"]
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                import json
                packages_data = json.loads(stdout)
                
                return [
                    {
                        "name": pkg["name"],
                        "version": pkg["version"],
                        "source": "uv",
                        "editable": pkg.get("editable_project_location") is not None
                    }
                    for pkg in packages_data
                ]
            else:
                self._logger.error(f"Failed to list packages with uv: {stderr}")
                return []
        
        except Exception as e:
            self._logger.error(f"Error listing packages with uv: {e}")
            return []
    
    # ========== GESTION DES FICHIERS PROJET ==========
    
    def sync_from_requirements(self, 
                              env_path: Path, 
                              requirements_path: Path,
                              **kwargs) -> InstallResult:
        """
        Synchronise depuis requirements.txt avec uv.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            requirements_path: Chemin vers requirements.txt
            **kwargs: Options uv
        """
        start_time = time.time()
        uv_cmd = self._find_uv_executable()
        
        if not uv_cmd:
            return InstallResult(
                success=False,
                message="uv executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            is_valid, error = self.validate_environment(env_path)
            if not is_valid:
                return InstallResult(
                    success=False,
                    message=error,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            if not requirements_path.exists():
                return InstallResult(
                    success=False,
                    message=f"Requirements file not found: {requirements_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande uv pip install
            cmd = [uv_cmd, "pip", "install", "-r", str(requirements_path)]
            
            # Options
            if kwargs.get("upgrade", False):
                cmd.append("--upgrade")
            
            if kwargs.get("offline", False):
                cmd.append("--offline")
            
            if kwargs.get("no_cache", False):
                cmd.append("--no-cache")
            
            self._logger.info(f"Syncing from requirements file with uv: {requirements_path}")
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                installed = self._parse_uv_install_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully synced from {requirements_path.name} with uv",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"uv sync failed: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during uv sync: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def sync_from_pyproject(self, 
                           env_path: Path, 
                           pyproject_path: Path,
                           groups: Optional[List[str]] = None,
                           **kwargs) -> InstallResult:
        """
        Synchronise depuis pyproject.toml avec uv (support natif).
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            pyproject_path: Chemin vers pyproject.toml
            groups: Groupes de dépendances à installer
            **kwargs: Options uv
                - dev: bool = False (installer dépendances dev)
                - all_extras: bool = False (installer tous les extras)
                - extras: List[str] = None (extras spécifiques)
        """
        start_time = time.time()
        uv_cmd = self._find_uv_executable()
        
        if not uv_cmd:
            return InstallResult(
                success=False,
                message="uv executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            is_valid, error = self.validate_environment(env_path)
            if not is_valid:
                return InstallResult(
                    success=False,
                    message=error,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            if not pyproject_path.exists():
                return InstallResult(
                    success=False,
                    message=f"pyproject.toml not found: {pyproject_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # uv supporte plusieurs approches pour pyproject.toml
            project_dir = pyproject_path.parent
            
            # Option 1: uv pip install avec le projet lui-même
            cmd = [uv_cmd, "pip", "install"]
            
            # Installer le projet en mode editable
            cmd.extend(["-e", str(project_dir)])
            
            # Gérer les groupes de dépendances
            if groups:
                for group in groups:
                    if group == "dev":
                        cmd.append("--dev")
                    else:
                        # Pour les autres groupes, on utilisera les extras
                        cmd.extend(["--extra", group])
            
            # Options extras
            if kwargs.get("dev", False):
                cmd.append("--dev")
            
            if kwargs.get("all_extras", False):
                cmd.append("--all-extras")
            
            if kwargs.get("extras"):
                for extra in kwargs["extras"]:
                    cmd.extend(["--extra", extra])
            
            # Options générales
            if kwargs.get("upgrade", False):
                cmd.append("--upgrade")
            
            if kwargs.get("offline", False):
                cmd.append("--offline")
            
            self._logger.info(f"Syncing from pyproject.toml with uv: {pyproject_path}")
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                installed = self._parse_uv_install_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully synced from pyproject.toml with uv",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                # Fallback: utiliser la conversion vers requirements
                self._logger.warning(f"uv sync failed, trying fallback: {stderr}")
                return self._sync_via_requirements_conversion(
                    env_path, pyproject_path, groups, **kwargs
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during uv pyproject sync: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    # ========== MÉTHODES UTILITAIRES ==========
    
    def _parse_uv_install_output(self, output: str) -> List[str]:
        """
        Parse la sortie de uv install pour extraire les packages installés.
        
        Args:
            output: Sortie de uv install
            
        Returns:
            Liste des noms de packages installés
        """
        packages = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # uv utilise des formats différents
            if "Installing" in line and "package" in line:
                # Format: "Installing 5 packages"
                continue
            elif line.startswith("+ "):
                # Format: "+ package-name==1.0.0"
                package_part = line[2:].split("==")[0].split(">=")[0].split("<=")[0]
                if package_part and package_part not in packages:
                    packages.append(package_part)
            elif "Installed" in line and len(line.split()) >= 2:
                # Format plus générique
                parts = line.split()
                for part in parts:
                    if part not in ["Installed", "packages:", "package"] and "-" in part:
                        package_name = part.split("==")[0].split(">=")[0].split("<=")[0]
                        if package_name and package_name not in packages:
                            packages.append(package_name)
        
        return packages
    
    def generate_lock_file(self, project_path: Path) -> InstallResult:
        """
        Génère un fichier uv.lock pour le projet.
        
        Args:
            project_path: Chemin vers le répertoire du projet
            
        Returns:
            InstallResult avec le résultat de la génération
        """
        start_time = time.time()
        uv_cmd = self._find_uv_executable()
        
        if not uv_cmd:
            return InstallResult(
                success=False,
                message="uv executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            pyproject_path = project_path / "pyproject.toml"
            if not pyproject_path.exists():
                return InstallResult(
                    success=False,
                    message=f"No pyproject.toml found in {project_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Générer le lock file avec uv lock
            cmd = [uv_cmd, "lock"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_path)
            
            if returncode == 0:
                lock_file = project_path / "uv.lock"
                
                return InstallResult(
                    success=True,
                    message=f"Lock file generated: {lock_file}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Failed to generate lock file: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error generating lock file: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def sync_from_lock_file(self, env_path: Path, lock_file_path: Path) -> InstallResult:
        """
        Synchronise depuis un fichier uv.lock.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            lock_file_path: Chemin vers uv.lock
            
        Returns:
            InstallResult avec le résultat de la synchronisation
        """
        start_time = time.time()
        uv_cmd = self._find_uv_executable()
        
        if not uv_cmd:
            return InstallResult(
                success=False,
                message="uv executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            if not lock_file_path.exists():
                return InstallResult(
                    success=False,
                    message=f"Lock file not found: {lock_file_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Synchroniser depuis le lock file
            cmd = [uv_cmd, "sync", "--frozen"]
            returncode, stdout, stderr = self._run_command(cmd, env_path, cwd=lock_file_path.parent)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Successfully synced from lock file",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Failed to sync from lock file: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error syncing from lock file: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def _run_command(self, cmd: List[str], env_path: Optional[Path] = None, cwd: Optional[Path] = None, timeout: int = 300) -> Tuple[int, str, str]:
        """Override pour supporter le paramètre cwd."""
        import subprocess
        import os
        
        env = os.environ.copy()
        
        # Configurer l'environnement virtuel si spécifié
        if env_path:
            if os.name == 'nt':  # Windows
                scripts_dir = env_path / "Scripts"
            else:  # Unix/Linux/macOS
                scripts_dir = env_path / "bin"
            
            if scripts_dir.exists():
                env["PATH"] = f"{scripts_dir}{os.pathsep}{env.get('PATH', '')}"
                env["VIRTUAL_ENV"] = str(env_path)
                if "PYTHONHOME" in env:
                    del env["PYTHONHOME"]
        
        try:
            self._logger.debug(f"Executing uv command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
                cwd=cwd or (env_path.parent if env_path else None)
            )
            
            self._logger.debug(f"uv command completed with return code: {result.returncode}")
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            error_msg = f"uv command timed out after {timeout} seconds: {' '.join(cmd)}"
            self._logger.error(error_msg)
            return 1, "", error_msg
        except Exception as e:
            error_msg = f"Failed to execute uv command: {e}"
            self._logger.error(error_msg)
            return 1, "", error_msg