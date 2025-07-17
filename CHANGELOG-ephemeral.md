# CHANGELOG - Environnements Éphémères

## Version 1.2.0 - Environnements Éphémères

### 🎉 Nouvelle Fonctionnalité Majeure

GestVenv introduit les **Environnements Éphémères** - des environnements virtuels temporaires avec nettoyage automatique garanti, parfaits pour les tests, CI/CD, et l'expérimentation.

### ✨ Fonctionnalités Principales

#### API Python Simple
```python
import gestvenv

async with gestvenv.ephemeral("test-env") as env:
    await env.install(["requests", "pandas"])
    result = await env.execute("python script.py")
    # Nettoyage automatique garanti
```

#### CLI Complète
```bash
# Création interactive
gestvenv ephemeral create test --interactive --packages "requests,pandas"

# Gestion
gestvenv ephemeral list
gestvenv ephemeral cleanup --all
gestvenv ephemeral stats
```

### 🔒 Niveaux d'Isolation

1. **PROCESS** (défaut) - Isolation par processus avec variables d'environnement
2. **NAMESPACE** - Isolation Linux avec namespaces (PID, NET, MNT, IPC, UTS)
3. **CONTAINER** - Isolation Docker/Podman avec images auto-générées
4. **CHROOT** - Isolation chroot jail (nécessite root)

### 📊 Monitoring et Ressources

- **Monitoring temps réel** : CPU, mémoire, disque par environnement
- **Limites configurables** : 
  ```python
  ResourceLimits(
      max_memory=2048,      # MB
      max_disk=4096,        # MB
      max_processes=20,
      max_cpu_percent=50.0,
      network_access=False
  )
  ```
- **Statistiques globales** : Usage total, environnements actifs

### 💾 Backends de Stockage Optimisés

- **TMPFS** : Stockage en RAM pour performance maximale
- **MEMORY** : Mémoire pure via /dev/shm
- **DISK** : Stockage disque standard avec pré-allocation

### 🧹 Gestion du Cycle de Vie

- **TTL configurable** : Destruction automatique après durée définie
- **Timeout d'inactivité** : Nettoyage des environnements inactifs
- **Cleanup scheduler** : Tâche de fond pour nettoyage périodique
- **Nettoyage d'urgence** : Cleanup forcé en cas d'arrêt

### 🚀 Performance

- **Création < 1 seconde** avec backend uv
- **Cache intelligent** pour réutilisation
- **Pré-allocation** d'espace disque
- **Pool d'environnements** (prévu Phase 3)

### 📁 Architecture Implémentée

```
gestvenv/core/ephemeral/
├── __init__.py          # API publique
├── models.py            # Modèles de données (EphemeralEnvironment, ResourceLimits, etc.)
├── manager.py           # Gestionnaire principal avec gestion du cycle de vie
├── context.py           # Context managers (ephemeral, ephemeral_sync)
├── lifecycle.py         # Contrôleur de cycle de vie et isolation
├── storage.py           # Gestion du stockage optimisé
├── monitoring.py        # Monitoring temps réel des ressources
├── cleanup.py           # Planificateur de nettoyage automatique
└── exceptions.py        # Exceptions spécifiques
```

### 🔧 Configuration

```toml
# ~/.config/gestvenv/config.toml
[ephemeral]
default_ttl = 3600                    # 1 heure
max_concurrent = 50                   # Environnements simultanés max
max_total_memory_mb = 8192           # 8GB total
storage_backend = "tmpfs"            # Stockage par défaut
default_isolation_level = "process"   # Isolation par défaut
cleanup_interval = 60                # Nettoyage toutes les minutes
```

### 📚 Documentation Complète

- **Guide principal** : `docs/ephemeral-environments.md`
- **Référence API** : `docs/api/ephemeral.md`
- **Guide de migration** : `docs/migration-to-ephemeral.md`
- **Exemples pratiques** : `examples/ephemeral_examples.py`

### 🎯 Cas d'Usage

#### Tests Automatisés
```python
@pytest.fixture
async def test_env():
    async with gestvenv.ephemeral("pytest") as env:
        await env.install(["pytest", "pytest-asyncio"])
        yield env
```

#### CI/CD Pipeline
```yaml
steps:
  - run: |
      gestvenv ephemeral create ci-test --requirements requirements.txt
      gestvenv run --env ci-test pytest tests/
```

#### Expérimentation Sécurisée
```python
async with gestvenv.ephemeral(
    "sandbox",
    isolation_level=IsolationLevel.CONTAINER
) as env:
    # Test de packages non fiables en toute sécurité
```

### 🐛 Corrections et Améliorations

- Fallback automatique si niveau d'isolation non disponible
- Gestion robuste des erreurs avec cleanup garanti
- Support des signaux système pour cleanup propre
- Détection et nettoyage des environnements orphelins

### 🔄 Changements Breaking

Aucun - Les environnements éphémères sont une nouvelle fonctionnalité qui n'affecte pas l'API existante.

### 📦 Dépendances

- `psutil` : Pour le monitoring des ressources
- `asyncio` : Architecture asynchrone complète
- Support optionnel de Docker/Podman pour isolation container

### 🚧 Travail Futur (Phase 3)

- Pool d'environnements pré-créés pour création instantanée
- Cache de templates pour réutilisation rapide
- API REST pour gestion à distance
- Support Kubernetes pour isolation cloud-native

### 🙏 Remerciements

Cette fonctionnalité majeure a été développée en réponse aux besoins de la communauté pour des environnements de test isolés et temporaires.

---

## Notes de Migration

Pour migrer vers les environnements éphémères, consultez le guide complet : `docs/migration-to-ephemeral.md`

Les principales différences avec les environnements traditionnels :
- Nettoyage automatique garanti
- API async-first
- Monitoring intégré
- Isolation de sécurité configurable
- Performance optimisée pour création/destruction rapide