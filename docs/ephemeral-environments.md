# Environnements Éphémères GestVenv

Les environnements éphémères sont des environnements virtuels Python temporaires avec nettoyage automatique garanti. Ils sont parfaits pour les tests, les scripts d'automatisation, les CI/CD pipelines, et l'expérimentation.

## Table des matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Démarrage rapide](#démarrage-rapide)
4. [API Python](#api-python)
5. [Interface CLI](#interface-cli)
6. [Configuration](#configuration)
7. [Niveaux d'isolation](#niveaux-disolation)
8. [Monitoring et ressources](#monitoring-et-ressources)
9. [Architecture](#architecture)
10. [Cas d'usage](#cas-dusage)
11. [Référence API](#référence-api)

## Introduction

Les environnements éphémères GestVenv offrent :

- ✨ **Création ultra-rapide** avec uv (< 1 seconde)
- 🧹 **Nettoyage automatique garanti** via context managers
- 🔒 **Isolation de sécurité** à plusieurs niveaux
- 📊 **Monitoring temps réel** des ressources
- 💾 **Stockage optimisé** (tmpfs, mémoire)
- 🚀 **API simple et intuitive**

## Installation

```bash
# Installation de GestVenv avec support éphémère
pip install gestvenv[ephemeral]

# Ou depuis les sources
git clone https://github.com/gestvenv/gestvenv
cd gestvenv
pip install -e .[dev,ephemeral]
```

## Démarrage rapide

### API Python

```python
import asyncio
import gestvenv

async def main():
    # Création d'un environnement éphémère
    async with gestvenv.ephemeral("test-env") as env:
        # Installation de packages
        await env.install(["requests", "pandas"])
        
        # Exécution de code
        result = await env.execute("python -c 'import requests; print(requests.__version__)'")
        print(result.stdout)
        
    # L'environnement est automatiquement nettoyé

asyncio.run(main())
```

### Version synchrone

```python
from gestvenv import ephemeral_sync

# Pour les cas simples sans async
with ephemeral_sync("test-env") as env:
    env.install(["requests"])
    result = env.execute("python -c 'import requests; print(\"OK\")'")
    print(result.stdout)
```

### CLI

```bash
# Créer un environnement interactif
gestvenv ephemeral create test-env --interactive

# Avec packages pré-installés
gestvenv ephemeral create --packages "requests,pandas" --ttl 3600

# Depuis un fichier requirements
gestvenv ephemeral create --requirements requirements.txt
```

## API Python

### Context Manager Principal

```python
async with gestvenv.ephemeral(
    name="my-env",                    # Nom optionnel
    backend=Backend.UV,                # Backend (uv, pip, pdm, poetry)
    python_version="3.11",             # Version Python
    ttl=3600,                         # Durée de vie en secondes
    isolation_level=IsolationLevel.PROCESS,  # Niveau d'isolation
    resource_limits=ResourceLimits(    # Limites de ressources
        max_memory=1024,              # MB
        max_disk=2048,                # MB
        max_processes=10,
        network_access=True
    )
) as env:
    # Utilisation de l'environnement
    pass
```

### Méthodes disponibles

```python
# Installation de packages
await env.install(["django", "pytest"])

# Exécution de commandes
result = await env.execute("python manage.py migrate")
print(f"Code retour: {result.returncode}")
print(f"Sortie: {result.stdout}")
print(f"Erreurs: {result.stderr}")

# Propriétés de l'environnement
print(f"ID: {env.id}")
print(f"Nom: {env.name}")
print(f"Status: {env.status}")
print(f"Âge: {env.age_seconds}s")
print(f"Chemin: {env.storage_path}")
```

### Gestion avancée

```python
from gestvenv.core.ephemeral import (
    list_active_environments,
    cleanup_environment,
    get_resource_usage
)

# Lister les environnements actifs
envs = await list_active_environments()
for env in envs:
    print(f"{env.name}: {env.status.value}")

# Nettoyage manuel
await cleanup_environment(env_id, force=True)

# Statistiques globales
usage = await get_resource_usage()
print(f"Mémoire utilisée: {usage['total_memory_mb']}MB")
```

## Interface CLI

### Commandes principales

```bash
# Créer un environnement
gestvenv ephemeral create [NAME] [OPTIONS]
  --backend {uv,pip,pdm,poetry}     # Backend à utiliser (défaut: uv)
  --python VERSION                   # Version Python
  --ttl SECONDS                      # Durée de vie
  --packages LIST                    # Packages à installer
  --requirements FILE                # Fichier requirements.txt
  --interactive                      # Mode interactif

# Lister les environnements
gestvenv ephemeral list [--format {table,json}]

# Nettoyer des environnements
gestvenv ephemeral cleanup [ENV_ID]
  --all                             # Nettoyer tous les environnements
  --force                           # Forcer le nettoyage

# Statistiques
gestvenv ephemeral stats [--format {table,json}]
```

### Mode interactif

```bash
$ gestvenv ephemeral create test --interactive
🚀 Création de l'environnement éphémère...
✅ Environnement créé: test (ID: a1b2c3d4)
📁 Stockage: /tmp/gestvenv-ephemeral/a1b2c3d4...
🐍 Python: 3.11
⚙️ Backend: uv

💡 Mode interactif - tapez 'exit' pour quitter
Commandes disponibles:
  install <package>  - Installer un package
  run <command>      - Exécuter une commande
  info               - Informations sur l'environnement
  exit               - Quitter

test> install requests
✅ requests installé

test> run python -c "import requests; print(requests.__version__)"
2.31.0

test> exit
🧹 Nettoyage automatique en cours...
✅ Environnement éphémère terminé
```

## Configuration

### Configuration globale

```toml
# ~/.config/gestvenv/config.toml
[ephemeral]
default_ttl = 3600                    # 1 heure par défaut
max_concurrent = 50                   # Environnements simultanés max
max_total_memory_mb = 8192           # 8GB total max
max_total_disk_mb = 20480            # 20GB total max
storage_backend = "tmpfs"            # tmpfs, memory, disk
default_isolation_level = "process"   # process, namespace, container, chroot
enable_monitoring = true
cleanup_interval = 60                 # Secondes
```

### Variables d'environnement

```bash
export GESTVENV_EPHEMERAL_TTL=7200
export GESTVENV_EPHEMERAL_BACKEND=uv
export GESTVENV_EPHEMERAL_STORAGE=/tmp/my-ephemeral
export GESTVENV_EPHEMERAL_MAX_CONCURRENT=100
```

### Configuration par code

```python
from gestvenv.core.ephemeral import EphemeralConfig, StorageBackend

config = EphemeralConfig(
    default_ttl=7200,
    max_concurrent=100,
    storage_backend=StorageBackend.MEMORY,
    enable_monitoring=True,
    enable_preallocation=True
)

# Utilisation avec configuration personnalisée
manager = EphemeralManager(config)
async with manager.create_ephemeral("test") as env:
    # ...
```

## Niveaux d'isolation

### 1. PROCESS (défaut)

Isolation basique par processus avec variables d'environnement isolées.

```python
async with gestvenv.ephemeral(
    "test",
    isolation_level=IsolationLevel.PROCESS
) as env:
    # Environnement isolé par processus
    pass
```

### 2. NAMESPACE (Linux uniquement)

Isolation par namespaces Linux (PID, NET, MNT, IPC, UTS).

```python
async with gestvenv.ephemeral(
    "test",
    isolation_level=IsolationLevel.NAMESPACE,
    resource_limits=ResourceLimits(network_access=False)
) as env:
    # Isolation complète avec namespaces
    pass
```

### 3. CONTAINER

Isolation par container Docker/Podman avec image auto-générée.

```python
async with gestvenv.ephemeral(
    "test",
    isolation_level=IsolationLevel.CONTAINER
) as env:
    # Environnement dans un container isolé
    pass
```

### 4. CHROOT

Isolation par chroot jail (nécessite root).

```python
async with gestvenv.ephemeral(
    "test",
    isolation_level=IsolationLevel.CHROOT
) as env:
    # Environnement en chroot jail
    pass
```

## Monitoring et ressources

### Limites de ressources

```python
from gestvenv.core.ephemeral import ResourceLimits

limits = ResourceLimits(
    max_memory=2048,        # MB
    max_disk=4096,         # MB
    max_processes=20,
    max_cpu_percent=50.0,
    network_access=True
)

async with gestvenv.ephemeral("limited", resource_limits=limits) as env:
    # Environnement avec limites
    pass
```

### Monitoring temps réel

```python
# Récupération de l'usage d'un environnement
from gestvenv.core.ephemeral.monitoring import ResourceTracker

tracker = ResourceTracker(manager)
usage = await tracker.get_current_usage(env)
print(f"Mémoire: {usage.memory_mb}MB")
print(f"CPU: {usage.cpu_percent}%")
print(f"Disque: {usage.disk_mb}MB")

# Historique des ressources
history = await tracker.get_resource_history(env.id)
for usage in history:
    print(f"{usage.timestamp}: {usage.memory_mb}MB")
```

### Backends de stockage

```python
from gestvenv.core.ephemeral import StorageBackend

# tmpfs (RAM) - Ultra rapide
async with gestvenv.ephemeral(
    "fast",
    storage_backend=StorageBackend.TMPFS
) as env:
    pass

# Mémoire pure (/dev/shm)
async with gestvenv.ephemeral(
    "memory",
    storage_backend=StorageBackend.MEMORY
) as env:
    pass

# Disque standard
async with gestvenv.ephemeral(
    "disk",
    storage_backend=StorageBackend.DISK
) as env:
    pass
```

## Architecture

### Composants principaux

```
gestvenv/core/ephemeral/
├── __init__.py          # Exports publics
├── models.py            # Modèles de données
├── manager.py           # Gestionnaire principal
├── lifecycle.py         # Contrôleur de cycle de vie
├── storage.py           # Gestion du stockage
├── monitoring.py        # Monitoring des ressources
├── cleanup.py           # Planificateur de nettoyage
├── context.py           # Context managers
└── exceptions.py        # Exceptions spécifiques
```

### Flux de création

```mermaid
graph TD
    A[ephemeral()] --> B[EphemeralManager]
    B --> C[Vérification limites]
    C --> D[StorageManager.allocate]
    D --> E[LifecycleController.create]
    E --> F[Création venv]
    F --> G[Configuration isolation]
    G --> H[Environnement prêt]
    H --> I[Utilisation]
    I --> J[Cleanup automatique]
```

### Cycle de vie

1. **PENDING** : En attente de création
2. **CREATING** : Création en cours
3. **READY** : Prêt à l'utilisation
4. **RUNNING** : Commande en exécution
5. **CLEANING_UP** : Nettoyage en cours
6. **DESTROYED** : Nettoyé et détruit

## Cas d'usage

### Tests automatisés

```python
import pytest
import gestvenv

@pytest.fixture
async def test_env():
    """Fixture pour environnement de test isolé"""
    async with gestvenv.ephemeral("pytest-env") as env:
        await env.install(["pytest", "pytest-asyncio"])
        yield env

async def test_my_package(test_env):
    """Test avec environnement isolé"""
    result = await test_env.execute("pytest tests/")
    assert result.returncode == 0
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
steps:
  - name: Test avec environnement éphémère
    run: |
      gestvenv ephemeral create ci-env \
        --requirements requirements.txt \
        --ttl 600
      
      gestvenv run --env ci-env pytest tests/
      gestvenv run --env ci-env flake8 src/
      
      gestvenv ephemeral cleanup ci-env
```

### Scripts d'automatisation

```python
async def process_data_files(files):
    """Traitement de fichiers avec dépendances isolées"""
    
    async with gestvenv.ephemeral("data-processor") as env:
        # Installation des dépendances spécifiques
        await env.install(["pandas", "numpy", "openpyxl"])
        
        for file in files:
            # Traitement isolé
            result = await env.execute(
                f"python process.py {file}"
            )
            
            if result.returncode != 0:
                print(f"Erreur: {result.stderr}")
```

### Sandbox d'expérimentation

```python
async def try_package(package_name):
    """Tester un package sans polluer le système"""
    
    async with gestvenv.ephemeral(
        f"try-{package_name}",
        isolation_level=IsolationLevel.CONTAINER
    ) as env:
        # Installation sécurisée
        await env.install([package_name])
        
        # Test du package
        result = await env.execute(
            f"python -c 'import {package_name}; print({package_name}.__version__)'"
        )
        
        print(f"{package_name} version: {result.stdout}")
```

## Référence API

### Classes principales

#### EphemeralEnvironment

```python
@dataclass
class EphemeralEnvironment:
    id: str                              # UUID unique
    name: Optional[str]                  # Nom optionnel
    backend: Backend                     # Backend utilisé
    python_version: str                  # Version Python
    status: EphemeralStatus             # État actuel
    storage_path: Optional[Path]        # Chemin de stockage
    resource_limits: ResourceLimits     # Limites configurées
    isolation_level: IsolationLevel     # Niveau d'isolation
    
    # Méthodes
    is_active() -> bool
    age_seconds() -> int
    is_expired() -> bool
    update_activity()
```

#### ResourceLimits

```python
@dataclass
class ResourceLimits:
    max_memory: Optional[int] = None     # MB
    max_disk: Optional[int] = None       # MB
    max_processes: int = 10
    max_cpu_percent: Optional[float] = None
    network_access: bool = True
```

#### OperationResult

```python
@dataclass
class OperationResult:
    returncode: int
    stdout: str
    stderr: str
    duration: float
    command: str
    success: bool  # returncode == 0
```

### Fonctions utilitaires

```python
# Context manager principal
async with ephemeral(name, **kwargs) -> EphemeralEnvironment

# Version synchrone
with ephemeral_sync(name, **kwargs) -> EphemeralEnvironment

# Gestion des environnements
await list_active_environments() -> List[EphemeralEnvironment]
await cleanup_environment(env_id: str, force: bool = False) -> bool
await get_resource_usage() -> Dict[str, Any]
await shutdown_manager() -> None
```

### Exceptions

```python
EphemeralException           # Exception de base
ResourceExhaustedException   # Limites de ressources atteintes
EnvironmentCreationException # Échec de création
CleanupException            # Échec de nettoyage
IsolationException          # Échec d'isolation
SecurityException           # Problème de sécurité
TimeoutException           # Timeout d'opération
EnvironmentNotFoundException # Environnement non trouvé
```

## Bonnes pratiques

### 1. Toujours utiliser le context manager

```python
# ✅ Bon
async with gestvenv.ephemeral("test") as env:
    await env.install(["requests"])

# ❌ Mauvais - pas de cleanup garanti
env = await create_environment("test")
await env.install(["requests"])
```

### 2. Gérer les erreurs

```python
try:
    async with gestvenv.ephemeral("test") as env:
        result = await env.execute("python script.py")
        if not result.success:
            print(f"Erreur: {result.stderr}")
except ResourceExhaustedException:
    print("Trop d'environnements actifs")
except EnvironmentCreationException as e:
    print(f"Création échouée: {e}")
```

### 3. Configurer les limites appropriées

```python
# Pour les tests courts
limits = ResourceLimits(
    max_memory=512,      # 512MB suffisant
    max_disk=1024,       # 1GB
    max_processes=5
)

# Pour les traitements lourds
limits = ResourceLimits(
    max_memory=4096,     # 4GB
    max_disk=10240,      # 10GB
    max_processes=50
)
```

### 4. Choisir le bon backend de stockage

```python
# Tests rapides -> tmpfs
StorageBackend.TMPFS

# Grande quantité de données -> disk
StorageBackend.DISK

# Sécurité maximale -> memory
StorageBackend.MEMORY
```

### 5. Monitoring en production

```python
# Activer le monitoring pour la production
config = EphemeralConfig(
    enable_monitoring=True,
    monitoring_interval=5
)

# Surveiller l'usage global
usage = await get_resource_usage()
if usage['active_environments'] > 40:
    logger.warning("Proche de la limite d'environnements")
```

## Dépannage

### Environnement non nettoyé

```bash
# Forcer le nettoyage de tous les environnements
gestvenv ephemeral cleanup --all --force

# Vérifier les processus orphelins
ps aux | grep gestvenv-ephemeral
```

### Erreur de création

```python
# Activer les logs de debug
import logging
logging.getLogger('gestvenv.core.ephemeral').setLevel(logging.DEBUG)

# Vérifier les prérequis
- Python 3.8+
- uv installé (pour backend uv)
- Docker/Podman (pour isolation container)
- Privilèges root (pour chroot)
```

### Performance

```python
# Optimisations
- Utiliser backend uv (le plus rapide)
- Activer la pré-allocation
- Utiliser tmpfs pour les tests courts
- Limiter le monitoring si non nécessaire

config = EphemeralConfig(
    enable_preallocation=True,
    pool_size=5,  # Pré-créer 5 environnements
    enable_template_cache=True
)
```

## Intégration avec l'écosystème GestVenv v2.0

### Extension VS Code

Les environnements éphémères sont intégrés dans l'extension VS Code :

```typescript
// Créer un environnement éphémère depuis VS Code
const env = await vscode.commands.executeCommand(
    'gestvenv.createEphemeral', 
    {
        name: 'test-env',
        packages: ['pytest', 'mypy']
    }
);

// Exécuter des tests dans l'environnement isolé
const result = await vscode.commands.executeCommand(
    'gestvenv.runInEphemeral',
    env.id,
    'pytest tests/'
);
```

### API Web

L'API REST expose les environnements éphémères :

```bash
# Créer via API
curl -X POST http://localhost:8000/api/v1/ephemeral/environments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "api-test",
    "backend": "uv",
    "packages": ["requests", "pandas"],
    "ttl": 600
  }'

# WebSocket pour monitoring temps réel
wscat -c ws://localhost:8000/ws
> {"type": "subscribe", "environment_id": "ephemeral:api-test"}
```

### Interface Web

Dashboard avec visualisation temps réel :
- Graphiques de ressources (CPU, mémoire, disque)
- Liste interactive des environnements actifs
- Actions rapides (create, cleanup, inspect)

## Performance v2.0

### Benchmarks

| Opération | v1.2 | v2.0 | Amélioration |
|-----------|------|------|--------------|
| Création (uv) | 1.2s | 0.8s | 33% plus rapide |
| Installation packages | 5s | 3s | 40% plus rapide |
| Cleanup | 0.5s | 0.2s | 60% plus rapide |
| Monitoring overhead | 5% | 2% | 60% moins |

### Optimisations v2.0

1. **Pool de pré-allocation** : Environnements prêts à l'emploi
2. **Cache de templates** : Réutilisation des configurations
3. **Compression zstd** : Stockage 3x plus compact
4. **Parallélisation** : Opérations async optimisées

## Changelog

### Version 2.0.0 (2024-07-17)
- **NOUVEAU** : Pool d'environnements pré-créés pour démarrage instantané
- **NOUVEAU** : Cache de templates avec compression zstd
- **NOUVEAU** : Intégration complète VS Code avec IntelliSense
- **NOUVEAU** : API REST/WebSocket pour usage distant
- **NOUVEAU** : Interface web avec monitoring temps réel
- **AMÉLIORATION** : Performance 30-60% supérieure sur toutes les opérations
- **AMÉLIORATION** : Utilisation mémoire réduite de 50%
- **FIX** : Correction des fuites mémoire dans le monitoring
- **FIX** : Meilleure gestion des signaux système (SIGTERM, SIGINT)

### Version 1.2.0
- Ajout initial du système d'environnements éphémères
- Support de 4 niveaux d'isolation
- Monitoring temps réel des ressources
- CLI complète pour la gestion

### Roadmap v2.1
- Support Kubernetes pour isolation cloud-native
- Intégration GitHub Actions native
- Snapshots d'environnements pour réutilisation
- Métriques Prometheus/Grafana