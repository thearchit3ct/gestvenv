# Guide des Templates GestVenv v1.1

Les templates de GestVenv v1.1 permettent de cr�er rapidement des projets avec une structure optimale et les bonnes pratiques int�gr�es.

## <� Vue d'Ensemble

### Templates Disponibles

| Template | Description | Cas d'usage | Niveau |
|----------|-------------|-------------|--------|
| **basic** | Projet Python minimal | Apprentissage, prototypes | D�butant |
| **cli** | Outil en ligne de commande | Scripts, utilitaires | Interm�diaire |
| **web** | Application web g�n�rique | Sites web simples | Interm�diaire |
| **fastapi** | API REST moderne | Microservices, APIs | Avanc� |
| **django** | Application web compl�te | Sites complexes, CMS | Avanc� |
| **data-science** | Analyse de donn�es | ML, Data Science, recherche | Sp�cialis� |

### Utilisation Rapide

```bash
# Lister les templates
gestvenv template list

# Cr�er depuis un template
gestvenv create-from-template <template> <nom_projet>

# Avec options avanc�es
gestvenv create-from-template django monsite \
    --author "Mon Nom" \
    --email "mon@email.com" \
    --version "1.0.0" \
    --python 3.11 \
    --output /mes-projets/monsite
```

## =� Template Basic

### Description
Le template basic cr�e une structure Python minimale mais correcte, id�ale pour l'apprentissage ou des prototypes rapides.

### Structure G�n�r�e
```
mon-projet/
   pyproject.toml          # Configuration moderne
   src/
      mon_projet/
          __init__.py
          main.py
   tests/
      __init__.py
      test_main.py
   README.md
   .gitignore
```

### Exemple d'Utilisation
```bash
gestvenv create-from-template basic mon-prototype
cd mon-prototype
gestvenv activate mon-prototype
python -m mon_projet.main
```

## =� Template CLI

### Description
Template pour cr�er des outils en ligne de commande robustes avec Click, Rich et gestion d'erreurs.

### Fonctionnalit�s Incluses
- Interface Click avec sous-commandes
- Affichage riche avec Rich
- Gestion de configuration
- Tests automatis�s
- Documentation int�gr�e

### Structure G�n�r�e
```
mon-cli/
   pyproject.toml
   src/
      mon_cli/
          __init__.py
          cli.py           # Interface principale
          commands/        # Sous-commandes
          config.py        # Configuration
          utils.py         # Utilitaires
   tests/
   docs/
   README.md
```

### D�pendances Principales
- `click>=8.1.0` - Interface CLI
- `rich>=13.0.0` - Affichage color�
- `typer>=0.9.0` - Alternative moderne � Click
- `pydantic>=2.0.0` - Validation de configuration

### Exemple d'Utilisation
```bash
gestvenv create-from-template cli mon-outil
cd mon-outil
gestvenv activate mon-outil

# D�veloppement
python -m mon_outil --help
python -m mon_outil command --option value

# Installation
pip install -e .
mon-outil --version
```

## < Template FastAPI

### Description
Template pour cr�er des APIs REST modernes avec FastAPI, SQLAlchemy, et Alembic pour les migrations.

### Fonctionnalit�s Incluses
- API REST compl�te avec FastAPI
- Base de donn�es SQLAlchemy
- Migrations Alembic
- Tests automatis�s avec pytest
- Documentation OpenAPI automatique
- Structure modulaire

### Structure G�n�r�e
```
mon-api/
   pyproject.toml
   alembic.ini              # Configuration migrations
   src/
      mon_api/
          __init__.py
          main.py          # Application FastAPI
          models/          # Mod�les SQLAlchemy
          routers/         # Endpoints API
          database.py      # Configuration DB
          dependencies.py  # D�pendances FastAPI
          config.py        # Configuration
   alembic/                 # Migrations
   tests/
   README.md
```

### D�pendances Principales
- `fastapi>=0.100.0` - Framework API
- `uvicorn[standard]>=0.20.0` - Serveur ASGI
- `sqlalchemy>=2.0.0` - ORM
- `alembic>=1.10.0` - Migrations
- `pydantic>=2.0.0` - Validation des donn�es
- `python-multipart>=0.0.6` - Support formulaires

### Exemple d'Utilisation
```bash
gestvenv create-from-template fastapi mon-api
cd mon-api
gestvenv activate mon-api

# D�veloppement
uvicorn mon_api.main:app --reload

# Tests
pytest

# Migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Endpoints par D�faut
- `GET /` - Page d'accueil de l'API
- `GET /api/v1/items/` - Liste des items
- `GET /api/v1/items/{id}` - Item sp�cifique
- `GET /docs` - Documentation interactive Swagger
- `GET /redoc` - Documentation ReDoc

## <� Template Django

### Description
Template pour applications web Django compl�tes avec configuration moderne, authentification, et structure modulaire.

### Fonctionnalit�s Incluses
- Configuration Django moderne
- Gestion des variables d'environnement
- App core pr�-configur�e
- Templates et vues de base
- Tests automatis�s
- Configuration PostgreSQL
- Debug toolbar en d�veloppement

### Structure G�n�r�e
```
mon-site/
   pyproject.toml
   manage.py
   .env.example             # Variables d'environnement
   mon_site/
      __init__.py
      settings.py          # Configuration Django
      urls.py              # URLs principales
      wsgi.py
   core/                    # App principale
      __init__.py
      admin.py
      models.py            # Mod�les de base
      views.py             # Vues
      urls.py
      tests.py
   templates/               # Templates HTML
   static/                  # Fichiers statiques
   media/                   # Uploads utilisateur
   requirements/            # Requirements par environnement
```

### D�pendances Principales
- `django>=4.2.0` - Framework web
- `django-environ>=0.10.0` - Variables d'environnement
- `psycopg2-binary>=2.9.0` - Driver PostgreSQL
- `django-debug-toolbar>=4.0.0` - Debug (dev)
- `gunicorn>=20.0.0` - Serveur de production
- `whitenoise>=6.0.0` - Fichiers statiques

### Exemple d'Utilisation
```bash
gestvenv create-from-template django mon-site \
    --author "Mon Nom" \
    --email "mon@email.com"
cd mon-site
gestvenv activate mon-site

# Configuration
cp .env.example .env
# �diter .env avec vos param�tres

# D�veloppement
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Tests
python manage.py test
```

### Configuration Pr�-int�gr�e
- Variables d'environnement avec django-environ
- Configuration multi-environnement (dev/prod)
- PostgreSQL configur�
- Gestion des fichiers statiques
- Internationalisation fran�aise
- Timezone Europe/Paris

## =, Template Data Science

### Description
Template complet pour projets de data science avec structure MLOps, notebooks Jupyter, et pipeline ML.

### Fonctionnalit�s Incluses
- Structure de projet standardis�e
- Notebooks Jupyter pr�-configur�s
- Pipeline de donn�es modulaire
- Classes de base pour mod�les ML
- Outils de visualisation
- Tests pour le code ML
- Configuration git pour notebooks

### Structure G�n�r�e
```
mon-analyse/
   pyproject.toml
   .gitignore               # Optimis� pour DS
   notebooks/
      01_exploration.ipynb # Exploration des donn�es
      02_preprocessing.ipynb
      03_modeling.ipynb
      04_evaluation.ipynb
   src/
      mon_analyse/
          data/            # Chargement des donn�es
             __init__.py
             loader.py
          models/          # Mod�les ML
             __init__.py
             base_model.py
          visualization/   # Graphiques
             __init__.py
             plots.py
          utils/           # Utilitaires
   data/
      raw/                 # Donn�es brutes
      processed/           # Donn�es trait�es
      external/            # Donn�es externes
   models/                  # Mod�les sauvegard�s
   reports/                 # Rapports g�n�r�s
   tests/
```

### D�pendances Principales
- `pandas>=2.0.0` - Manipulation de donn�es
- `numpy>=1.24.0` - Calculs num�riques
- `matplotlib>=3.7.0` - Graphiques de base
- `seaborn>=0.12.0` - Visualisation statistique
- `scikit-learn>=1.3.0` - Machine Learning
- `jupyter>=1.0.0` - Notebooks
- `jupyterlab>=4.0.0` - Interface avanc�e
- `ipykernel>=6.25.0` - Kernel Python

### Groupes de D�pendances Optionnels
```bash
# Visualisation avanc�e
gestvenv install --group viz mon-analyse

# Machine Learning avanc�
gestvenv install --group ml mon-analyse

# Deep Learning
gestvenv install --group deep mon-analyse

# NLP
gestvenv install --group nlp mon-analyse
```

### Exemple d'Utilisation
```bash
gestvenv create-from-template data-science mon-analyse
cd mon-analyse
gestvenv activate mon-analyse

# D�marrer JupyterLab
jupyter lab

# Ou Jupyter classique
jupyter notebook

# Ex�cuter des scripts
python -m mon_analyse.data.loader
python -m mon_analyse.models.base_model
```

### Classes Utilitaires Incluses

#### DataLoader
```python
from mon_analyse.data.loader import DataLoader

loader = DataLoader()
df = loader.load_raw_data("dataset.csv")
X_train, X_test, y_train, y_test = loader.split_data(df, "target")
```

#### BaseModel
```python
from mon_analyse.models.base_model import BaseModel

class MonModele(BaseModel):
    def build_model(self):
        # Impl�mentation du mod�le
        pass
    
    def train(self, X_train, y_train):
        # Entra�nement
        pass
```

#### Visualisation
```python
from mon_analyse.visualization.plots import plot_correlation_matrix

plot_correlation_matrix(df)
plot_feature_distribution(df, ['feature1', 'feature2'])
```

## =' Personnalisation des Templates

### Variables Disponibles
Tous les templates supportent ces variables de substitution :

- `{{project_name}}` - Nom du projet
- `{{package_name}}` - Nom du package Python (normalis�)
- `{{author}}` - Nom de l'auteur
- `{{email}}` - Email de l'auteur
- `{{version}}` - Version initiale
- `{{description}}` - Description du projet
- `{{license}}` - Licence (MIT par d�faut)
- `{{python_version}}` - Version Python requise

### Exemple avec Variables
```bash
gestvenv create-from-template fastapi mon-api \
    --author "Jean Dupont" \
    --email "jean@example.com" \
    --version "0.1.0" \
    --python ">=3.11"
```

### Templates Utilisateur

Vous pouvez cr�er vos propres templates dans `~/.gestvenv/templates/user/` :

```
~/.gestvenv/templates/user/
   mon-template/
       template.py          # Configuration du template
       {{package_name}}/
          __init__.py
       pyproject.toml
```

## =� Workflows Recommand�s

### Pour D�buter (Template Basic)
```bash
# 1. Cr�ation
gestvenv create-from-template basic mon-projet

# 2. D�veloppement
cd mon-projet
gestvenv activate mon-projet
code .  # Ou votre �diteur pr�f�r�

# 3. Tests
python -m pytest

# 4. Package
python -m build
```

### Pour une API (Template FastAPI)
```bash
# 1. Cr�ation avec configuration
gestvenv create-from-template fastapi mon-api \
    --author "Mon Nom" \
    --email "mon@email.com"

# 2. Setup environnement
cd mon-api
gestvenv activate mon-api

# 3. Base de donn�es
alembic upgrade head

# 4. D�veloppement
uvicorn mon_api.main:app --reload

# 5. Tests
pytest --cov=mon_api

# 6. Documentation
# Accessible sur http://localhost:8000/docs
```

### Pour Data Science (Template Data Science)
```bash
# 1. Cr�ation
gestvenv create-from-template data-science mon-analyse

# 2. Setup avec extensions
cd mon-analyse
gestvenv activate mon-analyse
gestvenv install --group viz --group ml

# 3. Configuration Git pour notebooks
nbstripout --install

# 4. D�marrage
jupyter lab

# 5. Structure recommand�e :
#    - 01_exploration.ipynb : EDA
#    - 02_preprocessing.ipynb : Nettoyage
#    - 03_modeling.ipynb : Mod�lisation
#    - 04_evaluation.ipynb : �valuation
```

Ce guide couvre l'utilisation compl�te du syst�me de templates de GestVenv v1.1. Les templates sont con�us pour vous faire gagner du temps et appliquer les bonnes pratiques d�s le d�but de vos projets.