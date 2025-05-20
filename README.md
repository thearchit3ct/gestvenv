# GestVenv : Gestionnaire d'Environnements Virtuels Python

GestVenv est un outil en ligne de commande qui simplifie et centralise la gestion des environnements virtuels Python. Il offre une interface unifiée pour créer, gérer et partager des environnements virtuels, remplaçant la nécessité d'utiliser plusieurs outils comme venv, virtualenv ou pipenv.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-brightgreen)
![Licence](https://img.shields.io/badge/licence-MIT-green)

## Fonctionnalités principales

- **Gestion simplifiée** des environnements virtuels Python
- **Interface unifiée** pour toutes les tâches de gestion d'environnements
- **Création et suppression** d'environnements avec différentes versions Python
- **Installation et mise à jour** faciles des packages
- **Export et import** de configurations pour partager des environnements
- **Clonage d'environnements** pour dupliquer des configurations
- **Compatible** avec Windows, macOS et Linux
- **Interface CLI intuitive** avec aide contextuelle

## Installation

```bash
# Installation depuis PyPI
pip install gestvenv

# Installation depuis le code source
git clone https://github.com/votrenom/gestvenv.git
cd gestvenv
pip install -e .
```

## Utilisation

### Création d'un environnement

```bash
# Créer un nouvel environnement avec la version Python par défaut
gestvenv create mon_projet

# Créer un environnement avec une version Python spécifique
gestvenv create mon_projet --python python3.9

# Créer un environnement avec des packages initiaux
gestvenv create mon_projet --packages "flask,pytest,gunicorn"
```

### Activation et désactivation

```bash
# Activer un environnement
gestvenv activate mon_projet
# Suivre les instructions affichées

# Désactiver l'environnement actif
gestvenv deactivate
# Suivre les instructions affichées
```

### Gestion des packages

```bash
# Installer des packages dans l'environnement actif
gestvenv install "pandas,matplotlib"

# Installer des packages dans un environnement spécifique
gestvenv install "pandas,matplotlib" --env mon_projet

# Mettre à jour tous les packages
gestvenv update --all

# Vérifier les mises à jour disponibles
gestvenv check
```

### Export et import

```bash
# Exporter un environnement au format JSON
gestvenv export mon_projet --output mon_projet_config.json

# Exporter un environnement au format requirements.txt
gestvenv export mon_projet --format requirements

# Importer un environnement depuis un fichier JSON
gestvenv import mon_projet_config.json

# Importer un environnement depuis un fichier requirements.txt
gestvenv import requirements.txt --name nouveau_projet
```

### Autres commandes utiles

```bash
# Lister tous les environnements
gestvenv list

# Afficher des informations détaillées sur un environnement
gestvenv info mon_projet

# Cloner un environnement existant
gestvenv clone mon_projet mon_projet_dev

# Exécuter une commande dans un environnement spécifique
gestvenv run mon_projet python script.py

# Afficher les versions Python disponibles
gestvenv pyversions

# Consulter la documentation
gestvenv docs
```

## Structure du projet

```
gestvenv/
├── __init__.py
├── cli.py                # Interface en ligne de commande
├── core/
│   ├── __init__.py
│   ├── env_manager.py    # Gestion des environnements
│   ├── package_manager.py  # Gestion des packages
│   └── config_manager.py   # Gestion des configurations
├── utils/
│   ├── __init__.py
│   ├── path_handler.py     # Gestion des chemins
│   ├── system_commands.py  # Commandes système
│   └── validators.py       # Validation des entrées
├── templates/
│   └── default_config.json  # Configuration par défaut
└── tests/                  # Tests unitaires et d'intégration
```

## Prérequis

- Python 3.7 ou supérieur
- pip (généralement inclus avec Python)
- Accès aux commandes système pour créer des environnements virtuels

## Dépendances

- **venv/virtualenv** : Pour la création d'environnements virtuels
- **argparse** : Pour l'analyse des arguments de ligne de commande
- **pathlib** : Pour la manipulation des chemins de fichiers
- **json** : Pour la gestion des fichiers de configuration

## Configuration

Les fichiers de configuration de GestVenv sont stockés dans les emplacements suivants selon votre système d'exploitation :

- **Windows** : `%APPDATA%\GestVenv\config.json`
- **macOS** : `~/Library/Application Support/GestVenv/config.json`
- **Linux** : `~/.config/gestvenv/config.json`

Les environnements virtuels sont créés par défaut dans un sous-répertoire `environments` de ce dossier, mais vous pouvez spécifier des chemins personnalisés lors de la création.

## Avantages par rapport aux outils existants

- **Interface unifiée** : Remplace plusieurs outils avec une seule interface cohérente
- **Gestion centralisée** : Liste et gère tous vos environnements à partir d'un seul outil
- **Partage simplifié** : Export/import de configurations pour une collaboration facile
- **Multi-versions** : Support intégré pour différentes versions de Python
- **Amélioration de la productivité** : Moins de temps passé à configurer, plus de temps à développer

## Contribution

Les contributions sont bienvenues ! Voici comment vous pouvez contribuer :

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add some amazing feature'`)
4. Poussez vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## Auteur

[thearchit3ct] - [thearchit3ct@outlook.fr]

---

*GestVenv - Simplifiez votre gestion d'environnements Python*
