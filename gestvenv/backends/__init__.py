"""
Module backends pour GestVenv v1.1

Ce module contient tous les backends de gestion de packages :
- PackageBackend : Interface abstraite commune
- PipBackend : Backend pip classique
- UvBackend : Backend uv haute performance
- PoetryBackend : Backend Poetry (futur)
- PDMBackend : Backend PDM (futur)
- BackendManager : Gestionnaire de sélection des backends
"""

from .base import PackageBackend, BackendCapabilities
from .pip_backend import PipBackend
from .uv_backend import UvBackend
from .poetry_backend import PoetryBackend
from .pdm_backend import PDMBackend
from .backend_manager import BackendManager

__all__ = [
    "PackageBackend",
    "BackendCapabilities",
    "PipBackend", 
    "UvBackend",
    "PoetryBackend",
    "PDMBackend",
    "BackendManager",
]

# Version du module backends
__version__ = "1.1.0"