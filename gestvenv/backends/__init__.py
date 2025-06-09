"""
Module backends pour GestVenv - Gestion multi-backend des packages Python.

Ce module fournit une architecture modulaire pour supporter différents
backends de gestion de packages (pip, uv, poetry, pdm) avec une interface
unifiée et une sélection automatique du backend optimal.

Nouveautés v1.1:
- Architecture backend modulaire
- Support pip, uv (actuel) + poetry, pdm (futur)
- Sélection automatique intelligente
- BackendCapabilities pour optimisations
- InstallResult standardisé

Exports:
    - PackageBackend: Interface abstraite pour tous les backends
    - PipBackend: Backend pip (référence et fallback)
    - UvBackend: Backend uv haute performance
    - PoetryBackend: Backend poetry avec support écosystème complet (futur)
    - PDMBackend: Backend PDM moderne (futur)
    - BackendManager: Gestionnaire de sélection automatique des backends

Usage:
    from gestvenv.backends import BackendManager, PackageBackend
    
    # Sélection automatique
    manager = BackendManager()
    backend = manager.get_backend()  # Détection automatique
    
    # Sélection explicite
    backend = manager.get_backend(BackendType.UV)
    
    # Utilisation
    result = backend.install_packages(env_path, ["requests", "flask"])
"""

import logging
from typing import Dict, Optional, List
from pathlib import Path

# Configuration du logger pour le module backends
logger = logging.getLogger(__name__)

# Imports de l'interface et types de base
try:
    from .base_backend import (
        PackageBackend,
        BackendCapabilities,
        InstallResult,
        BackendType
    )
    _BASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Interface backend de base non disponible: {e}")
    _BASE_AVAILABLE = False

# Imports des backends concrets
try:
    from .pip_backend import PipBackend
    _PIP_BACKEND_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PipBackend non disponible: {e}")
    PipBackend = None
    _PIP_BACKEND_AVAILABLE = False

try:
    from .uv_backend import UvBackend
    _UV_BACKEND_AVAILABLE = True
except ImportError as e:
    logger.warning(f"UvBackend non disponible: {e}")
    UvBackend = None
    _UV_BACKEND_AVAILABLE = False

try:
    from .poetry_backend import PoetryBackend
    _POETRY_BACKEND_AVAILABLE = True
except ImportError as e:
    logger.info(f"PoetryBackend non disponible (futur): {e}")
    PoetryBackend = None
    _POETRY_BACKEND_AVAILABLE = False

try:
    from .pdm_backend import PdmBackend
    _PDM_BACKEND_AVAILABLE = True
except ImportError as e:
    logger.info(f"PdmBackend non disponible (futur): {e}")
    PdmBackend = None
    _PDM_BACKEND_AVAILABLE = False

# Registry des backends disponibles
AVAILABLE_BACKENDS = {}
if _PIP_BACKEND_AVAILABLE:
    AVAILABLE_BACKENDS[BackendType.PIP] = PipBackend
if _UV_BACKEND_AVAILABLE:
    AVAILABLE_BACKENDS[BackendType.UV] = UvBackend
if _POETRY_BACKEND_AVAILABLE:
    AVAILABLE_BACKENDS[BackendType.POETRY] = PoetryBackend
if _PDM_BACKEND_AVAILABLE:
    AVAILABLE_BACKENDS[BackendType.PDM] = PdmBackend

class BackendManager:
    """
    Gestionnaire de sélection automatique des backends.
    
    Sélectionne le backend optimal selon:
    1. Backend explicitement spécifié
    2. Détection de projet (uv.lock → uv, poetry.lock → poetry)
    3. Préférences utilisateur
    4. Ordre par défaut: uv > pip > poetry > pdm
    5. Fallback: pip (toujours disponible)
    """
    
    def __init__(self) -> None:
        self.backends = {}
        self._initialize_backends()
        logger.info(f"BackendManager initialisé avec {len(self.backends)} backends disponibles")
    
    def _initialize_backends(self) -> None:
        """Initialise tous les backends disponibles."""
        for backend_type, backend_class in AVAILABLE_BACKENDS.items():
            try:
                backend = backend_class()
                if backend.is_available():
                    self.backends[backend_type] = backend
                    logger.debug(f"Backend {backend_type.value} initialisé et disponible")
                else:
                    logger.debug(f"Backend {backend_type.value} non disponible sur le système")
            except Exception as e:
                logger.warning(f"Erreur initialisation backend {backend_type.value}: {e}")
        
        # Assurer qu'on a au moins pip
        if BackendType.PIP not in self.backends and _PIP_BACKEND_AVAILABLE:
            try:
                self.backends[BackendType.PIP] = PipBackend()
                logger.info("Backend pip ajouté comme fallback")
            except Exception as e:
                logger.error(f"Impossible d'initialiser le backend pip fallback: {e}")
    
    def get_backend(self, 
                   backend_type: Optional[BackendType] = None, 
                   project_path: Optional[Path] = None,
                   preferred: Optional[str] = None) -> PackageBackend:
        """
        Sélectionne le backend approprié.
        
        Args:
            backend_type: Type de backend explicitement demandé
            project_path: Chemin du projet pour détection automatique
            preferred: Backend préféré configuré par l'utilisateur
            
        Returns:
            Instance du backend sélectionné
            
        Raises:
            ValueError: Si aucun backend n'est disponible
        """
        # 1. Backend explicitement spécifié
        if backend_type and backend_type != BackendType.AUTO:
            if backend_type in self.backends:
                logger.debug(f"Backend {backend_type.value} sélectionné explicitement")
                return self.backends[backend_type]
            else:
                logger.warning(f"Backend {backend_type.value} demandé mais non disponible")
        
        # 2. Détection automatique depuis le projet
        if project_path:
            detected = self.detect_backend_from_project(project_path)
            if detected and detected in self.backends:
                logger.debug(f"Backend {detected.value} détecté depuis le projet")
                return self.backends[detected]
        
        # 3. Backend préféré utilisateur
        if preferred:
            try:
                pref_type = BackendType(preferred)
                if pref_type in self.backends:
                    logger.debug(f"Backend {preferred} sélectionné depuis préférences")
                    return self.backends[pref_type]
            except ValueError:
                logger.warning(f"Backend préféré '{preferred}' invalide")
        
        # 4. Ordre par défaut: uv > pip > poetry > pdm
        default_order = [BackendType.UV, BackendType.PIP, BackendType.POETRY, BackendType.PDM]
        for backend_type in default_order:
            if backend_type in self.backends:
                logger.debug(f"Backend {backend_type.value} sélectionné par défaut")
                return self.backends[backend_type]
        
        # 5. Aucun backend disponible (ne devrait jamais arriver)
        raise ValueError("Aucun backend de packages disponible")
    
    def detect_backend_from_project(self, project_path: Path) -> Optional[BackendType]:
        """
        Détecte le backend approprié basé sur les fichiers du projet.
        
        Args:
            project_path: Chemin vers le dossier du projet
            
        Returns:
            Type de backend détecté ou None
        """
        if not project_path.exists():
            return None
        
        # Recherche des fichiers de lock spécifiques
        if (project_path / "uv.lock").exists():
            return BackendType.UV
        
        if (project_path / "poetry.lock").exists():
            return BackendType.POETRY
        
        if (project_path / "pdm.lock").exists():
            return BackendType.PDM
        
        # Recherche des fichiers de configuration
        if (project_path / "pyproject.toml").exists():
            # Analyser le contenu pour détecter l'outil
            try:
                import tomllib if hasattr(__builtins__, 'tomllib') else tomli
                with open(project_path / "pyproject.toml", "rb") as f:
                    data = tomllib.load(f)
                
                # Vérifier la section [tool.X]
                tools = data.get("tool", {})
                
                if "poetry" in tools:
                    return BackendType.POETRY
                elif "pdm" in tools:
                    return BackendType.PDM
                elif "uv" in tools:
                    return BackendType.UV
                
            except Exception as e:
                logger.debug(f"Erreur lecture pyproject.toml: {e}")
        
        # Pas de détection possible
        return None
    
    def list_available_backends(self) -> List[BackendType]:
        """
        Liste tous les backends disponibles sur le système.
        
        Returns:
            Liste des types de backends disponibles
        """
        return list(self.backends.keys())
    
    def get_backend_info(self, backend_type: BackendType) -> Optional[Dict]:
        """
        Retourne les informations sur un backend.
        
        Args:
            backend_type: Type de backend
            
        Returns:
            Dictionnaire avec les informations du backend
        """
        if backend_type not in self.backends:
            return None
        
        backend = self.backends[backend_type]
        return {
            'name': backend.name,
            'version': backend.version,
            'available': backend.is_available(),
            'capabilities': backend.capabilities,
        }


# Factory function pour compatibilité
def get_backend(backend_type: BackendType = BackendType.AUTO, 
               project_path: Optional[Path] = None,
               preferred: Optional[str] = None) -> PackageBackend:
    """
    Fonction de commodité pour obtenir un backend.
    
    Args:
        backend_type: Type de backend demandé
        project_path: Chemin du projet pour détection
        preferred: Backend préféré
        
    Returns:
        Instance du backend sélectionné
    """
    manager = BackendManager()
    return manager.get_backend(backend_type, project_path, preferred)


def list_available_backends() -> List[BackendType]:
    """
    Fonction de commodité pour lister les backends disponibles.
    
    Returns:
        Liste des backends disponibles
    """
    manager = BackendManager()
    return manager.list_available_backends()


# Exports publics
__all__ = [
    # Interface et types
    'PackageBackend',
    'BackendCapabilities', 
    'InstallResult',
    'BackendType',
    
    # Manager
    'BackendManager',
    'get_backend',
    'list_available_backends',
    
    # Registry
    'AVAILABLE_BACKENDS'
]

# Ajouter les backends concrets s'ils sont disponibles
if _PIP_BACKEND_AVAILABLE:
    __all__.append('PipBackend')
if _UV_BACKEND_AVAILABLE:
    __all__.append('UvBackend')
if _POETRY_BACKEND_AVAILABLE:
    __all__.append('PoetryBackend')
if _PDM_BACKEND_AVAILABLE:
    __all__.append('PdmBackend')

# Version du module backends
__version__ = "1.1.0"