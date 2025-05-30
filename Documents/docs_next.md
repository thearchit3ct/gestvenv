# GestVenv - Documentation complète

## Table des matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Concepts fondamentaux](#concepts-fondamentaux)
4. [Gestion des environnements](#gestion-des-environnements)
5. [Gestion des packages](#gestion-des-packages)
6. [Mode hors ligne et cache](#mode-hors-ligne-et-cache)
7. [Import et export](#import-et-export)
8. [Diagnostic et réparation](#diagnostic-et-réparation)
9. [Workflows recommandés](#workflows-recommandés)
10. [Référence des commandes](#référence-des-commandes)
11. [Configuration avancée](#configuration-avancée)
12. [Architecture du projet](#architecture-du-projet)

## Introduction

GestVenv est un gestionnaire d'environnements virtuels Python conçu pour simplifier et centraliser la gestion des environnements virtuels. L'outil offre une interface unifiée qui combine les fonctionnalités de plusieurs outils comme venv, virtualenv et pipenv, en y ajoutant des fonctionnalités supplémentaires comme la gestion de cache, le mode hors ligne, et le diagnostic automatique.

### Caractéristiques principales

- Création, activation et suppression d'environnements virtuels
- Installation, mise à jour et désinstallation de packages
- Mode hors ligne avec cache de packages
- Import/export de configurations d'environnements
- Clonage d'environnements existants
- Diagnostic et réparation automatique
- Interface en ligne de commande intuitive

## Installation

### Prérequis

- Python 3.6 ou supérieur
- pip (gestionnaire de packages Python)

### Installation

```bash
# Installation via pip
pip install gestvenv

# Vérification de l'installation
gestvenv --version

# Initialisation de la configuration
gestvenv config init
```

### Configuration initiale

```bash
# Afficher la configuration actuelle
gestvenv config show

# Définir le répertoire des environnements
gestvenv config set environments_path ~/Projects/.venvs

# Configurer le cache
gestvenv config set cache.max_size 8GB
gestvenv config set cache.max_age 60  # 60 jours
gestvenv config set cache.auto_cleanup true

# Mode hors ligne par défaut
gestvenv config set offline_mode false
gestvenv config set use_cache true
```

## Concepts fondamentaux

### Environnements virtuels

GestVenv gère des environnements virtuels Python isolés, chacun avec sa propre installation Python et ses propres packages. Cela permet de créer des environnements de développement séparés pour différents projets, évitant ainsi les conflits de dépendances.

### Structure des données

GestVenv utilise plusieurs classes de données pour représenter les informations :
- `EnvironmentInfo` : informations sur un environnement virtuel
- `PackageInfo` : informations sur un package Python
- `EnvironmentHealth` : état de santé d'un environnement
- `ConfigInfo` : configuration globale de GestVenv

### Cache et mode hors ligne

Le système de cache permet de stocker localement les packages téléchargés, pour :
- Accélérer les installations ultérieures
- Permettre l'installation de packages sans connexion internet (mode hors ligne)
- Partager des packages entre différents environnements

## Gestion des environnements

### Création d'environnements

```bash
# Environnement basique
gestvenv create monapp

# Avec version Python spécifique
gestvenv create monapp --python 3.11

# Avec description
gestvenv create monapp --python 3.11 --description "Application web principale"

# Création avec packages initiaux
gestvenv create monapp --python 3.11 --packages "flask requests"

# Création avec requirements.txt
gestvenv create monapp --python 3.11 -r requirements.txt
```

### Gestion active

```bash
# Lister tous les environnements
gestvenv list
gestvenv list --detailed  # Avec plus d'informations

# Informations détaillées
gestvenv info monapp

# Activation
gestvenv activate monapp

# Désactivation
gestvenv deactivate

# Suppression
gestvenv remove monapp
gestvenv remove monapp --force  # Sans confirmation
```

### Clonage d'environnements

```bash
# Clonage simple
gestvenv clone monapp monapp_test

# Clonage avec nouvelle version Python
gestvenv clone monapp monapp_py311 --python 3.11

# Clonage partiel (sans les données)
gestvenv clone monapp monapp_clean --packages-only
```

## Gestion des packages

### Installation

```bash
# Installation simple
gestvenv install monapp requests flask

# Installation avec versions spécifiques
gestvenv install monapp "requests>=2.28.0" "flask==2.2.0"

# Installation depuis requirements.txt
gestvenv install monapp -r requirements.txt
gestvenv install monapp -r dev-requirements.txt

# Installation en mode développement
gestvenv install monapp -e .  # Package local en mode éditable
```

### Mise à jour

```bash
# Mettre à jour un package
gestvenv update monapp requests

# Mettre à jour tous les packages
gestvenv update monapp --all

# Vérifier les mises à jour disponibles
gestvenv check monapp
gestvenv check monapp --outdated  # Seulement les obsolètes
```

### Suppression

```bash
# Supprimer un package
gestvenv remove monapp requests

# Supprimer plusieurs packages
gestvenv remove monapp requests flask pandas

# Supprimer avec dépendances
gestvenv remove monapp requests --dependencies
```

## Mode hors ligne et cache

### Informations sur le cache

```bash
# Informations générales
gestvenv cache info

# Statistiques détaillées
gestvenv cache stats

# Espace utilisé par package
gestvenv cache list --sizes
```

### Ajout manuel au cache

```bash
# Ajouter un package
gestvenv cache add requests

# Ajouter avec version spécifique
gestvenv cache add "requests==2.28.0"

# Ajouter depuis requirements.txt
gestvenv cache add -r requirements.txt

# Pré-téléchargement pour plusieurs plateformes
gestvenv cache add numpy --platforms "win_amd64,macosx_10_9_x86_64,linux_x86_64"
```

### Gestion du cache

```bash
# Lister les packages en cache
gestvenv cache list
gestvenv cache list --filter requests  # Filtrer par nom

# Nettoyer le cache
gestvenv cache clean  # Cleanup automatique
gestvenv cache clean --all  # Suppression complète
gestvenv cache clean --older-than 30  # Plus de 30 jours

# Supprimer un package spécifique
gestvenv cache remove requests
gestvenv cache remove "requests==2.28.0"
```

### Import/Export du cache

```bash
# Exporter le cache
gestvenv cache export backup_cache.tar.gz
gestvenv cache export backup_cache.tar.gz --compress

# Importer un cache
gestvenv cache import backup_cache.tar.gz
gestvenv cache import backup_cache.tar.gz --merge  # Fusionner avec l'existant

# Synchroniser entre machines
gestvenv cache export --format json cache_index.json
gestvenv cache import cache_index.json --download-missing
```

### Utilisation du mode hors ligne

```bash
# Forcer le mode hors ligne pour une commande
gestvenv --offline install monapp requests flask

# Créer un environnement hors ligne
gestvenv --offline create projet_offline --python 3.11

# Vérifier la disponibilité hors ligne
gestvenv cache check-offline -r requirements.txt
```

### Configuration du mode hors ligne

```bash
# Activer le mode hors ligne par défaut
gestvenv config set offline_mode true

# Retour au mode en ligne
gestvenv config set offline_mode false

# Mode hybride (utilise le cache quand disponible)
gestvenv config set cache.fallback_to_online true
```

## Import et export

### Export de configurations

```bash
# Export JSON complet
gestvenv export monapp config.json

# Export requirements.txt
gestvenv export monapp requirements.txt --format requirements

# Export avec métadonnées
gestvenv export monapp config.json --include-metadata

# Export pour distribution
gestvenv export monapp dist_config.json --production-ready
```

### Import de configurations

```bash
# Import depuis JSON
gestvenv import config.json nouveau_env

# Import depuis requirements.txt
gestvenv import requirements.txt nouveau_env --format requirements

# Import avec résolution des conflits
gestvenv import config.json existing_env --merge --resolve-conflicts
```

## Diagnostic et réparation

### Vérification de santé

```bash
# Vérifier un environnement
gestvenv doctor monapp

# Vérification complète
gestvenv doctor monapp --full

# Réparation automatique
gestvenv doctor monapp --fix
```

### Informations système

```bash
# Versions Python disponibles
gestvenv pyversions

# Informations système
gestvenv system-info

# État du cache
gestvenv cache health-check
```

### Logs et débogage

```bash
# Afficher les logs récents
gestvenv logs

# Logs spécifiques à un environnement
gestvenv logs monapp

# Export des logs pour support
gestvenv logs --export debug.log
```

## Workflows recommandés

### Développement web (Django/Flask)

```bash
# Créer l'environnement de développement
gestvenv create webapp --python 3.11 --description "Application web principale"

# Pré-télécharger les dépendances communes
gestvenv cache add django djangorestframework gunicorn
gestvenv cache add pytest pytest-django black flake8 mypy

# Installation des dépendances
gestvenv activate webapp
gestvenv install webapp django djangorestframework
gestvenv install webapp pytest pytest-django --dev  # Dépendances de développement
```

### Développement quotidien

```bash
# Activation de l'environnement
gestvenv activate webapp

# Installation de nouvelles dépendances
gestvenv install webapp redis celery

# Tests et linting (mode hors ligne)
gestvenv --offline run webapp pytest
gestvenv --offline run webapp black .
gestvenv --offline run webapp flake8 .

# Export pour partage
gestvenv export webapp webapp_config.json
```

### Projet data science

```bash
# Créer environnement data science
gestvenv create datascience --python 3.10

# Pré-télécharger packages lourds (recommandé avant déplacement)
gestvenv cache add numpy pandas matplotlib seaborn
gestvenv cache add scikit-learn jupyter notebook
gestvenv cache add plotly dash streamlit

# Installation par étapes
gestvenv install datascience numpy pandas matplotlib
gestvenv install datascience scikit-learn jupyter
gestvenv install datascience plotly dash  # Optionnel
```

### DevOps/CI-CD

```bash
# Environnement de production
gestvenv create production --python 3.11

# Cache des dépendances de production
gestvenv cache add -r requirements.txt
gestvenv cache add -r requirements-prod.txt

# Installation hors ligne (simulation CI/CD)
gestvenv --offline install production -r requirements.txt
gestvenv --offline install production -r requirements-prod.txt

# Test de l'environnement
gestvenv run production python -m pytest
```

## Référence des commandes

### Commandes de base

- `create` : Crée un nouvel environnement virtuel
- `activate` : Active un environnement virtuel
- `deactivate` : Désactive l'environnement actif
- `delete` : Supprime un environnement virtuel
- `list` : Liste tous les environnements virtuels
- `info` : Affiche des informations sur un environnement

### Gestion des packages

- `install` : Installe des packages dans un environnement
- `uninstall` : Désinstalle des packages d'un environnement
- `update` : Met à jour des packages dans un environnement
- `check` : Vérifie les mises à jour disponibles

### Import/Export

- `export` : Exporte la configuration d'un environnement
- `import` : Importe une configuration d'environnement
- `clone` : Clone un environnement existant

### Exécution et diagnostic

- `run` : Exécute une commande dans un environnement
- `doctor` : Diagnostique et répare les environnements
- `system-info` : Affiche les informations système détaillées

### Configuration et cache

- `config` : Configure les paramètres par défaut
- `cache` : Gère le cache de packages
- `logs` : Gère et affiche les logs de GestVenv
- `pyversions` : Liste les versions Python disponibles
- `docs` : Affiche la documentation

## Configuration avancée

### Sauvegardes de configuration

```bash
# Sauvegarde de configuration
gestvenv config backup

# Restauration
gestvenv config restore backup_config.json

# Reset complet
gestvenv config reset --confirm
```

### Configuration pour les équipes

```bash
# Exporter la configuration pour l'équipe
gestvenv export webapp team_config.json --include-metadata

# Partager le cache de packages
gestvenv cache export team_cache.tar.gz
```

### Paramètres avancés

```bash
# Activer la vérification automatique des mises à jour
gestvenv config set check_updates_on_activate true

# Configurer le nettoyage automatique du cache
gestvenv config set auto_cleanup_cache true

# Définir le timeout des opérations
gestvenv config set operation_timeout 300  # 5 minutes
```

## Architecture du projet

GestVenv est organisé selon une architecture modulaire avec les composants principaux suivants :

### Structure des modules

- `core` : Composants principaux et modèles de données
  - `models.py` : Classes de données (EnvironmentInfo, PackageInfo, etc.)
  - `env_manager.py` : Gestion des environnements virtuels
  - `config_manager.py` : Gestion de la configuration

- `utils` : Modules utilitaires
  - `path_utils.py` : Gestion des chemins de fichiers
  - `system_utils.py` : Interaction avec le système
  - `validation_utils.py` : Validation des entrées
  - `format_utils.py` : Formatage et affichage
  - `logging_utils.py` : Gestion des logs

- `services` : Services spécifiques (implicites dans le code fourni)
  - `environment_service` : Service de gestion des environnements
  - `package_service` : Service de gestion des packages
  - `cache_service` : Service de gestion du cache
  - `diagnostic_service` : Service de diagnostic et réparation

- `cli.py` : Interface en ligne de commande

### Flux de données

1. L'utilisateur interagit avec l'application via l'interface CLI (`cli.py`)
2. La CLI transmet les commandes au gestionnaire d'environnements (`env_manager.py`)
3. Le gestionnaire utilise les services spécifiques pour exécuter les commandes
4. Les opérations sont enregistrées via le système de logging (`logging_utils.py`)
5. La configuration est gérée par le gestionnaire de configuration (`config_manager.py`)

GestVenv utilise un stockage persistant pour :

- Les métadonnées des environnements
- La configuration de l'application
- Le cache de packages
- Les logs d'opérations

Cette architecture modulaire permet une grande flexibilité et extensibilité, facilitant l'ajout de nouvelles fonctionnalités tout en maintenant un code propre et maintenable.

---

Cette documentation couvre les aspects principaux de GestVenv. Pour toute question ou problème, consultez les logs via `gestvenv logs` ou utilisez la commande `gestvenv doctor` pour diagnostiquer et réparer automatiquement les problèmes.
