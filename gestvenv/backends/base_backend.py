"""
Interface abstraite pour tous les backends de packages Python.

Ce module définit l'interface commune que tous les backends (pip, uv, poetry, etc.)
doivent implémenter pour assurer une compatibilité et une utilisation uniforme
dans GestVenv.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Types de backends supportés."""
    PIP = "pip"
    UV = "uv"
    POETRY = "poetry"
    PDM = "pdm"
    CONDA = "conda"


@dataclass
class BackendCapabilities:
    """
    Capacités d'un backend de packages.
    
    Permet de définir quelles fonctionnalités sont supportées
    par chaque backend pour optimiser les opérations.
    """
    # Formats supportés
    supports_requirements_txt: bool = True
    supports_pyproject_toml: bool = False
    supports_lock_files: bool = False
    
    # Fonctionnalités avancées
    supports_dependency_groups: bool = False
    supports_editable_installs: bool = True
    supports_parallel_installs: bool = False
    supports_offline_mode: bool = False
    
    # Performance
    supports_caching: bool = True
    supports_incremental_installs: bool = False
    
    # Création d'environnements
    can_create_environments: bool = True
    preferred_venv_tool: str = "venv"  # venv, virtualenv, custom


@dataclass
class InstallResult:
    """
    Résultat d'une opération d'installation.
    
    Standardise les retours des opérations pour un traitement uniforme
    des succès, erreurs et avertissements.
    """
    success: bool
    message: str = ""
    packages_installed: List[str] = None
    packages_failed: List[str] = None
    warnings: List[str] = None
    execution_time: float = 0.0
    backend_used: str = ""
    
    def __post_init__(self):
        if self.packages_installed is None:
            self.packages_installed = []
        if self.packages_failed is None:
            self.packages_failed = []
        if self.warnings is None:
            self.warnings = []


class PackageBackend(ABC):
    """
    Interface abstraite pour tous les backends de gestion de packages.
    
    Cette classe définit l'interface commune que tous les backends doivent
    implémenter pour être utilisés dans GestVenv. Elle garantit une
    compatibilité et une utilisation uniforme entre pip, uv, poetry, etc.
    """
    
    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._version_cache = None
    
    # ========== PROPRIÉTÉS OBLIGATOIRES ==========
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom du backend (pip, uv, poetry, etc.)."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        """Capacités supportées par ce backend."""
        pass
    
    @property
    def version(self) -> Optional[str]:
        """
        Version du backend.
        
        Par défaut, tente de détecter automatiquement la version.
        Les backends peuvent override cette méthode pour une détection spécifique.
        """
        if self._version_cache is None:
            self._version_cache = self._detect_version()
        return self._version_cache
    
    # ========== MÉTHODES DE DISPONIBILITÉ ==========
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si le backend est disponible sur le système.
        
        Returns:
            True si le backend peut être utilisé, False sinon
        """
        pass
    
    def validate_environment(self, env_path: Path) -> Tuple[bool, str]:
        """
        Valide qu'un environnement est compatible avec ce backend.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            Tuple (is_valid, error_message)
        """
        if not env_path.exists():
            return False, f"Environment path does not exist: {env_path}"
        
        if not (env_path / "pyvenv.cfg").exists():
            return False, f"Not a valid Python virtual environment: {env_path}"
        
        return True, ""
    
    # ========== GESTION DES ENVIRONNEMENTS ==========
    
    @abstractmethod
    def create_environment(self, 
                          name: str, 
                          python_version: str, 
                          path: Path,
                          **kwargs) -> InstallResult:
        """
        Crée un nouvel environnement virtuel.
        
        Args:
            name: Nom de l'environnement
            python_version: Version Python à utiliser (ex: "3.11", "python3.11")
            path: Chemin où créer l'environnement
            **kwargs: Options spécifiques au backend
            
        Returns:
            InstallResult avec le résultat de la création
        """
        pass
    
    def delete_environment(self, env_path: Path) -> InstallResult:
        """
        Supprime un environnement virtuel.
        
        Args:
            env_path: Chemin vers l'environnement à supprimer
            
        Returns:
            InstallResult avec le résultat de la suppression
        """
        import shutil
        
        try:
            if env_path.exists():
                shutil.rmtree(env_path)
                return InstallResult(
                    success=True,
                    message=f"Environment deleted successfully: {env_path}",
                    backend_used=self.name
                )
            else:
                return InstallResult(
                    success=True,
                    message=f"Environment already deleted: {env_path}",
                    backend_used=self.name
                )
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Failed to delete environment: {e}",
                backend_used=self.name
            )
    
    # ========== GESTION DES PACKAGES ==========
    
    @abstractmethod
    def install_packages(self, 
                        env_path: Path, 
                        packages: List[str],
                        **kwargs) -> InstallResult:
        """
        Installe des packages dans l'environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à installer
            **kwargs: Options spécifiques (upgrade, no-deps, etc.)
            
        Returns:
            InstallResult avec le résultat de l'installation
        """
        pass
    
    @abstractmethod
    def uninstall_packages(self, 
                          env_path: Path, 
                          packages: List[str],
                          **kwargs) -> InstallResult:
        """
        Désinstalle des packages de l'environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à désinstaller
            **kwargs: Options spécifiques
            
        Returns:
            InstallResult avec le résultat de la désinstallation
        """
        pass
    
    @abstractmethod
    def update_packages(self, 
                       env_path: Path, 
                       packages: Optional[List[str]] = None,
                       **kwargs) -> InstallResult:
        """
        Met à jour des packages dans l'environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à mettre à jour (None = tous)
            **kwargs: Options spécifiques
            
        Returns:
            InstallResult avec le résultat de la mise à jour
        """
        pass
    
    @abstractmethod
    def get_installed_packages(self, env_path: Path) -> List[Dict[str, str]]:
        """
        Liste les packages installés dans l'environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            Liste de dictionnaires avec name, version, source pour chaque package
        """
        pass
    
    # ========== GESTION DES FICHIERS PROJET ==========
    
    @abstractmethod
    def sync_from_requirements(self, 
                              env_path: Path, 
                              requirements_path: Path,
                              **kwargs) -> InstallResult:
        """
        Synchronise l'environnement depuis un fichier requirements.txt.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            requirements_path: Chemin vers requirements.txt
            **kwargs: Options spécifiques
            
        Returns:
            InstallResult avec le résultat de la synchronisation
        """
        pass
    
    def sync_from_pyproject(self, 
                           env_path: Path, 
                           pyproject_path: Path,
                           groups: Optional[List[str]] = None,
                           **kwargs) -> InstallResult:
        """
        Synchronise l'environnement depuis pyproject.toml.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            pyproject_path: Chemin vers pyproject.toml
            groups: Groupes de dépendances à installer (ex: ["dev", "test"])
            **kwargs: Options spécifiques
            
        Returns:
            InstallResult avec le résultat de la synchronisation
        """
        if not self.capabilities.supports_pyproject_toml:
            # Fallback: conversion vers requirements.txt
            return self._sync_via_requirements_conversion(
                env_path, pyproject_path, groups, **kwargs
            )
        
        # Implémentation par défaut pour les backends qui ne supportent pas
        return InstallResult(
            success=False,
            message=f"Backend {self.name} does not support pyproject.toml synchronization",
            backend_used=self.name
        )
    
    # ========== MÉTHODES UTILITAIRES ==========
    
    def _detect_version(self) -> Optional[str]:
        """
        Détecte automatiquement la version du backend.
        
        Méthode par défaut qui peut être overridée par les backends spécifiques.
        """
        try:
            import subprocess
            result = subprocess.run(
                [self.name, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Extraire la version du output
                version_line = result.stdout.strip().split('\n')[0]
                # Formats courants: "pip 23.0.1", "uv 0.1.15", etc.
                parts = version_line.split()
                if len(parts) >= 2:
                    return parts[1]
            return "unknown"
        except Exception:
            return None
    
    def _sync_via_requirements_conversion(self, 
                                        env_path: Path, 
                                        pyproject_path: Path,
                                        groups: Optional[List[str]] = None,
                                        **kwargs) -> InstallResult:
        """
        Fallback: conversion pyproject.toml → requirements.txt puis installation.
        
        Utilisé quand le backend ne supporte pas nativement pyproject.toml.
        """
        try:
            from ..utils.pyproject_parser import PyProjectParser
            
            parser = PyProjectParser(pyproject_path)
            
            # Extraire les dépendances
            if groups:
                packages = []
                for group in groups:
                    packages.extend(parser.get_dependencies(group))
            else:
                packages = parser.get_dependencies("main")
            
            if not packages:
                return InstallResult(
                    success=True,
                    message="No dependencies to install",
                    backend_used=self.name
                )
            
            # Installer via install_packages
            return self.install_packages(env_path, packages, **kwargs)
            
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Failed to convert pyproject.toml: {e}",
                backend_used=self.name
            )
    
    def _run_command(self, 
                    cmd: List[str], 
                    env_path: Optional[Path] = None,
                    timeout: int = 300) -> Tuple[int, str, str]:
        """
        Exécute une commande avec gestion d'erreurs standardisée.
        
        Args:
            cmd: Commande à exécuter
            env_path: Environnement virtuel à utiliser (optionnel)
            timeout: Timeout en secondes
            
        Returns:
            Tuple (returncode, stdout, stderr)
        """
        import subprocess
        import os
        
        env = os.environ.copy()
        
        # Configurer l'environnement virtuel si spécifié
        if env_path:
            if os.name == 'nt':  # Windows
                scripts_dir = env_path / "Scripts"
                python_exe = scripts_dir / "python.exe"
            else:  # Unix/Linux/macOS
                scripts_dir = env_path / "bin"
                python_exe = scripts_dir / "python"
            
            if python_exe.exists():
                env["PATH"] = f"{scripts_dir}{os.pathsep}{env.get('PATH', '')}"
                env["VIRTUAL_ENV"] = str(env_path)
                if "PYTHONHOME" in env:
                    del env["PYTHONHOME"]
        
        try:
            self._logger.debug(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
                cwd=env_path.parent if env_path else None
            )
            
            self._logger.debug(f"Command completed with return code: {result.returncode}")
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds: {' '.join(cmd)}"
            self._logger.error(error_msg)
            return 1, "", error_msg
        except Exception as e:
            error_msg = f"Failed to execute command: {e}"
            self._logger.error(error_msg)
            return 1, "", error_msg
    
    def __str__(self) -> str:
        """Représentation string du backend."""
        available = "✓" if self.is_available() else "✗"
        version = self.version or "unknown"
        return f"{self.name} {version} {available}"
    
    def __repr__(self) -> str:
        """Représentation repr du backend."""
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"