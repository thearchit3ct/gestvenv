# Démarrage rapide GestVenv v1.1

Apprenez les bases de GestVenv en 10 minutes.

## Installation express

```bash
pip install gestvenv[performance]
gestvenv config set-backend auto
```

## Premier environnement

### Création basique

```bash
# Environnement simple
gestvenv create monapp
cd monapp

# Activation (optionnelle avec GestVenv)
gestvenv shell monapp
```

### Depuis un projet existant

```bash
# Depuis pyproject.toml
gestvenv create-from-pyproject ./mon-projet/pyproject.toml monapp

# Depuis requirements.txt
gestvenv create monapp
gestvenv install -r requirements.txt --env monapp
```

## Gestion des packages

### Installation de packages

```bash
# Package unique
gestvenv install requests --env monapp

# Packages multiples
gestvenv install requests flask pandas --env monapp

# Avec contraintes de version
gestvenv install "requests>=2.25.0" "flask==2.0.*" --env monapp
```

### Groupes de dépendances

```bash
# Installation groupe dev
gestvenv install --group dev --env monapp

# Groupes multiples
gestvenv install --group dev --group test --env monapp

# Synchronisation complète depuis pyproject.toml
gestvenv sync monapp
```

## Workflows essentiels

### Développement web

```bash
# Création depuis template
gestvenv create-from-template web monwebapp
cd monwebapp

# Installation des dépendances
gestvenv sync .

# Ajout d'un package
gestvenv install fastapi uvicorn
```

### Data science

```bash
# Template data science
gestvenv create-from-template datascience monanalyse
cd monanalyse

# Stack complète
gestvenv install numpy pandas matplotlib jupyter scikit-learn
```

### CLI tool

```bash
# Template CLI
gestvenv create-from-template cli moncli
cd moncli

# Dépendances CLI typiques
gestvenv install click typer rich
```

## Cache et mode hors ligne

### Pré-téléchargement

```bash
# Cache des packages populaires
gestvenv cache add numpy pandas matplotlib requests flask

# Cache depuis requirements
gestvenv cache add -r requirements.txt

# Vérification du cache
gestvenv cache list
```

### Travail hors ligne

```bash
# Installation hors ligne
gestvenv --offline install requests --env monapp

# Création d'environnement hors ligne
gestvenv --offline create-from-pyproject ./pyproject.toml monapp
```

## Configuration rapide

### Réglages recommandés

```bash
# Cache activé avec 2GB
gestvenv config set cache-enabled true
gestvenv config set cache-size 2GB

# Nettoyage automatique
gestvenv config set auto-cleanup true

# Téléchargements parallèles
gestvenv config set parallel-downloads 4
```

### Configuration par projet

```bash
# Dans le répertoire du projet
gestvenv config set-local backend uv
gestvenv config set-local cache-size 500MB
```

## Commandes essentielles

### Gestion d'environnements

```bash
# Lister les environnements
gestvenv list

# Informations détaillées
gestvenv info monapp

# Activation d'environnement
gestvenv shell monapp

# Suppression
gestvenv remove monapp
```

### Gestion des packages

```bash
# Lister les packages installés
gestvenv list-packages --env monapp

# Mise à jour des packages
gestvenv update --env monapp

# Génération requirements.txt
gestvenv export requirements.txt --env monapp

# Génération pyproject.toml
gestvenv export pyproject.toml --env monapp
```

### Diagnostic et maintenance

```bash
# Diagnostic de l'environnement
gestvenv doctor

# Nettoyage du cache
gestvenv cache clean

# Réparation d'environnement
gestvenv repair monapp
```

## Exemples concrets

### Projet Flask

```bash
# Création
gestvenv create-from-template web flask-app
cd flask-app

# Installation dépendances
gestvenv install flask flask-sqlalchemy python-dotenv

# Configuration développement
gestvenv install --group dev pytest black flake8

# Lancement
gestvenv run flask run
```

### Analyse de données

```bash
# Environnement data science
gestvenv create-from-template datascience analyse-ventes
cd analyse-ventes

# Stack data science
gestvenv install pandas numpy matplotlib seaborn plotly jupyter

# Lancement Jupyter
gestvenv run jupyter notebook
```

### Package Python

```bash
# Structure de package
gestvenv create-from-template package monpackage
cd monpackage

# Outils de développement
gestvenv install --group dev build twine pytest-cov mypy

# Build et test
gestvenv run python -m build
gestvenv run pytest --cov
```

## Bonnes pratiques

### Structure de projet recommandée

```
mon-projet/
├── pyproject.toml          # Configuration principale
├── README.md
├── .gestvenv/             # Géré automatiquement
│   ├── environments/      # Environnements virtuels
│   └── cache/            # Cache local
├── src/
│   └── mon_package/
└── tests/
```

### Workflow de développement

```bash
# 1. Création projet
gestvenv create-from-template [type] monprojet

# 2. Installation dépendances
gestvenv sync .

# 3. Développement avec environnement actif
gestvenv shell .

# 4. Ajout de dépendances
gestvenv install nouvelle-dependance

# 5. Tests
gestvenv run pytest

# 6. Export pour partage
gestvenv export requirements.txt
```

### Optimisations performance

```bash
# Backend le plus rapide
gestvenv config set-backend uv

# Cache agressif
gestvenv config set cache-size 5GB
gestvenv config set cache-compression true

# Téléchargements parallèles
gestvenv config set parallel-downloads 8

# Mode binaire préféré
gestvenv config set prefer-binary true
```

## Migration rapide depuis virtualenv/conda

### Depuis virtualenv

```bash
# Environnement existant
source old-venv/bin/activate
pip freeze > requirements.txt
deactivate

# Migration vers GestVenv
gestvenv create monapp
gestvenv install -r requirements.txt --env monapp
```

### Depuis conda

```bash
# Export environnement conda
conda env export > environment.yml

# Création équivalent GestVenv
gestvenv create-from-conda environment.yml monapp
```

## Prochaines étapes

- [Guide utilisateur complet](user_guide/README.md)
- [Configuration avancée](user_guide/configuration.md)
- [Templates personnalisés](user_guide/templates.md)
- [Intégration CI/CD](examples/advanced_workflows/ci_cd_integration.md)

## Aide et support

```bash
# Aide intégrée
gestvenv --help
gestvenv create --help

# Diagnostic problèmes
gestvenv doctor --verbose

# Communauté
gestvenv feedback
```

Besoin d'aide ? Consultez la [documentation complète](index.md) ou ouvrez une [issue GitHub](https://github.com/gestvenv/gestvenv/issues).