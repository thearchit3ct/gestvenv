# Vue d'ensemble de l'interface en ligne de commande

## Introduction

GestVenv fournit une interface en ligne de commande (CLI) complète pour gérer les environnements virtuels Python. Cette référence présente la structure générale des commandes, les conventions utilisées et les fonctionnalités communes à toutes les commandes.

## Structure des commandes

Les commandes GestVenv suivent une structure cohérente :

```
gestvenv <commande> [sous-commande] [options] [arguments]
```

Où :
- `<commande>` est l'action principale à effectuer (create, install, list, etc.)
- `[sous-commande]` est une action spécifique à la commande principale (optionnel)
- `[options]` sont des paramètres optionnels précédés de `--` ou `-`
- `[arguments]` sont les valeurs requises pour la commande

## Catégories de commandes

Les commandes GestVenv sont organisées en plusieurs catégories :

1. **Commandes de gestion d'environnements** : create, activate, remove, list, info, clone, etc.
2. **Commandes de gestion de packages** : install, update, uninstall, list-packages, etc.
3. **Commandes d'import/export** : export, import, convert, etc.
4. **Commandes de configuration** : config, shell-init, etc.
5. **Commandes utilitaires** : run, run-script, search, pyversions, etc.

Chaque catégorie est détaillée dans sa propre section de la documentation.

## Options globales

Ces options peuvent être utilisées avec n'importe quelle commande :

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Affiche l'aide pour la commande |
| `--version`, `-v` | Affiche la version de GestVenv |
| `--verbose` | Affiche des informations détaillées pendant l'exécution |
| `--quiet`, `-q` | Réduit les sorties au minimum |
| `--no-color` | Désactive la coloration de la sortie |
| `--log-level` | Définit le niveau de journalisation (debug, info, warning, error) |
| `--env` | Spécifie l'environnement cible (pour les commandes qui opèrent sur un environnement) |
| `--config` | Spécifie un fichier de configuration alternatif |

Exemple d'utilisation :

```bash
gestvenv list --verbose
gestvenv install flask --env mon_projet --log-level debug
```

## Aide et documentation

### Afficher l'aide générale

```bash
gestvenv --help
```

Exemple de sortie :

```
GestVenv - Gestionnaire d'Environnements Virtuels Python

Usage:
  gestvenv <commande> [options] [arguments]

Commandes disponibles:
  Environnements:
    create        Crée un nouvel environnement virtuel
    activate      Affiche les commandes pour activer un environnement
    remove        Supprime un environnement virtuel
    list          Liste tous les environnements disponibles
    info          Affiche des informations sur un environnement
    clone         Clone un environnement existant
    
  Packages:
    install       Installe des packages dans un environnement
    update        Met à jour des packages dans un environnement
    uninstall     Supprime des packages d'un environnement
    list-packages Liste les packages installés dans un environnement
    
  Import/Export:
    export        Exporte la configuration d'un environnement
    import        Importe une configuration d'environnement
    convert       Convertit entre différents formats de configuration
    
  Utilitaires:
    run           Exécute une commande dans un environnement
    run-script    Exécute un script défini dans .gestvenv.json
    search        Recherche des packages sur PyPI
    pyversions    Liste les versions Python disponibles
    
  Configuration:
    config        Gère la configuration de GestVenv
    shell-init    Initialise l'intégration avec le shell
    
Options globales:
  --help, -h      Affiche cette aide
  --version, -v   Affiche la version
  --verbose       Affiche des informations détaillées
  --quiet, -q     Réduit les sorties au minimum
  --no-color      Désactive la coloration de la sortie
  --log-level     Définit le niveau de journalisation
  --env           Spécifie l'environnement cible
  --config        Spécifie un fichier de configuration alternatif

Pour plus d'informations sur une commande spécifique:
  gestvenv <commande> --help
```

### Afficher l'aide pour une commande spécifique

```bash
gestvenv create --help
```

Exemple de sortie :

```
GestVenv - Crée un nouvel environnement virtuel

Usage:
  gestvenv create <nom> [options]

Arguments:
  <nom>           Nom de l'environnement à créer

Options:
  --python        Version Python à utiliser (ex: python3.9)
  --packages      Liste de packages à installer, séparés par des virgules
  --requirements  Chemin vers un fichier requirements.txt
  --path          Chemin personnalisé pour l'environnement
  --minimal       Crée un environnement minimal (sans pip)
  --system-site   Permet l'accès aux packages du système
  --help, -h      Affiche cette aide

Exemples:
  gestvenv create mon_projet
  gestvenv create mon_projet --python python3.9
  gestvenv create mon_projet --packages "flask,pytest"
  gestvenv create mon_projet --requirements requirements.txt
```

## Complétion automatique

GestVenv prend en charge la complétion automatique des commandes dans les shells compatibles.

### Bash

```bash
# Ajouter à votre ~/.bashrc
eval "$(gestvenv shell-init bash)"
```

### Zsh

```bash
# Ajouter à votre ~/.zshrc
eval "$(gestvenv shell-init zsh)"
```

### PowerShell

```powershell
# Ajouter à votre profil PowerShell
Invoke-Expression (& gestvenv shell-init powershell)
```

## Format de sortie

GestVenv utilise un format de sortie cohérent avec une coloration appropriée :

- **Vert** : Succès, informations positives
- **Jaune** : Avertissements
- **Rouge** : Erreurs
- **Bleu** : Informations, en-têtes
- **Gras** : Éléments importants, noms d'environnements

Pour désactiver la coloration :

```bash
gestvenv --no-color list
```

## Codes de retour

GestVenv utilise les codes de retour standards pour indiquer le résultat d'une commande :

| Code | Signification |
|------|---------------|
| 0    | Succès |
| 1    | Erreur générale |
| 2    | Erreur d'utilisation (options/arguments invalides) |
| 3    | Environnement non trouvé |
| 4    | Erreur d'exécution de commande externe |
| 5    | Erreur de permission |

Ces codes peuvent être utilisés dans des scripts pour vérifier le résultat des commandes.

## Environnement actif

De nombreuses commandes opèrent sur l'environnement "actif" si aucun environnement n'est spécifié. L'environnement actif est :

1. L'environnement spécifié par l'option `--env`
2. L'environnement actuellement activé dans le shell (si l'intégration shell est configurée)
3. L'environnement défini dans le fichier `.gestvenv.json` du répertoire courant
4. L'environnement défini dans la configuration comme `active_env`

## Utilisation dans des scripts

GestVenv est conçu pour être facilement utilisable dans des scripts shell ou Python. Exemple de script shell :

```bash
#!/bin/bash
# Script pour créer et configurer un environnement Django

PROJECT_NAME=$1
ENV_NAME="${PROJECT_NAME}_env"

# Créer l'environnement
gestvenv create $ENV_NAME --python python3.9 || exit 1

# Installer Django
gestvenv install "django>=4.0.0" --env $ENV_NAME || exit 1

# Exporter la configuration
gestvenv export $ENV_NAME --output $PROJECT_NAME.json

echo "Environnement Django configuré : $ENV_NAME"
```

## Prochaines étapes

Pour des informations détaillées sur chaque catégorie de commandes, consultez les sections suivantes :

- [Commandes de gestion d'environnements](environment-commands.md)
- [Commandes de gestion de packages](package-commands.md)
- [Commandes utilitaires](utility-commands.md)
- [Options globales](global-options.md)