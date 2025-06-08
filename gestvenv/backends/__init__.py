"""
Module backends pour GestVenv - Gestion multi-backend des packages Python.

Ce module fournit une architecture modulaire pour supporter différents
backends de gestion de packages (pip, uv, poetry, pdm) avec une interface
unifiée et une sélection automatique du backend optimal.

Exports:
    - PackageBackend: Interface abstraite pour tous les backends
    - PipBackend: Backend pip (référence et fallback)
    - UvBackend: Backend uv haute performance
    - PoetryBackend: Backend poetry avec support écosystème complet
    - BackendManager: Gestionnaire de sélection automatique des backends
"""

from .base_backend import (
    PackageBackend,
    BackendCapabilities,
    InstallResult,
    BackendType
)
from .pip_backend import PipBackend
from .uv_backend import UvBackend
from .poetry_backend import PoetryBackend

__all__ = [
    # Interface et types
    'PackageBackend',
    'BackendCapabilities', 
    'InstallResult',
    'BackendType',
    
    # Backends concrets
    'PipBackend',
    'UvBackend',
    'PoetryBackend',
    
    # Manager
    'BackendManager'
]

# Backends disponibles par ordre de préférence
AVAILABLE_BACKENDS = {
    BackendType.PIP: PipBackend,
    BackendType.UV: UvBackend,
    BackendType.POETRY: PoetryBackend,
}

class BackendManager:
    """
    Gestionnaire de sélection automatique des backends.
    
    Sélectionne le backend optimal selon:
    1. Backend explicitement spécifié
    2. Détection de projet (uv.lock → uv, poetry.lock → poetry)
    3. Préférences utilisateur
    4. Ordre par défaut: uv > pip > poetry
    5. Fallback: pip (toujours disponible)
    """
    
    def __init__(self):
        self.backends = {}
        self._initialize_backends()
    
    def _initialize_backends(self):
        """Initialise tous les backends disponibles."""
        for backend_type, backend_class in AVAILABLE_BACKENDS.items():
            try:
                backend = backend_class()
                if backend.is_available():
                    self.backends[backend_type] = backend
            except Exception:
                # Backend non disponible, on continue
                pass
        
        # Assurer qu'on a au moins pip
        if BackendType.PIP not in self.backends:
            self.backends[BackendType.PIP] = PipBackend()
    
    def get_backend(self, 
                   backend_type: BackendType = None, 
                   project_path: str = None,
                   preferred: str = None) -> PackageBackend:
        """
        Sélectionne le backend approprié.
        
        Args:
            backend_type: Type de backend explicitement demandé
            project_path: Chemin du projet pour détection automatique
            preferred: Backend préféré configuré par l'utilisateur
            
        Returns:
            Instance du backend sélectionné
        """
        # 1. Backend explicitement spécifié
        if backend_type and backend_type in self.backends:
            return self.backends[backend_type]
        
        # 2. Détection de projet
        if project_path:
            detected = self._detect_project_backend(project_path)
            if detected and detected in self.backends:
                return self.backends[detected]
        
        # 3. Préférence utilisateur
        if preferred:
            try:
                preferred_type = BackendType(preferred.lower())
                if preferred_type in self.backends:
                    return self.backends[preferred_type]
            except ValueError:
                pass
        
        # 4. Ordre de préférence par défaut
        for backend_type in [BackendType.UV, BackendType.PIP, BackendType.POETRY]:
            if backend_type in self.backends:
                return self.backends[backend_type]
        
        # 5. Fallback ultime
        return PipBackend()
    
    def _detect_project_backend(self, project_path: str) -> BackendType:
        """
        Détecte le backend optimal pour un projet.
        
        Args:
            project_path: Chemin vers le répertoire du projet
            
        Returns:
            Type de backend détecté ou None
        """
        from pathlib import Path
        
        project_dir = Path(project_path)
        
        # Indicateurs par backend
        indicators = {
            BackendType.UV: ['uv.lock'],
            BackendType.POETRY: ['poetry.lock'],
            BackendType.PIP: ['requirements.txt', 'requirements.in']
        }
        
        # Vérifier les fichiers indicateurs
        for backend_type, files in indicators.items():
            if any((project_dir / file).exists() for file in files):
                return backend_type
        
        # Vérifier pyproject.toml pour des indices
        pyproject_path = project_dir / 'pyproject.toml'
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, 'rb') as f:
                    data = tomllib.load(f)
                
                # Vérifier les sections tool
                if 'tool' in data:
                    if 'poetry' in data['tool']:
                        return BackendType.POETRY
                    if 'uv' in data['tool']:
                        return BackendType.UV
                        
            except Exception:
                pass
        
        return None
    
    def get_available_backends(self) -> list[BackendType]:
        """Retourne la liste des backends disponibles."""
        return list(self.backends.keys())
    
    def get_backend_info(self, backend_type: BackendType) -> dict:
        """
        Retourne les informations d'un backend.
        
        Args:
            backend_type: Type de backend
            
        Returns:
            Dictionnaire avec les informations du backend
        """
        if backend_type not in self.backends:
            return {'available': False}
        
        backend = self.backends[backend_type]
        return {
            'available': True,
            'name': backend.name,
            'version': backend.version,
            'capabilities': backend.capabilities.__dict__
        }


# Instance globale du gestionnaire
backend_manager = BackendManager()