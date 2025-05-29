"""
Interface abstraite pour tous les backends de packages dans GestVenv v1.1.

Ce module définit la classe de base abstraite PackageBackend qui doit être
implémentée par tous les backends de gestion de packages (pip, uv, poetry, pdm, etc.).

L'interface garantit une API uniforme pour toutes les opérations sur les
environnements virtuels, permettant une architecture modulaire et extensible.

Version 1.1 - Nouvelles fonctionnalités:
- Support complet pyproject.toml
- Gestion des groupes de dépendances
- Lock files et synchronisation
- Métriques de performance
- Validation avancée
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Union, Set
import logging

logger = logging.getLogger(__name__)


@dataclass
class BackendCapabilities:
    """Décrit les capacités d'un backend."""
    supports_lock_files: bool = False
    supports_dependency_groups: bool = False
    supports_editable_installs: bool = True
    supports_pyproject_sync: bool = False
    supports_parallel_install: bool = False
    supports_hash_verification: bool = False
    supports_compile_bytecode: bool = True
    max_parallel_jobs: int = 1


@dataclass
class InstallResult:
    """Résultat d'une opération d'installation."""
    success: bool
    installed_packages: List[str] = None
    failed_packages: List[str] = None
    error_message: Optional[str] = None
    duration: float = 0.0
    
    def __post_init__(self):
        if self.installed_packages is None:
            self.installed_packages = []
        if self.failed_packages is None:
            self.failed_packages = []


class PackageBackend(ABC):
    """
    Interface abstraite pour tous les backends de gestion de packages.
    
    Cette classe définit l'API commune que tous les backends doivent implémenter
    pour garantir l'interopérabilité et la modularité du système.
    """
    
    def __init__(self):
        """Initialise le backend."""
        self._capabilities = None
        self._version = None
        self._available = None
    
    # ========== Propriétés abstraites ==========
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Retourne le nom du backend.
        
        Returns:
            str: Nom du backend (ex: "pip", "uv", "poetry")
        """
        pass
    
    @property
    def version(self) -> Optional[str]:
        """
        Retourne la version du backend.
        
        Returns:
            Optional[str]: Version du backend ou None si non disponible
        """
        if self._version is None:
            self._version = self._detect_version()
        return self._version
    
    @property
    def capabilities(self) -> BackendCapabilities:
        """
        Retourne les capacités du backend.
        
        Returns:
            BackendCapabilities: Capacités supportées par le backend
        """
        if self._capabilities is None:
            self._capabilities = self._get_capabilities()
        return self._capabilities
    
    # ========== Méthodes abstraites principales ==========
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si le backend est disponible sur le système.
        
        Returns:
            bool: True si le backend est installé et utilisable
        """
        pass
    
    @abstractmethod
    def create_environment(self, name: str, python_version: str, path: Path) -> bool:
        """
        Crée un nouvel environnement virtuel.
        
        Args:
            name: Nom de l'environnement
            python_version: Version ou commande Python à utiliser
            path: Chemin où créer l'environnement
            
        Returns:
            bool: True si la création a réussi
        """
        pass
    
    @abstractmethod
    def install_packages(self, env_path: Path, packages: List[str], 
                        upgrade: bool = False, **kwargs) -> InstallResult:
        """
        Installe des packages dans un environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à installer
            upgrade: Si True, met à jour les packages existants
            **kwargs: Options supplémentaires spécifiques au backend
            
        Returns:
            InstallResult: Résultat de l'installation
        """
        pass
    
    @abstractmethod
    def uninstall_packages(self, env_path: Path, packages: List[str]) -> Tuple[bool, str]:
        """
        Désinstalle des packages d'un environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à désinstaller
            
        Returns:
            Tuple[bool, str]: (succès, message)
        """
        pass
    
    @abstractmethod
    def update_packages(self, env_path: Path, packages: List[str], 
                       strategy: str = "only-if-needed") -> bool:
        """
        Met à jour des packages dans un environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            packages: Liste des packages à mettre à jour
            strategy: Stratégie de mise à jour ("only-if-needed", "eager", "to-latest")
            
        Returns:
            bool: True si la mise à jour a réussi
        """
        pass
    
    @abstractmethod
    def get_installed_packages(self, env_path: Path) -> List[Dict[str, str]]:
        """
        Liste les packages installés dans un environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            List[Dict[str, str]]: Liste des packages avec nom et version
        """
        pass
    
    # ========== Méthodes pour pyproject.toml ==========
    
    @abstractmethod
    def sync_from_pyproject(self, env_path: Path, pyproject_path: Path,
                           groups: Optional[List[str]] = None) -> bool:
        """
        Synchronise l'environnement avec un fichier pyproject.toml.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            pyproject_path: Chemin vers le fichier pyproject.toml
            groups: Groupes de dépendances à installer (None = tous)
            
        Returns:
            bool: True si la synchronisation a réussi
        """
        pass
    
    def supports_pyproject(self) -> bool:
        """
        Indique si le backend supporte nativement pyproject.toml.
        
        Returns:
            bool: True si le support est natif
        """
        return self.capabilities.supports_pyproject_sync
    
    # ========== Méthodes pour lock files ==========
    
    def create_lock_file(self, env_path: Path, output_path: Path) -> bool:
        """
        Crée un fichier de lock pour l'environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            output_path: Chemin de sortie pour le lock file
            
        Returns:
            bool: True si la création a réussi
        """
        logger.warning(f"Le backend {self.name} ne supporte pas les lock files")
        return False
    
    def install_from_lock_file(self, env_path: Path, lock_file_path: Path) -> bool:
        """
        Installe les packages depuis un fichier de lock.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            lock_file_path: Chemin vers le fichier de lock
            
        Returns:
            bool: True si l'installation a réussi
        """
        logger.warning(f"Le backend {self.name} ne supporte pas les lock files")
        return False
    
    def update_lock_file(self, env_path: Path, lock_file_path: Path) -> bool:
        """
        Met à jour un fichier de lock existant.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            lock_file_path: Chemin vers le fichier de lock
            
        Returns:
            bool: True si la mise à jour a réussi
        """
        logger.warning(f"Le backend {self.name} ne supporte pas les lock files")
        return False
    
    # ========== Méthodes utilitaires ==========
    
    def get_python_executable(self, env_path: Path) -> Optional[Path]:
        """
        Retourne le chemin vers l'exécutable Python de l'environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            Optional[Path]: Chemin vers python ou None si non trouvé
        """
        import os
        
        if os.name == 'nt':  # Windows
            python_exe = env_path / "Scripts" / "python.exe"
        else:  # Unix-like
            python_exe = env_path / "bin" / "python"
        
        return python_exe if python_exe.exists() else None
    
    def get_pip_executable(self, env_path: Path) -> Optional[Path]:
        """
        Retourne le chemin vers l'exécutable pip de l'environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            Optional[Path]: Chemin vers pip ou None si non trouvé
        """
        import os
        
        if os.name == 'nt':  # Windows
            pip_exe = env_path / "Scripts" / "pip.exe"
        else:  # Unix-like
            pip_exe = env_path / "bin" / "pip"
        
        return pip_exe if pip_exe.exists() else None
    
    def get_activation_script(self, env_path: Path) -> Optional[Path]:
        """
        Retourne le chemin vers le script d'activation.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            Optional[Path]: Chemin vers le script d'activation
        """
        import os
        
        if os.name == 'nt':  # Windows
            activate_script = env_path / "Scripts" / "activate.bat"
        else:  # Unix-like
            activate_script = env_path / "bin" / "activate"
        
        return activate_script if activate_script.exists() else None
    
    def validate_environment(self, env_path: Path) -> Tuple[bool, List[str]]:
        """
        Valide qu'un environnement est fonctionnel.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            Tuple[bool, List[str]]: (valide, liste des problèmes)
        """
        issues = []
        
        # Vérifier l'existence du répertoire
        if not env_path.exists():
            issues.append(f"Le répertoire {env_path} n'existe pas")
            return False, issues
        
        # Vérifier l'exécutable Python
        python_exe = self.get_python_executable(env_path)
        if not python_exe or not python_exe.exists():
            issues.append("Exécutable Python introuvable")
        
        # Vérifier pip
        pip_exe = self.get_pip_executable(env_path)
        if not pip_exe or not pip_exe.exists():
            issues.append("Exécutable pip introuvable")
        
        # Vérifier le script d'activation
        activate_script = self.get_activation_script(env_path)
        if not activate_script or not activate_script.exists():
            issues.append("Script d'activation introuvable")
        
        # Vérifier pyvenv.cfg
        pyvenv_cfg = env_path / "pyvenv.cfg"
        if not pyvenv_cfg.exists():
            issues.append("Fichier pyvenv.cfg manquant")
        
        return len(issues) == 0, issues
    
    def check_updates(self, env_path: Path) -> List[Dict[str, str]]:
        """
        Vérifie les mises à jour disponibles pour les packages.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            
        Returns:
            List[Dict[str, str]]: Liste des packages avec mises à jour
        """
        # Implémentation par défaut basique
        logger.info(f"Vérification des mises à jour avec {self.name}")
        return []
    
    def export_requirements(self, env_path: Path, output_path: Path,
                          include_versions: bool = True) -> bool:
        """
        Exporte les packages installés au format requirements.txt.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            output_path: Chemin de sortie pour le fichier requirements
            include_versions: Si True, inclut les versions
            
        Returns:
            bool: True si l'export a réussi
        """
        try:
            packages = self.get_installed_packages(env_path)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for pkg in packages:
                    if include_versions:
                        f.write(f"{pkg['name']}=={pkg['version']}\n")
                    else:
                        f.write(f"{pkg['name']}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export requirements: {e}")
            return False
    
    def install_editable(self, env_path: Path, package_path: Path,
                        extras: Optional[List[str]] = None) -> bool:
        """
        Installe un package en mode éditable (développement).
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            package_path: Chemin vers le package local
            extras: Extras à installer
            
        Returns:
            bool: True si l'installation a réussi
        """
        if not self.capabilities.supports_editable_installs:
            logger.warning(f"Le backend {self.name} ne supporte pas les installations éditables")
            return False
        
        # Implémentation par défaut
        package_spec = f"-e {package_path}"
        if extras:
            package_spec += f"[{','.join(extras)}]"
        
        result = self.install_packages(env_path, [package_spec])
        return result.success
    
    def run_command(self, env_path: Path, command: List[str]) -> Tuple[int, str, str]:
        """
        Exécute une commande dans le contexte de l'environnement.
        
        Args:
            env_path: Chemin vers l'environnement virtuel
            command: Commande à exécuter
            
        Returns:
            Tuple[int, str, str]: (code retour, stdout, stderr)
        """
        import subprocess
        
        python_exe = self.get_python_executable(env_path)
        if not python_exe:
            return 1, "", "Exécutable Python introuvable"
        
        try:
            # Construire la commande complète
            full_command = [str(python_exe)] + command
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=False
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except Exception as e:
            return 1, "", str(e)
    
    # ========== Méthodes à implémenter par les backends ==========
    
    @abstractmethod
    def _detect_version(self) -> Optional[str]:
        """
        Détecte la version du backend installé.
        
        Returns:
            Optional[str]: Version ou None si non détectable
        """
        pass
    
    @abstractmethod
    def _get_capabilities(self) -> BackendCapabilities:
        """
        Retourne les capacités spécifiques du backend.
        
        Returns:
            BackendCapabilities: Capacités du backend
        """
        pass
    
    # ========== Méthodes d'aide pour les implémentations ==========
    
    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None,
                    env: Optional[Dict[str, str]] = None,
                    timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """
        Exécute une commande système de manière sécurisée.
        
        Args:
            cmd: Commande à exécuter
            cwd: Répertoire de travail
            env: Variables d'environnement
            timeout: Timeout en secondes
            
        Returns:
            Tuple[int, str, str]: (code retour, stdout, stderr)
        """
        import subprocess
        import os
        
        try:
            # Préparer l'environnement
            cmd_env = os.environ.copy()
            if env:
                cmd_env.update(env)
            
            # Exécuter la commande
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=cmd_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return -1, "", f"Timeout après {timeout} secondes"
        except Exception as e:
            return -1, "", str(e)
    
    def _parse_package_spec(self, package_spec: str) -> Dict[str, Any]:
        """
        Parse une spécification de package.
        
        Args:
            package_spec: Spécification (ex: "flask>=2.0", "numpy[extra]")
            
        Returns:
            Dict avec name, version_spec, extras, etc.
        """
        import re
        
        # Pattern pour parser les spécifications de packages
        pattern = r'^([a-zA-Z0-9._-]+)(\[[a-zA-Z0-9,._-]+\])?([><=!]+.*)?$'
        match = re.match(pattern, package_spec.strip())
        
        if not match:
            return {"name": package_spec, "version_spec": None, "extras": []}
        
        name = match.group(1)
        extras_str = match.group(2)
        version_spec = match.group(3)
        
        # Parser les extras
        extras = []
        if extras_str:
            extras_str = extras_str.strip('[]')
            extras = [e.strip() for e in extras_str.split(',')]
        
        return {
            "name": name,
            "version_spec": version_spec,
            "extras": extras,
            "full_spec": package_spec
        }
    
    def __str__(self) -> str:
        """Représentation string du backend."""
        version = self.version or "unknown"
        available = "available" if self.is_available() else "not available"
        return f"{self.name} v{version} ({available})"
    
    def __repr__(self) -> str:
        """Représentation pour debug."""
        return f"<{self.__class__.__name__}(name={self.name}, available={self.is_available()})>"


# Types utilitaires pour les implémentations
PackageSpec = Union[str, Dict[str, Any]]
CommandResult = Tuple[int, str, str]


__all__ = ['PackageBackend', 'BackendCapabilities', 'InstallResult', 'PackageSpec', 'CommandResult']