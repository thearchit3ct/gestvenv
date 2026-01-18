# ADR 0002: Architecture Async/Await

## Statut
Accepté

## Contexte
GestVenv effectue de nombreuses opérations I/O:
- Téléchargement de packages
- Lecture/écriture de fichiers de configuration
- Exécution de commandes subprocess
- Opérations réseau (PyPI, cache distant)

Ces opérations bénéficieraient d'une exécution asynchrone pour:
- Améliorer les performances
- Permettre l'annulation des opérations
- Supporter le parallélisme

## Décision
Adopter une architecture hybride sync/async:

### Services asynchrones
```python
# Services avec support async natif
AsyncCacheService      # Cache avec aiofiles
AsyncEnvironmentManager # Gestion des environnements
LifecycleController    # Cycle de vie éphémère
```

### Utilitaires async
```python
# gestvenv/utils/async_utils.py
AsyncLock              # Verrou async avec timeout
AsyncSemaphore         # Sémaphore pour limiter la concurrence
AsyncCache             # Cache en mémoire avec TTL
gather_with_concurrency # Parallélisme contrôlé
run_in_executor        # Bridge sync → async
sync_to_async          # Wrapper sync → async
async_to_sync          # Wrapper async → sync
```

### Patterns utilisés
1. **Context Managers Async**
   ```python
   async with async_cache_context(config) as cache:
       await cache.get_package(...)
   ```

2. **Parallélisme contrôlé**
   ```python
   results = await gather_with_concurrency(
       5,  # max concurrent
       *[download(pkg) for pkg in packages]
   )
   ```

3. **Timeout et annulation**
   ```python
   async with asyncio.timeout(30):
       await long_operation()
   ```

## Conséquences

### Positives
- Meilleures performances pour les opérations I/O
- Code plus maintenable avec async/await
- Support natif pour timeouts et annulation
- Parallélisme facile à implémenter

### Négatives
- Complexité accrue (sync + async)
- Debugging plus difficile
- Incompatibilité potentielle avec certaines bibliothèques

### Neutres
- CLI reste synchrone (click est sync)
- Bridge sync/async pour l'interopérabilité
- Tests nécessitent pytest-asyncio

## Notes d'implémentation
- Utiliser `asyncio.run()` comme point d'entrée
- Préférer `async with` pour la gestion des ressources
- Toujours définir des timeouts raisonnables
- Documenter si une fonction est async ou sync
