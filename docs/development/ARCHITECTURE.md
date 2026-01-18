# Architecture GestVenv

## Vue d'ensemble

GestVenv est un gestionnaire d'environnements virtuels Python moderne et performant.

```
┌─────────────────────────────────────────────────────────────────┐
│                           CLI (click)                            │
│  create | list | install | sync | doctor | cache | ephemeral    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      Core Services                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Environment │  │   Cache     │  │      Ephemeral          │  │
│  │   Manager   │  │  Service    │  │      Manager            │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                 │
└─────────┼────────────────┼─────────────────────┼─────────────────┘
          │                │                     │
┌─────────▼────────────────▼─────────────────────▼─────────────────┐
│                         Backends                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │   pip   │  │   uv    │  │ poetry  │  │   pdm   │             │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

## Structure des modules

```
gestvenv/
├── __init__.py           # Exports principaux
├── cli.py                # Interface ligne de commande
├── cli/
│   └── commands/         # Commandes CLI modulaires
│       ├── diff.py       # Comparaison d'environnements
│       ├── deps.py       # Analyse des dépendances
│       └── security.py   # Scan de sécurité
│
├── core/
│   ├── config_manager.py # Gestion de la configuration
│   ├── environment_manager.py # Gestion des environnements
│   ├── models.py         # Modèles de données
│   ├── exceptions.py     # Exceptions personnalisées
│   └── ephemeral/        # Environnements éphémères
│       ├── manager.py    # Gestionnaire principal
│       ├── lifecycle.py  # Cycle de vie
│       ├── monitoring.py # Monitoring ressources
│       └── cgroups.py    # Isolation cgroups v2
│
├── backends/
│   ├── __init__.py       # Interface commune
│   ├── pip_backend.py    # Backend pip
│   ├── uv_backend.py     # Backend uv
│   ├── poetry_backend.py # Backend poetry
│   └── pdm_backend.py    # Backend pdm
│
├── services/
│   ├── cache_service.py      # Service de cache sync
│   ├── async_cache_service.py # Service de cache async
│   ├── diagnostic_service.py  # Diagnostics
│   └── migration_service.py   # Migrations
│
├── observability/
│   ├── metrics.py        # Métriques Prometheus
│   ├── logging_config.py # Logging structuré
│   └── tracing.py        # Tracing des opérations
│
└── utils/
    ├── async_utils.py    # Utilitaires async
    ├── retry.py          # Logique de retry
    ├── error_handling.py # Gestion d'erreurs enrichie
    ├── debug.py          # Outils de débogage
    └── performance.py    # Monitoring performance
```

## Flux de données

### Création d'environnement
```
User Request
     │
     ▼
┌─────────────┐
│    CLI      │ parse args, validate
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Environment │ check existing, prepare
│   Manager   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Backend    │ pip/uv/poetry/pdm
│  Selection  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Create    │ venv creation
│    Venv     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Install    │ packages from requirements
│  Packages   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Update    │ metadata, index
│  Metadata   │
└─────────────┘
```

### Installation de packages
```
Package Request
     │
     ▼
┌─────────────┐     ┌─────────────┐
│   Cache     │────▶│   Cache     │ hit?
│   Check     │     │   Service   │
└──────┬──────┘     └─────────────┘
       │ miss
       ▼
┌─────────────┐
│  Download   │ from PyPI
│   Package   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Install   │ via backend
│   Package   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Update    │ cache, metrics
│    Cache    │
└─────────────┘
```

## Modèles de données principaux

### EnvironmentInfo
```python
@dataclass
class EnvironmentInfo:
    name: str
    path: Path
    python_version: str
    created_at: datetime
    backend: BackendType
    packages: List[PackageInfo]
    is_active: bool
```

### Config
```python
@dataclass
class Config:
    environments_path: Path
    default_backend: BackendType
    cache_settings: CacheSettings
    logging_level: str
```

### InstallResult
```python
@dataclass
class InstallResult:
    success: bool
    message: str
    packages_installed: List[str]
    packages_failed: List[str]
    execution_time: float
```

## Patterns utilisés

### 1. Strategy Pattern (Backends)
Chaque backend implémente une interface commune, permettant d'interchanger les implémentations.

### 2. Factory Pattern (Environment Creation)
Le manager crée les environnements via une factory qui sélectionne le backend approprié.

### 3. Observer Pattern (Monitoring)
Les métriques et logs sont collectés via des observers non-bloquants.

### 4. Context Manager (Resources)
Les ressources (fichiers, connexions) sont gérées via context managers async.

### 5. Retry with Backoff (Network)
Les opérations réseau utilisent un retry exponentiel avec jitter.

## Points d'extension

### Ajouter un nouveau backend
1. Créer `gestvenv/backends/new_backend.py`
2. Implémenter l'interface `BackendInterface`
3. Enregistrer dans `BackendType` enum
4. Ajouter la détection dans le sélecteur

### Ajouter une nouvelle commande CLI
1. Créer le module dans `gestvenv/cli/commands/`
2. Définir le groupe click
3. Importer dans `cli.py`
4. Ajouter les tests

### Ajouter des métriques
1. Définir dans `observability/metrics.py`
2. Instrumenter le code concerné
3. Documenter dans Grafana dashboard
