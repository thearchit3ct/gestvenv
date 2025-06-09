# Documentation Utilisateur GestVenv

## Table des matières

1. [Introduction](#introduction)
2. [Installation et configuration](#installation-et-configuration)
3. [Premiers pas](#premiers-pas)
4. [Gestion des environnements](#gestion-des-environnements)
5. [Gestion des packages](#gestion-des-packages)
6. [Import et export](#import-et-export)
7. [Mode hors ligne et cache](#mode-hors-ligne-et-cache)
8. [Diagnostic et maintenance](#diagnostic-et-maintenance)
9. [Workflows et bonnes pratiques](#workflows-et-bonnes-pratiques)
10. [Référence des commandes](#référence-des-commandes)
11. [Configuration avancée](#configuration-avancée)
12. [Dépannage](#dépannage)

---

## Introduction

**GestVenv** est un gestionnaire d'environnements virtuels Python moderne qui simplifie et centralise la gestion de vos projets Python. Il combine les fonctionnalités de plusieurs outils existants (venv, virtualenv, pipenv) en ajoutant des fonctionnalités avancées comme le mode hors ligne, le diagnostic automatique et la gestion intelligente du cache.

### Pourquoi GestVenv ?

- **Interface unifiée** : Une seule commande pour toutes vos opérations
- **Mode hors ligne** : Travaillez sans connexion internet grâce au cache intelligent
- **Diagnostic automatique** : Détection et réparation automatique des problèmes
- **Gestion avancée** : Import/export, clonage, métadonnées riches
- **Robustesse** : Système de sauvegarde et de récupération intégré

### Fonctionnalités principales

✅ Création et gestion d'environnements virtuels  
✅ Installation et gestion de packages Python  
✅ Cache local pour le mode hors ligne  
✅ Import/export de configurations  
✅ Clonage d'environnements  
✅ Diagnostic et réparation automatique  
✅ Interface en ligne de commande intuitive  
✅ Support multi-plateforme (Windows, macOS, Linux)  

---

## Installation et configuration

### Prérequis

- **Python 3.6+** (recommandé: Python 3.8+)
- **pip** (gestionnaire de packages Python)
- **Accès en écriture** dans le répertoire utilisateur

### Installation

```bash
# Installation via pip
pip install gestvenv

# Vérification de l'installation
gestvenv --version
```

### Configuration initiale

```bash
# Afficher la configuration actuelle
gestvenv config --show

# Configurer la version Python par défaut
gestvenv config --set-python python3.11

# Activer le cache de packages
gestvenv config --enable-cache

# Configurer la taille maximale du cache (en Mo)
gestvenv config --cache-max-size 5000

# Vérifier la santé du système
gestvenv system-info
```

---

## Premiers pas

### Créer votre premier environnement

```bash
# Environnement simple
gestvenv create mon_projet

# Avec version Python spécifique
gestvenv create mon_projet --python python3.11

# Avec packages initiaux
gestvenv create mon_projet --packages "flask,requests,pytest"

# Avec description
gestvenv create mon_projet --description "Mon premier projet web"
```

### Activer et utiliser l'environnement

```bash
# Activer l'environnement
gestvenv activate mon_projet
# Puis exécuter la commande affichée

# Vérifier l'environnement actif
gestvenv list

# Installer des packages supplémentaires
gestvenv install "pandas,matplotlib"

# Voir les informations de l'environnement
gestvenv info mon_projet
```

### Désactiver et nettoyer

```bash
# Désactiver l'environnement
gestvenv deactivate

# Supprimer l'environnement (avec confirmation)
gestvenv delete mon_projet
```

---

## Gestion des environnements

### Création d'environnements

#### Création basique
```bash
gestvenv create nom_environnement
```

#### Création avancée
```bash
# Avec version Python spécifique
gestvenv create webapp --python python3.11

# Avec chemin personnalisé
gestvenv create webapp --path /chemin/vers/environnement

# Avec packages depuis requirements.txt
gestvenv create webapp -r requirements.txt

# Avec description et métadonnées
gestvenv create webapp --description "Application web principale"

# En mode hors ligne (utilise le cache)
gestvenv create webapp --offline --packages "flask,gunicorn"
```

### Lister et examiner les environnements

```bash
# Liste simple
gestvenv list

# Liste détaillée
gestvenv list --verbose

# Liste avec état de santé
gestvenv list --health

# Format JSON
gestvenv list --json

# Informations détaillées sur un environnement
gestvenv info webapp

# Avec liste complète des packages
gestvenv info webapp --packages
```

### Activation et utilisation

```bash
# Activer un environnement
gestvenv activate webapp

# Exécuter une commande dans un environnement
gestvenv run webapp python script.py

# Avec variables d'environnement
gestvenv run webapp --env "DEBUG=1,API_KEY=secret" python app.py

# Avec timeout
gestvenv run webapp --timeout 60 python long_script.py

# En arrière-plan
gestvenv run webapp --background python worker.py
```

### Clonage d'environnements

```bash
# Clonage complet
gestvenv clone webapp webapp_test

# Clonage sans packages (structure seulement)
gestvenv clone webapp webapp_clean --skip-packages

# Avec nouvelle description
gestvenv clone webapp webapp_prod --description "Version production"
```

### Suppression d'environnements

```bash
# Suppression avec confirmation
gestvenv delete webapp

# Suppression forcée (sans confirmation)
gestvenv delete webapp --force
```

---

## Gestion des packages

### Installation de packages

```bash
# Dans l'environnement actif
gestvenv install "flask,requests"

# Dans un environnement spécifique
gestvenv install --env webapp "django,psycopg2"

# Depuis requirements.txt
gestvenv install -r requirements.txt

# En mode éditable (développement)
gestvenv install -e ./mon_package

# Packages de développement
gestvenv install --dev "pytest,black,flake8"

# Avec mise à jour forcée
gestvenv install --upgrade "flask>=2.0"

# En mode hors ligne
gestvenv install --offline "flask,requests"
```

### Mise à jour de packages

```bash
# Mettre à jour des packages spécifiques
gestvenv update "flask,requests"

# Mettre à jour tous les packages
gestvenv update --all

# Dans un environnement spécifique
gestvenv update --env webapp --all

# En mode hors ligne
gestvenv update --offline "flask"
```

### Vérification des mises à jour

```bash
# Vérifier les mises à jour disponibles
gestvenv check

# Pour un environnement spécifique
gestvenv check webapp

# Appliquer automatiquement les mises à jour
gestvenv check webapp --apply
```

### Désinstallation de packages

```bash
# Désinstaller des packages
gestvenv uninstall "old_package,unused_lib"

# Avec confirmation automatique
gestvenv uninstall --yes "test_package"

# Avec les dépendances
gestvenv uninstall --with-dependencies "complex_package"

# Dans un environnement spécifique
gestvenv uninstall --env webapp "django"
```

---

## Import et export

### Export de configurations

```bash
# Export JSON (par défaut)
gestvenv export webapp

# Avec fichier de sortie spécifique
gestvenv export webapp --output webapp_config.json

# Export au format requirements.txt
gestvenv export webapp --format requirements --output requirements.txt

# Avec métadonnées complètes
gestvenv export webapp --include-metadata

# Ajout de métadonnées personnalisées
gestvenv export webapp --add-metadata "auteur:John Doe,version:1.0"

# Export optimisé pour la production
gestvenv export webapp --production
```

### Import de configurations

```bash
# Import depuis JSON
gestvenv import config.json --name nouveau_projet

# Import depuis requirements.txt
gestvenv import requirements.txt --name projet_requirements

# Fusion avec environnement existant
gestvenv import config.json --merge

# Avec résolution automatique des conflits
gestvenv import config.json --merge --resolve-conflicts
```

### Partage entre équipes

```bash
# Créer un package de distribution complet
gestvenv export webapp --output team_config.json --include-metadata

# Importer dans un nouvel environnement
gestvenv import team_config.json --name webapp_local

# Vérifier la compatibilité
gestvenv doctor webapp_local
```

---

## Mode hors ligne et cache

### Configuration du cache

```bash
# Informations sur le cache
gestvenv cache info

# Activer le cache
gestvenv config --enable-cache

# Configurer la taille maximale (en Mo)
gestvenv config --cache-max-size 10000

# Configurer l'âge maximum des packages (en jours)
gestvenv config --cache-max-age 90
```

### Gestion du cache

```bash
# Lister les packages en cache
gestvenv cache list

# Avec détails complets
gestvenv cache list --detailed

# Ajouter des packages au cache
gestvenv cache add "flask,django,numpy"

# Ajouter depuis requirements.txt
gestvenv cache add -r requirements.txt

# Nettoyer le cache
gestvenv cache clean

# Nettoyage avec paramètres personnalisés
gestvenv cache clean --max-age 30 --max-size 5000

# Nettoyage forcé
gestvenv cache clean --force

# Supprimer des packages spécifiques
gestvenv cache remove "old_package"

# Vérifier l'intégrité du cache
gestvenv cache verify

# Réparer le cache si nécessaire
gestvenv cache verify --fix
```

### Export/Import du cache

```bash
# Exporter le cache
gestvenv cache export --output cache_backup.json

# Importer un cache
gestvenv cache import cache_backup.json

# Fusionner avec le cache existant
gestvenv cache import cache_backup.json --merge
```

### Utilisation du mode hors ligne

```bash
# Activer le mode hors ligne globalement
gestvenv config --offline

# Créer un environnement hors ligne
gestvenv create projet_offline --offline --packages "flask,requests"

# Installer des packages hors ligne
gestvenv install --offline "numpy,pandas"

# Vérifier la disponibilité hors ligne
gestvenv cache list --filter numpy

# Retour au mode en ligne
gestvenv config --online
```

---

## Diagnostic et maintenance

### Diagnostic d'environnements

```bash
# Diagnostic simple
gestvenv doctor webapp

# Diagnostic complet
gestvenv doctor webapp --full

# Diagnostic avec réparation automatique
gestvenv doctor webapp --fix

# Diagnostic de tous les environnements
gestvenv doctor

# Inclure la vérification du cache
gestvenv doctor --check-cache
```

### Informations système

```bash
# Informations système complètes
gestvenv system-info

# Format JSON
gestvenv system-info --json

# Export vers fichier
gestvenv system-info --export system_report.json

# Versions Python disponibles
gestvenv pyversions
```

### Gestion des logs

```bash
# Afficher les logs récents
gestvenv logs show

# Dernières 100 lignes
gestvenv logs show --lines 100

# Filtrer par niveau d'erreur
gestvenv logs show --level ERROR

# Filtrer par environnement
gestvenv logs show --env webapp

# Exporter les logs
gestvenv logs export debug_logs.txt --days 7

# Nettoyer les anciens logs
gestvenv logs clean --days 30

# Nettoyage forcé
gestvenv logs clean --force
```

### Maintenance préventive

```bash
# Vérification complète du système
gestvenv doctor --full --check-cache

# Nettoyage général
gestvenv cache clean
gestvenv logs clean --days 30

# Sauvegarde de la configuration
gestvenv config --backup

# Validation de l'intégrité
gestvenv config --validate
```

---

## Workflows et bonnes pratiques

### Workflow de développement web

```bash
# 1. Créer l'environnement de développement
gestvenv create webapp --python python3.11 \
  --description "Application web principale"

# 2. Pré-télécharger les dépendances communes
gestvenv cache add "flask,django,fastapi,requests,pytest"

# 3. Installation des dépendances de base
gestvenv activate webapp
gestvenv install "flask,python-dotenv"

# 4. Installation des outils de développement
gestvenv install --dev "pytest,black,flake8,mypy"

# 5. Export de la configuration pour l'équipe
gestvenv export webapp --output team_config.json --include-metadata
```

### Workflow data science

```bash
# 1. Créer l'environnement data science
gestvenv create datascience --python python3.10

# 2. Pré-télécharger les packages lourds (recommandé)
gestvenv cache add "numpy,pandas,matplotlib,scikit-learn,jupyter"

# 3. Installation par étapes (pour éviter les conflits)
gestvenv install "numpy,pandas"
gestvenv install "matplotlib,seaborn"
gestvenv install "scikit-learn,jupyter"

# 4. Packages optionnels
gestvenv install "plotly,dash,streamlit"

# 5. Export pour reproductibilité
gestvenv export datascience --format requirements --output requirements.txt
```

### Workflow DevOps/Production

```bash
# 1. Environnement de production
gestvenv create production --python python3.11

# 2. Mode hors ligne pour la production
gestvenv config --offline

# 3. Cache des dépendances de production
gestvenv cache add -r requirements-prod.txt

# 4. Installation hors ligne
gestvenv install --offline -r requirements-prod.txt

# 5. Vérification de l'environnement
gestvenv doctor production --full

# 6. Export de la configuration finale
gestvenv export production --production --output prod_config.json
```

### Gestion multi-projets

```bash
# Projets avec versions Python différentes
gestvenv create legacy_app --python python3.8
gestvenv create modern_app --python python3.11

# Clonage pour tests
gestvenv clone legacy_app legacy_test
gestvenv clone modern_app modern_test

# Environments dédiés par tâche
gestvenv create webapp_frontend --packages "nodejs,webpack"
gestvenv create webapp_backend --packages "django,psycopg2"
gestvenv create webapp_testing --packages "pytest,selenium"
```

---

## Référence des commandes

### Commandes de gestion d'environnements

| Commande | Description | Exemples |
|----------|-------------|----------|
| `create` | Crée un nouvel environnement | `gestvenv create myapp --python python3.11` |
| `activate` | Active un environnement | `gestvenv activate myapp` |
| `deactivate` | Désactive l'environnement actif | `gestvenv deactivate` |
| `delete` | Supprime un environnement | `gestvenv delete myapp --force` |
| `list` | Liste tous les environnements | `gestvenv list --verbose` |
| `info` | Informations détaillées | `gestvenv info myapp --packages` |
| `clone` | Clone un environnement | `gestvenv clone source target` |

### Commandes de gestion des packages

| Commande | Description | Exemples |
|----------|-------------|----------|
| `install` | Installe des packages | `gestvenv install "flask,requests"` |
| `uninstall` | Désinstalle des packages | `gestvenv uninstall --yes "old_pkg"` |
| `update` | Met à jour des packages | `gestvenv update --all` |
| `check` | Vérifie les mises à jour | `gestvenv check myapp --apply` |

### Commandes d'import/export

| Commande | Description | Exemples |
|----------|-------------|----------|
| `export` | Exporte une configuration | `gestvenv export myapp --format json` |
| `import` | Importe une configuration | `gestvenv import config.json --merge` |

### Commandes de cache

| Commande | Description | Exemples |
|----------|-------------|----------|
| `cache list` | Liste les packages en cache | `gestvenv cache list --detailed` |
| `cache add` | Ajoute au cache | `gestvenv cache add "numpy,pandas"` |
| `cache clean` | Nettoie le cache | `gestvenv cache clean --force` |
| `cache info` | Informations sur le cache | `gestvenv cache info` |
| `cache export` | Exporte le cache | `gestvenv cache export backup.json` |
| `cache import` | Importe un cache | `gestvenv cache import backup.json` |
| `cache remove` | Supprime du cache | `gestvenv cache remove "old_pkg"` |
| `cache verify` | Vérifie l'intégrité | `gestvenv cache verify --fix` |

### Commandes de diagnostic

| Commande | Description | Exemples |
|----------|-------------|----------|
| `doctor` | Diagnostique des environnements | `gestvenv doctor myapp --fix` |
| `system-info` | Informations système | `gestvenv system-info --json` |
| `pyversions` | Versions Python disponibles | `gestvenv pyversions` |

### Commandes de configuration

| Commande | Description | Exemples |
|----------|-------------|----------|
| `config` | Gère la configuration | `gestvenv config --show` |
| `logs` | Gère les logs | `gestvenv logs show --lines 50` |

### Commandes utilitaires

| Commande | Description | Exemples |
|----------|-------------|----------|
| `run` | Exécute une commande | `gestvenv run myapp python script.py` |
| `docs` | Affiche la documentation | `gestvenv docs workflows` |

---

## Configuration avancée

### Fichier de configuration

Le fichier de configuration se trouve par défaut dans :
- **Linux/macOS** : `~/.config/gestvenv/config.json`
- **Windows** : `%APPDATA%\GestVenv\config.json`

### Paramètres principaux

```bash
# Python par défaut
gestvenv config --set-python python3.11

# Répertoire des environnements
gestvenv config --set environments_path ~/Projects/.venvs

# Mode hors ligne
gestvenv config --offline  # ou --online

# Cache
gestvenv config --enable-cache
gestvenv config --cache-max-size 8000  # en Mo
gestvenv config --cache-max-age 120    # en jours
```

### Gestion des sauvegardes

```bash
# Créer une sauvegarde
gestvenv config --backup

# Lister les sauvegardes disponibles
gestvenv config --list-backups

# Restaurer une sauvegarde
gestvenv config --restore backup_20231120

# Réinitialiser la configuration
gestvenv config --reset
```

### Configuration par projet

Vous pouvez créer un fichier `.gestvenv.json` dans votre projet :

```json
{
  "environment": "mon_projet",
  "python_version": "python3.11",
  "packages": [
    "flask>=2.0",
    "requests>=2.28",
    "pytest>=7.0"
  ],
  "dev_packages": [
    "black",
    "flake8",
    "mypy"
  ],
  "metadata": {
    "description": "Application web",
    "author": "Mon Nom"
  }
}
```

### Variables d'environnement

GestVenv reconnaît ces variables d'environnement :

```bash
# Répertoire des données
export GESTVENV_DATA_DIR=/custom/path

# Mode debug
export GESTVENV_DEBUG=1

# Mode hors ligne par défaut
export GESTVENV_OFFLINE=1

# Taille maximale du cache
export GESTVENV_CACHE_SIZE=10000
```

---

## Dépannage

### Problèmes courants

#### "Environnement non trouvé"
```bash
# Vérifier la liste des environnements
gestvenv list

# Recréer l'environnement si nécessaire
gestvenv create nom_environnement

# Diagnostic complet
gestvenv doctor nom_environnement --full
```

#### "Package non trouvé en mode hors ligne"
```bash
# Vérifier le cache
gestvenv cache list --filter package_name

# Ajouter le package au cache
gestvenv cache add "package_name"

# Passer en mode en ligne temporairement
gestvenv config --online
gestvenv install "package_name"
gestvenv config --offline
```

#### "Environnement corrompu"
```bash
# Diagnostic avec réparation
gestvenv doctor nom_environnement --fix

# Si la réparation échoue, recréer
gestvenv export nom_environnement --output backup.json
gestvenv delete nom_environnement --force
gestvenv import backup.json --name nom_environnement
```

### Diagnostic avancé

```bash
# Vérification complète du système
gestvenv system-info
gestvenv doctor --full --check-cache

# Logs détaillés
gestvenv logs show --level DEBUG --lines 200

# Validation de la configuration
gestvenv config --validate

# Test de l'intégrité du cache
gestvenv cache verify --fix
```

### Récupération d'urgence

```bash
# Sauvegarde de sécurité
gestvenv config --backup

# Réinitialisation complète
gestvenv config --reset --confirm

# Reconstruction depuis les sauvegardes
gestvenv config --restore latest_backup

# Nettoyage complet du cache
gestvenv cache clean --all
```

### Support et aide

```bash
# Aide contextuelle
gestvenv --help
gestvenv <commande> --help

# Documentation intégrée
gestvenv docs <sujet>

# Informations de debug
gestvenv --debug <commande>

# Export d'un rapport de diagnostic
gestvenv system-info --export diagnostic_report.json
gestvenv logs export --output logs_for_support.txt
```

---

Cette documentation couvre l'ensemble des fonctionnalités de GestVenv. Pour des cas d'usage spécifiques ou des questions avancées, consultez la documentation intégrée avec `gestvenv docs` ou utilisez `gestvenv --help` pour obtenir de l'aide sur les commandes.