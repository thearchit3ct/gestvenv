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

- **🔥 Performance** : 10x plus rapide avec le backend uv
- **📦 Support pyproject.toml** : Conformité complète PEP 621
- **🎯 Backends modulaires** : pip, uv, poetry, pdm
- **💾 Cache intelligent** : Mode hors ligne efficace
- **🔧 Diagnostic automatique** : Détection et réparation des problèmes
- **📋 Templates intégrés** : Démarrage rapide pour tous projets
- **🔄 Migration transparente** : Compatible 100% avec v1.0

## ⚡ Installation

```bash
# Installation standard
pip install gestvenv

# Avec performances optimisées
pip install gestvenv[performance]

# Installation complète
pip install gestvenv[full]
```

## 🎯 Utilisation

### Création d'environnements

```bash
# Environnement basique
gestvenv create monapp

# Depuis pyproject.toml
gestvenv create-from-pyproject ./pyproject.toml monapp

# Avec template
gestvenv create-from-template web monwebapp
```

### Gestion des packages

```bash
# Installation
gestvenv install requests flask --env monapp

# Installation avec groupes
gestvenv install --group dev --env monapp

# Synchronisation
gestvenv sync monapp
```

### Cache et mode hors ligne

```bash
# Pré-téléchargement
gestvenv cache add numpy pandas matplotlib

# Installation hors ligne
gestvenv --offline install requests
```

### Backends disponibles

```bash
# Backend automatique (recommandé)
gestvenv config set-backend auto

# Backend spécifique
gestvenv config set-backend uv  # ou pip, poetry, pdm
```

## 📊 Performance

| Backend | Installation | Résolution | Cache |
|---------|-------------|------------|-------|
| **uv**  | 🔥🔥🔥      | 🔥🔥🔥     | 🔥🔥🔥 |
| pip     | 🔥          | 🔥         | 🔥    |
| poetry  | 🔥🔥        | 🔥🔥       | 🔥🔥  |

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