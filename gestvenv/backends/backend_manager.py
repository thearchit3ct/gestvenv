"""
Gestionnaire de backends pour GestVenv v1.1
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import PackageBackend
from .pip_backend import PipBackend
from .uv_backend import UvBackend
from .poetry_backend import PoetryBackend
from .pdm_backend import PDMBackend
from ..core.models import Config, EnvironmentInfo
from ..core.exceptions import BackendError

logger = logging.getLogger(__name__)


class BackendManager:
    """Gestionnaire de sélection et configuration des backends"""
    
    def __init__(self, config: Config):
        self.config = config
        self.backends: Dict[str, PackageBackend] = {}
        self.preferred_backend = config.preferred_backend
        self.initialize_backends()
        
    def initialize_backends(self) -> None:
        """Initialise tous les backends disponibles"""
        backend_classes = {
            'pip': PipBackend,
            'uv': UvBackend,
            'poetry': PoetryBackend,
            'pdm': PDMBackend
        }
        
        for name, backend_class in backend_classes.items():
            try:
                backend = backend_class()
                self.backends[name] = backend
                status = "✓" if backend.available else "✗"
                logger.debug(f"Backend {name}: {status}")
            except Exception as e:
                logger.error(f"Erreur initialisation backend {name}: {e}")
                
    def get_backend(self, preference: str, env_info: Optional[EnvironmentInfo] = None) -> PackageBackend:
        """Sélectionne le backend optimal"""
        if preference == "auto":
            return self._select_optimal_backend(env_info)
        elif preference in self.backends and self.backends[preference].available:
            return self.backends[preference]
        else:
            # Fallback vers le premier disponible
            return self._get_fallback_backend()
            
    def detect_project_backend(self, project_path: Path) -> str:
        """Détecte le backend optimal pour un projet"""
        # Priorité basée sur les fichiers présents
        detection_rules = [
            ("uv.lock", "uv"),
            ("poetry.lock", "poetry"),
            ("pdm.lock", "pdm"),
            ("pyproject.toml", self._detect_pyproject_backend),
            ("requirements.txt", "pip")
        ]
        
        for filename, backend_or_func in detection_rules:
            file_path = project_path / filename
            if file_path.exists():
                if callable(backend_or_func):
                    backend = backend_or_func(file_path)
                    if backend:
                        return backend
                else:
                    return backend_or_func
                    
        return "auto"
        
    def list_available_backends(self) -> List[str]:
        """Liste des backends disponibles"""
        return [name for name, backend in self.backends.items() if backend.available]
        
    def get_backend_info(self) -> Dict[str, Any]:
        """Informations détaillées sur les backends"""
        info = {
            "preferred": self.preferred_backend,
            "available": [],
            "unavailable": [],
            "details": {}
        }
        
        for name, backend in self.backends.items():
            backend_info = {
                "name": name,
                "version": backend.version,
                "available": backend.available,
                "performance_score": backend.get_performance_score(),
                "capabilities": {
                    "lock_files": backend.capabilities.supports_lock_files,
                    "dependency_groups": backend.capabilities.supports_dependency_groups,
                    "parallel_install": backend.capabilities.supports_parallel_install,
                    "pyproject_sync": backend.capabilities.supports_pyproject_sync
                }
            }
            
            info["details"][name] = backend_info
            
            if backend.available:
                info["available"].append(name)
            else:
                info["unavailable"].append(name)
                
        return info
        
    def set_preferred_backend(self, backend: str) -> bool:
        """Définit le backend préféré"""
        valid_backends = ["auto"] + list(self.backends.keys())
        
        if backend not in valid_backends:
            raise BackendError(f"Backend invalide: {backend}")
            
        self.preferred_backend = backend
        self.config.preferred_backend = backend
        
        return True
        
    def get_best_backend_for_feature(self, feature: str) -> Optional[PackageBackend]:
        """Récupère le meilleur backend pour une fonctionnalité"""
        compatible_backends = [
            backend for backend in self.backends.values()
            if backend.available and backend.supports_feature(feature)
        ]
        
        if not compatible_backends:
            return None
            
        # Tri par score de performance
        return max(compatible_backends, key=lambda b: b.get_performance_score())
        
    def validate_backend_config(self, backend_name: str, config: Dict[str, Any]) -> List[str]:
        """Valide la configuration d'un backend"""
        errors = []
        
        if backend_name not in self.backends:
            errors.append(f"Backend inconnu: {backend_name}")
            return errors
            
        backend = self.backends[backend_name]
        
        if not backend.available:
            errors.append(f"Backend {backend_name} non disponible")
            
        # Validation spécifique selon le backend
        if backend_name == "uv" and config.get("max_parallel_jobs", 1) > 8:
            errors.append("max_parallel_jobs trop élevé pour uv (max 8)")
            
        return errors
        
    # Méthodes privées
    
    def _select_optimal_backend(self, env_info: Optional[EnvironmentInfo]) -> PackageBackend:
        """Sélection basée sur performance et disponibilité"""
        # Détection basée sur l'environnement
        if env_info:
            if env_info.lock_file_path:
                if env_info.lock_file_path.name == "uv.lock" and self.backends['uv'].available:
                    return self.backends['uv']
                elif env_info.lock_file_path.name == "poetry.lock" and self.backends['poetry'].available:
                    return self.backends['poetry']
                elif env_info.lock_file_path.name == "pdm.lock" and self.backends['pdm'].available:
                    return self.backends['pdm']
                    
            # Détection basée sur pyproject.toml
            if env_info.pyproject_info and env_info.pyproject_info.source_path:
                detected = self.detect_project_backend(env_info.pyproject_info.source_path.parent)
                if detected != "auto" and self.backends[detected].available:
                    return self.backends[detected]
        
        # Sélection par priorité de performance
        priority_order = ['uv', 'poetry', 'pdm', 'pip']
        
        for backend_name in priority_order:
            backend = self.backends.get(backend_name)
            if backend and backend.available:
                return backend
                
        raise BackendError("Aucun backend disponible")
        
    def _get_fallback_backend(self) -> PackageBackend:
        """Backend de fallback (pip en priorité)"""
        if self.backends['pip'].available:
            return self.backends['pip']
            
        # Dernier recours: premier disponible
        for backend in self.backends.values():
            if backend.available:
                return backend
                
        raise BackendError("Aucun backend disponible")
        
    def _detect_pyproject_backend(self, pyproject_path: Path) -> Optional[str]:
        """Détecte le backend depuis pyproject.toml"""
        try:
            from ..utils import TomlHandler
            
            data = TomlHandler.load(pyproject_path)
            tool_sections = data.get('tool', {})
            
            # Détection par sections [tool.*]
            if 'poetry' in tool_sections:
                return 'poetry'
            elif 'pdm' in tool_sections:
                return 'pdm'
            elif 'uv' in tool_sections:
                return 'uv'
            
            # Détection par build-system
            build_system = data.get('build-system', {})
            build_backend = build_system.get('build-backend', '')
            
            if 'poetry' in build_backend:
                return 'poetry'
            elif 'pdm' in build_backend:
                return 'pdm'
            
            # Par défaut, préférer uv pour pyproject.toml moderne
            return 'uv'
            
        except Exception as e:
            logger.debug(f"Erreur détection backend pyproject: {e}")
            return None
            
    def _calculate_backend_score(self, backend: PackageBackend, context: Optional[Dict[str, Any]] = None) -> float:
        """Calcule un score pour un backend dans un contexte donné"""
        score = float(backend.get_performance_score())
        
        if context:
            # Bonus pour support de fonctionnalités requises
            if context.get('needs_lock_files') and backend.capabilities.supports_lock_files:
                score += 2
            if context.get('needs_groups') and backend.capabilities.supports_dependency_groups:
                score += 1
            if context.get('needs_parallel') and backend.capabilities.supports_parallel_install:
                score += 1
                
        return score