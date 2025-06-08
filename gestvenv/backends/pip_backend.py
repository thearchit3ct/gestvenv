"""
Backend pip pour GestVenv.

Ce backend utilise pip comme gestionnaire de packages et constitue le backend
de référence et de fallback pour GestVenv. Il préserve toute la compatibilité
avec la version 1.0 et supporte les fonctionnalités classiques de pip.

Caractéristiques:
- Compatibilité 100% avec v1.0
- Support requirements.txt natif
- Gestion configuration pip (index-url, trusted-hosts)
- Backend de fallback garanti disponible
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base_backend import PackageBackend, BackendCapabilities, InstallResult


class PipBackend(PackageBackend):
    """
    Backend pip - Implementation de référence et fallback.
    
    Ce backend utilise pip pour toutes les opérations de packages et venv
    pour la création d'environnements virtuels. Il est garanti d'être
    disponible sur toute installation Python standard.
    """
    
    def __init__(self):
        super().__init__()
        self._pip_version = None
    
    @property
    def name(self) -> str:
        """Nom du backend."""
        return "pip"
    
    @property
    def capabilities(self) -> BackendCapabilities:
        """Capacités du backend pip."""
        return BackendCapabilities(
            supports_requirements_txt=True,
            supports_pyproject_toml=False,  # Via conversion seulement
            supports_lock_files=False,
            supports_dependency_groups=False,
            supports_editable_installs=True,
            supports_parallel_installs=False,
            supports_offline_mode=True,
            supports_caching=True,
            supports_incremental_installs=True,
            can_create_environments=True,
            preferred_venv_tool="venv"
        )
    
    @property
    def version(self) -> Optional[str]:
        """Version de pip."""
        if self._pip_version is None:
            self._pip_version = self._detect_pip_version()
        return self._pip_version
    
    def _detect_pip_version(self) -> Optional[str]:
        """Détecte la version de pip."""
        try:
            import pip
            return pip.__version__
        except ImportError:
            # Fallback: utiliser pip --version
            try:
                returncode, stdout, _ = self._run_command([sys.executable, "-m", "pip", "--version"])
                if returncode == 0:
                    # Format: "pip 23.0.1 from ..."
                    parts = stdout.strip().split()
                    if len(parts) >= 2:
                        return parts[1]
            except Exception:
                pass
        return "unknown"
    
    def is_available(self) -> bool:
        """Vérifie si pip est disponible."""
        try:
            # Tester import pip
            import pip
            return True
        except ImportError:
            # Fallback: tester pip en ligne de commande
            try:
                returncode, _, _ = self._run_command([sys.executable, "-m", "pip", "--version"])
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
        Crée un environnement virtuel avec venv.
        
        Args:
            name: Nom de l'environnement
            python_version: Version Python (ex: "3.11", "python3.11")
            path: Chemin où créer l'environnement
            **kwargs: Options additionnelles
                - system_site_packages: bool = False
                - symlinks: bool = False (Unix seulement)
                - upgrade_deps: bool = True
        """
        start_time = time.time()
        
        try:
            # Préparer la commande
            python_cmd = self._resolve_python_command(python_version)
            if not python_cmd:
                return InstallResult(
                    success=False,
                    message=f"Python version '{python_version}' not found",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Options venv
            cmd = [python_cmd, "-m", "venv"]
            
            if kwargs.get("system_site_packages", False):
                cmd.append("--system-site-packages")
            
            if kwargs.get("symlinks", False) and os.name != 'nt':
                cmd.append("--symlinks")
            
            cmd.append(str(path))
            
            # Créer l'environnement
            self._logger.info(f"Creating environment '{name}' at {path}")
            returncode, stdout, stderr = self._run_command(cmd)
            
            if returncode != 0:
                return InstallResult(
                    success=False,
                    message=f"Failed to create environment: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Mettre à jour pip si demandé
            if kwargs.get("upgrade_deps", True):
                upgrade_result = self._upgrade_pip_in_environment(path)
                if not upgrade_result.success:
                    # Log warning mais continue
                    self._logger.warning(f"Failed to upgrade pip: {upgrade_result.message}")
            
            return InstallResult(
                success=True,
                message=f"Environment '{name}' created successfully",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error creating environment: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def _resolve_python_command(self, python_version: str) -> Optional[str]:
        """
        Résout la commande Python à utiliser.
        
        Args:
            python_version: Version demandée ("3.11", "python3.11", "python")
            
        Returns:
            Commande Python résolue ou None si non trouvée
        """
        # Candidats possibles
        candidates = []
        
        if python_version.startswith("python"):
            candidates.append(python_version)
        else:
            # Ajouter les variantes
            candidates.extend([
                f"python{python_version}",
                f"python{python_version.split('.')[0]}",
                "python",
                "python3"
            ])
        
        # Tester chaque candidat
        for cmd in candidates:
            try:
                returncode, stdout, _ = self._run_command([cmd, "--version"])
                if returncode == 0:
                    # Vérifier que la version correspond
                    if python_version in ["python", "python3"] or python_version in stdout:
                        return cmd
            except Exception:
                continue
        
        return None
    
    def _upgrade_pip_in_environment(self, env_path: Path) -> InstallResult:
        """Met à jour pip dans l'environnement."""
        cmd = [self._get_python_executable(env_path), "-m", "pip", "install", "--upgrade", "pip"]
        returncode, stdout, stderr = self._run_command(cmd, env_path)
        
        return InstallResult(
            success=returncode == 0,
            message=stderr if returncode != 0 else "pip upgraded successfully",
            backend_used=self.name
        )
    
    # ========== GESTION DES PACKAGES ==========
    
    def install_packages(self, 
                        env_path: Path, 
                        packages: List[str],
                        **kwargs) -> InstallResult:
        """
        Installe des packages avec pip.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à installer
            **kwargs: Options pip
                - upgrade: bool = False
                - no_deps: bool = False
                - editable: bool = False (pour packages locaux)
                - index_url: str = None
                - extra_index_url: str = None
                - trusted_host: List[str] = None
                - no_cache_dir: bool = False
        """
        if not packages:
            return InstallResult(
                success=True,
                message="No packages to install",
                backend_used=self.name
            )
        
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
            
            # Construire la commande pip
            cmd = [self._get_python_executable(env_path), "-m", "pip", "install"]
            
            # Options
            if kwargs.get("upgrade", False):
                cmd.append("--upgrade")
            
            if kwargs.get("no_deps", False):
                cmd.append("--no-deps")
            
            if kwargs.get("no_cache_dir", False):
                cmd.append("--no-cache-dir")
            
            # Index URLs
            if kwargs.get("index_url"):
                cmd.extend(["--index-url", kwargs["index_url"]])
            
            if kwargs.get("extra_index_url"):
                cmd.extend(["--extra-index-url", kwargs["extra_index_url"]])
            
            # Trusted hosts
            if kwargs.get("trusted_host"):
                for host in kwargs["trusted_host"]:
                    cmd.extend(["--trusted-host", host])
            
            # Packages (gérer les packages editables)
            if kwargs.get("editable", False):
                for package in packages:
                    cmd.extend(["-e", package])
            else:
                cmd.extend(packages)
            
            # Exécuter l'installation
            self._logger.info(f"Installing packages: {', '.join(packages)}")
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                # Extraire les packages installés du output
                installed = self._parse_pip_install_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully installed {len(installed)} packages",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Installation failed: {stderr}",
                    packages_failed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during installation: {e}",
                packages_failed=packages,
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def uninstall_packages(self, 
                          env_path: Path, 
                          packages: List[str],
                          **kwargs) -> InstallResult:
        """
        Désinstalle des packages avec pip.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à désinstaller
            **kwargs: Options pip
                - yes: bool = True (répondre oui automatiquement)
        """
        if not packages:
            return InstallResult(
                success=True,
                message="No packages to uninstall",
                backend_used=self.name
            )
        
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
            
            # Construire la commande
            cmd = [self._get_python_executable(env_path), "-m", "pip", "uninstall"]
            
            if kwargs.get("yes", True):
                cmd.append("-y")
            
            cmd.extend(packages)
            
            # Exécuter la désinstallation
            self._logger.info(f"Uninstalling packages: {', '.join(packages)}")
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                return InstallResult(
                    success=True,
                    message=f"Successfully uninstalled {len(packages)} packages",
                    packages_installed=packages,  # Packages "traités" avec succès
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Uninstallation failed: {stderr}",
                    packages_failed=packages,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during uninstallation: {e}",
                packages_failed=packages,
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def update_packages(self, 
                       env_path: Path, 
                       packages: Optional[List[str]] = None,
                       **kwargs) -> InstallResult:
        """
        Met à jour des packages avec pip.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à mettre à jour (None = tous)
            **kwargs: Options pip
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
            
            # Si aucun package spécifié, mettre à jour tous les packages
            if packages is None:
                installed_packages = self.get_installed_packages(env_path)
                packages = [pkg["name"] for pkg in installed_packages if pkg["name"] not in ["pip", "setuptools"]]
            
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
                message=f"Unexpected error during update: {e}",
                packages_failed=packages or [],
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    def get_installed_packages(self, env_path: Path) -> List[Dict[str, str]]:
        """
        Liste les packages installés avec pip list.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            Liste de dictionnaires {name, version, source}
        """
        try:
            is_valid, _ = self.validate_environment(env_path)
            if not is_valid:
                return []
            
            cmd = [self._get_python_executable(env_path), "-m", "pip", "list", "--format=json"]
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                import json
                packages_data = json.loads(stdout)
                
                return [
                    {
                        "name": pkg["name"],
                        "version": pkg["version"],
                        "source": "pip",
                        "editable": pkg.get("editable_project_location") is not None
                    }
                    for pkg in packages_data
                ]
            else:
                self._logger.error(f"Failed to list packages: {stderr}")
                return []
        
        except Exception as e:
            self._logger.error(f"Error listing packages: {e}")
            return []
    
    # ========== GESTION DES FICHIERS PROJET ==========
    
    def sync_from_requirements(self, 
                              env_path: Path, 
                              requirements_path: Path,
                              **kwargs) -> InstallResult:
        """
        Synchronise depuis requirements.txt.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            requirements_path: Chemin vers requirements.txt
            **kwargs: Options pip
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
            
            if not requirements_path.exists():
                return InstallResult(
                    success=False,
                    message=f"Requirements file not found: {requirements_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            
            # Installer depuis requirements.txt
            cmd = [
                self._get_python_executable(env_path), 
                "-m", "pip", "install", 
                "-r", str(requirements_path)
            ]
            
            # Ajouter options
            if kwargs.get("upgrade", False):
                cmd.append("--upgrade")
            
            if kwargs.get("no_cache_dir", False):
                cmd.append("--no-cache-dir")
            
            self._logger.info(f"Syncing from requirements file: {requirements_path}")
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                installed = self._parse_pip_install_output(stdout)
                
                return InstallResult(
                    success=True,
                    message=f"Successfully synced from {requirements_path.name}",
                    packages_installed=installed,
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Sync failed: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during sync: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )
    
    # ========== MÉTHODES UTILITAIRES ==========
    
    def _get_python_executable(self, env_path: Path) -> str:
        """Retourne le chemin vers l'exécutable Python de l'environnement."""
        if os.name == 'nt':  # Windows
            return str(env_path / "Scripts" / "python.exe")
        else:  # Unix/Linux/macOS
            return str(env_path / "bin" / "python")
    
    def _parse_pip_install_output(self, output: str) -> List[str]:
        """
        Parse la sortie de pip install pour extraire les packages installés.
        
        Args:
            output: Sortie de pip install
            
        Returns:
            Liste des noms de packages installés
        """
        packages = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            # Rechercher les lignes "Successfully installed ..."
            if line.startswith("Successfully installed"):
                # Format: "Successfully installed package1-1.0.0 package2-2.0.0"
                parts = line.split("Successfully installed")[1].strip().split()
                for part in parts:
                    # Extraire le nom du package (avant le dernier tiret)
                    package_name = part.rsplit('-', 1)[0]
                    if package_name:
                        packages.append(package_name)
            
            # Aussi chercher les lignes individuelles de packages
            elif "Installing collected packages:" in line:
                continue
            elif line.startswith("  ") and not line.startswith("  "):
                # Package individuel dans la liste
                package_name = line.strip().split()[0]
                if package_name and package_name not in packages:
                    packages.append(package_name)
        
        return packages
    
    def export_requirements(self, env_path: Path, output_path: Path) -> InstallResult:
        """
        Exporte les packages installés vers requirements.txt.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            output_path: Chemin de sortie pour requirements.txt
            
        Returns:
            InstallResult avec le résultat de l'export
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
            
            cmd = [self._get_python_executable(env_path), "-m", "pip", "freeze"]
            returncode, stdout, stderr = self._run_command(cmd, env_path)
            
            if returncode == 0:
                # Écrire le fichier requirements.txt
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(stdout)
                
                # Compter les packages
                package_count = len([line for line in stdout.split('\n') if line.strip() and not line.startswith('#')])
                
                return InstallResult(
                    success=True,
                    message=f"Exported {package_count} packages to {output_path}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Export failed: {stderr}",
                    backend_used=self.name,
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Unexpected error during export: {e}",
                backend_used=self.name,
                execution_time=time.time() - start_time
            )