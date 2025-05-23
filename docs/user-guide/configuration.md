# Configuration de GestVenv

## Introduction

GestVenv offre de nombreuses options de configuration pour s'adapter à vos besoins spécifiques. Cette section détaille comment configurer l'outil et personnaliser son comportement à travers les fichiers de configuration et les variables d'environnement.

## Fichier de configuration principal

### Emplacement du fichier

GestVenv stocke sa configuration principale dans un fichier JSON situé à un emplacement spécifique selon votre système d'exploitation :

- **Windows** : `%APPDATA%\GestVenv\config.json`
- **macOS** : `~/Library/Application Support/GestVenv/config.json`
- **Linux** : `~/.config/gestvenv/config.json`

### Structure du fichier de configuration

Le fichier de configuration principal a la structure suivante :

```json
{
  "environments": {
    "projet1": {
      "path": "/chemin/vers/env",
      "python_version": "3.9",
      "created_at": "2025-05-18T14:30:00",
      "packages": [
        "flask==2.0.1",
        "pytest==6.2.5"
      ]
    },
    "projet2": {
      "path": "/chemin/vers/autre/env",
      "python_version": "3.8",
      "created_at": "2025-05-10T09:15:00",
      "packages": [
        "django==4.0.0",
        "pillow==9.0.0"
      ]
    }
  },
  "active_env": "projet1",
  "default_python": "python3",
  "default_env_path": "/chemin/vers/environnements",
  "pip_options": "--index-url https://pypi.org/simple",
  "plugins_enabled": true,
  "log_level": "info"
}
```

### Affichage de la configuration actuelle

Pour afficher la configuration actuelle :

```bash
gestvenv config show
```

## Modification de la configuration

### Via la ligne de commande

Vous pouvez modifier la configuration via des commandes dédiées :

```bash
# Définir le chemin par défaut pour les environnements
gestvenv config set default_env_path "/nouveau/chemin"

# Définir la version Python par défaut
gestvenv config set default_python python3.9

# Définir les options pip par défaut
gestvenv config set pip_options "--index-url https://mon-miroir-pypi.com/simple"

# Activer ou désactiver les plugins
gestvenv config set plugins_enabled true

# Définir le niveau de log
gestvenv config set log_level debug
```

### Modification directe du fichier

Vous pouvez également éditer directement le fichier de configuration avec un éditeur de texte. Après modification, GestVenv validera automatiquement le fichier à sa prochaine utilisation.

### Réinitialisation de la configuration

Pour réinitialiser la configuration aux valeurs par défaut :

```bash
gestvenv config reset
```

## Variables d'environnement

GestVenv prend en charge plusieurs variables d'environnement qui peuvent remplacer les paramètres du fichier de configuration :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `GESTVENV_DEFAULT_PATH` | Chemin par défaut pour les environnements | `/home/user/envs` |
| `GESTVENV_DEFAULT_PYTHON` | Version Python par défaut | `python3.9` |
| `GESTVENV_PIP_OPTIONS` | Options pip par défaut | `--index-url https://pypi.org/simple` |
| `GESTVENV_LOG_LEVEL` | Niveau de log | `debug`, `info`, `warning`, `error` |
| `GESTVENV_CONFIG_PATH` | Chemin vers le fichier de configuration | `/chemin/vers/config.json` |

Exemple d'utilisation :

```bash
# Définir temporairement le niveau de log à debug
GESTVENV_LOG_LEVEL=debug gestvenv list

# Utiliser un fichier de configuration alternatif
GESTVENV_CONFIG_PATH=/chemin/vers/autre/config.json gestvenv create test_projet
```

## Configuration par projet

### Fichier .gestvenv.json

Vous pouvez créer un fichier `.gestvenv.json` dans le répertoire de votre projet pour définir des paramètres spécifiques à ce projet :

```json
{
  "environment": "mon_projet",
  "python_version": "3.9",
  "auto_activate": true,
  "pip_options": "--index-url https://pypi.org/simple",
  "scripts": {
    "test": "pytest",
    "start": "flask run"
  }
}
```

Ce fichier permet de :
- Associer automatiquement un environnement à un projet
- Activer automatiquement l'environnement lorsque vous entrez dans le répertoire (avec shell hooks)
- Définir des scripts personnalisés pour le projet

### Utilisation des scripts de projet

Avec un fichier `.gestvenv.json` configuré, vous pouvez exécuter les scripts définis :

```bash
gestvenv run-script test
# Équivalent à : gestvenv run mon_projet pytest

gestvenv run-script start
# Équivalent à : gestvenv run mon_projet flask run
```

## Personnalisation avancée

### Hooks

GestVenv prend en charge des hooks personnalisés qui s'exécutent à différentes étapes :

```bash
# Définir un hook post-création
gestvenv config set-hook post_create "echo 'Environnement créé avec succès'"

# Définir un hook pré-suppression
gestvenv config set-hook pre_remove "echo 'Suppression de l'environnement...'"
```

Les hooks disponibles sont :
- `pre_create`, `post_create` : avant/après la création d'un environnement
- `pre_remove`, `post_remove` : avant/après la suppression d'un environnement
- `pre_install`, `post_install` : avant/après l'installation de packages
- `pre_activate`, `post_activate` : avant/après l'activation d'un environnement

### Configuration de l'intégration du shell

Pour une meilleure intégration avec votre shell, vous pouvez ajouter des configurations spécifiques :

#### Bash

```bash
# Ajouter à votre ~/.bashrc
eval "$(gestvenv shell-init bash)"
```

#### Zsh

```bash
# Ajouter à votre ~/.zshrc
eval "$(gestvenv shell-init zsh)"
```

#### PowerShell

```powershell
# Ajouter à votre profil PowerShell
Invoke-Expression (& gestvenv shell-init powershell)
```

Ces intégrations permettent :
- L'auto-complétion des commandes GestVenv
- L'activation automatique des environnements basée sur le répertoire
- Des alias pour les commandes fréquentes

## Bonnes pratiques

1. **Versionnez les fichiers `.gestvenv.json`** dans vos projets pour standardiser l'environnement de développement.
2. **Utilisez des variables d'environnement** pour les configurations spécifiques à une machine.
3. **Créez des profils de configuration** pour différents contextes (développement, test, production).
4. **Vérifiez régulièrement** votre configuration avec `gestvenv config show`.
5. **Documentez les hooks personnalisés** pour faciliter la compréhension par l'équipe.

## Dépannage

- Si vous rencontrez des problèmes après une modification de configuration, vérifiez la validité du JSON avec `gestvenv config validate`.
- Pour résoudre les conflits entre variables d'environnement et fichier de configuration, utilisez `gestvenv config debug` pour voir quelle valeur est effectivement utilisée.
- En cas de corruption du fichier de configuration, utilisez `gestvenv config reset` pour revenir aux valeurs par défaut.