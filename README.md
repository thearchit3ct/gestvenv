# 🌟 GestVenv v1.1

<div align="center">
  <img src="logo.png" alt="GestVenv Logo" width="200" height="200"/>
  <br/>
  <em>Gestionnaire d'environnements virtuels Python moderne</em>
</div>

[![PyPI version](https://badge.fury.io/py/gestvenv.svg)](https://badge.fury.io/py/gestvenv)
[![Python Support](https://img.shields.io/pypi/pyversions/gestvenv.svg)](https://pypi.org/project/gestvenv/)
[![Tests](https://github.com/gestvenv/gestvenv/workflows/Tests/badge.svg)](https://github.com/gestvenv/gestvenv/actions)
[![Coverage](https://codecov.io/gh/gestvenv/gestvenv/branch/main/graph/badge.svg)](https://codecov.io/gh/gestvenv/gestvenv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Fonctionnalités

### 🏗️ Création d'Environnements
- **🔥 Performance** : 10x plus rapide avec le backend uv
- **📋 Templates avancés** : Django, FastAPI, Data Science, CLI
- **🔄 Import multi-format** : pyproject.toml, conda, Pipfile, requirements.txt
- **🎯 Auto-détection** : Backend optimal selon le projet

### 📦 Gestion des Packages
- **📊 Groupes de dépendances** : Support PEP 621 complet
- **💾 Cache intelligent** : Mode hors ligne avec compression
- **🔄 Synchronisation** : Sync automatique pyproject.toml
- **⚡ Téléchargements parallèles** : Installation optimisée

### 🔧 Outils Avancés
- **🩺 Diagnostic complet** : Détection et réparation auto
- **🐚 Intégration shell** : Commandes run/shell intégrées
- **⚙️ Configuration flexible** : Locale + variables d'environnement
- **📊 Monitoring santé** : État détaillé des environnements

### 🚀 Environnements Éphémères (Nouveau!)
- **⚡ Création ultra-rapide** : < 1 seconde avec uv
- **🧹 Nettoyage automatique** : Context managers Python
- **🔒 Isolation sécurisée** : Process, namespace, container, chroot
- **📊 Monitoring temps réel** : CPU, mémoire, disque
- **💾 Stockage optimisé** : tmpfs, mémoire pour performance max

### 🌉 Migration
- **🔄 Import Pipenv** : Migration transparente depuis Pipfile
- **🐍 Support Conda** : Import environment.yml
- **📋 Export multi-format** : JSON, requirements, pyproject.toml
- **🔗 Compatibilité totale** : Avec v1.0 et autres outils

## ⚡ Installation

```bash
# Installation standard
pip install gestvenv

# Avec performances optimisées
pip install gestvenv[performance]

# Installation complète
pip install gestvenv[full]
```

## 🎯 Utilisation Rapide

### Création d'environnements

```bash
# Environnement basique
gestvenv create monapp

# Depuis templates intégrés
gestvenv create-from-template django monwebapp
gestvenv create-from-template data-science monanalyse
gestvenv create-from-template fastapi monapi

# Import depuis projets existants
gestvenv create-from-pyproject ./pyproject.toml monapp
gestvenv create-from-conda ./environment.yml monapp
gestvenv import-from-pipfile ./Pipfile monapp

# Auto-détection et création
gestvenv import ./mon-projet/pyproject.toml  # Détecte le format automatiquement
```

### Gestion avancée des packages

```bash
# Installation avec groupes de dépendances
gestvenv install requests flask --env monapp --group web
gestvenv install pytest black --env monapp --group dev

# Listage par groupes
gestvenv list-packages --env monapp --group dev

# Synchronisation automatique
gestvenv sync monapp --groups dev,test --clean

# Mise à jour intelligente
gestvenv update --env monapp --all
```

### Cache intelligent et mode hors ligne

```bash
# Pré-téléchargement depuis requirements
gestvenv cache add -r requirements.txt --python-version 3.11

# Export/import de cache
gestvenv cache export /backup/cache.tar.gz --compress
gestvenv cache import /backup/cache.tar.gz --verify

# Mode hors ligne complet
gestvenv --offline create monapp
gestvenv --offline install requests --env monapp
```

### Diagnostic et réparation

```bash
# Diagnostic complet
gestvenv doctor --full --performance

# Réparation automatique
gestvenv doctor --auto-fix
gestvenv repair monapp --all

# Nettoyage du système
gestvenv cleanup --orphaned --cache
```

### Configuration avancée

```bash
# Configuration globale
gestvenv config set preferred_backend uv
gestvenv config set cache_size_mb 2000

# Configuration locale du projet
gestvenv config set --local preferred_backend poetry

# Variables d'environnement
export GESTVENV_BACKEND=uv
export GESTVENV_CACHE_ENABLED=true
```

### Environnements éphémères

```python
# API Python avec nettoyage automatique
import gestvenv

async with gestvenv.ephemeral("test-env") as env:
    await env.install(["requests", "pandas"])
    result = await env.execute("python -c 'import requests; print(requests.__version__)'")
    print(result.stdout)
    # Cleanup automatique garanti
```

```bash
# CLI pour tests rapides
gestvenv ephemeral create test --interactive --packages "requests,pandas"
gestvenv ephemeral list
gestvenv ephemeral cleanup --all
```

### Intégration shell

```bash
# Exécution dans l'environnement
gestvenv run --env monapp python mon_script.py
gestvenv run --env monapp pytest tests/

# Shell interactif
gestvenv shell --env monapp

# Activation classique
gestvenv activate monapp
```

## 📊 Performance et Backends

| Backend | Installation | Résolution | Cache | Groupes | Lock Files | Auto-détection |
|---------|-------------|------------|-------|---------|------------|----------------|
| **uv**  | 🔥🔥🔥      | 🔥🔥🔥     | 🔥🔥🔥 | ✅       | ✅         | ✅             |
| **PDM** | 🔥🔥🔥      | 🔥🔥🔥     | 🔥🔥🔥 | ✅       | ✅         | ✅             |
| poetry  | 🔥🔥        | 🔥🔥       | 🔥🔥  | ✅       | ✅         | ✅             |
| pip     | 🔥          | 🔥         | 🔥    | ✅       | ❌         | ✅             |

### Templates Intégrés

| Template | Description | Dépendances | Structure |
|----------|-------------|-------------|-----------|
| **django** | Projet Django moderne | Django 4.2+, environ, psycopg2 | Apps, settings, URLs |
| **fastapi** | API REST performante | FastAPI, SQLAlchemy, Alembic | Modèles, routeurs, DB |
| **data-science** | Analyse de données | Pandas, NumPy, Jupyter, Scikit-learn | Notebooks, pipelines ML |
| **cli** | Outil en ligne de commande | Click, Rich, Typer | Commands, utils |
| **basic** | Projet Python standard | Minimal | Structure basique |

## 🗂️ Structure de projet supportée

```
mon-projet/
├── pyproject.toml          # Configuration principale (PEP 621)
├── requirements.txt        # Support legacy
├── .gestvenv/             # Cache et configuration
│   ├── environments/      # Environnements virtuels
│   └── cache/            # Cache packages
└── src/                  # Code source
```

## 🔧 Configuration

```bash
# Configuration globale
gestvenv config list
gestvenv config set cache-size 2GB
gestvenv config set auto-cleanup true

# Configuration par projet
gestvenv config --local set backend uv
gestvenv config --local set python-version 3.11
```

## 📋 Templates intégrés

```bash
# Web application
gestvenv create-from-template web monapp
# → Flask/FastAPI, gunicorn, pytest

# Data science
gestvenv create-from-template datascience analyse
# → numpy, pandas, jupyter, matplotlib

# CLI tool
gestvenv create-from-template cli montool
# → click, rich, typer
```

## 🔄 Migration depuis v1.0

```bash
# Migration automatique
gestvenv migrate-from-v1

# Migration manuelle
gestvenv import-v1-environments ~/.gestvenv-v1/
```

## 🩺 Diagnostic et maintenance

```bash
# Diagnostic complet
gestvenv doctor

# Réparation automatique
gestvenv repair --env monapp

# Nettoyage cache
gestvenv clean cache
gestvenv clean environments --unused
```

## 📚 Documentation

- [Guide d'installation](docs/installation.md)
- [Démarrage rapide](docs/quickstart.md) 
- [Guide utilisateur](docs/user_guide/)
- [Migration v1.0 → v1.1](docs/user_guide/migration.md)
- [Documentation API](docs/api/)

## 🔧 Développement

```bash
# Cloner le projet
git clone https://github.com/gestvenv/gestvenv.git
cd gestvenv

# Installation développement
pip install -e .[dev]

# Tests
pytest

# Linting
pre-commit run --all-files
```

## 🤝 Contribution

Les contributions sont bienvenues ! 

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour plus de détails.

## 📄 Licence

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour les détails.

## 🙏 Remerciements

- Communauté Python pour les standards PEP
- Équipes uv, poetry, PDM pour l'inspiration
- Tous les contributeurs et utilisateurs

---

<div align="center">
  <strong>GestVenv v1.1 - L'avenir de la gestion d'environnements Python</strong>
</div>