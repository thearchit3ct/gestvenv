# GestVenv v1.1 🐍

**Gestionnaire d'environnements virtuels Python moderne avec support multi-backend**

[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/gestvenv/gestvenv)
[![Python](https://img.shields.io/badge/python-3.9+-green)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-green)](https://github.com/gestvenv/gestvenv/actions)

---

## 📋 Vue d'ensemble

GestVenv v1.1 est un gestionnaire d'environnements virtuels Python moderne qui simplifie et centralise la gestion des environnements de développement. Cette version apporte un support natif pour les standards Python modernes (`pyproject.toml`) et une architecture multi-backend pour des performances optimisées.

### ✨ Fonctionnalités principales

- 🚀 **Multi-backend** : Support de `pip`, `uv`, `poetry`, `pdm` avec sélection automatique
- 📦 **pyproject.toml natif** : Support complet des standards modernes (PEP 621, PEP 631)
- ⚡ **Performances optimisées** : Cache intelligent et mode hors ligne
- 🔄 **Migration automatique** : Transition fluide depuis requirements.txt
- 🎯 **Groupes de dépendances** : Gestion avancée (dev, test, docs, etc.)
- 🔒 **Lock files** : Reproductibilité garantie
- 🛠️ **Templates** : Configurations réutilisables
- 📊 **Monitoring** : Santé et performance des environnements

---

## 🚀 Installation

### Installation standard

```bash
pip install gestvenv
```

### Installation avec backends optionnels

```bash
# Avec uv pour des performances optimales
pip install "gestvenv[uv]"

# Avec tous les backends
pip install "gestvenv[all]"

# Pour le développement
pip install "gestvenv[dev,test]"
```

### Vérification de l'installation

```bash
gestvenv --version
# ou
gv --version
```

---

## 🎯 Utilisation rapide

### Création d'environnements

```bash
# Création simple
gestvenv create monprojet

# Avec version Python spécifique
gestvenv create monprojet --python 3.11

# Avec packages initiaux
gestvenv create monprojet --packages "flask,pytest,black"

# Depuis pyproject.toml
gestvenv create-from-pyproject ./pyproject.toml monprojet

# Avec groupes de dépendances
gestvenv create-from-pyproject ./pyproject.toml monprojet --groups dev,test
```

### Gestion des environnements

```bash
# Lister les environnements
gestvenv list

# Activer un environnement
gestvenv activate monprojet

# Informations détaillées
gestvenv info monprojet

# Supprimer un environnement
gestvenv delete monprojet
```

### Gestion des packages

```bash
# Installer des packages
gestvenv install flask --env monprojet

# Synchroniser avec pyproject.toml
gestvenv sync monprojet --groups dev,test

# Mettre à jour
gestvenv update monprojet --all

# Export vers différents formats
gestvenv export monprojet --format requirements.txt
gestvenv export monprojet --format pyproject.toml
```

---

## 📚 Guide complet

### Backends supportés

| Backend | Performances | Lock files | Groupes | Installation |
|---------|--------------|------------|---------|--------------|
| `pip`   | Standard     | ❌         | ✅      | Inclus       |
| `uv`    | ⚡ Très rapide | ✅        | ✅      | `pip install uv` |
| `poetry`| Standard     | ✅         | ✅      | `pip install poetry` |
| `pdm`   | Rapide       | ✅         | ✅      | `pip install pdm` |

### Configuration automatique de backend

GestVenv sélectionne automatiquement le meilleur backend disponible :

1. **uv** si disponible (performances optimales)
2. **poetry** si `pyproject.toml` avec `[tool.poetry]`
3. **pdm** si `pyproject.toml` avec `[tool.pdm]`
4. **pip** comme fallback universel

### Support pyproject.toml

#### Création depuis pyproject.toml

```toml
# pyproject.toml
[project]
name = "mon-projet"
dependencies = [
    "flask>=2.0",
    "requests>=2.28",
]

[project.optional-dependencies]
dev = ["pytest", "black", "isort"]
test = ["pytest-cov", "tox"]
docs = ["sphinx", "sphinx-rtd-theme"]
```

```bash
# Création avec groupes spécifiques
gestvenv create-from-pyproject ./pyproject.toml monprojet --groups dev,test

# Synchronisation
gestvenv sync monprojet --groups dev
```

#### Migration requirements.txt → pyproject.toml

```bash
# Conversion automatique
gestvenv convert-to-pyproject requirements.txt

# Migration complète d'un projet existant
gestvenv migrate --from-requirements requirements.txt --to-pyproject
```

### Templates et réutilisation

#### Créer un template

```bash
# Exporter la configuration d'un environnement
gestvenv export monprojet --format template --output web_template.json

# Créer un template global
gestvenv template create web_app web_template.json
```

#### Utiliser un template

```bash
# Créer depuis un template
gestvenv create nouveau_projet --template web_app

# Lister les templates disponibles
gestvenv template list
```

### Mode hors ligne

```bash
# Activer le mode hors ligne
gestvenv config set offline_mode true

# Création hors ligne (utilise le cache)
gestvenv create projet_offline --offline

# Gérer le cache
gestvenv cache list
gestvenv cache clean
```

### Monitoring et santé

```bash
# Vérifier la santé d'un environnement
gestvenv check monprojet

# Informations détaillées avec scores
gestvenv info monprojet --health

# Réparation automatique
gestvenv repair monprojet
```

---

## ⚙️ Configuration

### Fichier de configuration

GestVenv utilise un fichier de configuration TOML : `~/.config/gestvenv/config.toml`

```toml
[general]
preferred_backend = "uv"
auto_activate = true
auto_migrate = true
offline_mode = false
default_python = "3.11"

[backends.uv]
resolution = "highest"
cache_dir = "~/.cache/uv"

[backends.pip]
timeout = 120
index_url = "https://pypi.org/simple"

[paths]
environments_dir = "~/.local/share/gestvenv/envs"
cache_dir = "~/.cache/gestvenv"
templates_dir = "~/.config/gestvenv/templates"

[security]
check_vulnerabilities = true
auto_update_pip = true
```

### Configuration via CLI

```bash
# Afficher la configuration
gestvenv config show

# Modifier un paramètre
gestvenv config set preferred_backend uv
gestvenv config set auto_activate true

# Backend spécifique
gestvenv backend set pip --index-url https://pypi.org/simple
gestvenv backend info uv
```

---

## 🔧 Cas d'usage avancés

### Développement en équipe

```bash
# 1. Créer l'environnement de référence
gestvenv create-from-pyproject ./pyproject.toml reference_env --groups dev,test

# 2. Exporter pour l'équipe
gestvenv export reference_env --format json --output team_config.json

# 3. Les membres de l'équipe importent
gestvenv import team_config.json mon_env_local
```

### CI/CD et reproductibilité

```bash
# Génération de lock file pour CI
gestvenv sync prod_env --lock-file requirements.lock

# Reproduction exacte en CI
gestvenv create ci_env --from-lock requirements.lock
```

### Projets multiples avec dépendances communes

```bash
# Environnement partagé pour les utilitaires
gestvenv create utils_env --packages "black,isort,pytest,mypy"

# Lier aux projets spécifiques
gestvenv create projet1 --inherit utils_env --packages "flask"
gestvenv create projet2 --inherit utils_env --packages "django"
```

---

## 🚀 Migration depuis autres outils

### Depuis virtualenv/venv

```bash
# Découverte automatique des environnements existants
gestvenv migrate --discover

# Migration manuelle
gestvenv migrate --from-path /path/to/old/env --name nouveau_nom
```

### Depuis poetry

```bash
# Import direct depuis poetry.lock
gestvenv import pyproject.toml mon_env --backend poetry

# Conversion vers format universel
gestvenv convert-from-poetry pyproject.toml
```

### Depuis conda

```bash
# Export depuis conda
conda env export > environment.yml

# Import dans GestVenv
gestvenv import environment.yml mon_env --format conda
```

---

## 🧪 API Python

### Utilisation programmatique

```python
from gestvenv import EnvironmentManager

# Créer le gestionnaire
manager = EnvironmentManager()

# Créer un environnement
success, message = manager.create_environment(
    name="mon_projet",
    python_version="3.11",
    packages=["flask", "pytest"],
    backend_type="uv"
)

# Informations
environments = manager.list_environments()
env_info = manager.get_environment_info("mon_projet")

# Synchronisation
success, message = manager.sync_environment(
    name="mon_projet", 
    groups=["dev", "test"]
)
```

### Configuration programmatique

```python
from gestvenv import ConfigManager

config = ConfigManager()

# Paramètres généraux
config.set_setting("preferred_backend", "uv")
config.set_offline_mode(True)

# Backends
config.set_backend_setting("uv", "resolution", "highest")

# Templates
template_data = {...}
config.add_template("web_app", template_data)
```

---

## 🛠️ Développement

### Installation pour le développement

```bash
git clone https://github.com/gestvenv/gestvenv.git
cd gestvenv

# Installation en mode développement
pip install -e ".[dev,test]"

# Installation des hooks pre-commit
pre-commit install
```

### Tests

```bash
# Tests complets
pytest

# Tests avec couverture
pytest --cov=gestvenv --cov-report=html

# Tests spécifiques
pytest tests/test_environment_manager.py
pytest -m "not slow"  # Exclure les tests lents
```

### Contribution

1. Fork du repository
2. Création d'une branche : `git checkout -b feature/nouvelle-fonctionnalite`
3. Commits : `git commit -am 'Ajout nouvelle fonctionnalité'`
4. Push : `git push origin feature/nouvelle-fonctionnalite`
5. Pull Request

---

## 📝 FAQ

### Questions fréquentes

**Q: Quelle est la différence avec pip-tools ou poetry ?**
R: GestVenv orchestre différents backends (pip, uv, poetry) et se concentre sur la gestion d'environnements plutôt que sur un seul workflow.

**Q: Puis-je utiliser GestVenv avec mes projets poetry existants ?**
R: Oui, GestVenv détecte automatiquement les projets poetry et utilise le backend approprié.

**Q: Comment migrer mes environnements existants ?**
R: Utilisez `gestvenv migrate --discover` pour la détection automatique ou `gestvenv migrate --from-path` pour la migration manuelle.

**Q: GestVenv modifie-t-il mes fichiers pyproject.toml ?**
R: Non, GestVenv lit les configurations sans les modifier. Il peut créer des fichiers de lock séparés.

---

## 📄 Licence

GestVenv est distribué sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

---

## 🙏 Remerciements

- TheArchit3ct pour la création et le développement de GestVenv
- L'équipe Python pour les PEP modernes
- Les mainteneurs de pip, uv, poetry, et pdm
- La communauté open source Python

---

## 📞 Support

- 🐛 **Bugs** : [GitHub Issues](https://github.com/gestvenv/gestvenv/issues)
- 💬 **Discussions** : [GitHub Discussions](https://github.com/gestvenv/gestvenv/discussions)
- 📖 **Documentation** : [gestvenv.readthedocs.io](https://gestvenv.readthedocs.io)
- 📧 **Contact** : TheArchit3ct - thearchit3ct@outlook.fr

---

<div align="center">

**⭐ Si GestVenv vous aide, n'hésitez pas à mettre une étoile sur GitHub ! ⭐**

[🏠 Site web](https://gestvenv.org) • [📚 Documentation](https://docs.gestvenv.org) • [🐙 GitHub](https://github.com/gestvenv/gestvenv)

</div>