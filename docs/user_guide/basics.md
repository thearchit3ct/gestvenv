# Guide des Bases GestVenv v1.1

Ce guide couvre toutes les fonctionnalités essentielles de GestVenv v1.1, incluant les nouvelles commandes et capacités avancées.

## =€ Création d'Environnements

### Méthodes de Création

#### Environnement Standard
```bash
# Création basique
gestvenv create monapp

# Avec version Python spécifique
gestvenv create monapp --python 3.11

# Avec backend spécifique
gestvenv create monapp --backend uv
```

#### Depuis Templates Intégrés
```bash
# Template Django complet
gestvenv create-from-template django monwebapp \
    --author "Mon Nom" \
    --email "mon@email.com" \
    --python 3.11

# Template Data Science
gestvenv create-from-template data-science monanalyse \
    --output /projets/analyse

# Template FastAPI
gestvenv create-from-template fastapi monapi
```

#### Import depuis Projets Existants
```bash
# Depuis pyproject.toml
gestvenv create-from-pyproject ./pyproject.toml monapp \
    --groups "dev,test" \
    --backend auto

# Depuis environment.yml (Conda)
gestvenv create-from-conda ./environment.yml monapp \
    --skip-conda-only

# Depuis Pipfile (Pipenv)
gestvenv import-from-pipfile ./Pipfile monapp \
    --include-dev
```

#### Auto-détection Intelligente
```bash
# Détection automatique du format
gestvenv import ./mon-projet/pyproject.toml
gestvenv import ./autre-projet/Pipfile
gestvenv import ./conda-projet/environment.yml
```

## =æ Gestion Avancée des Packages

### Installation avec Groupes
```bash
# Installation dans un groupe spécifique
gestvenv install pytest black mypy --env monapp --group dev
gestvenv install requests flask --env monapp --group web

# Installation éditable
gestvenv install -e ./mon-package --env monapp
```

### Listage et Inspection
```bash
# Lister tous les packages
gestvenv list-packages --env monapp

# Filtrer par groupe
gestvenv list-packages --env monapp --group dev

# Packages obsolètes
gestvenv list-packages --env monapp --outdated

# Format JSON pour scripts
gestvenv list-packages --env monapp --format json
```

### Synchronisation et Mise à Jour
```bash
# Synchronisation avec pyproject.toml
gestvenv sync monapp --groups dev,test --clean

# Mise à jour de packages spécifiques
gestvenv update requests flask --env monapp

# Mise à jour complète
gestvenv update --env monapp --all
```

## =¾ Cache Intelligent

### Gestion du Cache
```bash
# Informations sur le cache
gestvenv cache info

# Ajouter des packages au cache
gestvenv cache add numpy pandas scipy

# Depuis un fichier requirements
gestvenv cache add -r requirements.txt --python-version 3.11

# Pour plusieurs plateformes
gestvenv cache add tensorflow --platforms "linux_x86_64,macosx_11_0_arm64"
```

### Export/Import de Cache
```bash
# Export compressé
gestvenv cache export /backup/cache-$(date +%Y%m%d).tar.gz --compress

# Import avec vérification
gestvenv cache import /backup/cache.tar.gz --verify

# Fusion avec cache existant
gestvenv cache import /backup/cache.tar.gz --merge
```

### Nettoyage
```bash
# Nettoyage basique
gestvenv cache clean --older-than 30

# Nettoyage avec limite de taille
gestvenv cache clean --size-limit 500MB

# Nettoyage forcé
gestvenv cache clean --force
```

## =' Diagnostic et Réparation

### Diagnostic Complet
```bash
# Diagnostic de base
gestvenv doctor

# Diagnostic avec auto-réparation
gestvenv doctor --auto-fix

# Diagnostic de performance
gestvenv doctor --performance --full

# Diagnostic d'un environnement spécifique
gestvenv doctor monapp
```

### Réparation Manuelle
```bash
# Réparation complète
gestvenv repair monapp --all

# Réparation spécifique
gestvenv repair monapp --fix-permissions --rebuild-metadata

# Simulation (dry-run)
gestvenv repair monapp --dry-run
```

### Nettoyage Système
```bash
# Environnements orphelins
gestvenv cleanup --orphaned

# Nettoyage complet
gestvenv cleanup --all --cache --force

# Simulation
gestvenv cleanup --orphaned --dry-run
```

## ™ Configuration Avancée

### Configuration Globale
```bash
# Backend par défaut
gestvenv config set preferred_backend uv

# Taille du cache
gestvenv config set cache_size_mb 2000

# Mode migration automatique
gestvenv config set auto_migrate true
```

### Configuration Locale
```bash
# Configuration pour le projet actuel
gestvenv config set --local preferred_backend poetry
gestvenv config set --local cache_enabled false

# Afficher la configuration
gestvenv config show
gestvenv config show --section cache
```

### Variables d'Environnement
```bash
# Variables supportées
export GESTVENV_BACKEND=uv
export GESTVENV_CACHE_ENABLED=true
export GESTVENV_CACHE_SIZE_MB=2000
export GESTVENV_OFFLINE_MODE=false
export GESTVENV_ENVIRONMENTS_PATH=/custom/path
```

## = Intégration Shell

### Exécution de Commandes
```bash
# Exécuter une commande
gestvenv run --env monapp python script.py

# Tests
gestvenv run --env monapp pytest tests/

# Avec répertoire de travail
gestvenv run --env monapp --cwd /projet pytest
```

### Shell Interactif
```bash
# Démarrer un shell
gestvenv shell --env monapp

# Shell spécifique
gestvenv shell --env monapp --shell bash
gestvenv shell --env monapp --shell zsh
```

### Activation Classique
```bash
# Activation
gestvenv activate monapp

# Désactivation
gestvenv deactivate
```

## = Monitoring et Inspection

### Listage Avancé
```bash
# Liste avec état de santé
gestvenv list --health

# Tri par taille
gestvenv list --sort size

# Filtrage par backend
gestvenv list --backend uv

# Format JSON
gestvenv list --format json
```

### Informations Détaillées
```bash
# Informations complètes d'un environnement
gestvenv info monapp

# Statistiques globales
gestvenv stats --detailed

# Performance du système
gestvenv stats --format json
```

## <	 Migration et Compatibilité

### Export Multi-format
```bash
# Export JSON complet
gestvenv export monapp export.json --format json

# Export requirements.txt
gestvenv export monapp requirements.txt --format requirements

# Export pyproject.toml
gestvenv export monapp pyproject.toml --format pyproject
```

### Conversion de Formats
```bash
# Requirements vers pyproject.toml
gestvenv convert-to-pyproject requirements.txt \
    --output pyproject.toml \
    --interactive

# Avec métadonnées personnalisées
gestvenv convert-to-pyproject requirements.txt \
    --output myproject.toml \
    --project-name "Mon Projet" \
    --author "Mon Nom"
```

## <˜ Support et Feedback

### Obtenir de l'Aide
```bash
# Aide générale
gestvenv --help

# Aide sur une commande
gestvenv create --help
gestvenv cache --help
```

### Envoyer du Feedback
```bash
# Feedback interactif
gestvenv feedback

# Feedback direct
gestvenv feedback --message "Excellente fonctionnalité !" --type feature

# Rapport de bug
gestvenv feedback --type bug --message "Problème avec sync"
```

Ce guide couvre les fonctionnalités essentielles de GestVenv v1.1. Pour des cas d'usage avancés, consultez les guides spécialisés dans les sections suivantes.