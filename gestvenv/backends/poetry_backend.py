"""
Backend Poetry pour GestVenv - Support complet de l'écosystème Poetry.

Poetry est un gestionnaire de dépendances et d'environnements Python moderne
qui utilise pyproject.toml comme fichier de configuration principal et génère
poetry.lock pour assurer la reproductibilité des installations.

Caractéristiques:
- Gestion complète poetry.lock
- Support groupes de dépendances Poetry
- Intégration build system
- Gestion des environnements virtuels Poetry
- Support des scripts et plugins Poetry
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base_backend import PackageBackend, BackendCapabilities, InstallResult


class PoetryBackend(PackageBackend):
    """
    Backend Poetry - Gestionnaire moderne avec pyproject.toml natif.
    
    Ce backend utilise Poetry pour toutes les opérations et offre une
    intégration complète avec l'écosystème Poetry, incluant la gestion
    des groupes de dépendances et des lock files.
    """
    
    def __init__(self):
        super().__init__()
        self._poetry_version = None
        self._poetry_executable = None
    
    @property
    def name(self) -> str:
        """Nom du backend."""
        return "poetry"
    
    @property
    def capabilities(self) -> BackendCapabilities:
        """Capacités du backend Poetry."""
        return BackendCapabilities(
            supports_requirements_txt=True,  # Via export
            supports_pyproject_toml=True,
            supports_lock_files=True,
            supports_dependency_groups=True,
            supports_editable_installs=True,
            supports_parallel_installs=True,
            supports_offline_mode=True,
            supports_caching=True,
            supports_incremental_installs=True,
            can_create_environments=True,
            preferred_venv_tool="poetry"
        )
    
    @property
    def version(self) -> Optional[str]:
        """Version de Poetry."""
        if self._poetry_version is None:
            self._poetry_version = self._detect_poetry_version()
        return self._poetry_version
    
    def _detect_poetry_version(self) -> Optional[str]:
        """Détecte la version de Poetry."""
        poetry_cmd = self._find_poetry_executable()
        if not poetry_cmd:
            return None
        
        try:
            returncode, stdout, _ = self._run_command([poetry_cmd, "--version"])
            if returncode == 0:
                # Format: "Poetry (version 1.6.1)" ou "Poetry version 1.6.1"
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+)', stdout)
                if version_match:
                    return version_match.group(1)
            return "unknown"
        except Exception:
            return None
    
    def _find_poetry_executable(self) -> Optional[str]:
        """Trouve l'exécutable Poetry."""
        if self._poetry_executable is None:
            # Chercher poetry dans le PATH
            poetry_path = shutil.which("poetry")
            if poetry_path:
                self._poetry_executable = poetry_path
            else:
                # Essayer des emplacements communs
                common_paths = [
                    Path.home() / ".local" / "bin" / "poetry",
                    Path.home() / ".poetry" / "bin" / "poetry",
                    Path("/usr/local/bin/poetry"),
                    Path("/opt/homebrew/bin/poetry"),
                ]
                
                if os.name == 'nt':  # Windows
                    common_paths.extend([
                        Path.home() / "AppData" / "Roaming" / "Python" / "Scripts" / "poetry.exe",
                        Path("C:") / "Program Files" / "Poetry" / "bin" / "poetry.exe",
                    ])
                
                for path in common_paths:
                    if path.exists():
                        self._poetry_executable = str(path)
                        break
        
        return self._poetry_executable
    
    def is_available(self) -> bool:
        """Vérifie si Poetry est disponible."""
        poetry_cmd = self._find_poetry_executable()
        if not poetry_cmd:
            return False
        
        try:
            returncode, _, _ = self._run_command([poetry_cmd, "--version"], timeout=10)
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
        Crée un environnement virtuel avec Poetry.
        
        Poetry gère ses propres environnements virtuels, cette méthode
        configure Poetry pour utiliser un environnement à l'emplacement spécifié.
        
        Args:
            name: Nom de l'environnement
            python_version: Version Python (ex: "3.11")
            path: Chemin où créer l'environnement
            **kwargs: Options Poetry
                - in_project: bool = True (créer .venv dans le projet)
        """
        start_time = time.time()
        poetry_cmd = self._find_poetry_executable()
        
        if not poetry_cmd:
            return InstallResult(
                success=False,
                message="Poetry executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            # Poetry fonctionne différemment - il gère ses propres venvs
            # On va créer un projet Poetry minimal si nécessaire
            
            project_dir = path.parent
            if not (project_dir / "pyproject.toml").exists():
                # Créer un projet Poetry minimal
                create_result = self._create_poetry_project(project_dir, name, python_version)
                if not create_result.success:
                    return create_result
            
            # Configurer Poetry pour utiliser Python spécifique
            if python_version and python_version != "python":
                python_cmd = self._resolve_python_command(python_version)
                if python_cmd:
                    cmd = [poetry_cmd, "env", "use", python_cmd]
                    returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
                    
                    if returncode != 0:
                        self._logger.warning(f"Failed to set Python version: {stderr}")
            
            # Créer l'environnement Poetry
            cmd = [poetry_cmd, "install", "--no-root"]
            
            # Configurer pour créer .venv dans le projet si demandé
            if kwargs.get("in_project", True):
                env = os.environ.copy()
                env["POETRY_VENV_IN_PROJECT"] = "true"
                returncode, stdout, stderr = self._run_command_with_env(cmd, project_dir, env)
            else:
                returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                # Vérifier que l'environnement a été créé
                venv_path = self._find_poetry_venv_path(project_dir)
                if venv_path and venv_path.exists():
                    return InstallResult(
                        success=True,
                        message=f"Poetry environment '{name}' created successfully at {venv_path}",
                        backend_used=self.name,
                        execution_time=time.time() - start_time
                    )
                else:
                    return InstallResult(
                        success=True,
                        message=f"Poetry environment '{name}' created (managed by Poetry)",
                        backend_used=self.name,
                        execution_time=time.time() - start_time,
                        warnings=["Environment path managed by Poetry"]
                    )
            else:
                return InstallResult(
                    success=False,
                    message=f"Failed to create Poetry environment: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error creating Poetry environment: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def _create_poetry_project(self, project_dir: Path, name: str, python_version: str) -> InstallResult:
        """Crée un projet Poetry minimal."""
        poetry_cmd = self._find_poetry_executable()
        
        try:
            # Créer le répertoire du projet
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialiser le projet Poetry
            cmd = [poetry_cmd, "init", "--no-interaction", "--name", name]
            
            if python_version and python_version != "python":
                # Normaliser la version Python pour Poetry
                if python_version.startswith("python"):
                    python_version = python_version.replace("python", "")
                
                # Poetry accepte des formats comme "^3.11"
                if not python_version.startswith("^") and not python_version.startswith(">="):
                    python_version = f"^{python_version}"
                
                cmd.extend(["--python", python_version])
            
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Poetry project initialized: {project_dir}",
                    backend_used=self.name
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Failed to initialize Poetry project: {stderr}",
                    backend_used=self.name
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Error creating Poetry project: {e}",
                backend_used=self.name
            )
    
    def _find_poetry_venv_path(self, project_dir: Path) -> Optional[Path]:
        """Trouve le chemin de l'environnement virtuel Poetry."""
        poetry_cmd = self._find_poetry_executable()
        if not poetry_cmd:
            return None
        
        try:
            cmd = [poetry_cmd, "env", "info", "--path"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                venv_path = Path(stdout.strip())
                if venv_path.exists():
                    return venv_path
            
            # Fallback: chercher .venv dans le projet
            local_venv = project_dir / ".venv"
            if local_venv.exists():
                return local_venv
        
        except Exception:
            pass
        
        return None
    
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
        Installe des packages avec Poetry.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            packages: Liste des packages à installer
            **kwargs: Options Poetry
                - group: str = None (groupe de dépendances)
                - dev: bool = False (ajouter au groupe dev)
                - optional: bool = False (dépendance optionnelle)
        """
        if not packages:
            return InstallResult(
                success=True,
                message="No packages to install",
                backend_used=self.name
            )
        
        start_time = time.time()
        poetry_cmd = self._find_poetry_executable()
        
        if not poetry_cmd:
            return InstallResult(
                success=False,
                message="Poetry executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            # Déterminer le répertoire du projet
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return InstallResult(
                    success=False,
                    message="No Poetry project found",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande poetry add
            cmd = [poetry_cmd, "add"]
            
            # Options de groupe
            if kwargs.get("dev", False):
                cmd.append("--group=dev")
            elif kwargs.get("group"):
                cmd.append(f"--group={kwargs['group']}")
            
            if kwargs.get("optional", False):
                cmd.append("--optional")
            
            # Ajouter les packages
            cmd.extend(packages)
            
            # Exécuter l'installation
            self._logger.info(f"Installing packages with Poetry: {', '.join(packages)}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                # Poetry ajoute automatiquement au pyproject.toml et met à jour poetry.lock
                installed = self._parse_poetry_add_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully installed {len(installed)} packages with Poetry",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Poetry installation failed: {stderr}",
                    packages_failed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during Poetry installation: {e}",
                packages_failed=packages,
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def uninstall_packages(self, 
                          env_path: Path, 
                          packages: List[str],
                          **kwargs) -> InstallResult:
        """
        Désinstalle des packages avec Poetry.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            packages: Liste des packages à désinstaller
            **kwargs: Options Poetry
                - group: str = None (groupe spécifique)
        """
        if not packages:
            return InstallResult(
                success=True,
                message="No packages to uninstall",
                backend_used=self.name
            )
        
        start_time = time.time()
        poetry_cmd = self._find_poetry_executable()
        
        if not poetry_cmd:
            return InstallResult(
                success=False,
                message="Poetry executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return InstallResult(
                    success=False,
                    message="No Poetry project found",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande poetry remove
            cmd = [poetry_cmd, "remove"]
            
            # Options de groupe
            if kwargs.get("group"):
                cmd.append(f"--group={kwargs['group']}")
            
            cmd.extend(packages)
            
            # Exécuter la désinstallation
            self._logger.info(f"Removing packages with Poetry: {', '.join(packages)}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Successfully removed {len(packages)} packages with Poetry",
                    packages_installed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Poetry removal failed: {stderr}",
                    packages_failed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during Poetry removal: {e}",
                packages_failed=packages,
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def update_packages(self, 
                       env_path: Path, 
                       packages: Optional[List[str]] = None,
                       **kwargs) -> InstallResult:
        """
        Met à jour des packages avec Poetry.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            packages: Liste des packages à mettre à jour (None = tous)
            **kwargs: Options Poetry
        """
        start_time = time.time()
        poetry_cmd = self._find_poetry_executable()
        
        if not poetry_cmd:
            return InstallResult(
                success=False,
                message="Poetry executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return InstallResult(
                    success=False,
                    message="No Poetry project found",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande poetry update
            cmd = [poetry_cmd, "update"]
            
            # Si des packages spécifiques sont demandés
            if packages:
                cmd.extend(packages)
            
            # Exécuter la mise à jour
            self._logger.info(f"Updating packages with Poetry: {packages or 'all packages'}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                updated = self._parse_poetry_update_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully updated packages with Poetry",
                    packages_installed=updated,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Poetry update failed: {stderr}",
                    packages_failed=packages or [],
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during Poetry update: {e}",
                packages_failed=packages or [],
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def get_installed_packages(self, env_path: Path) -> List[Dict[str, str]]:
        """
        Liste les packages installés avec Poetry.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            
        Returns:
            Liste de dictionnaires {name, version, source}
        """
        poetry_cmd = self._find_poetry_executable()
        if not poetry_cmd:
            return []
        
        try:
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return []
            
            cmd = [poetry_cmd, "show", "--no-dev", "--format", "json"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                import json
                packages_data = json.loads(stdout)
                
                result = []
                for pkg in packages_data:
                    result.append({
                        "name": pkg["name"],
                        "version": pkg["version"],
                        "source": "poetry",
                        "category": pkg.get("category", "main"),
                        "description": pkg.get("description", "")
                    })
                
                return result
            else:
                # Fallback: utiliser show simple
                return self._get_packages_simple(poetry_cmd, project_dir)
        
        except Exception as e:
            self._logger.error(f"Error listing packages with Poetry: {e}")
            return []
    
    def _get_packages_simple(self, poetry_cmd: str, project_dir: Path) -> List[Dict[str, str]]:
        """Fallback pour lister les packages sans JSON."""
        try:
            cmd = [poetry_cmd, "show"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                packages = []
                for line in stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('-'):
                        parts = line.split()
                        if len(parts) >= 2:
                            packages.append({
                                "name": parts[0],
                                "version": parts[1],
                                "source": "poetry"
                            })
                return packages
        
        except Exception:
            pass
        
        return []
    
    # ========== GESTION DES FICHIERS PROJET ==========
    
    def sync_from_requirements(self, 
                              env_path: Path, 
                              requirements_path: Path,
                              **kwargs) -> InstallResult:
        """
        Synchronise depuis requirements.txt en l'important dans Poetry.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            requirements_path: Chemin vers requirements.txt
            **kwargs: Options Poetry
        """
        start_time = time.time()
        
        try:
            # Lire le fichier requirements.txt
            if not requirements_path.exists():
                return InstallResult(
                    success=False,
                    message=f"Requirements file not found: {requirements_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            with open(requirements_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Parser les packages
            packages = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    packages.append(line)
            
            if not packages:
                return InstallResult(
                    success=True,
                    message="No packages found in requirements.txt",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Installer les packages avec Poetry
            return self.install_packages(env_path, packages, **kwargs)
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during requirements sync: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def sync_from_pyproject(self, 
                           env_path: Path, 
                           pyproject_path: Path,
                           groups: Optional[List[str]] = None,
                           **kwargs) -> InstallResult:
        """
        Synchronise depuis pyproject.toml avec Poetry.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            pyproject_path: Chemin vers pyproject.toml
            groups: Groupes de dépendances à installer
            **kwargs: Options Poetry
                - with_dev: bool = False (inclure dépendances dev)
                - sync: bool = True (synchroniser exactement)
        """
        start_time = time.time()
        poetry_cmd = self._find_poetry_executable()
        
        if not poetry_cmd:
            return InstallResult(
                success=False,
                message="Poetry executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            project_dir = pyproject_path.parent
            
            if not pyproject_path.exists():
                return InstallResult(
                    success=False,
                    message=f"pyproject.toml not found: {pyproject_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande poetry install
            cmd = [poetry_cmd, "install"]
            
            # Options de synchronisation
            if kwargs.get("sync", True):
                cmd.append("--sync")
            
            # Gestion des groupes
            if groups:
                if "dev" in groups:
                    cmd.append("--with=dev")
                    groups = [g for g in groups if g != "dev"]
                
                if groups:
                    cmd.append(f"--with={','.join(groups)}")
            elif kwargs.get("with_dev", False):
                cmd.append("--with=dev")
            else:
                cmd.append("--without=dev")
            
            # Exécuter l'installation
            self._logger.info(f"Syncing from pyproject.toml with Poetry: {pyproject_path}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                installed = self._parse_poetry_install_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully synced from pyproject.toml with Poetry",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Poetry sync failed: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during Poetry pyproject sync: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    # ========== MÉTHODES UTILITAIRES ==========
    
    def _find_project_directory(self, env_path: Path) -> Optional[Path]:
        """
        Trouve le répertoire du projet Poetry.
        
        Args:
            env_path: Chemin de départ pour la recherche
            
        Returns:
            Chemin vers le répertoire contenant pyproject.toml ou None
        """
        # Essayer plusieurs stratégies de recherche
        search_paths = [
            env_path,
            env_path.parent,
            env_path.parent.parent,
        ]
        
        # Si env_path semble être un .venv, chercher dans le parent
        if env_path.name == ".venv":
            search_paths.insert(0, env_path.parent)
        
        for path in search_paths:
            if path.exists() and (path / "pyproject.toml").exists():
                return path
        
        return None
    
    def _parse_poetry_add_output(self, output: str) -> List[str]:
        """Parse la sortie de poetry add."""
        packages = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if "Installing" in line and "(" in line:
                # Format: "Installing package-name (1.0.0)"
                import re
                match = re.search(r'Installing\s+([a-zA-Z0-9\-_]+)', line)
                if match:
                    packages.append(match.group(1))
        
        return packages
    
    def _parse_poetry_update_output(self, output: str) -> List[str]:
        """Parse la sortie de poetry update."""
        packages = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if "Updating" in line and "(" in line:
                # Format: "Updating package-name (1.0.0 -> 1.1.0)"
                import re
                match = re.search(r'Updating\s+([a-zA-Z0-9\-_]+)', line)
                if match:
                    packages.append(match.group(1))
        
        return packages
    
    def _parse_poetry_install_output(self, output: str) -> List[str]:
        """Parse la sortie de poetry install."""
        packages = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if ("Installing" in line or "Updating" in line) and "(" in line:
                import re
                match = re.search(r'(?:Installing|Updating)\s+([a-zA-Z0-9\-_]+)', line)
                if match:
                    packages.append(match.group(1))
        
        return packages
    
    def _run_command_with_env(self, cmd: List[str], cwd: Path, env: Dict[str, str], timeout: int = 300) -> Tuple[int, str, str]:
        """Exécute une commande avec un environnement personnalisé."""
        import subprocess
        
        try:
            self._logger.debug(f"Executing Poetry command with env: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
                cwd=cwd
            )
            
            self._logger.debug(f"Poetry command completed with return code: {result.returncode}")
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            error_msg = f"Poetry command timed out after {timeout} seconds: {' '.join(cmd)}"
            self._logger.error(error_msg)
            return 1, "", error_msg
        except Exception as e:
            error_msg = f"Failed to execute Poetry command: {e}"
            self._logger.error(error_msg)
            return 1, "", error_msg
    
    def export_requirements(self, project_path: Path, output_path: Path, **kwargs) -> InstallResult:
        """
        Exporte les dépendances Poetry vers requirements.txt.
        
        Args:
            project_path: Chemin vers le projet Poetry
            output_path: Chemin de sortie pour requirements.txt
            **kwargs: Options d'export
                - dev: bool = False (inclure dépendances dev)
                - without_hashes: bool = True (exclure les hashes)
        """
        start_time = time.time()
        poetry_cmd = self._find_poetry_executable()
        
        if not poetry_cmd:
            return InstallResult(
                success=False,
                message="Poetry executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            # Construire la commande poetry export
            cmd = [poetry_cmd, "export", "--format", "requirements.txt"]
            
            if kwargs.get("dev", False):
                cmd.append("--dev")
            
            if kwargs.get("without_hashes", True):
                cmd.append("--without-hashes")
            
            cmd.extend(["--output", str(output_path)])
            
            # Exécuter l'export
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_path)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Requirements exported to {output_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Poetry export failed: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during Poetry export: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def show_dependency_tree(self, project_path: Path) -> InstallResult:
        """
        Affiche l'arbre des dépendances Poetry.
        
        Args:
            project_path: Chemin vers le projet Poetry
            
        Returns:
            InstallResult avec l'arbre des dépendances dans le message
        """
        poetry_cmd = self._find_poetry_executable()
        
        if not poetry_cmd:
            return InstallResult(
                success=False,
                message="Poetry executable not found",
                backend_used=self.name
            )
        
        try:
            cmd = [poetry_cmd, "show", "--tree"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_path)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Dependency tree:\n{stdout}",
                    backend_used=self.name
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Failed to show dependency tree: {stderr}",
                    backend_used=self.name
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Error showing dependency tree: {e}",
                backend_used=self.name
            )