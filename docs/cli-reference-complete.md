# Référence CLI Complète GestVenv v1.1

Cette référence couvre toutes les commandes disponibles dans GestVenv v1.1, incluant les 35 nouvelles fonctionnalités implémentées.

## 📋 Table des Matières

- [Commandes Générales](#commandes-générales)
- [Gestion des Environnements](#gestion-des-environnements)
- [Gestion des Packages](#gestion-des-packages)
- [Cache et Mode Hors Ligne](#cache-et-mode-hors-ligne)
- [Backends](#backends)
- [Templates](#templates)
- [Diagnostic et Réparation](#diagnostic-et-réparation)
- [Configuration](#configuration)
- [Import/Export](#importexport)
- [Utilitaires](#utilitaires)

## Commandes Générales

### `gestvenv --help`
Affiche l'aide générale et liste toutes les commandes disponibles.

```bash
gestvenv --help
gestvenv <commande> --help  # Aide spécifique à une commande
```

### `gestvenv --version`
Affiche la version de GestVenv.

```bash
gestvenv --version
```

### Options Globales

| Option | Description |
|--------|-------------|
| `--verbose, -v` | Mode verbeux avec informations détaillées |
| `--offline` | Mode hors ligne (utilise uniquement le cache) |
| `--help` | Affiche l'aide |
| `--version` | Affiche la version |

## Gestion des Environnements

### `create` - Création basique
Crée un nouvel environnement virtuel.

```bash
gestvenv create <nom> [OPTIONS]
```

**Options :**
- `--python <version>` : Version Python à utiliser
- `--backend {pip,uv,poetry,pdm,auto}` : Backend à utiliser (défaut: auto)
- `--template <nom>` : Template à utiliser
- `--packages <liste>` : Packages initiaux (séparés par des virgules)
- `--path <chemin>` : Chemin personnalisé pour l'environnement

**Exemples :**
```bash
# Création simple
gestvenv create monapp

# Avec options avancées
gestvenv create monapp --python 3.11 --backend uv --packages "requests,flask"
```

### `create-from-template` - 🆕 Depuis un template
Crée un environnement depuis un template intégré.

```bash
gestvenv create-from-template <template> <nom> [OPTIONS]
```

**Options :**
- `--author <nom>` : Nom de l'auteur
- `--email <email>` : Email de l'auteur  
- `--version <version>` : Version initiale (défaut: 0.1.0)
- `--python <version>` : Version Python à utiliser
- `--backend {pip,uv,poetry,pdm,auto}` : Backend à utiliser
- `--output <chemin>` : Répertoire de sortie pour le projet

**Templates disponibles :**
- `basic` : Projet Python minimal
- `cli` : Outil en ligne de commande avec Click
- `web` : Application web générique
- `fastapi` : API REST avec FastAPI + SQLAlchemy
- `django` : Application Django complète
- `data-science` : Projet ML/Data Science avec Jupyter

**Exemples :**
```bash
# Template Django
gestvenv create-from-template django monsite \
    --author "Jean Dupont" \
    --email "jean@example.com" \
    --python 3.11

# Template Data Science
gestvenv create-from-template data-science monanalyse \
    --output /projets/analyse
```

### `create-from-pyproject` - Depuis pyproject.toml
Crée un environnement depuis un fichier pyproject.toml.

```bash
gestvenv create-from-pyproject <fichier> [nom] [OPTIONS]
```

**Options :**
- `--backend {pip,uv,poetry,pdm,auto}` : Backend à utiliser
- `--groups <groupes>` : Groupes de dépendances (séparés par des virgules)
- `--python <version>` : Version Python à utiliser

**Exemples :**
```bash
# Création simple
gestvenv create-from-pyproject ./pyproject.toml monapp

# Avec groupes spécifiques
gestvenv create-from-pyproject ./pyproject.toml monapp --groups "dev,test"
```

### `create-from-conda` - 🆕 Depuis environment.yml
Crée un environnement depuis un fichier conda environment.yml.

```bash
gestvenv create-from-conda <fichier> [nom] [OPTIONS]
```

**Options :**
- `--backend {pip,uv,auto}` : Backend à utiliser
- `--python <version>` : Version Python à utiliser
- `--skip-conda-only` : Ignorer les packages conda uniquement

**Exemples :**
```bash
# Migration depuis conda
gestvenv create-from-conda ./environment.yml monapp

# En ignorant les packages conda-only
gestvenv create-from-conda ./environment.yml monapp --skip-conda-only
```

### `list` - Listage des environnements
Liste tous les environnements avec options de filtrage.

```bash
gestvenv list [OPTIONS]
```

**Options :**
- `--active-only` : Afficher seulement les environnements actifs
- `--format {table,json}` : Format de sortie (défaut: table)
- `--backend <backend>` : Filtrer par backend
- `--health <état>` : Filtrer par état de santé
- `--sort {name,created,used,size}` : Critère de tri (défaut: used)

**Exemples :**
```bash
# Liste simple
gestvenv list

# Avec filtres
gestvenv list --backend uv --sort size

# Format JSON pour scripts
gestvenv list --format json
```

### `activate` - Activation d'environnement
Active un environnement virtuel.

```bash
gestvenv activate <nom>
```

### `deactivate` - Désactivation
Désactive l'environnement actuel.

```bash
gestvenv deactivate
```

### `delete` - Suppression
Supprime un environnement.

```bash
gestvenv delete <nom> [OPTIONS]
```

**Options :**
- `--force` : Forcer la suppression même si actif
- `--backup` : Créer une sauvegarde avant suppression

### `info` - Informations détaillées
Affiche les informations détaillées d'un environnement.

```bash
gestvenv info <nom>
```

### `sync` - Synchronisation
Synchronise un environnement avec pyproject.toml.

```bash
gestvenv sync <nom> [OPTIONS]
```

**Options :**
- `--groups <groupes>` : Groupes à synchroniser (séparés par des virgules)
- `--clean` : Nettoyer les packages non listés
- `--upgrade` : Mettre à jour les packages existants

### `clone` - Clonage
Clone un environnement existant.

```bash
gestvenv clone <source> <cible> [OPTIONS]
```

**Options :**
- `--python <version>` : Version Python différente pour le clone
- `--backend {pip,uv}` : Backend différent pour le clone

## Gestion des Packages

### `list-packages` - 🆕 Listage avancé des packages
Liste les packages d'un environnement avec filtrage par groupes.

```bash
gestvenv list-packages [OPTIONS]
```

**Options :**
- `--env <nom>` : Environnement à analyser
- `--group <groupe>` : Filtrer par groupe de dépendances
- `--format {table,json}` : Format de sortie
- `--outdated` : Afficher seulement les packages obsolètes

**Exemples :**
```bash
# Tous les packages
gestvenv list-packages --env monapp

# Packages de développement uniquement
gestvenv list-packages --env monapp --group dev

# Packages obsolètes
gestvenv list-packages --env monapp --outdated
```

### `install` - Installation de packages
Installe des packages dans un environnement.

```bash
gestvenv install <packages...> [OPTIONS]
```

**Options :**
- `--env <nom>` : Environnement cible
- `--group <groupe>` : Installer dans un groupe de dépendances
- `--backend {pip,uv}` : Backend à utiliser
- `--editable, -e` : Installation en mode éditable
- `--upgrade` : Mettre à jour si déjà installé

**Exemples :**
```bash
# Installation simple
gestvenv install requests flask --env monapp

# Dans un groupe spécifique
gestvenv install pytest black --env monapp --group dev

# Mode éditable
gestvenv install -e ./mon-package --env monapp
```

### `uninstall` - Désinstallation
Désinstalle des packages.

```bash
gestvenv uninstall <packages...> [OPTIONS]
```

**Options :**
- `--env <nom>` : Environnement cible
- `--yes` : Confirmer automatiquement

### `update` - 🆕 Mise à jour
Met à jour des packages.

```bash
gestvenv update [packages...] [OPTIONS]
```

**Options :**
- `--env <nom>` : Environnement à mettre à jour
- `--all` : Mettre à jour tous les packages
- `--dry-run` : Simulation sans installation

**Exemples :**
```bash
# Packages spécifiques
gestvenv update requests flask --env monapp

# Tous les packages
gestvenv update --env monapp --all

# Simulation
gestvenv update --env monapp --all --dry-run
```

## Cache et Mode Hors Ligne

### `cache info` - Informations du cache
Affiche les informations détaillées du cache.

```bash
gestvenv cache info
```

### `cache add` - 🆕 Ajout au cache
Ajoute des packages au cache avec support des fichiers requirements.

```bash
gestvenv cache add [packages...] [OPTIONS]
```

**Options :**
- `-r, --requirements <fichier>` : Fichier requirements.txt
- `--platforms <plateformes>` : Plateformes cibles (séparées par des virgules)
- `--python-version <version>` : Version Python pour le cache

**Exemples :**
```bash
# Packages individuels
gestvenv cache add numpy pandas matplotlib

# Depuis requirements.txt
gestvenv cache add -r requirements.txt --python-version 3.11

# Multi-plateformes
gestvenv cache add tensorflow --platforms "linux_x86_64,macosx_11_0_arm64"
```

### `cache clean` - Nettoyage du cache
Nettoie le cache selon différents critères.

```bash
gestvenv cache clean [OPTIONS]
```

**Options :**
- `--older-than <jours>` : Nettoyer les éléments plus anciens que X jours
- `--size-limit <taille>` : Nettoyer pour atteindre cette taille max (ex: 500MB)
- `--force` : Forcer le nettoyage sans confirmation

### `cache export` - 🆕 Export du cache
Exporte le cache vers un fichier archive.

```bash
gestvenv cache export <fichier_sortie> [OPTIONS]
```

**Options :**
- `--compress` : Compresser l'archive

**Exemples :**
```bash
# Export simple
gestvenv cache export /backup/cache.tar.gz

# Avec compression
gestvenv cache export /backup/cache.tar.gz --compress
```

### `cache import` - 🆕 Import de cache
Importe un cache depuis un fichier archive.

```bash
gestvenv cache import <fichier> [OPTIONS]
```

**Options :**
- `--merge` : Fusionner avec le cache existant
- `--verify` : Vérifier l'intégrité après import

**Exemples :**
```bash
# Import avec remplacement
gestvenv cache import /backup/cache.tar.gz

# Fusion avec vérification
gestvenv cache import /backup/cache.tar.gz --merge --verify
```

## Backends

### `backend list` - Liste des backends
Liste les backends disponibles avec leurs capacités.

```bash
gestvenv backend list [OPTIONS]
```

**Options :**
- `--available-only` : Afficher seulement les backends disponibles

### `backend set` - Configuration du backend par défaut
Définit le backend par défaut.

```bash
gestvenv backend set <backend> [OPTIONS]
```

**Options :**
- `--global` : Définir comme backend global

**Backends supportés :**
- `auto` : Sélection automatique (recommandé)
- `uv` : Ultra-rapide, recommandé pour les performances
- `pdm` : Moderne, standards PEP 621
- `poetry` : Populaire, écosystème mature
- `pip` : Legacy, universellement compatible

### `backend info` - 🆕 Informations détaillées
Affiche les informations détaillées d'un backend.

```bash
gestvenv backend info [backend] [OPTIONS]
```

**Options :**
- `--detailed` : Informations détaillées

## Templates

### `template list` - Liste des templates
Liste les templates disponibles.

```bash
gestvenv template list [OPTIONS]
```

**Options :**
- `--category <catégorie>` : Filtrer par catégorie
- `--builtin-only` : Afficher seulement les templates intégrés

### `template create` - Création de projet depuis template
Crée un projet depuis un template (équivalent à create-from-template).

```bash
gestvenv template create <template> <nom_projet> [OPTIONS]
```

## Diagnostic et Réparation

### `doctor` - 🆕 Diagnostic avancé
Effectue un diagnostic complet du système et des environnements.

```bash
gestvenv doctor [nom] [OPTIONS]
```

**Options :**
- `--auto-fix` : Réparation automatique des problèmes détectés
- `--full` : Diagnostic complet avec recommandations
- `--performance` : Focus sur l'analyse de performance

**Exemples :**
```bash
# Diagnostic global
gestvenv doctor

# Avec auto-réparation
gestvenv doctor --auto-fix

# Performance complète
gestvenv doctor --performance --full

# Environnement spécifique
gestvenv doctor monapp
```

### `repair` - 🆕 Réparation manuelle
Répare un environnement corrompu.

```bash
gestvenv repair [nom] [OPTIONS]
```

**Options :**
- `--fix-permissions` : Réparer les permissions
- `--rebuild-metadata` : Reconstruire les métadonnées
- `--fix-packages` : Réparer les packages corrompus
- `--all` : Appliquer toutes les réparations
- `--dry-run` : Simulation sans modification

**Exemples :**
```bash
# Réparation complète
gestvenv repair monapp --all

# Réparations spécifiques
gestvenv repair monapp --fix-permissions --rebuild-metadata

# Simulation
gestvenv repair monapp --dry-run
```

## Configuration

### `config show` - Affichage de la configuration
Affiche la configuration actuelle.

```bash
gestvenv config show [OPTIONS]
```

**Options :**
- `--section <section>` : Section spécifique à afficher
- `--format {table,json}` : Format de sortie

### `config set` - 🆕 Configuration avec support local
Définit une valeur de configuration.

```bash
gestvenv config set <clé> <valeur> [OPTIONS]
```

**Options :**
- `--type {str,int,bool,float}` : Type de la valeur
- `--local` : Configuration locale au projet

**Clés supportées :**
- `preferred_backend` : Backend par défaut
- `default_python_version` : Version Python par défaut
- `auto_migrate` : Migration automatique
- `offline_mode` : Mode hors ligne
- `cache_enabled` : Cache activé
- `cache_size_mb` : Taille max du cache

**Exemples :**
```bash
# Configuration globale
gestvenv config set preferred_backend uv
gestvenv config set cache_size_mb 2000

# Configuration locale du projet
gestvenv config set --local preferred_backend poetry

# Types spécifiques
gestvenv config set cache_enabled true --type bool
```

### `config reset` - Reset de la configuration
Remet la configuration par défaut.

```bash
gestvenv config reset [OPTIONS]
```

**Options :**
- `--backup` : Créer une sauvegarde avant reset
- `--force` : Forcer sans confirmation

## Import/Export

### `export` - Export d'environnement
Exporte un environnement vers différents formats.

```bash
gestvenv export <nom> [fichier_sortie] [OPTIONS]
```

**Options :**
- `--format {json,requirements,pyproject}` : Format d'export
- `--include-cache` : Inclure le cache local

**Exemples :**
```bash
# Export JSON
gestvenv export monapp backup.json --format json

# Export requirements.txt
gestvenv export monapp requirements.txt --format requirements

# Export pyproject.toml
gestvenv export monapp project.toml --format pyproject
```

### `import` - 🆕 Import intelligent
Importe un environnement avec détection automatique du format.

```bash
gestvenv import <fichier_source> [nom] [OPTIONS]
```

**Options :**
- `--force` : Écraser l'environnement existant

**Formats supportés :**
- `.json` : Export GestVenv
- `.toml` : pyproject.toml
- `.txt` : requirements.txt
- `.yml/.yaml` : environment.yml (conda)
- `Pipfile` : Pipenv

**Exemples :**
```bash
# Auto-détection
gestvenv import ./pyproject.toml
gestvenv import ./Pipfile monapp
gestvenv import ./environment.yml monapp

# Avec nom spécifique
gestvenv import ./requirements.txt monapp --force
```

### `import-from-pipfile` - 🆕 Import Pipenv
Importe depuis un Pipfile (Pipenv).

```bash
gestvenv import-from-pipfile <pipfile> [nom] [OPTIONS]
```

**Options :**
- `--backend {pip,uv,auto}` : Backend à utiliser
- `--include-dev` : Inclure les dépendances de développement

**Exemples :**
```bash
# Import simple
gestvenv import-from-pipfile ./Pipfile monapp

# Avec dépendances dev
gestvenv import-from-pipfile ./Pipfile monapp --include-dev
```

### `convert-to-pyproject` - Conversion vers pyproject.toml
Convertit requirements.txt vers pyproject.toml.

```bash
gestvenv convert-to-pyproject <fichier_req> [OPTIONS]
```

**Options :**
- `--output, -o <fichier>` : Fichier de sortie
- `--interactive` : Mode interactif pour personnaliser

## Utilitaires

### `run` - 🆕 Exécution de commandes
Exécute une commande dans un environnement.

```bash
gestvenv run <commande...> [OPTIONS]
```

**Options :**
- `--env <nom>` : Environnement dans lequel exécuter
- `--cwd <répertoire>` : Répertoire de travail

**Exemples :**
```bash
# Script Python
gestvenv run --env monapp python script.py

# Tests
gestvenv run --env monapp pytest tests/

# Avec répertoire spécifique
gestvenv run --env monapp --cwd /projet pytest
```

### `shell` - 🆕 Shell interactif
Démarre un shell avec l'environnement activé.

```bash
gestvenv shell [OPTIONS]
```

**Options :**
- `--env <nom>` : Environnement à activer
- `--shell {bash,zsh,fish,powershell}` : Shell cible

**Exemples :**
```bash
# Shell par défaut
gestvenv shell --env monapp

# Shell spécifique
gestvenv shell --env monapp --shell zsh
```

### `feedback` - 🆕 Système de feedback
Envoie du feedback aux développeurs.

```bash
gestvenv feedback [OPTIONS]
```

**Options :**
- `--message <texte>` : Message de feedback
- `--type {bug,feature,improvement,question}` : Type de feedback
- `--anonymous` : Feedback anonyme

**Exemples :**
```bash
# Interactif
gestvenv feedback

# Direct
gestvenv feedback --message "Excellente fonctionnalité !" --type feature

# Rapport de bug
gestvenv feedback --type bug --message "Problème avec sync"
```

### `stats` - Statistiques d'utilisation
Affiche les statistiques d'utilisation.

```bash
gestvenv stats [OPTIONS]
```

**Options :**
- `--detailed` : Statistiques détaillées
- `--format {table,json}` : Format de sortie

### `cleanup` - 🆕 Nettoyage du système
Nettoie les environnements et le cache.

```bash
gestvenv cleanup [OPTIONS]
```

**Options :**
- `--orphaned` : Nettoyer seulement les environnements orphelins
- `--all` : Nettoyer tous les environnements
- `--cache` : Nettoyer aussi le cache
- `--force` : Forcer sans confirmation
- `--dry-run` : Simulation sans suppression

**Exemples :**
```bash
# Environnements orphelins
gestvenv cleanup --orphaned

# Nettoyage complet
gestvenv cleanup --all --cache --force

# Simulation
gestvenv cleanup --orphaned --dry-run
```

## Variables d'Environnement

GestVenv v1.1 supporte les variables d'environnement suivantes :

| Variable | Description | Type | Exemple |
|----------|-------------|------|---------|
| `GESTVENV_BACKEND` | Backend par défaut | string | `uv` |
| `GESTVENV_PYTHON_VERSION` | Version Python par défaut | string | `3.11` |
| `GESTVENV_CACHE_ENABLED` | Cache activé | boolean | `true` |
| `GESTVENV_CACHE_SIZE_MB` | Taille max du cache | integer | `2000` |
| `GESTVENV_OFFLINE_MODE` | Mode hors ligne | boolean | `false` |
| `GESTVENV_AUTO_MIGRATE` | Migration automatique | boolean | `true` |
| `GESTVENV_ENVIRONMENTS_PATH` | Chemin des environnements | path | `/custom/path` |
| `GESTVENV_TEMPLATES_PATH` | Chemin des templates | path | `/templates` |

**Exemple d'utilisation :**
```bash
export GESTVENV_BACKEND=uv
export GESTVENV_CACHE_ENABLED=true
export GESTVENV_CACHE_SIZE_MB=2000
gestvenv create monapp  # Utilisera uv avec cache activé
```

## Codes de Sortie

| Code | Signification |
|------|---------------|
| 0 | Succès |
| 1 | Erreur générale |
| 2 | Utilisation incorrecte |
| 130 | Interruption utilisateur (Ctrl+C) |

Cette référence couvre l'ensemble des fonctionnalités de GestVenv v1.1. Pour des exemples d'usage avancés, consultez les guides utilisateur spécialisés.