# gestvenv/core/strategies.py
"""
Stratégies de configuration pour GestVenv v1.1
==============================================

Ce module définit les stratégies optimales pour :
- Migration v1.0 → v1.1
- Selection des backends
- Templates par défaut
- Cache intelligent

Version: 1.1.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path
import time
from enum import Enum

# ===== STRATÉGIES DE MIGRATION =====

class MigrationMode(Enum):
    """Modes de migration disponibles."""
    NEVER = "never"           # Jamais migrer automatiquement
    PROMPT = "prompt"         # Demander à l'utilisateur
    AUTO = "auto"            # Migration automatique
    SMART = "smart"          # Migration intelligente contextuelle


@dataclass
class MigrationStrategy:
    """Configuration de la stratégie de migration."""
    mode: MigrationMode = MigrationMode.PROMPT
    create_backup: bool = True
    rollback_available: bool = True
    max_backup_age_days: int = 30
    prompt_message: str = (
        "Environnement '{env_name}' détecté en v{old_version}. "
        "Migrer vers v{new_version} pour bénéficier des nouvelles fonctionnalités ? (y/N)"
    )
    
    def should_migrate(self, env_name: str, current_version: str, target_version: str) -> bool:
        """Détermine si la migration doit être proposée."""
        if self.mode == MigrationMode.NEVER:
            return False
        elif self.mode == MigrationMode.AUTO:
            return True
        elif self.mode == MigrationMode.PROMPT:
            return True  # Sera géré par l'interface utilisateur
        elif self.mode == MigrationMode.SMART:
            # Migration intelligente : migre seulement si bénéfices évidents
            return self._has_clear_benefits(current_version, target_version)
        return False
    
    def _has_clear_benefits(self, current: str, target: str) -> bool:
        """Vérifie s'il y a des bénéfices clairs à migrer."""
        # Exemples de bénéfices clairs
        benefits = [
            "1.0.0->1.1.0",  # Support pyproject.toml + backends modernes
        ]
        migration_path = f"{current}->{target}"
        return migration_path in benefits


# ===== STRATÉGIES DE BACKEND =====

class BackendSelectionStrategy(Enum):
    """Stratégies de sélection des backends."""
    CONSERVATIVE = "conservative"  # Toujours pip
    PERFORMANCE = "performance"    # Préfère uv/performance
    AUTO = "auto"                 # Détection intelligente
    USER_CHOICE = "user_choice"   # Laisse l'utilisateur choisir


@dataclass
class BackendStrategy:
    """Configuration de la stratégie de backend."""
    selection_mode: BackendSelectionStrategy = BackendSelectionStrategy.CONSERVATIVE
    fallback_chain: List[str] = field(default_factory=lambda: ["pip"])
    auto_upgrade: bool = False
    performance_priority: bool = False
    
    def get_preferred_backend(self, project_context: Optional[Dict] = None) -> str:
        """Retourne le backend préféré selon la stratégie."""
        if self.selection_mode == BackendSelectionStrategy.CONSERVATIVE:
            return "pip"
        
        elif self.selection_mode == BackendSelectionStrategy.PERFORMANCE:
            # Préfère uv si disponible, sinon pip
            if self._is_backend_available("uv"):
                return "uv"
            return "pip"
        
        elif self.selection_mode == BackendSelectionStrategy.AUTO:
            return self._detect_optimal_backend(project_context)
        
        else:  # USER_CHOICE
            return "pip"  # Valeur par défaut, l'utilisateur peut changer
    
    def _is_backend_available(self, backend: str) -> bool:
        """Vérifie si un backend est disponible."""
        # Implémentation simplifiée - à remplacer par une vraie détection
        import shutil
        return shutil.which(backend) is not None
    
    def _detect_optimal_backend(self, project_context: Optional[Dict] = None) -> str:
        """Détection intelligente du backend optimal."""
        if not project_context:
            return "pip"
        
        # Si pyproject.toml avec build-backend spécifique
        if "pyproject_info" in project_context:
            build_backend = project_context["pyproject_info"].get("build_system", {}).get("build-backend", "")
            if "poetry" in build_backend and self._is_backend_available("poetry"):
                return "poetry"
            elif "pdm" in build_backend and self._is_backend_available("pdm"):
                return "pdm"
        
        # Si uv disponible et pas de contraintes spéciales
        if self._is_backend_available("uv"):
            return "uv"
        
        return "pip"


# ===== TEMPLATES ESSENTIELS =====

ESSENTIAL_TEMPLATES = {
    "python_basic": {
        "name": "Projet Python Basique",
        "description": "Template minimal pour un projet Python",
        "pyproject_template": {
            "project": {
                "name": "{project_name}",
                "version": "0.1.0",
                "description": "Un nouveau projet Python",
                "requires-python": ">=3.8",
                "dependencies": []
            },
            "project.optional-dependencies": {
                "dev": ["pytest>=7.0", "black", "mypy", "ruff"]
            },
            "build-system": {
                "requires": ["setuptools>=65.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            }
        },
        "files_to_create": [
            "src/{project_name}/__init__.py",
            "tests/__init__.py",
            "tests/test_{project_name}.py",
            "README.md",
            ".gitignore"
        ]
    },
    
    "web_fastapi": {
        "name": "API Web FastAPI",
        "description": "API REST moderne avec FastAPI",
        "pyproject_template": {
            "project": {
                "name": "{project_name}",
                "version": "0.1.0",
                "description": "API web avec FastAPI",
                "requires-python": ">=3.8",
                "dependencies": [
                    "fastapi>=0.104.0",
                    "uvicorn[standard]>=0.24.0",
                    "pydantic>=2.0.0"
                ]
            },
            "project.optional-dependencies": {
                "dev": ["pytest>=7.0", "httpx", "black", "mypy", "ruff"],
                "prod": ["gunicorn", "python-multipart"]
            }
        },
        "files_to_create": [
            "src/{project_name}/__init__.py",
            "src/{project_name}/main.py",
            "src/{project_name}/api/__init__.py", 
            "src/{project_name}/models/__init__.py",
            "tests/test_api.py",
            "README.md",
            ".gitignore"
        ]
    },
    
    "data_science": {
        "name": "Analyse de Données",
        "description": "Projet d'analyse de données avec les outils essentiels",
        "pyproject_template": {
            "project": {
                "name": "{project_name}",
                "version": "0.1.0", 
                "description": "Projet d'analyse de données",
                "requires-python": ">=3.8",
                "dependencies": [
                    "pandas>=2.0.0",
                    "numpy>=1.24.0",
                    "matplotlib>=3.7.0",
                    "seaborn>=0.12.0",
                    "jupyter>=1.0.0"
                ]
            },
            "project.optional-dependencies": {
                "dev": ["pytest>=7.0", "black", "mypy", "ruff"],
                "ml": ["scikit-learn", "scipy", "plotly"],
                "export": ["openpyxl", "xlsxwriter"]
            }
        },
        "files_to_create": [
            "notebooks/01_exploration.ipynb",
            "src/{project_name}/__init__.py",
            "src/{project_name}/data/__init__.py",
            "src/{project_name}/analysis/__init__.py",
            "tests/test_analysis.py",
            "data/raw/.gitkeep",
            "data/processed/.gitkeep",
            "README.md",
            ".gitignore"
        ]
    },
    
    "cli_app": {
        "name": "Application CLI",
        "description": "Application en ligne de commande moderne",
        "pyproject_template": {
            "project": {
                "name": "{project_name}",
                "version": "0.1.0",
                "description": "Application CLI",
                "requires-python": ">=3.8",
                "dependencies": [
                    "click>=8.0.0",
                    "rich>=13.0.0",
                    "typer>=0.9.0"
                ]
            },
            "project.optional-dependencies": {
                "dev": ["pytest>=7.0", "black", "mypy", "ruff"]
            },
            "project.scripts": {
                "{project_name}": "{project_name}.cli:main"
            }
        },
        "files_to_create": [
            "src/{project_name}/__init__.py",
            "src/{project_name}/cli.py",
            "src/{project_name}/core.py",
            "tests/test_cli.py",
            "README.md",
            ".gitignore"
        ]
    }
}


# ===== STRATÉGIE DE CACHE =====

@dataclass
class CacheStrategy:
    """Configuration du cache intelligent."""
    enabled: bool = True
    ttl_seconds: int = 3600  # 1 heure
    max_entries: int = 100
    persist_to_disk: bool = True
    cache_location: Optional[Path] = None
    invalidation_method: str = "mtime"  # mtime, hash, manual
    
    def __post_init__(self):
        if self.cache_location is None:
            self.cache_location = Path.home() / ".gestvenv" / "cache"
    
    def should_cache_entry(self, file_path: Path) -> bool:
        """Détermine si un fichier doit être mis en cache."""
        if not self.enabled:
            return False
        
        # Cache seulement les fichiers pyproject.toml et requirements.txt
        return file_path.name in ["pyproject.toml", "requirements.txt", "Pipfile"]
    
    def is_cache_valid(self, cache_entry: Dict, file_path: Path) -> bool:
        """Vérifie si une entrée de cache est toujours valide."""
        if not file_path.exists():
            return False
        
        # Vérification TTL
        age = time.time() - cache_entry.get("cached_at", 0)
        if age > self.ttl_seconds:
            return False
        
        # Vérification mtime
        if self.invalidation_method == "mtime":
            file_mtime = file_path.stat().st_mtime
            cached_mtime = cache_entry.get("file_mtime", 0)
            return file_mtime == cached_mtime
        
        return True


# ===== CONFIGURATION GLOBALE DES STRATÉGIES =====

@dataclass
class GestVenvStrategies:
    """Configuration globale des stratégies GestVenv."""
    migration: MigrationStrategy = field(default_factory=MigrationStrategy)
    backend: BackendStrategy = field(default_factory=BackendStrategy)
    cache: CacheStrategy = field(default_factory=CacheStrategy)
    templates: Dict[str, Any] = field(default_factory=lambda: ESSENTIAL_TEMPLATES)
    
    # Paramètres généraux
    auto_detect_project_type: bool = True
    suggest_optimizations: bool = True
    verbose_operations: bool = False
    
    @classmethod
    def get_conservative_config(cls) -> 'GestVenvStrategies':
        """Configuration conservatrice pour maximiser la compatibilité."""
        return cls(
            migration=MigrationStrategy(mode=MigrationMode.PROMPT),
            backend=BackendStrategy(selection_mode=BackendSelectionStrategy.CONSERVATIVE),
            cache=CacheStrategy(enabled=True, ttl_seconds=7200),  # 2h plus sûr
            auto_detect_project_type=False,
            suggest_optimizations=False
        )
    
    @classmethod
    def get_performance_config(cls) -> 'GestVenvStrategies':
        """Configuration optimisée pour les performances."""
        return cls(
            migration=MigrationStrategy(mode=MigrationMode.SMART),
            backend=BackendStrategy(
                selection_mode=BackendSelectionStrategy.PERFORMANCE,
                fallback_chain=["uv", "pip"],
                performance_priority=True
            ),
            cache=CacheStrategy(enabled=True, ttl_seconds=3600, max_entries=200),
            auto_detect_project_type=True,
            suggest_optimizations=True
        )
    
    @classmethod
    def get_developer_config(cls) -> 'GestVenvStrategies':
        """Configuration pour développeurs avancés."""
        return cls(
            migration=MigrationStrategy(mode=MigrationMode.AUTO),
            backend=BackendStrategy(selection_mode=BackendSelectionStrategy.AUTO),
            cache=CacheStrategy(enabled=True, ttl_seconds=1800),  # 30min pour dev rapide
            auto_detect_project_type=True,
            suggest_optimizations=True,
            verbose_operations=True
        )


# ===== FONCTIONS UTILITAIRES =====

def get_default_strategies() -> GestVenvStrategies:
    """Retourne la configuration de stratégies par défaut (conservatrice)."""
    return GestVenvStrategies.get_conservative_config()


def detect_optimal_strategies(user_context: Optional[Dict] = None) -> GestVenvStrategies:
    """Détecte les stratégies optimales selon le contexte utilisateur."""
    if not user_context:
        return get_default_strategies()
    
    # Utilisateur expérimenté avec uv installé
    if (user_context.get("experience_level") == "advanced" and 
        user_context.get("has_uv", False)):
        return GestVenvStrategies.get_performance_config()
    
    # Développeur avec besoins spécifiques
    if user_context.get("is_developer", False):
        return GestVenvStrategies.get_developer_config()
    
    # Par défaut : conservateur
    return GestVenvStrategies.get_conservative_config()


# ===== EXPORTS =====

__all__ = [
    'MigrationMode',
    'MigrationStrategy', 
    'BackendSelectionStrategy',
    'BackendStrategy',
    'CacheStrategy',
    'GestVenvStrategies',
    'ESSENTIAL_TEMPLATES',
    'get_default_strategies',
    'detect_optimal_strategies'
]