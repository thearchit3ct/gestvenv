# GestVenv v2.0 - Release Notes

<div align="center">
  <h2>L'avenir de la gestion d'environnements Python est arrivé</h2>
  <p><em>Version majeure avec environnements éphémères, extension VS Code et interface web moderne</em></p>
</div>

---

## Vue d'ensemble

**GestVenv v2.0** représente une refonte majeure de notre gestionnaire d'environnements virtuels Python. Cette version introduit trois fonctionnalités révolutionnaires qui transforment la façon dont les développeurs travaillent avec Python :

1. **Environnements Éphémères** - Environnements temporaires avec nettoyage automatique
2. **Extension VS Code Native** - Intégration IDE profonde avec IntelliSense
3. **Interface Web Moderne** - Dashboard complet pour gestion à distance

---

## Nouveautés Majeures

### 1. Environnements Éphémères

Les environnements éphémères permettent de créer des environnements virtuels temporaires qui se nettoient automatiquement après utilisation. Idéal pour les tests, CI/CD, et expérimentations.

#### Caractéristiques

| Fonctionnalité | Description |
|----------------|-------------|
| **Création ultra-rapide** | < 1 seconde avec le backend uv |
| **Nettoyage automatique** | Garanti via context managers Python |
| **4 niveaux d'isolation** | process, namespace, container, chroot |
| **Monitoring temps réel** | CPU, mémoire, disque |
| **Stockage optimisé** | tmpfs, memory, disk |

#### Exemple d'utilisation

```python
import asyncio
from gestvenv import ephemeral

async def test_package():
    async with ephemeral("test-env") as env:
        # Installation de packages
        await env.install(["requests", "pandas"])

        # Exécution de code
        result = await env.execute("python -c 'import pandas; print(pandas.__version__)'")
        print(result.stdout)

        # Nettoyage automatique garanti à la sortie du context manager

asyncio.run(test_package())
```

#### Commandes CLI

```bash
# Créer un environnement éphémère interactif
gv ephemeral create test --interactive --packages "requests,flask"

# Lister les environnements actifs
gv ephemeral list

# Voir les statistiques
gv ephemeral stats

# Nettoyage manuel
gv ephemeral cleanup --all
```

---

### 2. Extension VS Code Native

Une extension VS Code complète offrant une intégration profonde avec GestVenv pour une expérience de développement optimale.

#### Fonctionnalités

- **IntelliSense complet** pour tous les packages Python installés
- **Auto-complétion contextuelle** avec documentation inline
- **Language Server Protocol (LSP)** pour analyse statique
- **Synchronisation temps réel** via WebSocket
- **Vue arborescente** des environnements et packages
- **Code actions** : installation rapide, mises à jour
- **Status bar** avec indicateur d'environnement actif

#### Installation

```bash
# Build de l'extension
cd extensions/vscode
npm install
npm run package

# Installation dans VS Code
# Extensions → Install from VSIX → gestvenv-vscode-x.x.x.vsix
```

#### Configuration VS Code

```json
{
  "gestvenv.autoActivate": true,
  "gestvenv.showStatusBar": true,
  "gestvenv.intellisenseEnabled": true,
  "gestvenv.websocketSync": true
}
```

---

### 3. Interface Web Moderne

Un dashboard web complet construit avec Vue 3 et Tailwind CSS, offrant une interface intuitive pour la gestion à distance.

#### Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | Vue 3, TypeScript, Tailwind CSS, Vite |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Communication | REST API + WebSocket |
| Base de données | SQLite (dev), PostgreSQL (prod) |

#### Fonctionnalités

- **Tableau de bord** avec vue d'ensemble du système
- **Gestion des environnements** : création, modification, suppression
- **Gestion des packages** : installation, mise à jour, désinstallation
- **Monitoring du cache** : statistiques, nettoyage, export/import
- **Templates de projets** : création rapide depuis templates
- **Suivi des opérations** en temps réel via WebSocket
- **Diagnostic système** avec réparation automatique

#### Démarrage

```bash
# Mode développement
cd web
./start-dev.sh

# Accéder à http://localhost:5173

# Mode production (Docker)
docker-compose up -d
```

#### Captures d'écran

L'interface comprend :
- Dashboard avec statistiques en temps réel
- Gestionnaire d'environnements avec vue en grille/liste
- Page Packages avec recherche et filtrage
- Page Cache avec actions d'export/import
- Page Système avec diagnostics
- Page Templates pour création rapide
- Page Opérations avec historique

---

## Améliorations de Performance

### Benchmarks

| Opération | v1.1 (pip) | v2.0 (uv) | Amélioration |
|-----------|------------|-----------|--------------|
| Création d'environnement | 5-10s | < 1s | **10x** |
| Installation de package | 10-30s | 2-5s | **5x** |
| Résolution de dépendances | 5-15s | 1-3s | **5x** |
| Démarrage CLI | 500ms | < 100ms | **5x** |

### Optimisations

- **Cache intelligent** avec compression zstd (40-60% réduction)
- **Téléchargements parallèles** pour installations multiples
- **Lazy loading** pour démarrage instantané
- **Async/await** partout pour I/O non-bloquant
- **Deduplication** automatique du cache

---

## Backends Supportés

GestVenv v2.0 supporte plusieurs backends avec auto-détection intelligente :

| Backend | Performance | Résolution | Cache | Groupes | Lock Files |
|---------|-------------|------------|-------|---------|------------|
| **uv** | Excellent | Excellent | Excellent | Oui | Oui |
| **PDM** | Excellent | Excellent | Excellent | Oui | Oui |
| **Poetry** | Très bon | Très bon | Très bon | Oui | Oui |
| **pip** | Bon | Bon | Bon | Oui | Non |

### Sélection automatique

GestVenv détecte automatiquement le meilleur backend selon :
- Fichiers de configuration présents (pyproject.toml, poetry.lock, etc.)
- Disponibilité des outils sur le système
- Performance et fonctionnalités requises

---

## Templates de Projets

Six templates prêts à l'emploi pour démarrer rapidement :

| Template | Description | Packages inclus |
|----------|-------------|-----------------|
| **basic** | Projet Python minimal | - |
| **cli** | Outil en ligne de commande | Click, Rich, Typer |
| **web** | Application web générique | Flask/FastAPI basics |
| **fastapi** | API REST performante | FastAPI, SQLAlchemy, Alembic, Uvicorn |
| **django** | Application Django complète | Django 4.2+, environ, psycopg2 |
| **data-science** | Analyse de données/ML | Pandas, NumPy, Jupyter, Scikit-learn, Matplotlib |

### Utilisation

```bash
# Créer depuis un template
gv create-from-template fastapi mon-api
gv create-from-template data-science mon-analyse
gv create-from-template django mon-site
```

---

## Configuration

### Configuration Globale

```toml
# ~/.config/gestvenv/config.toml

[general]
preferred_backend = "uv"
default_python = "3.11"
auto_cleanup = true
verbose = false

[cache]
enabled = true
size_mb = 2000
compression = "zstd"
ttl_days = 30

[ephemeral]
default_isolation = "namespace"
default_storage = "tmpfs"
auto_cleanup_seconds = 3600
max_environments = 10

[ide]
vscode_extension = true
intellisense_enabled = true
websocket_port = 8765

[web]
api_port = 8000
enable_cors = true
jwt_enabled = false
```

### Configuration Projet

```toml
# .gestvenv/config.toml

[project]
name = "mon-projet"
backend = "uv"
python_version = "3.11"

[dependencies]
groups = ["main", "dev", "test", "docs"]

[scripts]
test = "pytest tests/"
lint = "ruff check ."
format = "black ."
```

### Variables d'Environnement

```bash
GESTVENV_BACKEND=uv
GESTVENV_CACHE_ENABLED=true
GESTVENV_OFFLINE_MODE=false
GESTVENV_PYTHON_VERSION=3.11
GESTVENV_VERBOSE=false
```

---

## API REST

### Endpoints Principaux

```
# Environnements
GET    /api/v1/environments              # Lister
POST   /api/v1/environments              # Créer
GET    /api/v1/environments/{name}       # Détails
PUT    /api/v1/environments/{name}       # Modifier
DELETE /api/v1/environments/{name}       # Supprimer

# Packages
GET    /api/v1/environments/{name}/packages        # Lister
POST   /api/v1/environments/{name}/packages        # Installer
DELETE /api/v1/environments/{name}/packages/{pkg}  # Désinstaller

# Cache
GET    /api/v1/cache/info               # Statistiques
POST   /api/v1/cache/clean              # Nettoyer
POST   /api/v1/cache/export             # Exporter
POST   /api/v1/cache/import             # Importer

# Système
GET    /api/v1/system/info              # Informations système
GET    /api/v1/system/health            # État de santé
POST   /api/v1/system/doctor            # Diagnostic
GET    /api/v1/system/operations        # Opérations en cours

# Templates
GET    /api/v1/templates                # Lister
POST   /api/v1/templates/create         # Créer depuis template
```

### WebSocket Events

```javascript
// Événements supportés
- environment_created
- environment_deleted
- environment_updated
- package_installed
- package_uninstalled
- operation_progress
- operation_completed
- cache_updated
- system_health_changed
```

---

## Versions de Maintenance

### v2.0.3 (2026-01-19)

Améliorations du workflow de release :

- **Sigstore v3** : Mise à jour pour compatibilité GitHub Actions
- **Script notify-success** : Correction syntaxe shell

### v2.0.2 (2026-01-19)

Corrections de stabilité CI/CD et qualité de code :

- **Import Python manquant** : Correction de l'import `List` dans `handlers.py`
- **Conflit de nommage** : Renommage de `websocket.py` → `ws_manager.py`
- **CI/CD** :
  - Ajout du serveur UI preview avant les tests E2E
  - Configuration viewport Cypress (1280x720)
  - Mise à jour des GitHub Actions vers v4
  - Mise à jour Sigstore vers v3.0.0
- **Correction de code** : Signature `disconnect()` corrigée

### v2.0.1 (2026-01-19)

Corrections de l'interface web :

- **CSS Tailwind** : Ajout de `postcss.config.js` manquant
- **Plugins Tailwind** : Installation de `@tailwindcss/forms` et `@tailwindcss/typography`
- **Composants Vue** : Remplacement des composants UI manquants par HTML natif avec Tailwind

---

## Migration depuis v1.x

### Migration Automatique

```bash
# Migration complète automatique
gv migrate --from-v1

# Vérification post-migration
gv doctor --full
```

### Migration Manuelle

```bash
# Import des environnements v1
gv import-v1-environments ~/.gestvenv-v1/

# Conversion de configuration
gv config migrate
```

### Changements de Configuration

| v1.x | v2.0 |
|------|------|
| `.gestvenvrc` | `.gestvenv/config.toml` |
| `~/.gestvenv/cache/` | `~/.cache/gestvenv/` |
| API v0 | API v1 |

---

## Breaking Changes

### Python

- **Python 3.8 n'est plus supporté** - Minimum requis : Python 3.9

### Configuration

- Format de configuration changé : `.gestvenvrc` → `.gestvenv/config.toml`
- Structure du cache réorganisée (migration automatique)

### API

- API v0 dépréciée, utilisez API v1
- Nouveaux endpoints avec préfixe `/api/v1/`

### CLI

- Certaines options renommées pour cohérence
- Nouvelles commandes pour environnements éphémères

---

## Installation

### PyPI (Recommandé)

```bash
# Installation standard
pip install gestvenv

# Avec performances optimisées (uv)
pip install gestvenv[performance]

# Installation complète
pip install gestvenv[full]

# Pour développeurs
pip install gestvenv[dev]
```

### Depuis les Sources

```bash
git clone https://github.com/gestvenv/gestvenv.git
cd gestvenv
pip install -e .[dev]
```

### Docker

```bash
# Build
docker build -t gestvenv .

# Run
docker-compose up -d
```

---

## Prérequis Système

### Python

- Python 3.9, 3.10, 3.11, 3.12, 3.13

### Systèmes d'Exploitation

- Linux (toutes distributions)
- macOS 10.15+
- Windows 10/11

### Optionnel

- uv (recommandé pour performance)
- Node.js 18+ (pour l'extension VS Code)
- Docker (pour le déploiement web)

---

## Remerciements

Merci à tous les contributeurs et à la communauté Python pour leur soutien continu :

- L'équipe Astral pour [uv](https://github.com/astral-sh/uv)
- L'équipe Poetry pour l'inspiration architecturale
- L'équipe PDM pour les standards PEP 621
- Microsoft pour l'API d'extension VS Code
- L'équipe Vue.js pour le framework réactif
- Tous les contributeurs et testeurs beta

---

## Ressources

- **Documentation complète** : [docs/](docs/)
- **Guide de démarrage** : [docs/quickstart.md](docs/quickstart.md)
- **Référence CLI** : [docs/cli-reference-complete.md](docs/cli-reference-complete.md)
- **API Web** : [docs/web-api.md](docs/web-api.md)
- **Environnements éphémères** : [docs/ephemeral-environments.md](docs/ephemeral-environments.md)
- **Extension VS Code** : [docs/vscode-extension.md](docs/vscode-extension.md)
- **Migration** : [docs/migration-v2.md](docs/migration-v2.md)

---

## Support

- **Issues** : [GitHub Issues](https://github.com/gestvenv/gestvenv/issues)
- **Discussions** : [GitHub Discussions](https://github.com/gestvenv/gestvenv/discussions)
- **Email** : contact@gestvenv.dev

---

<div align="center">
  <h3>GestVenv v2.0</h3>
  <p><strong>L'avenir de la gestion d'environnements Python</strong></p>
  <p>
    <a href="https://github.com/gestvenv/gestvenv">GitHub</a> •
    <a href="https://pypi.org/project/gestvenv/">PyPI</a> •
    <a href="docs/">Documentation</a>
  </p>
  <p><em>Licence MIT - 2026</em></p>
</div>
