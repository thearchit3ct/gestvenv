# Guide des Bases GestVenv v1.1

Ce guide couvre toutes les fonctionnalit�s essentielles de GestVenv v1.1, incluant les nouvelles commandes et capacit�s avanc�es.

## =� Cr�ation d'Environnements

### M�thodes de Cr�ation

#### Environnement Standard
```bash
# Cr�ation basique
gestvenv create monapp

# Avec version Python sp�cifique
gestvenv create monapp --python 3.11

# Avec backend sp�cifique
gestvenv create monapp --backend uv
```

#### Depuis Templates Int�gr�s
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

#### Auto-d�tection Intelligente
```bash
# D�tection automatique du format
gestvenv import ./mon-projet/pyproject.toml
gestvenv import ./autre-projet/Pipfile
gestvenv import ./conda-projet/environment.yml
```

## =� Gestion Avanc�e des Packages

### Installation avec Groupes
```bash
# Installation dans un groupe sp�cifique
gestvenv install pytest black mypy --env monapp --group dev
gestvenv install requests flask --env monapp --group web

# Installation �ditable
gestvenv install -e ./mon-package --env monapp
```

### Listage et Inspection
```bash
# Lister tous les packages
gestvenv list-packages --env monapp

# Filtrer par groupe
gestvenv list-packages --env monapp --group dev

# Packages obsol�tes
gestvenv list-packages --env monapp --outdated

# Format JSON pour scripts
gestvenv list-packages --env monapp --format json
```

### Synchronisation et Mise � Jour
```bash
# Synchronisation avec pyproject.toml
gestvenv sync monapp --groups dev,test --clean

# Mise � jour de packages sp�cifiques
gestvenv update requests flask --env monapp

# Mise � jour compl�te
gestvenv update --env monapp --all
```

## =� Cache Intelligent

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
# Export compress�
gestvenv cache export /backup/cache-$(date +%Y%m%d).tar.gz --compress

# Import avec v�rification
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

# Nettoyage forc�
gestvenv cache clean --force
```

## =' Diagnostic et R�paration

### Diagnostic Complet
```bash
# Diagnostic de base
gestvenv doctor

# Diagnostic avec auto-r�paration
gestvenv doctor --auto-fix

# Diagnostic de performance
gestvenv doctor --performance --full

# Diagnostic d'un environnement sp�cifique
gestvenv doctor monapp
```

### R�paration Manuelle
```bash
# R�paration compl�te
gestvenv repair monapp --all

# R�paration sp�cifique
gestvenv repair monapp --fix-permissions --rebuild-metadata

# Simulation (dry-run)
gestvenv repair monapp --dry-run
```

### Nettoyage Syst�me
```bash
# Environnements orphelins
gestvenv cleanup --orphaned

# Nettoyage complet
gestvenv cleanup --all --cache --force

# Simulation
gestvenv cleanup --orphaned --dry-run
```

## � Configuration Avanc�e

### Configuration Globale
```bash
# Backend par d�faut
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
# Variables support�es
export GESTVENV_BACKEND=uv
export GESTVENV_CACHE_ENABLED=true
export GESTVENV_CACHE_SIZE_MB=2000
export GESTVENV_OFFLINE_MODE=false
export GESTVENV_ENVIRONMENTS_PATH=/custom/path
```

## = Int�gration Shell

### Ex�cution de Commandes
```bash
# Ex�cuter une commande
gestvenv run --env monapp python script.py

# Tests
gestvenv run --env monapp pytest tests/

# Avec r�pertoire de travail
gestvenv run --env monapp --cwd /projet pytest
```

### Shell Interactif
```bash
# D�marrer un shell
gestvenv shell --env monapp

# Shell sp�cifique
gestvenv shell --env monapp --shell bash
gestvenv shell --env monapp --shell zsh
```

### Activation Classique
```bash
# Activation
gestvenv activate monapp

# D�sactivation
gestvenv deactivate
```

## = Monitoring et Inspection

### Listage Avanc�
```bash
# Liste avec �tat de sant�
gestvenv list --health

# Tri par taille
gestvenv list --sort size

# Filtrage par backend
gestvenv list --backend uv

# Format JSON
gestvenv list --format json
```

### Informations D�taill�es
```bash
# Informations compl�tes d'un environnement
gestvenv info monapp

# Statistiques globales
gestvenv stats --detailed

# Performance du syst�me
gestvenv stats --format json
```

## <	 Migration et Compatibilit�

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

# Avec m�tadonn�es personnalis�es
gestvenv convert-to-pyproject requirements.txt \
    --output myproject.toml \
    --project-name "Mon Projet" \
    --author "Mon Nom"
```

## <� Support et Feedback

### Obtenir de l'Aide
```bash
# Aide g�n�rale
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
gestvenv feedback --message "Excellente fonctionnalit� !" --type feature

# Rapport de bug
gestvenv feedback --type bug --message "Probl�me avec sync"
```

Ce guide couvre les fonctionnalit�s essentielles de GestVenv v1.1. Pour des cas d'usage avanc�s, consultez les guides sp�cialis�s dans les sections suivantes.