"""
Backend PDM pour GestVenv - Gestionnaire moderne avec support PEP 582.

PDM (Python Dependency Manager) est un gestionnaire de dépendances moderne
qui implémente PEP 582 (__pypackages__) et PEP 621 (métadonnées projet).
Il offre une gestion avancée des dépendances avec des performances optimisées.

Caractéristiques:
- Support PEP 582 (__pypackages__ directory)
- Support pyproject.toml natif avec PEP 621
- Génération automatique pdm.lock
- Installation rapide avec cache intelligent
- Support des groupes de dépendances
- Gestion des scripts et hooks
- Compatible avec environnements virtuels classiques
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base_backend import PackageBackend, BackendCapabilities, InstallResult


class PdmBackend(PackageBackend):
    """
    Backend PDM - Gestionnaire moderne avec PEP 582 et PEP 621.
    
    Ce backend utilise PDM pour toutes les opérations et offre une
    approche moderne de la gestion des dépendances Python avec support
    des standards PEP les plus récents.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._pdm_version = None
        self._pdm_executable = None
    
    @property
    def name(self) -> str:
        """Nom du backend."""
        return "pdm"
    
    @property
    def capabilities(self) -> BackendCapabilities:
        """Capacités du backend PDM."""
        return BackendCapabilities(
            supports_requirements_txt=True,  # Via export et import
            supports_pyproject_toml=True,
            supports_lock_files=True,
            supports_dependency_groups=True,
            supports_editable_installs=True,
            supports_parallel_installs=True,
            supports_offline_mode=True,
            supports_caching=True,
            supports_incremental_installs=True,
            can_create_environments=True,
            preferred_venv_tool="pdm"
        )
    
    @property
    def version(self) -> Optional[str]:
        """Version de PDM."""
        if self._pdm_version is None:
            self._pdm_version = self._detect_pdm_version()
        return self._pdm_version
    
    def _detect_pdm_version(self) -> Optional[str]:
        """Détecte la version de PDM."""
        pdm_cmd = self._find_pdm_executable()
        if not pdm_cmd:
            return None
        
        try:
            returncode, stdout, _ = self._run_command([pdm_cmd, "--version"])
            if returncode == 0:
                # Format: "PDM, version 2.10.4" ou "pdm 2.10.4"
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+)', stdout)
                if version_match:
                    return version_match.group(1)
            return "unknown"
        except Exception:
            return None
    
    def _find_pdm_executable(self) -> Optional[str]:
        """Trouve l'exécutable PDM."""
        if self._pdm_executable is None:
            # Chercher pdm dans le PATH
            pdm_path = shutil.which("pdm")
            if pdm_path:
                self._pdm_executable = pdm_path
            else:
                # Essayer des emplacements communs
                common_paths = [
                    Path.home() / ".local" / "bin" / "pdm",
                    Path("/usr/local/bin/pdm"),
                    Path("/opt/homebrew/bin/pdm"),
                ]
                
                if os.name == 'nt':  # Windows
                    common_paths.extend([
                        Path.home() / "AppData" / "Roaming" / "Python" / "Scripts" / "pdm.exe",
                        Path("C:") / "Program Files" / "Python" / "Scripts" / "pdm.exe",
                    ])
                
                for path in common_paths:
                    if path.exists():
                        self._pdm_executable = str(path)
                        break
        
        return self._pdm_executable
    
    def is_available(self) -> bool:
        """Vérifie si PDM est disponible."""
        pdm_cmd = self._find_pdm_executable()
        if not pdm_cmd:
            return False
        
        try:
            returncode, _, _ = self._run_command([pdm_cmd, "--version"], timeout=10)
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
        Crée un environnement avec PDM.
        
        PDM peut utiliser des environnements virtuels classiques ou PEP 582.
        
        Args:
            name: Nom de l'environnement
            python_version: Version Python (ex: "3.11")
            path: Chemin où créer l'environnement
            **kwargs: Options PDM
                - use_pep582: bool = False (utiliser __pypackages__)
                - backend: str = "venv" (venv, virtualenv)
        """
        start_time = time.time()
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            # PDM fonctionne avec des projets, créer un projet minimal si nécessaire
            project_dir = path.parent
            if not (project_dir / "pyproject.toml").exists():
                init_result = self._initialize_pdm_project(project_dir, name, python_version)
                if not init_result.success:
                    return init_result
            
            # Choix du mode: PEP 582 ou venv classique
            if kwargs.get("use_pep582", False):
                # Configuration PEP 582
                result = self._setup_pep582_environment(project_dir, python_version)
            else:
                # Environnement virtuel classique
                result = self._setup_venv_environment(project_dir, path, python_version, **kwargs)
            
            if result.success:
                result.message = f"PDM environment '{name}' created successfully"
                result.execution_time = time.time() - start_time
            
            return result
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error creating PDM environment: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def _initialize_pdm_project(self, project_dir: Path, name: str, python_version: str) -> InstallResult:
        """Initialise un projet PDM minimal."""
        pdm_cmd = self._find_pdm_executable()
        
        try:
            # Créer le répertoire du projet
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialiser le projet PDM
            cmd = [pdm_cmd, "init", "--non-interactive"]
            
            if python_version and python_version != "python":
                # Normaliser la version Python
                if python_version.startswith("python"):
                    python_version = python_version.replace("python", "")
                
                cmd.extend(["--python", python_version])
            
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                # Personnaliser le pyproject.toml avec le nom correct
                self._customize_pyproject_toml(project_dir, name)
                
                return InstallResult(
                    success=True,
                    message=f"PDM project initialized: {project_dir}",
                    backend_used=self.name
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Failed to initialize PDM project: {stderr}",
                    backend_used=self.name
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Error initializing PDM project: {e}",
                backend_used=self.name
            )
    
    def _customize_pyproject_toml(self, project_dir: Path, name: str):
        """Personnalise le pyproject.toml généré."""
        pyproject_path = project_dir / "pyproject.toml"
        if not pyproject_path.exists():
            return
        
        try:
            # Lire le contenu actuel
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remplacer le nom par défaut
            content = content.replace('name = ""', f'name = "{name}"')
            content = content.replace('name = "untitled"', f'name = "{name}"')
            
            # Écrire le contenu modifié
            with open(pyproject_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        except Exception as e:
            self._logger.warning(f"Failed to customize pyproject.toml: {e}")
    
    def _setup_pep582_environment(self, project_dir: Path, python_version: str) -> InstallResult:
        """Configure un environnement PEP 582 (__pypackages__)."""
        pdm_cmd = self._find_pdm_executable()
        
        try:
            # Configurer PDM pour utiliser PEP 582
            cmd = [pdm_cmd, "config", "python.use_venv", "false"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode != 0:
                return InstallResult(
                    success=False,
                    message=f"Failed to configure PEP 582: {stderr}",
                    backend_used=self.name
                )
            
            # Installer les dépendances de base (créera __pypackages__)
            cmd = [pdm_cmd, "install", "--no-lock"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message="PEP 582 environment configured",
                    backend_used=self.name,
                    warnings=["Using PEP 582 (__pypackages__) instead of virtual environment"]
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Failed to setup PEP 582 environment: {stderr}",
                    backend_used=self.name
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Error setting up PEP 582: {e}",
                backend_used=self.name
            )
    
    def _setup_venv_environment(self, project_dir: Path, venv_path: Path, python_version: str, **kwargs) -> InstallResult:
        """Configure un environnement virtuel classique."""
        pdm_cmd = self._find_pdm_executable()
        
        try:
            # Configurer PDM pour utiliser venv
            cmd = [pdm_cmd, "config", "python.use_venv", "true"]
            returncode, _, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode != 0:
                self._logger.warning(f"Failed to configure venv mode: {stderr}")
            
            # Créer l'environnement virtuel
            cmd = [pdm_cmd, "venv", "create"]
            
            if python_version and python_version != "python":
                python_cmd = self._resolve_python_command(python_version)
                if python_cmd:
                    cmd.extend(["--python", python_cmd])
            
            # Backend de création (venv par défaut)
            backend = kwargs.get("backend", "venv")
            if backend != "venv":
                cmd.extend(["--backend", backend])
            
            # Nom de l'environnement
            cmd.append(str(venv_path.name))
            
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                # Lier l'environnement au projet
                use_cmd = [pdm_cmd, "use", str(venv_path)]
                use_returncode, _, use_stderr = self._run_command(use_cmd, cwd=project_dir)
                
                if use_returncode != 0:
                    self._logger.warning(f"Failed to link venv to project: {use_stderr}")
                
                return InstallResult(
                    success=True,
                    message="Virtual environment created and linked",
                    backend_used=self.name
                )
            else:
                # Fallback: créer avec venv standard puis configurer PDM
                return self._create_venv_fallback(project_dir, venv_path, python_version)
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Error setting up venv: {e}",
                backend_used=self.name
            )
    
    def _create_venv_fallback(self, project_dir: Path, venv_path: Path, python_version: str) -> InstallResult:
        """Fallback: créer venv standard puis configurer PDM."""
        try:
            import subprocess
            
            python_cmd = self._resolve_python_command(python_version)
            if not python_cmd:
                return InstallResult(
                    success=False,
                    message=f"Python version '{python_version}' not found",
                    backend_used=self.name
                )
            
            # Créer avec venv standard
            cmd = [python_cmd, "-m", "venv", str(venv_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                # Configurer PDM pour utiliser cet environnement
                pdm_cmd = self._find_pdm_executable()
                use_cmd = [pdm_cmd, "use", str(venv_path)]
                use_result = subprocess.run(use_cmd, capture_output=True, text=True, cwd=project_dir)
                
                return InstallResult(
                    success=True,
                    message="Environment created with venv fallback and linked to PDM",
                    backend_used=self.name,
                    warnings=["Used venv fallback instead of pdm venv"]
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Fallback venv creation failed: {result.stderr}",
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
        Installe des packages avec PDM.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            packages: Liste des packages à installer
            **kwargs: Options PDM
                - group: str = None (groupe de dépendances: dev, test, etc.)
                - dev: bool = False (ajouter au groupe dev)
                - optional: bool = False (dépendance optionnelle)
                - editable: bool = False (installation éditable)
                - dry_run: bool = False (simulation)
        """
        if not packages:
            return InstallResult(
                success=True,
                message="No packages to install",
                backend_used=self.name
            )
        
        start_time = time.time()
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            # Déterminer le répertoire du projet
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return InstallResult(
                    success=False,
                    message="No PDM project found",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande pdm add
            cmd = [pdm_cmd, "add"]
            
            # Options de groupe
            if kwargs.get("dev", False):
                cmd.extend(["--group", "dev"])
            elif kwargs.get("group"):
                cmd.extend(["--group", kwargs["group"]])
            
            # Options d'installation
            if kwargs.get("editable", False):
                cmd.append("--editable")
            
            if kwargs.get("dry_run", False):
                cmd.append("--dry-run")
            
            # Ajouter les packages
            cmd.extend(packages)
            
            # Exécuter l'installation
            self._logger.info(f"Installing packages with PDM: {', '.join(packages)}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                # PDM ajoute automatiquement au pyproject.toml et met à jour pdm.lock
                installed = self._parse_pdm_add_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully installed {len(installed)} packages with PDM",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"PDM installation failed: {stderr}",
                    packages_failed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during PDM installation: {e}",
                packages_failed=packages,
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def uninstall_packages(self, 
                          env_path: Path, 
                          packages: List[str],
                          **kwargs) -> InstallResult:
        """
        Désinstalle des packages avec PDM.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            packages: Liste des packages à désinstaller
            **kwargs: Options PDM
                - group: str = None (groupe spécifique)
                - dry_run: bool = False (simulation)
        """
        if not packages:
            return InstallResult(
                success=True,
                message="No packages to uninstall",
                backend_used=self.name
            )
        
        start_time = time.time()
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return InstallResult(
                    success=False,
                    message="No PDM project found",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande pdm remove
            cmd = [pdm_cmd, "remove"]
            
            # Options de groupe
            if kwargs.get("group"):
                cmd.extend(["--group", kwargs["group"]])
            
            if kwargs.get("dry_run", False):
                cmd.append("--dry-run")
            
            cmd.extend(packages)
            
            # Exécuter la désinstallation
            self._logger.info(f"Removing packages with PDM: {', '.join(packages)}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Successfully removed {len(packages)} packages with PDM",
                    packages_installed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"PDM removal failed: {stderr}",
                    packages_failed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during PDM removal: {e}",
                packages_failed=packages,
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def update_packages(self, 
                       env_path: Path, 
                       packages: Optional[List[str]] = None,
                       **kwargs) -> InstallResult:
        """
        Met à jour des packages avec PDM.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            packages: Liste des packages à mettre à jour (None = tous)
            **kwargs: Options PDM
                - groups: List[str] = None (groupes à mettre à jour)
                - dry_run: bool = False (simulation)
        """
        start_time = time.time()
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return InstallResult(
                    success=False,
                    message="No PDM project found",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Construire la commande pdm update
            cmd = [pdm_cmd, "update"]
            
            # Si des packages spécifiques sont demandés
            if packages:
                cmd.extend(packages)
            
            # Options de groupes
            if kwargs.get("groups"):
                for group in kwargs["groups"]:
                    cmd.extend(["--group", group])
            
            if kwargs.get("dry_run", False):
                cmd.append("--dry-run")
            
            # Exécuter la mise à jour
            self._logger.info(f"Updating packages with PDM: {packages or 'all packages'}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                updated = self._parse_pdm_update_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully updated packages with PDM",
                    packages_installed=updated,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"PDM update failed: {stderr}",
                    packages_failed=packages or [],
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during PDM update: {e}",
                packages_failed=packages or [],
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def get_installed_packages(self, env_path: Path) -> List[Dict[str, str]]:
        """
        Liste les packages installés avec PDM.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            
        Returns:
            Liste de dictionnaires {name, version, source, group}
        """
        pdm_cmd = self._find_pdm_executable()
        if not pdm_cmd:
            return []
        
        try:
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return []
            
            cmd = [pdm_cmd, "list", "--json"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                import json
                packages_data = json.loads(stdout)
                
                result = []
                for pkg in packages_data:
                    result.append({
                        "name": pkg["name"],
                        "version": pkg["version"],
                        "source": "pdm",
                        "group": pkg.get("group", "main"),
                        "editable": pkg.get("editable", False),
                        "summary": pkg.get("summary", "")
                    })
                
                return result
            else:
                # Fallback: utiliser list simple
                return self._get_packages_simple(pdm_cmd, project_dir)
        
        except Exception as e:
            self._logger.error(f"Error listing packages with PDM: {e}")
            return []
    
    def _get_packages_simple(self, pdm_cmd: str, project_dir: Path) -> List[Dict[str, str]]:
        """Fallback pour lister les packages sans JSON."""
        try:
            cmd = [pdm_cmd, "list"]
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                packages = []
                for line in stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('-') and not line.startswith('Package'):
                        parts = line.split()
                        if len(parts) >= 2:
                            packages.append({
                                "name": parts[0],
                                "version": parts[1],
                                "source": "pdm"
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
        Synchronise depuis requirements.txt en l'important dans PDM.
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            requirements_path: Chemin vers requirements.txt
            **kwargs: Options PDM
                - group: str = None (groupe de destination)
        """
        start_time = time.time()
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            project_dir = self._find_project_directory(env_path)
            if not project_dir:
                return InstallResult(
                    success=False,
                    message="No PDM project found",
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
            
            # Construire la commande pdm import
            cmd = [pdm_cmd, "import", str(requirements_path)]
            
            # Options de groupe
            if kwargs.get("group"):
                cmd.extend(["--group", kwargs["group"]])
            
            self._logger.info(f"Importing requirements file with PDM: {requirements_path}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                # Installer après import
                install_cmd = [pdm_cmd, "install"]
                install_returncode, install_stdout, install_stderr = self._run_command(install_cmd, cwd=project_dir)
                
                if install_returncode == 0:
                    imported = self._parse_pdm_install_output(install_stdout)
                    
                    return InstallResult(
                        success=True,
                        message=f"Successfully imported and installed from {requirements_path.name}",
                        packages_installed=imported,
                        backend_used=self.name,
                        execution_time=time.time() - start_time
                    )
                else:
                    return InstallResult(
                        success=False,
                        message=f"Import succeeded but install failed: {install_stderr}",
                        backend_used=self.name,
                        execution_time=time.time() - start_time
                    )
            else:
                return InstallResult(
                    success=False,
                    message=f"PDM import failed: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during PDM import: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def sync_from_pyproject(self, 
                           env_path: Path, 
                           pyproject_path: Path,
                           groups: Optional[List[str]] = None,
                           **kwargs) -> InstallResult:
        """
        Synchronise depuis pyproject.toml avec PDM (support natif).
        
        Args:
            env_path: Chemin vers l'environnement virtuel (ou projet)
            pyproject_path: Chemin vers pyproject.toml
            groups: Groupes de dépendances à installer
            **kwargs: Options PDM
                - dev: bool = False (inclure dépendances dev)
                - sync: bool = True (synchroniser exactement)
                - dry_run: bool = False (simulation)
        """
        start_time = time.time()
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
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
            
            # Construire la commande pdm install
            if kwargs.get("sync", True):
                cmd = [pdm_cmd, "sync"]
            else:
                cmd = [pdm_cmd, "install"]
            
            # Gestion des groupes
            if groups:
                if "dev" in groups:
                    cmd.append("--dev")
                    groups = [g for g in groups if g != "dev"]
                
                if groups:
                    for group in groups:
                        cmd.extend(["--group", group])
            elif kwargs.get("dev", False):
                cmd.append("--dev")
            else:
                cmd.append("--prod")
            
            if kwargs.get("dry_run", False):
                cmd.append("--dry-run")
            
            # Exécuter l'installation
            self._logger.info(f"Syncing from pyproject.toml with PDM: {pyproject_path}")
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_dir)
            
            if returncode == 0:
                installed = self._parse_pdm_install_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully synced from pyproject.toml with PDM",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"PDM sync failed: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during PDM pyproject sync: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    # ========== MÉTHODES UTILITAIRES ==========
    
    def _find_project_directory(self, env_path: Path) -> Optional[Path]:
        """
        Trouve le répertoire du projet PDM.
        
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
        
        # Si env_path semble être __pypackages__, chercher dans le parent
        if env_path.name == "__pypackages__":
            search_paths.insert(0, env_path.parent)
        
        for path in search_paths:
            if path.exists() and (path / "pyproject.toml").exists():
                # Vérifier que c'est bien un projet PDM
                if self._is_pdm_project(path):
                    return path
        
        return None
    
    def _is_pdm_project(self, project_dir: Path) -> bool:
        """Vérifie si un répertoire est un projet PDM."""
        pyproject_path = project_dir / "pyproject.toml"
        if not pyproject_path.exists():
            return False
        
        try:
            # Lire le pyproject.toml pour vérifier les sections PDM
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Rechercher des indices PDM
            pdm_indicators = [
                "[tool.pdm]",
                "pdm-backend",
                "__pypackages__",
                "pdm.lock"
            ]
            
            for indicator in pdm_indicators:
                if indicator in content:
                    return True
            
            # Vérifier la présence de pdm.lock
            if (project_dir / "pdm.lock").exists():
                return True
            
            return False
        
        except Exception:
            return False
    
    def _parse_pdm_add_output(self, output: str) -> List[str]:
        """Parse la sortie de pdm add."""
        packages = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if "Adding packages to" in line or "Installing" in line:
                # Format: "Adding packages to pyproject.toml..." ou "Installing package-name..."
                import re
                match = re.search(r'Installing\s+([a-zA-Z0-9\-_]+)', line)
                if match:
                    packages.append(match.group(1))
            elif line.startswith("+ "):
                # Format: "+ package-name==1.0.0"
                package_part = line[2:].split("==")[0].split(">=")[0].split("<=")[0]
                if package_part and package_part not in packages:
                    packages.append(package_part)
        
        return packages
    
    def _parse_pdm_update_output(self, output: str) -> List[str]:
        """Parse la sortie de pdm update."""
        packages = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if "Updating" in line or "Updated" in line:
                # Format: "Updating package-name (1.0.0 -> 1.1.0)"
                import re
                match = re.search(r'(?:Updating|Updated)\s+([a-zA-Z0-9\-_]+)', line)
                if match:
                    packages.append(match.group(1))
        
        return packages
    
    def _parse_pdm_install_output(self, output: str) -> List[str]:
        """Parse la sortie de pdm install/sync."""
        packages = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if ("Installing" in line or "Updated" in line) and "(" in line:
                import re
                match = re.search(r'(?:Installing|Updated)\s+([a-zA-Z0-9\-_]+)', line)
                if match:
                    packages.append(match.group(1))
        
        return packages
    
    def export_requirements(self, project_path: Path, output_path: Path, **kwargs) -> InstallResult:
        """
        Exporte les dépendances PDM vers requirements.txt.
        
        Args:
            project_path: Chemin vers le projet PDM
            output_path: Chemin de sortie pour requirements.txt
            **kwargs: Options d'export
                - groups: List[str] = None (groupes à inclure)
                - dev: bool = False (inclure dépendances dev)
                - without_hashes: bool = True (exclure les hashes)
        """
        start_time = time.time()
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
        
        try:
            # Construire la commande pdm export
            cmd = [pdm_cmd, "export"]
            
            # Options de format
            cmd.extend(["--format", "requirements"])
            
            if kwargs.get("dev", False):
                cmd.append("--dev")
            
            if kwargs.get("groups"):
                for group in kwargs["groups"]:
                    cmd.extend(["--group", group])
            
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
                    message=f"PDM export failed: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during PDM export: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def show_dependency_tree(self, project_path: Path) -> InstallResult:
        """
        Affiche l'arbre des dépendances PDM.
        
        Args:
            project_path: Chemin vers le projet PDM
            
        Returns:
            InstallResult avec l'arbre des dépendances dans le message
        """
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
                backend_used=self.name
            )
        
        try:
            cmd = [pdm_cmd, "list", "--graph"]
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
    
    def run_script(self, project_path: Path, script_name: str, args: List[str] = None) -> InstallResult:
        """
        Exécute un script PDM défini dans pyproject.toml.
        
        Args:
            project_path: Chemin vers le projet PDM
            script_name: Nom du script à exécuter
            args: Arguments à passer au script
            
        Returns:
            InstallResult avec le résultat de l'exécution
        """
        pdm_cmd = self._find_pdm_executable()
        
        if not pdm_cmd:
            return InstallResult(
                success=False,
                message="PDM executable not found",
                backend_used=self.name
            )
        
        try:
            cmd = [pdm_cmd, "run", script_name]
            if args:
                cmd.extend(args)
            
            returncode, stdout, stderr = self._run_command(cmd, cwd=project_path)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Script '{script_name}' executed successfully:\n{stdout}",
                    backend_used=self.name
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Script '{script_name}' failed: {stderr}",
                    backend_used=self.name
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Error running script: {e}",
                backend_used=self.name
            )