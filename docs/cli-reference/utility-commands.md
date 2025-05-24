# Commandes utilitaires

Ce document détaille les commandes utilitaires de GestVenv qui facilitent la gestion et l'utilisation de vos environnements virtuels Python.

## List

Liste tous les environnements virtuels gérés par GestVenv.

```bash
gestvenv list [OPTIONS]
```

### Options

- `--format {table,json,simple}` : Format de sortie (par défaut: table)
- `--sort {name,date,python}` : Trie les environnements par nom, date de création ou version Python

### Exemples

```bash
# Lister tous les environnements au format par défaut
gestvenv list

# Lister les environnements au format JSON
gestvenv list --format json

# Lister les environnements triés par date de création
gestvenv list --sort date
```

## Info

Affiche des informations détaillées sur un environnement spécifique.

```bash
gestvenv info [ENV_NAME] [OPTIONS]
```

### Arguments

- `ENV_NAME` : Nom de l'environnement (par défaut: environnement actif)

### Options

- `--format {text,json}` : Format de sortie (par défaut: text)
- `--show-packages` : Inclut la liste complète des packages installés

### Exemples

```bash
# Afficher les informations sur l'environnement actif
gestvenv info

# Afficher les informations détaillées avec packages sur un environnement spécifique
gestvenv info web_project --show-packages

# Exporter les informations au format JSON
gestvenv info data_science --format json > data_science_info.json
```

## Run

Exécute une commande dans un environnement spécifique sans avoir à l'activer manuellement.

```bash
gestvenv run [ENV_NAME] [COMMAND] [ARGS...]
```

### Arguments

- `ENV_NAME` : Nom de l'environnement dans lequel exécuter la commande
- `COMMAND` : Commande à exécuter
- `ARGS` : Arguments à passer à la commande

### Exemples

```bash
# Exécuter un script Python dans un environnement spécifique
gestvenv run web_project python app.py

# Exécuter un serveur de développement Flask
gestvenv run web_project flask run --debug

# Exécuter des tests avec pytest
gestvenv run test_env pytest tests/
```

## Rename

Renomme un environnement existant.

```bash
gestvenv rename [OLD_NAME] [NEW_NAME]
```

### Arguments

- `OLD_NAME` : Nom actuel de l'environnement
- `NEW_NAME` : Nouveau nom pour l'environnement

### Exemples

```bash
# Renommer un environnement
gestvenv rename old_project new_project
```

## Clone

Clone un environnement existant pour créer une copie.

```bash
gestvenv clone [SOURCE_ENV] [TARGET_ENV] [OPTIONS]
```

### Arguments

- `SOURCE_ENV` : Nom de l'environnement source à cloner
- `TARGET_ENV` : Nom du nouvel environnement à créer

### Options

- `--packages-only` : Clone uniquement la liste des packages, pas l'environnement complet
- `--python VERSION` : Utilise une version Python spécifique pour le nouvel environnement

### Exemples

```bash
# Cloner un environnement complet
gestvenv clone production staging

# Cloner un environnement avec une version Python différente
gestvenv clone python38_project python39_project --python python3.9

# Cloner uniquement les packages installés
gestvenv clone template new_project --packages-only
```

## Docs

Affiche la documentation de GestVenv ou ouvre le navigateur avec la documentation en ligne.

```bash
gestvenv docs [TOPIC] [OPTIONS]
```

### Arguments

- `TOPIC` : Sujet spécifique de la documentation (optionnel)

### Options

- `--offline` : Affiche la documentation en mode texte dans le terminal
- `--browser` : Ouvre la documentation dans le navigateur (par défaut)

### Exemples

```bash
# Ouvrir la documentation générale dans le navigateur
gestvenv docs

# Afficher la documentation sur l'installation en mode texte
gestvenv docs install --offline

# Ouvrir la documentation des commandes d'environnement dans le navigateur
gestvenv docs env-commands
```

## Pyversions

Liste les versions Python installées sur le système et disponibles pour GestVenv.

```bash
gestvenv pyversions [OPTIONS]
```

### Options

- `--path` : Affiche également les chemins d'installation
- `--system` : Inclut uniquement les versions installées au niveau système
- `--detail` : Affiche des informations détaillées (version exacte, date de build, etc.)

### Exemples

```bash
# Lister toutes les versions Python disponibles
gestvenv pyversions

# Lister les versions Python avec leurs chemins d'installation
gestvenv pyversions --path

# Afficher des informations détaillées sur les versions Python
gestvenv pyversions --detail
```

## Clean

Nettoie les fichiers temporaires et les caches dans les environnements.

```bash
gestvenv clean [ENV_NAME] [OPTIONS]
```

### Arguments

- `ENV_NAME` : Nom de l'environnement à nettoyer (par défaut: tous les environnements)

### Options

- `--cache` : Nettoie uniquement les caches pip
- `--packages` : Supprime les archives téléchargées des packages
- `--pyc` : Supprime les fichiers compilés Python (.pyc)
- `--all` : Effectue tous les nettoyages possibles

### Exemples

```bash
# Nettoyer les caches dans tous les environnements
gestvenv clean --cache

# Nettoyer complètement un environnement spécifique
gestvenv clean web_project --all

# Supprimer les fichiers .pyc dans un environnement
gestvenv clean data_analysis --pyc
```

## Config

Affiche ou modifie la configuration de GestVenv.

```bash
gestvenv config [ACTION] [KEY] [VALUE] [OPTIONS]
```

### Arguments

- `ACTION` : Action à effectuer (get, set, unset, list)
- `KEY` : Clé de configuration (pour get, set, unset)
- `VALUE` : Valeur à définir (pour set)

### Options

- `--global` : Applique l'action à la configuration globale
- `--local` : Applique l'action à la configuration du projet actuel

### Exemples

```bash
# Lister toutes les configurations
gestvenv config list

# Définir le chemin par défaut pour les nouveaux environnements
gestvenv config set default_path "/path/to/envs" --global

# Obtenir la valeur d'une configuration spécifique
gestvenv config get python_version

# Réinitialiser une configuration
gestvenv config unset custom_index_url
```

## Repair

Répare un environnement endommagé ou corrige des problèmes de configuration.

```bash
gestvenv repair [ENV_NAME] [OPTIONS]
```

### Arguments

- `ENV_NAME` : Nom de l'environnement à réparer

### Options

- `--config-only` : Répare uniquement les fichiers de configuration
- `--rebuild` : Reconstruit l'environnement tout en préservant la liste des packages
- `--force` : Force la réparation sans demander de confirmation

### Exemples

```bash
# Tenter de réparer un environnement endommagé
gestvenv repair broken_env

# Reconstruire entièrement un environnement
gestvenv repair corrupted_env --rebuild

# Réparer uniquement les fichiers de configuration
gestvenv repair misconfig_env --config-only
```