# 🐍 GestVenv - Gestionnaire d'Environnements Virtuels Python

[![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)](https://github.com/thearchit3ct/gestvenv)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

**GestVenv** est un outil en ligne de commande moderne et intelligent pour la gestion des environnements virtuels Python. Il simplifie la création, l'activation, la gestion des packages et offre désormais un **mode hors ligne avec cache intelligent** pour travailler sans connexion Internet.

## ✨ Fonctionnalités Principales

### 🚀 Gestion d'Environnements

- ✅ Création rapide d'environnements avec différentes versions Python
- ✅ Activation/désactivation simplifiée
- ✅ Clonage d'environnements existants
- ✅ Gestion centralisée de tous vos environnements

### 📦 Gestion Intelligente des Packages

- ✅ Installation, mise à jour et suppression de packages
- ✅ **Cache local intelligent** pour les packages Python
- ✅ **Mode hors ligne** complet
- ✅ Optimisation automatique des installations
- ✅ Export/import de configurations

### 🔧 Outils de Développement

- ✅ Exécution de commandes dans des environnements spécifiques
- ✅ Vérification des dépendances et mises à jour
- ✅ Documentation intégrée
- ✅ Support multi-plateforme

## 🆕 Nouveautés v1.1.0 - Cache Intelligent & Mode Hors Ligne

### Cache Local Automatique

```bash
# Le cache se remplit automatiquement lors des installations
gestvenv install myenv requests flask

# Gérer le cache manuellement
gestvenv cache info          # Informations sur le cache
gestvenv cache list          # Lister les packages en cache
gestvenv cache clean         # Nettoyer le cache
gestvenv cache add requests  # Pré-télécharger un package
```

### Mode Hors Ligne

```bash
# Activer le mode hors ligne
gestvenv --offline install myenv requests

# Configurer le mode par défaut
gestvenv config set offline_mode true

# Travailler complètement hors ligne
gestvenv --offline create project_env --python 3.11
gestvenv --offline install project_env -r requirements.txt
```

## 🚀 Installation

### Installation via pip (recommandée)

```bash
pip install gestvenv
```

### Installation depuis les sources

```bash
git clone https://github.com/thearchit3ct/gestvenv.git
cd gestvenv
pip install -e .
```

## 📖 Guide de Démarrage Rapide

### 1. Créer votre premier environnement

```bash
# Créer un environnement avec la version Python par défaut
gestvenv create monprojet

# Créer avec une version Python spécifique
gestvenv create monprojet --python 3.11

# Créer et pré-remplir le cache
gestvenv create monprojet --python 3.11 --enable-cache
```

### 2. Activer et gérer l'environnement

```bash
# Activer l'environnement
gestvenv activate monprojet

# Lister tous les environnements
gestvenv list

# Obtenir des infos détaillées
gestvenv info monprojet
```

### 3. Gérer les packages intelligemment

```bash
# Installation classique (avec mise en cache automatique)
gestvenv install monprojet requests flask pandas

# Installation en mode hors ligne (utilise le cache)
gestvenv --offline install monprojet requests flask

# Pré-télécharger des packages pour usage hors ligne
gestvenv cache add numpy scipy matplotlib
```

## 🛠️ Référence des Commandes

### Gestion des Environnements

| Commande | Description | Exemple |
|----------|-------------|---------|
| `create` | Créer un nouvel environnement | `gestvenv create myapp --python 3.11` |
| `activate` | Activer un environnement | `gestvenv activate myapp` |
| `deactivate` | Désactiver l'environnement actuel | `gestvenv deactivate` |
| `list` | Lister tous les environnements | `gestvenv list` |
| `info` | Informations sur un environnement | `gestvenv info myapp` |
| `clone` | Cloner un environnement | `gestvenv clone myapp myapp_copy` |
| `remove` | Supprimer un environnement | `gestvenv remove myapp` |

### Gestion des Packages

| Commande | Description | Exemple |
|----------|-------------|---------|
| `install` | Installer des packages | `gestvenv install myapp requests flask` |
| `update` | Mettre à jour des packages | `gestvenv update myapp requests` |
| `remove` | Supprimer des packages | `gestvenv remove myapp requests` |
| `check` | Vérifier les mises à jour | `gestvenv check myapp` |

### Cache Intelligent

| Commande | Description | Exemple |
|----------|-------------|---------|
| `cache info` | Informations sur le cache | `gestvenv cache info` |
| `cache list` | Lister les packages en cache | `gestvenv cache list` |
| `cache clean` | Nettoyer le cache | `gestvenv cache clean` |
| `cache add` | Ajouter un package au cache | `gestvenv cache add numpy==1.21.0` |
| `cache remove` | Supprimer du cache | `gestvenv cache remove numpy` |
| `cache export` | Exporter le cache | `gestvenv cache export cache_backup.tar.gz` |
| `cache import` | Importer un cache | `gestvenv cache import cache_backup.tar.gz` |

### Import/Export

| Commande | Description | Exemple |
|----------|-------------|---------|
| `export` | Exporter la configuration | `gestvenv export myapp config.json` |
| `import` | Importer une configuration | `gestvenv import config.json newenv` |

### Utilitaires

| Commande | Description | Exemple |
|----------|-------------|---------|
| `run` | Exécuter une commande | `gestvenv run myapp python script.py` |
| `pyversions` | Versions Python disponibles | `gestvenv pyversions` |
| `docs` | Documentation intégrée | `gestvenv docs` |

## 🔧 Options Globales

| Option | Description | Exemple |
|--------|-------------|---------|
| `--offline` | Forcer le mode hors ligne | `gestvenv --offline install myapp requests` |
| `--online` | Forcer le mode en ligne | `gestvenv --online install myapp requests` |
| `--enable-cache` | Activer le cache | `gestvenv --enable-cache create myapp` |
| `--disable-cache` | Désactiver le cache | `gestvenv --disable-cache install myapp requests` |
| `--verbose` | Affichage détaillé | `gestvenv --verbose create myapp` |
| `--quiet` | Mode silencieux | `gestvenv --quiet install myapp requests` |

## 📋 Cas d'Usage en Développement

### Projet Web avec Django/Flask

```bash
# Configuration initiale
gestvenv create webapp --python 3.11
gestvenv cache add django djangorestframework gunicorn
gestvenv install webapp django djangorestframework gunicorn

# Développement hors ligne
gestvenv --offline activate webapp
gestvenv --offline install webapp pytest black flake8
```

### Projet Data Science

```bash
# Pré-télécharger les packages lourds
gestvenv cache add numpy pandas matplotlib seaborn scikit-learn jupyter

# Créer l'environnement
gestvenv create datascience --python 3.10
gestvenv --offline install datascience numpy pandas matplotlib seaborn

# Export pour partage d'équipe
gestvenv export datascience team_config.json
gestvenv cache export datascience_cache.tar.gz
```

### Déploiement et CI/CD

```bash
# Préparer le cache pour le déploiement
gestvenv cache add -r production_requirements.txt

# Déploiement hors ligne
gestvenv --offline create production --python 3.11
gestvenv --offline install production -r production_requirements.txt
```

## ⚙️ Configuration

### Fichier de Configuration

GestVenv utilise un fichier de configuration situé à `~/.gestvenv/config.json` :

```json
{
  "offline_mode": false,
  "use_cache": true,
  "cache": {
    "max_size": "5GB",
    "max_age": 30,
    "auto_cleanup": true
  },
  "environments_path": "~/.gestvenv/environments",
  "default_python": "python3"
}
```

### Configuration via CLI

```bash
# Configurer le mode hors ligne par défaut
gestvenv config set offline_mode true

# Configurer la taille maximale du cache
gestvenv config set cache.max_size 10GB

# Configurer le nettoyage automatique
gestvenv config set cache.auto_cleanup false
```

## 🎯 Optimisations et Performance

- ⚡ **Création d'environnement** : < 10 secondes
- ⚡ **Démarrage de l'application** : < 2 secondes  
- ⚡ **Support de 50+ environnements** simultanés
- 💾 **Cache intelligent** : Réduction de 80% du temps d'installation
- 🔒 **Mode hors ligne** : Développement sans interruption

## 🤝 Contribution

Les contributions sont les bienvenues ! Consultez notre [guide de contribution](CONTRIBUTING.md).

### Développement Local

```bash
git clone https://github.com/thearchit3ct/gestvenv.git
cd gestvenv
gestvenv create gestvenv-dev --python 3.11
gestvenv activate gestvenv-dev
gestvenv install gestvenv-dev -e .
pytest
```

## 📄 License

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🆘 Support

- 📖 [Documentation complète](https://github.com/thearchit3ct/gestvenv/wiki)
- 🐛 [Signaler un bug](https://github.com/thearchit3ct/gestvenv/issues)
- 💬 [Discussions](https://github.com/thearchit3ct/gestvenv/discussions)
- 📧 Contact : <thearchit3ct@outlook.fr>

---

<div align="center">

**Développé avec ❤️ pour la communauté Python**

⭐ Si GestVenv vous est utile, n'hésitez pas à laisser une étoile sur GitHub !

</div>

---

*GestVenv - Simplifiez votre gestion d'environnements Python*
