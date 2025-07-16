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
        
        # Backend spécifique demandé
        if preference in self.backends:
            backend = self.backends[preference]
            if backend.available:
                return backend
            else:
                raise BackendError(f"Backend '{preference}' non disponible")
        
        # Fallback vers pip
        logger.warning(f"Backend '{preference}' inconnu, utilisation de pip")
        return self.backends['pip']
    
    def _select_optimal_backend(self, env_info: Optional[EnvironmentInfo] = None) -> PackageBackend:
        """Auto-détection du backend optimal"""
        
        # 1. Détection basée sur les fichiers projet
        if env_info and env_info.path.exists():
            detected_backend = self._detect_from_project_files(env_info.path)
            if detected_backend:
                return detected_backend
        
        # 2. Détection basée sur les métadonnées environnement
        if env_info and env_info.backend_type:
            requested_backend = env_info.backend_type.value
            if requested_backend in self.backends and self.backends[requested_backend].available:
                return self.backends[requested_backend]
        
        # 3. Sélection par ordre de préférence/performance
        preference_order = ['uv', 'pip', 'poetry', 'pdm']
        
        for backend_name in preference_order:
            if backend_name in self.backends and self.backends[backend_name].available:
                logger.info(f"Auto-sélection du backend: {backend_name}")
                return self.backends[backend_name]
        
        # 4. Fallback ultime vers pip
        return self.backends['pip']
    
    def _detect_from_project_files(self, project_path: Path) -> Optional[PackageBackend]:
        """Détecte le backend selon les fichiers présents"""
        
        # Recherche dans le répertoire et ses parents
        search_paths = [project_path] + list(project_path.parents)[:3]  # Limite à 3 niveaux
        
        for path in search_paths:
            # Poetry: pyproject.toml avec [tool.poetry]
            pyproject_toml = path / "pyproject.toml"
            if pyproject_toml.exists():
                try:
                    import toml
                    config = toml.load(pyproject_toml)
                    if "tool" in config:
                        if "poetry" in config["tool"] and "poetry" in self.backends:
                            if self.backends["poetry"].available:
                                logger.info("Détection Poetry via pyproject.toml")
                                return self.backends["poetry"]
                        
                        if "pdm" in config["tool"] and "pdm" in self.backends:
                            if self.backends["pdm"].available:
                                logger.info("Détection PDM via pyproject.toml")
                                return self.backends["pdm"]
                except Exception:
                    pass
            
            # Poetry: poetry.lock
            if (path / "poetry.lock").exists() and "poetry" in self.backends:
                if self.backends["poetry"].available:
                    logger.info("Détection Poetry via poetry.lock")
                    return self.backends["poetry"]
            
            # PDM: pdm.lock
            if (path / "pdm.lock").exists() and "pdm" in self.backends:
                if self.backends["pdm"].available:
                    logger.info("Détection PDM via pdm.lock")
                    return self.backends["pdm"]
            
            # UV: uv.lock
            if (path / "uv.lock").exists() and "uv" in self.backends:
                if self.backends["uv"].available:
                    logger.info("Détection UV via uv.lock")
                    return self.backends["uv"]
        
        return None
    
    def get_available_backends(self) -> List[str]:
        """Liste des backends disponibles"""
        return [name for name, backend in self.backends.items() if backend.available]
    
    def get_backend_recommendations(self, project_path: Optional[Path] = None) -> Dict[str, Any]:
        """Recommandations de backends pour un projet"""
        recommendations = {
            'detected': None,
            'optimal': None,
            'alternatives': [],
            'reasons': []
        }
        
        # Détection automatique
        if project_path:
            detected = self._detect_from_project_files(project_path)
            if detected:
                recommendations['detected'] = detected.name
                recommendations['reasons'].append(f"Détecté automatiquement: {detected.name}")
        
        # Backend optimal basé sur la performance
        available = self.get_available_backends()
        performance_order = {
            'uv': 10,
            'pdm': 8, 
            'poetry': 6,
            'pip': 4
        }
        
        if available:
            optimal = max(available, key=lambda x: performance_order.get(x, 0))
            recommendations['optimal'] = optimal
            recommendations['reasons'].append(f"Performances optimales: {optimal}")
        
        # Alternatives
        recommendations['alternatives'] = [
            name for name in available 
            if name != recommendations.get('optimal')
        ]
        
        return recommendations
    
    def validate_backend_compatibility(self, backend_name: str, env_info: EnvironmentInfo) -> bool:
        """Valide la compatibilité backend/environnement"""
        if backend_name not in self.backends:
            return False
            
        backend = self.backends[backend_name]
        
        # Vérifications basiques
        if not backend.available:
            return False
        
        # Vérifications spécifiques selon le type d'environnement
        if env_info.pyproject_info:
            # Pour les projets avec pyproject.toml
            if backend_name in ['poetry', 'pdm'] and not backend.capabilities.supports_pyproject_sync:
                return False
        
        return True