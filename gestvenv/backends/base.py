"""
Interface abstraite pour les backends de packages GestVenv v1.1
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core.models import PackageInfo, InstallResult


@dataclass
class BackendCapabilities:
    """Capacités d'un backend de packages"""
    supports_lock_files: bool = False
    supports_dependency_groups: bool = False
    supports_parallel_install: bool = False
    supports_editable_installs: bool = True
    supports_workspace: bool = False
    supports_pyproject_sync: bool = False
    supported_formats: List[str] = field(default_factory=list)
    max_parallel_jobs: int = 1
    
    def __post_init__(self):
        """Validation post-initialisation"""
        if self.max_parallel_jobs < 1:
            self.max_parallel_jobs = 1


class PackageBackend(ABC):
    """Interface abstraite pour tous les backends de packages"""
    
    def __init__(self):
        self._name = self.__class__.__name__.replace('Backend', '').lower()
        self._version: Optional[str] = None
        self._available: Optional[bool] = None
        self._capabilities = self._init_capabilities()
        
    @property
    def name(self) -> str:
        """Nom du backend"""
        return self._name
        
    @property
    def version(self) -> Optional[str]:
        """Version du backend"""
        if self._version is None:
            self._version = self._get_version()
        return self._version
        
    @property
    def available(self) -> bool:
        """Disponibilité du backend"""
        if self._available is None:
            self._available = self._check_availability()
        return self._available
        
    @property
    def capabilities(self) -> BackendCapabilities:
        """Capacités du backend"""
        return self._capabilities
        
    @abstractmethod
    def _check_availability(self) -> bool:
        """Vérifie si le backend est disponible sur le système"""
        pass
        
    @abstractmethod
    def _get_version(self) -> Optional[str]:
        """Récupère la version du backend"""
        pass
        
    @abstractmethod
    def _init_capabilities(self) -> BackendCapabilities:
        """Initialise les capacités du backend"""
        pass
        
    @abstractmethod
    def create_environment(self, path: Path, python_version: str) -> bool:
        """Crée un environnement virtuel"""
        pass
        
    @abstractmethod
    def install_package(self, env_path: Path, package: str, **kwargs) -> InstallResult:
        """Installe un package"""
        pass
        
    @abstractmethod
    def uninstall_package(self, env_path: Path, package: str) -> bool:
        """Désinstalle un package"""
        pass
        
    @abstractmethod
    def update_package(self, env_path: Path, package: str) -> bool:
        """Met à jour un package"""
        pass
        
    @abstractmethod
    def list_packages(self, env_path: Path) -> List[PackageInfo]:
        """Liste les packages installés"""
        pass
        
    def sync_from_pyproject(
        self, 
        env_path: Path, 
        pyproject_path: Path, 
        groups: Optional[List[str]] = None
    ) -> bool:
        """Synchronise depuis pyproject.toml (optionnel)"""
        return False
        
    def install_from_requirements(self, env_path: Path, req_path: Path) -> bool:
        """Installe depuis requirements.txt (optionnel)"""
        return False
        
    def create_lock_file(self, pyproject_path: Path) -> Optional[Path]:
        """Crée un fichier de verrouillage (optionnel)"""
        return None
        
    def install_from_lock(self, env_path: Path, lock_path: Path) -> bool:
        """Installe depuis fichier de verrouillage (optionnel)"""
        return False
        
    def get_performance_score(self) -> int:
        """Score de performance (1-10)"""
        return 5
        
    def supports_feature(self, feature: str) -> bool:
        """Vérifie le support d'une fonctionnalité"""
        return hasattr(self.capabilities, f'supports_{feature}') and \
               getattr(self.capabilities, f'supports_{feature}')
               
    def validate_package_spec(self, package: str) -> bool:
        """Valide une spécification de package"""
        if not package or not package.strip():
            return False
            
        # Validation basique - éviter caractères dangereux
        dangerous_chars = [';', '|', '&', '`', '$']
        return not any(char in package for char in dangerous_chars)
        
    def __str__(self) -> str:
        """Représentation textuelle"""
        status = "✓" if self.available else "✗"
        version_str = f" v{self.version}" if self.version else ""
        return f"{status} {self.name.title()}{version_str}"
        
    def __repr__(self) -> str:
        """Représentation pour debug"""
        return f"<{self.__class__.__name__}(available={self.available}, version={self.version})>"