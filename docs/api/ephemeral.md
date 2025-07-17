# API Référence - Environnements Éphémères

## Module `gestvenv.core.ephemeral`

### Context Managers

#### `ephemeral(name=None, **kwargs)`

Context manager asynchrone pour créer un environnement éphémère avec nettoyage automatique.

**Paramètres:**
- `name` (str, optional): Nom de l'environnement. Si omis, un nom est généré automatiquement.
- `backend` (Backend, optional): Backend à utiliser (UV, PIP, PDM, POETRY). Défaut: UV.
- `python_version` (str, optional): Version Python à utiliser. Défaut: "3.11".
- `ttl` (int, optional): Time-to-live en secondes. Si défini, l'environnement est détruit après ce délai.
- `max_idle_time` (int, optional): Temps d'inactivité maximum en secondes. Défaut: 300.
- `isolation_level` (IsolationLevel, optional): Niveau d'isolation. Défaut: PROCESS.
- `security_mode` (SecurityMode, optional): Mode de sécurité. Défaut: RESTRICTED.
- `resource_limits` (ResourceLimits, optional): Limites de ressources.
- `storage_backend` (StorageBackend, optional): Backend de stockage. Défaut: TMPFS.
- `tags` (dict, optional): Tags personnalisés pour l'environnement.

**Retourne:**
- `EphemeralEnvironment`: Environnement éphémère configuré.

**Exemple:**
```python
import asyncio
from gestvenv import ephemeral
from gestvenv.core.models import Backend
from gestvenv.core.ephemeral import IsolationLevel, ResourceLimits

async def main():
    # Utilisation basique
    async with ephemeral("test") as env:
        await env.install(["requests"])
        result = await env.execute("python --version")
        print(result.stdout)
    
    # Configuration avancée
    limits = ResourceLimits(max_memory=2048, max_disk=4096)
    async with ephemeral(
        "advanced",
        backend=Backend.UV,
        python_version="3.12",
        ttl=3600,
        isolation_level=IsolationLevel.CONTAINER,
        resource_limits=limits
    ) as env:
        # Utilisation de l'environnement isolé
        pass

asyncio.run(main())
```

#### `ephemeral_sync(name=None, **kwargs)`

Version synchrone du context manager pour les cas simples sans async.

**Note:** Utilise `asyncio.run()` en interne, donc ne peut pas être utilisé dans un contexte async existant.

**Paramètres:** Identiques à `ephemeral()`.

**Exemple:**
```python
from gestvenv import ephemeral_sync

with ephemeral_sync("test") as env:
    env.install(["requests"])
    result = env.execute("python -c 'import requests; print(\"OK\")'")
    print(result.stdout)
```

### Classes

#### `EphemeralEnvironment`

Représente un environnement virtuel éphémère.

**Attributs:**
- `id` (str): Identifiant unique UUID.
- `name` (str): Nom de l'environnement.
- `backend` (Backend): Backend utilisé.
- `python_version` (str): Version Python.
- `status` (EphemeralStatus): État actuel.
- `storage_path` (Path): Chemin de stockage.
- `venv_path` (Path): Chemin du virtualenv.
- `resource_limits` (ResourceLimits): Limites configurées.
- `isolation_level` (IsolationLevel): Niveau d'isolation.
- `security_mode` (SecurityMode): Mode de sécurité.
- `created_at` (datetime): Date de création.
- `last_activity` (datetime): Dernière activité.
- `packages` (List[str]): Packages installés.
- `tags` (Dict[str, str]): Tags personnalisés.

**Propriétés:**
- `is_active` (bool): True si l'environnement est actif (READY ou RUNNING).
- `age_seconds` (int): Âge en secondes depuis la création.
- `idle_seconds` (int): Temps d'inactivité en secondes.

**Méthodes:**
- `update_activity()`: Met à jour le timestamp de dernière activité.
- `is_expired() -> bool`: Vérifie si le TTL est expiré.
- `is_idle_expired() -> bool`: Vérifie si le temps d'inactivité est dépassé.

**Méthodes ajoutées par le context manager:**
- `execute(command: str, timeout: Optional[int] = None, capture_output: bool = True) -> OperationResult`: Exécute une commande.
- `install(packages: Union[str, List[str]], upgrade: bool = False) -> OperationResult`: Installe des packages.

#### `ResourceLimits`

Définit les limites de ressources pour un environnement.

**Attributs:**
- `max_memory` (Optional[int]): Limite mémoire en MB.
- `max_disk` (Optional[int]): Limite disque en MB.
- `max_processes` (int): Nombre maximum de processus. Défaut: 10.
- `max_cpu_percent` (Optional[float]): Pourcentage CPU maximum.
- `network_access` (bool): Autoriser l'accès réseau. Défaut: True.

**Exemple:**
```python
from gestvenv.core.ephemeral import ResourceLimits

limits = ResourceLimits(
    max_memory=2048,      # 2GB
    max_disk=5120,        # 5GB
    max_processes=20,
    max_cpu_percent=50.0,
    network_access=False  # Isolation réseau
)
```

#### `OperationResult`

Résultat de l'exécution d'une commande.

**Attributs:**
- `returncode` (int): Code de retour de la commande.
- `stdout` (str): Sortie standard.
- `stderr` (str): Sortie d'erreur.
- `duration` (float): Durée d'exécution en secondes.
- `command` (str): Commande exécutée.
- `success` (bool): True si returncode == 0.

#### `EphemeralConfig`

Configuration globale pour le système d'environnements éphémères.

**Attributs:**
- `default_ttl` (int): TTL par défaut. Défaut: 3600.
- `max_concurrent` (int): Nombre max d'environnements simultanés. Défaut: 50.
- `max_total_memory_mb` (int): Mémoire totale max. Défaut: 8192.
- `max_total_disk_mb` (int): Disque total max. Défaut: 20480.
- `cleanup_interval` (int): Intervalle de nettoyage en secondes. Défaut: 60.
- `force_cleanup_after` (int): Nettoyage forcé après X secondes. Défaut: 7200.
- `storage_backend` (StorageBackend): Backend de stockage. Défaut: TMPFS.
- `base_storage_path` (Path): Chemin de base pour le stockage.
- `default_security_mode` (SecurityMode): Mode de sécurité par défaut.
- `default_isolation_level` (IsolationLevel): Niveau d'isolation par défaut.
- `enable_monitoring` (bool): Activer le monitoring. Défaut: True.
- `monitoring_interval` (int): Intervalle de monitoring. Défaut: 5.
- `enable_preallocation` (bool): Pré-allocation d'environnements. Défaut: True.
- `pool_size` (int): Taille du pool. Défaut: 3.
- `enable_template_cache` (bool): Cache de templates. Défaut: True.

### Énumérations

#### `EphemeralStatus`

États possibles d'un environnement.

```python
class EphemeralStatus(Enum):
    PENDING = "pending"          # En attente de création
    CREATING = "creating"        # Création en cours
    READY = "ready"             # Prêt à l'utilisation
    RUNNING = "running"         # Commande en exécution
    CLEANING_UP = "cleaning_up" # Nettoyage en cours
    DESTROYED = "destroyed"     # Détruit
    FAILED = "failed"           # Échec
```

#### `IsolationLevel`

Niveaux d'isolation disponibles.

```python
class IsolationLevel(Enum):
    PROCESS = "process"      # Isolation par processus (défaut)
    NAMESPACE = "namespace"  # Namespaces Linux
    CONTAINER = "container"  # Docker/Podman
    CHROOT = "chroot"       # Chroot jail
```

#### `StorageBackend`

Backends de stockage disponibles.

```python
class StorageBackend(Enum):
    DISK = "disk"       # Disque standard
    TMPFS = "tmpfs"     # RAM (tmpfs)
    MEMORY = "memory"   # Mémoire pure (/dev/shm)
```

#### `SecurityMode`

Modes de sécurité.

```python
class SecurityMode(Enum):
    PERMISSIVE = "permissive"  # Accès complet
    RESTRICTED = "restricted"   # Accès limité (défaut)
    SANDBOXED = "sandboxed"    # Isolation maximale
```

### Fonctions utilitaires

#### `list_active_environments() -> List[EphemeralEnvironment]`

Retourne la liste de tous les environnements éphémères actifs.

```python
envs = await list_active_environments()
for env in envs:
    print(f"{env.name}: {env.status.value}")
```

#### `cleanup_environment(env_id: str, force: bool = False) -> bool`

Nettoie manuellement un environnement par son ID.

**Paramètres:**
- `env_id` (str): ID de l'environnement.
- `force` (bool): Forcer le nettoyage même si des processus sont actifs.

**Retourne:**
- `bool`: True si le nettoyage a réussi.

#### `get_resource_usage() -> Dict[str, Any]`

Retourne les statistiques globales d'usage des ressources.

**Retourne:**
```python
{
    "active_environments": 5,
    "total_memory_mb": 2048.5,
    "total_disk_mb": 4096.0,
    "max_concurrent": 50,
    "max_total_memory_mb": 8192,
    "max_total_disk_mb": 20480
}
```

#### `shutdown_manager() -> None`

Arrête le gestionnaire global et nettoie tous les environnements.

### Exceptions

#### `EphemeralException`

Exception de base pour tous les problèmes liés aux environnements éphémères.

#### `ResourceExhaustedException`

Levée quand les limites de ressources sont atteintes.

```python
try:
    async with ephemeral("test") as env:
        pass
except ResourceExhaustedException as e:
    print(f"Limite atteinte: {e}")
```

#### `EnvironmentCreationException`

Levée lors d'un échec de création d'environnement.

#### `CleanupException`

Levée lors d'un échec de nettoyage.

#### `IsolationException`

Levée lors d'un problème de configuration d'isolation.

#### `EnvironmentNotFoundException`

Levée quand un environnement n'est pas trouvé.

### Gestionnaire avancé

#### `EphemeralManager`

Gestionnaire principal des environnements éphémères (usage avancé).

```python
from gestvenv.core.ephemeral import EphemeralManager, EphemeralConfig

# Configuration personnalisée
config = EphemeralConfig(
    max_concurrent=100,
    storage_backend=StorageBackend.MEMORY,
    default_isolation_level=IsolationLevel.CONTAINER
)

# Création du gestionnaire
manager = EphemeralManager(config)
await manager.start()

# Utilisation
async with manager.create_ephemeral("custom") as env:
    # ...
    pass

# Arrêt
await manager.stop()
```

### Monitoring avancé

#### `ResourceTracker`

Classe de monitoring des ressources (usage interne).

```python
from gestvenv.core.ephemeral.monitoring import ResourceTracker

tracker = manager.resource_tracker
usage = await tracker.get_current_usage(env)
print(f"Mémoire: {usage.memory_mb}MB")
print(f"CPU: {usage.cpu_percent}%")

# Historique
history = await tracker.get_resource_history(env.id)
```

### Intégration avec ProcessManager

Le `ProcessManager` gère l'exécution sécurisée des commandes dans les environnements.

```python
# Usage interne - exposé via env.execute()
result = await manager.lifecycle_controller.process_manager.run_command(
    env,
    "python script.py",
    timeout=60,
    capture_output=True
)
```

## Exemples avancés

### Gestion d'erreurs complète

```python
from gestvenv import ephemeral
from gestvenv.core.ephemeral import (
    ResourceExhaustedException,
    EnvironmentCreationException,
    CleanupException
)

async def safe_ephemeral_usage():
    try:
        async with ephemeral("test") as env:
            try:
                result = await env.execute("python script.py")
                if not result.success:
                    print(f"Erreur script: {result.stderr}")
                    return False
                return True
            except TimeoutError:
                print("Timeout d'exécution")
                return False
                
    except ResourceExhaustedException:
        print("Trop d'environnements actifs")
        # Attendre ou nettoyer
        return False
        
    except EnvironmentCreationException as e:
        print(f"Création échouée: {e}")
        return False
        
    except CleanupException as e:
        print(f"Nettoyage échoué: {e}")
        # Log pour investigation
        return False
```

### Pool d'environnements personnalisé

```python
from gestvenv.core.ephemeral import EphemeralManager, EphemeralConfig

class EphemeralPool:
    def __init__(self, size=5):
        self.config = EphemeralConfig(
            enable_preallocation=True,
            pool_size=size
        )
        self.manager = EphemeralManager(self.config)
        
    async def __aenter__(self):
        await self.manager.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.manager.stop()
        
    async def get_environment(self):
        return self.manager.create_ephemeral()

# Utilisation
async def main():
    async with EphemeralPool(10) as pool:
        # Utilisation d'environnements du pool
        async with await pool.get_environment() as env:
            await env.install(["requests"])
```

### Monitoring personnalisé

```python
import asyncio
from gestvenv import ephemeral, get_resource_usage

async def monitor_resources():
    """Monitore les ressources en arrière-plan"""
    while True:
        usage = await get_resource_usage()
        if usage['active_environments'] > 40:
            print("⚠️ Charge élevée détectée")
        if usage['total_memory_mb'] > 7000:
            print("⚠️ Mémoire proche de la limite")
        await asyncio.sleep(30)

async def main():
    # Lancer le monitoring
    monitor_task = asyncio.create_task(monitor_resources())
    
    # Utilisation normale
    async with ephemeral("app") as env:
        await env.install(["django"])
        # ...
    
    monitor_task.cancel()
```