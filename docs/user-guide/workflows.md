# Flux de travail avec GestVenv

## Introduction

Cette section présente des flux de travail courants et des scénarios d'utilisation de GestVenv pour vous aider à intégrer efficacement l'outil dans votre processus de développement Python. Ces guides pratiques illustrent comment GestVenv peut améliorer votre productivité dans différentes situations.

## Développement d'un nouveau projet

### Workflow de base

1. **Création de l'environnement**
   ```bash
   gestvenv create mon_projet --python python3.9
   ```

2. **Activation de l'environnement**
   ```bash
   gestvenv activate mon_projet
   # Suivre les instructions affichées
   ```

3. **Installation des dépendances initiales**
   ```bash
   gestvenv install "flask,pytest,python-dotenv"
   ```

4. **Création du fichier de projet**
   ```bash
   # Dans le répertoire de votre projet
   echo '{
     "environment": "mon_projet",
     "auto_activate": true,
     "scripts": {
       "test": "pytest",
       "dev": "flask run --debug"
     }
   }' > .gestvenv.json
   ```

5. **Développement et tests**
   ```bash
   gestvenv run-script test
   gestvenv run-script dev
   ```

6. **Export de l'environnement pour le contrôle de version**
   ```bash
   gestvenv export mon_projet --output requirements.txt
   # Ajouter requirements.txt à votre dépôt Git
   ```

## Collaboration en équipe

### Partage d'un environnement de projet

1. **Développeur initial : Création et configuration**
   ```bash
   gestvenv create projet_equipe --python python3.9
   gestvenv install "django,djangorestframework,pytest,coverage"
   ```

2. **Export de la configuration complète**
   ```bash
   gestvenv export projet_equipe --output projet_equipe.json --add-metadata "description:API REST Django,auteur:Équipe Backend"
   # Ajouter projet_equipe.json au dépôt Git
   ```

3. **Autres développeurs : Import de l'environnement**
   ```bash
   git clone [url-du-repo]
   cd [repo]
   gestvenv import projet_equipe.json
   gestvenv activate projet_equipe
   ```

4. **Mise à jour après modifications**
   ```bash
   # Après avoir installé de nouveaux packages
   gestvenv install "celery,redis"
   # Mettre à jour le fichier partagé
   gestvenv export projet_equipe --output projet_equipe.json --overwrite
   # Committer les modifications
   git add projet_equipe.json
   git commit -m "Ajout de Celery et Redis pour les tâches asynchrones"
   git push
   ```

5. **Autres développeurs : Mise à jour de leur environnement**
   ```bash
   git pull
   gestvenv import projet_equipe.json --update
   ```

## Gestion de plusieurs projets

### Organisation efficace

1. **Structure de base**
   ```
   ~/projets/
   ├── projet_web/
   │   ├── .gestvenv.json  # Lié à l'environnement "web_env"
   │   └── ...
   ├── projet_api/
   │   ├── .gestvenv.json  # Lié à l'environnement "api_env"
   │   └── ...
   └── projet_data/
       ├── .gestvenv.json  # Lié à l'environnement "data_env"
       └── ...
   ```

2. **Création d'environnements dédiés**
   ```bash
   gestvenv create web_env --python python3.8
   gestvenv create api_env --python python3.9
   gestvenv create data_env --python python3.10
   ```

3. **Configuration des fichiers de projet**
   ```bash
   # Pour projet_web/.gestvenv.json
   echo '{
     "environment": "web_env",
     "auto_activate": true
   }' > projet_web/.gestvenv.json
   
   # Répéter pour les autres projets avec leurs environnements respectifs
   ```

4. **Navigation entre projets avec activation automatique**
   ```bash
   # Avec l'intégration shell configurée (voir Configuration)
   cd ~/projets/projet_web   # Active automatiquement web_env
   cd ~/projets/projet_api   # Désactive web_env, active api_env
   cd ~/projets/projet_data  # Désactive api_env, active data_env
   ```

5. **Vue d'ensemble des environnements**
   ```bash
   gestvenv list
   ```

## Migration de projets existants

### Depuis virtualenv/venv

1. **Capture des dépendances existantes**
   ```bash
   # Activer l'environnement existant
   source /chemin/vers/env/bin/activate
   # Exporter les dépendances
   pip freeze > requirements.txt
   # Désactiver l'environnement
   deactivate
   ```

2. **Création d'un environnement GestVenv**
   ```bash
   gestvenv create nouveau_projet --requirements requirements.txt
   ```

3. **Vérification de l'environnement**
   ```bash
   gestvenv info nouveau_projet
   ```

### Depuis pipenv

1. **Export depuis Pipenv**
   ```bash
   pipenv run pip freeze > requirements.txt
   ```

2. **Import dans GestVenv**
   ```bash
   gestvenv create nouveau_projet --requirements requirements.txt
   ```

## Cycle de développement continu

### Workflow quotidien

1. **Début de journée**
   ```bash
   cd ~/projets/mon_projet  # Active automatiquement l'environnement si configuré
   git pull                 # Récupérer les dernières modifications
   
   # Si les dépendances ont changé (requirements.txt mis à jour)
   gestvenv install --requirements requirements.txt
   ```

2. **Développement et tests**
   ```bash
   gestvenv run-script test  # Exécute les tests définis dans .gestvenv.json
   ```

3. **Ajout de nouvelles dépendances**
   ```bash
   gestvenv install "nouvelle-lib"
   gestvenv export mon_projet --output requirements.txt --overwrite
   # Committer les modifications de requirements.txt
   ```

4. **Fin de journée**
   ```bash
   # Optionnel: créer un snapshot de l'environnement actuel
   gestvenv snapshot mon_projet --name "jour-$(date +%Y%m%d)"
   ```

## Intégration avec les IDE

### VS Code

1. **Configuration du dossier .vscode/settings.json**
   ```json
   {
     "python.defaultInterpreterPath": "${env:HOME}/.config/gestvenv/environments/mon_projet/bin/python",
     "python.terminal.activateEnvironment": true
   }
   ```

2. **Création d'une tâche d'initialisation dans .vscode/tasks.json**
   ```json
   {
     "version": "2.0.0",
     "tasks": [
       {
         "label": "Activer GestVenv",
         "type": "shell",
         "command": "eval \"$(gestvenv activate-cmd mon_projet)\"",
         "problemMatcher": []
       }
     ]
   }
   ```

### PyCharm

1. **Configuration de l'interpréteur Python**
   - Ouvrir Settings > Project > Python Interpreter
   - Ajouter un nouvel interpréteur
   - Sélectionner "Existing environment"
   - Parcourir jusqu'à `~/.config/gestvenv/environments/mon_projet/bin/python`

## Scénarios spécialisés

### Environnements pour l'apprentissage machine

```bash
# Création d'un environnement pour data science
gestvenv create data_science --python python3.9
gestvenv install "numpy,pandas,scikit-learn,matplotlib,jupyter"

# Lancement de Jupyter Notebook
gestvenv run data_science jupyter notebook
```

### Environnements pour le développement web

```bash
# Création d'un environnement pour Django
gestvenv create django_projet --python python3.9
gestvenv install "django,djangorestframework,psycopg2-binary"

# Création d'un projet Django
gestvenv run django_projet django-admin startproject monsite
```

### Environnements pour le déploiement

```bash
# Création d'un environnement de production
gestvenv create production --python python3.9 --minimal
gestvenv install --requirements requirements-prod.txt

# Génération d'un export pour le déploiement
gestvenv export production --format requirements --output requirements-deploy.txt
```

## Bonnes pratiques

1. **Créez un fichier `.gestvenv.json`** pour chaque projet afin de standardiser l'environnement.
2. **Utilisez les scripts personnalisés** pour standardiser les commandes courantes.
3. **Exportez régulièrement** la configuration pour le partage et la sauvegarde.
4. **Configurez l'intégration shell** pour une expérience plus fluide.
5. **Organisez vos environnements** par catégorie ou par client pour une meilleure gestion.
6. **Utilisez des snapshots** avant les changements majeurs ou les mises à jour risquées.

## Automatisation avec GestVenv

### Scripting avec GestVenv

```bash
#!/bin/bash
# Script pour initialiser un nouveau projet web

PROJECT_NAME=$1
PYTHON_VERSION=${2:-python3.9}

# Créer l'environnement
gestvenv create $PROJECT_NAME --python $PYTHON_VERSION

# Installer les packages de base
gestvenv install "flask,pytest,python-dotenv,flask-sqlalchemy" --env $PROJECT_NAME

# Exporter la configuration
gestvenv export $PROJECT_NAME --output $PROJECT_NAME.json

echo "Environnement $PROJECT_NAME créé avec succès"
```

Ce document vous a présenté différents flux de travail pour intégrer GestVenv dans votre processus de développement. Adaptez ces exemples à vos besoins spécifiques pour tirer le meilleur parti de GestVenv.