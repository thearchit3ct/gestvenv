# 📚 Guide Complet d'Utilisation de GestVenv

## Table des Matières
1. [Installation et Configuration](#installation-et-configuration)
2. [Commandes de Base](#commandes-de-base)
3. [Mode Hors Ligne et Cache](#mode-hors-ligne-et-cache)
4. [Workflows de Développement](#workflows-de-développement)
5. [Gestion Avancée](#gestion-avancée)
6. [Exemples Pratiques](#exemples-pratiques)
7. [Résolution de Problèmes](#résolution-de-problèmes)

## 🚀 Installation et Configuration

### Installation Initiale
```bash
# Installation via pip
pip install gestvenv

# Vérification de l'installation
gestvenv --version

# Initialisation de la configuration
gestvenv config init
```

### Configuration Personnalisée
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

## 🛠️ Commandes de Base

### 1. Gestion des Environnements

#### Création d'Environnements
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

#### Gestion Active
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

#### Clonage d'Environnements
```bash
# Clonage simple
gestvenv clone monapp monapp_test

# Clonage avec nouvelle version Python
gestvenv clone monapp monapp_py311 --python 3.11

# Clonage partiel (sans les données)
gestvenv clone monapp monapp_clean --packages-only
```

### 2. Gestion des Packages

#### Installation
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

#### Mise à Jour
```bash
# Mettre à jour un package
gestvenv update monapp requests

# Mettre à jour tous les packages
gestvenv update monapp --all

# Vérifier les mises à jour disponibles
gestvenv check monapp
gestvenv check monapp --outdated  # Seulement les obsolètes
```

#### Suppression
```bash
# Supprimer un package
gestvenv remove monapp requests

# Supprimer plusieurs packages
gestvenv remove monapp requests flask pandas

# Supprimer avec dépendances
gestvenv remove monapp requests --dependencies
```

## 🏠 Mode Hors Ligne et Cache

### 3. Gestion du Cache

#### Informations sur le Cache
```bash
# Informations générales
gestvenv cache info

# Statistiques détaillées
gestvenv cache stats

# Espace utilisé par package
gestvenv cache list --sizes
```

#### Ajout Manuel au Cache
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

#### Gestion du Cache
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

#### Import/Export du Cache
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

### 4. Mode Hors Ligne

#### Utilisation Basique
```bash
# Forcer le mode hors ligne pour une commande
gestvenv --offline install monapp requests flask

# Créer un environnement hors ligne
gestvenv --offline create projet_offline --python 3.11

# Vérifier la disponibilité hors ligne
gestvenv cache check-offline -r requirements.txt
```

#### Configuration Persistante
```bash
# Activer le mode hors ligne par défaut
gestvenv config set offline_mode true

# Retour au mode en ligne
gestvenv config set offline_mode false

# Mode hybride (utilise le cache quand disponible)
gestvenv config set cache.fallback_to_online true
```

## 💼 Workflows de Développement

### 5. Projet Web (Django/Flask)

#### Setup Initial
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

#### Développement Quotidien
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

### 6. Projet Data Science

#### Configuration Environnement
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

#### Workflow d'Analyse
```bash
# Activation et lancement Jupyter
gestvenv activate datascience
gestvenv run datascience jupyter notebook

# Installation de packages additionnels
gestvenv install datascience seaborn plotly

# Sauvegarde de l'état
gestvenv export datascience ds_env.json
gestvenv cache export ds_cache.tar.gz
```

### 7. Projet DevOps/CI-CD

#### Préparation Déploiement
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

#### Gestion Multi-Environnements
```bash
# Environnement de test
gestvenv clone production test
gestvenv install test pytest-cov coverage

# Environnement de staging
gestvenv clone production staging
gestvenv install staging debug-toolbar

# Synchronisation des caches entre environnements
gestvenv cache export production_cache.tar.gz
# Sur autre machine/serveur:
gestvenv cache import production_cache.tar.gz
```

## 🔧 Gestion Avancée

### 8. Import/Export

#### Export de Configurations
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

#### Import de Configurations
```bash
# Import depuis JSON
gestvenv import config.json nouveau_env

# Import depuis requirements.txt
gestvenv import requirements.txt nouveau_env --format requirements

# Import avec résolution des conflits
gestvenv import config.json existing_env --merge --resolve-conflicts
```

### 9. Exécution de Commandes

#### Commandes Simples
```bash
# Exécuter un script
gestvenv run monapp python script.py

# Commande avec arguments
gestvenv run monapp python manage.py migrate

# Commande interactive
gestvenv run monapp python -i
```

#### Commandes Complexes
```bash
# Exécution avec variables d'environnement
gestvenv run monapp --env DEBUG=True python manage.py runserver

# Exécution en arrière-plan
gestvenv run monapp --background celery worker

# Exécution avec timeout
gestvenv run monapp --timeout 300 python long_script.py
```

### 10. Outils de Diagnostic

#### Vérification de Santé
```bash
# Vérifier un environnement
gestvenv doctor monapp

# Vérification complète
gestvenv doctor monapp --full

# Réparation automatique
gestvenv doctor monapp --fix
```

#### Informations Système
```bash
# Versions Python disponibles
gestvenv pyversions

# Informations système
gestvenv system-info

# État du cache
gestvenv cache health-check
```

## 🎯 Exemples Pratiques

### Scenario 1: Nouveau Projet API REST
```bash
# 1. Création de l'environnement
gestvenv create api_project --python 3.11 --description "API REST avec FastAPI"

# 2. Installation des dépendances principales
gestvenv install api_project fastapi uvicorn pydantic sqlalchemy

# 3. Ajout des outils de développement
gestvenv install api_project pytest httpx black isort mypy

# 4. Configuration pour le travail hors ligne
gestvenv cache add fastapi uvicorn pytest httpx

# 5. Test hors ligne
gestvenv --offline activate api_project
gestvenv --offline run api_project pytest

# 6. Export pour l'équipe
gestvenv export api_project api_project.json
gestvenv cache export api_cache.tar.gz
```

### Scenario 2: Migration de Projet Existant
```bash
# 1. Analyser le projet existant
cat requirements.txt | head -10

# 2. Pré-télécharger toutes les dépendances
gestvenv cache add -r requirements.txt
gestvenv cache add -r dev-requirements.txt

# 3. Créer le nouvel environnement
gestvenv create legacy_migration --python 3.9

# 4. Installation hors ligne
gestvenv --offline install legacy_migration -r requirements.txt

# 5. Tests de migration
gestvenv run legacy_migration python -m pytest tests/

# 6. Validation
gestvenv doctor legacy_migration --full
```

### Scenario 3: Développement Multi-Projet
```bash
# Projet principal
gestvenv create main_app --python 3.11
gestvenv install main_app django redis celery

# Microservice 1
gestvenv clone main_app microservice_1
gestvenv install microservice_1 fastapi

# Microservice 2  
gestvenv clone main_app microservice_2
gestvenv install microservice_2 flask

# Gestion centralisée du cache
gestvenv cache list --by-project
gestvenv cache clean --projects main_app,microservice_1,microservice_2
```

## 🆘 Résolution de Problèmes

### Problèmes Courants

#### Cache Corrompu
```bash
# Vérifier l'intégrité du cache
gestvenv cache verify

# Nettoyer le cache corrompu
gestvenv cache clean --corrupted

# Reconstruire le cache
gestvenv cache rebuild
```

#### Environnement Endommagé
```bash
# Diagnostic
gestvenv doctor monapp

# Réparation
gestvenv doctor monapp --fix

# Reconstruction complète
gestvenv remove monapp
gestvenv import backup_config.json monapp
```

#### Problèmes de Performance
```bash
# Optimisation du cache
gestvenv cache optimize

# Nettoyage des anciens packages
gestvenv cache clean --older-than 30

# Défragmentation
gestvenv cache defrag
```

### Debugging Avancé

#### Mode Verbose
```bash
# Installation avec logs détaillés
gestvenv --verbose install monapp requests

# Diagnostic complet
gestvenv --verbose doctor monapp --full

# Cache avec détails
gestvenv --verbose cache info
```

#### Logs et Traces
```bash
# Afficher les logs récents
gestvenv logs

# Logs spécifiques à un environnement
gestvenv logs monapp

# Export des logs pour support
gestvenv logs --export debug.log
```

### Configuration de Récupération
```bash
# Sauvegarde de configuration
gestvenv config backup

# Restauration
gestvenv config restore backup_config.json

# Reset complet
gestvenv config reset --confirm
```

---

## 💡 Conseils et Bonnes Pratiques

### Optimisation du Cache
- Pré-téléchargez les packages lourds (numpy, pandas, tensorflow) avant de partir en déplacement
- Utilisez `gestvenv cache clean --older-than 30` régulièrement
- Configurez une taille de cache adaptée à votre espace disque

### Workflow d'Équipe
- Partagez les fichiers de configuration JSON plutôt que les environnements complets
- Utilisez l'export/import de cache pour synchroniser les équipes
- Documentez vos environnements avec `--description`

### Sécurité
- Ne jamais partager d'environnements contenant des secrets
- Utilisez des requirements.txt pour les déploiements de production
- Vérifiez l'intégrité avec `gestvenv doctor` avant les déploiements

Cette documentation couvre tous les aspects de GestVenv. Pour des questions spécifiques, consultez `gestvenv docs` ou visitez notre [documentation en ligne](https://github.com/thearchit3ct/gestvenv/wiki).