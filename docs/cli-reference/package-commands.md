# Commandes de gestion des packages

Ce document détaille toutes les commandes GestVenv dédiées à la gestion des packages Python.

## Install

Installe un ou plusieurs packages dans un environnement virtuel.

```bash
gestvenv install [PACKAGES] [OPTIONS]
```

### Arguments

- `PACKAGES` : Liste de packages à installer, séparés par des virgules.

### Options

- `--env ENV_NAME` : Spécifie l'environnement dans lequel installer les packages (par défaut : environnement actif)
- `--version VERSION` : Spécifie la version du package à installer (ex: pandas==1.4.0)
- `--editable, -e` : Installe le package en mode éditable (pour le développement)
- `--no-deps` : Installe le package sans installer ses dépendances
- `--index-url URL` : Spécifie l'URL de l'index de packages à utiliser
- `--from-file FILE` : Installe des packages à partir d'un fichier requirements.txt

### Exemples

```bash
# Installer plusieurs packages dans l'environnement actif
gestvenv install "pandas,matplotlib,scikit-learn"

# Installer une version spécifique d'un package dans un environnement particulier
gestvenv install "flask==2.0.1" --env web_project

# Installer à partir d'un fichier requirements.txt
gestvenv install --from-file requirements.txt

# Installer un package depuis un dépôt Git
gestvenv install "git+https://github.com/user/package.git"
```

## Update

Met à jour des packages installés dans un environnement virtuel.

```bash
gestvenv update [PACKAGES] [OPTIONS]
```

### Arguments

- `PACKAGES` : Liste de packages à mettre à jour (si omis, vérifie les mises à jour disponibles)

### Options

- `--env ENV_NAME` : Spécifie l'environnement dans lequel mettre à jour les packages
- `--all` : Met à jour tous les packages de l'environnement
- `--dry-run` : Affiche les packages qui seraient mis à jour sans effectuer l'action
- `--latest` : Met à jour vers la dernière version, même si cela rompt la compatibilité

### Exemples

```bash
# Vérifier les mises à jour disponibles dans l'environnement actif
gestvenv update

# Mettre à jour tous les packages de l'environnement "data_analysis"
gestvenv update --all --env data_analysis

# Simuler une mise à jour pour voir ce qui serait mis à jour
gestvenv update --all --dry-run
```

## Uninstall

Désinstalle un ou plusieurs packages d'un environnement virtuel.

```bash
gestvenv uninstall [PACKAGES] [OPTIONS]
```

### Arguments

- `PACKAGES` : Liste de packages à désinstaller, séparés par des virgules.

### Options

- `--env ENV_NAME` : Spécifie l'environnement dans lequel désinstaller les packages
- `--yes, -y` : Confirme automatiquement la désinstallation sans demander
- `--no-deps` : Ne supprime pas les dépendances

### Exemples

```bash
# Désinstaller deux packages de l'environnement actif
gestvenv uninstall "pandas,matplotlib"

# Désinstaller un package d'un environnement spécifique sans confirmation
gestvenv uninstall pytest --env test_env --yes
```

## List

Liste les packages installés dans un environnement virtuel.

```bash
gestvenv list [OPTIONS]
```

### Options

- `--env ENV_NAME` : Spécifie l'environnement pour lequel lister les packages
- `--outdated` : Affiche uniquement les packages ayant des mises à jour disponibles
- `--format {list,json,table}` : Format de sortie (par défaut: table)

### Exemples

```bash
# Lister tous les packages installés dans l'environnement actif
gestvenv list

# Lister les packages obsolètes dans l'environnement "web_app"
gestvenv list --outdated --env web_app

# Exporter la liste des packages au format JSON
gestvenv list --format json > packages.json
```

## Check

Vérifie les dépendances et les potentiels conflits dans un environnement.

```bash
gestvenv check [OPTIONS]
```

### Options

- `--env ENV_NAME` : Spécifie l'environnement à vérifier
- `--verbose, -v` : Affiche des informations détaillées
- `--fix` : Tente de résoudre les conflits détectés

### Exemples

```bash
# Vérifier les dépendances de l'environnement actif
gestvenv check

# Vérification détaillée d'un environnement spécifique
gestvenv check --env data_science --verbose

# Tenter de résoudre les conflits détectés
gestvenv check --fix
```

## Freeze

Génère un fichier requirements.txt à partir des packages installés.

```bash
gestvenv freeze [OPTIONS]
```

### Options

- `--env ENV_NAME` : Spécifie l'environnement à geler
- `--output FILE` : Spécifie le fichier de sortie (par défaut: requirements.txt)
- `--no-version` : N'inclut pas les versions des packages
- `--dev` : Inclut les packages de développement

### Exemples

```bash
# Générer un requirements.txt à partir de l'environnement actif
gestvenv freeze

# Spécifier un fichier de sortie pour un environnement particulier
gestvenv freeze --env web_app --output web_requirements.txt
```

## Search

Recherche des packages sur PyPI.

```bash
gestvenv search [QUERY] [OPTIONS]
```

### Arguments

- `QUERY` : Terme de recherche

### Options

- `--limit N` : Limite le nombre de résultats (par défaut: 10)
- `--info` : Affiche des informations détaillées sur le premier résultat

### Exemples

```bash
# Rechercher des packages liés à "data visualization"
gestvenv search "data visualization"

# Obtenir des informations détaillées sur un package spécifique
gestvenv search pandas --info
```
