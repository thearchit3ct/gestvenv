# Structure du code

Ce document détaille l'organisation du code source de GestVenv, expliquant la structure des répertoires et des fichiers ainsi que leurs responsabilités respectives.

## Organisation des répertoires

Le projet GestVenv est organisé selon la structure de répertoires suivante :

```
gestvenv/
├── __init__.py                # Définit le package et sa version
├── cli.py                     # Point d'entrée et interface en ligne de commande
├── core/                      # Logique métier principale
│   ├── __init__.py
│   ├── env_manager.py         # Gestion des environnements virtuels
│   ├── package_manager.py     # Gestion des packages
│   └── config_manager.py      # Gestion des configurations
├── utils/                     # Utilitaires communs
│   ├── __init__.py
│   ├── path_handler.py        # Gestion des chemins
│   ├── system_commands.py     # Commandes système
│   └── validators.py          # Validation des entrées
├── templates/                 # Modèles et ressources
│   └── default_config.json    # Configuration par défaut
├── commands/                  # Implémentation des commandes CLI
│   ├── __init__.py
│   ├── env_commands.py        # Commandes de gestion d'environnements
│   ├── package_commands.py    # Commandes de gestion de packages
│   └── utility_commands.py    # Commandes utilitaires
└── tests/                     # Tests unitaires et d'intégration
    ├── __init__.py
    ├── test_env_manager.py
    ├── test_package_manager.py
    └── ...
```

## Fichiers principaux

### __init__.py

Le fichier `__init__.py` à la racine du package définit les métadonnées fondamentales :

```python
"""GestVenv - Gestionnaire d'Environnements Virtuels Python."""

__version__ = '1.0.0'
__author__ = 'Votre nom'
__email__ = 'votre.email@exemple.com'
```

### cli.py

Le fichier `cli.py` est le point d'entrée principal de l'application. Il contient :

- La définition de la structure des commandes (via argparse)
- La fonction principale `main()` qui est le point d'entrée
- La logique de routage des commandes vers les implémentations appropriées

```python
#!/usr/bin/env python3
"""
Interface en ligne de commande pour GestVenv.
"""

import argparse
import sys
from gestvenv import __version__
from gestvenv.commands import env_commands, package_commands, utility_commands

def main():
    """Point d'entrée principal pour l'application GestVenv."""
    parser = create_parser()
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        try:
            return args.func(args)
        except Exception as e:
            print(f"Erreur: {str(e)}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 0

def create_parser():
    """Crée et configure le parser d'arguments."""
    # Implémentation du parser d'arguments
    # ...

if __name__ == "__main__":
    sys.exit(main())
```

## Module core

### env_manager.py

Le gestionnaire d'environnements est responsable de toutes les opérations liées aux environnements virtuels :

```python
"""
Gestionnaire d'environnements virtuels.
"""

import os
import venv
from pathlib import Path
from gestvenv.utils import path_handler, system_commands

class EnvManager:
    """Classe pour gérer les environnements virtuels Python."""
    
    def __init__(self, config_manager):
        """Initialise le gestionnaire d'environnements."""
        self.config_manager = config_manager
        
    def create_environment(self, name, python_version=None, packages=None):
        """Crée un nouvel environnement virtuel."""
        # Implémentation...
        
    def activate_environment(self, name):
        """Retourne les commandes nécessaires pour activer un environnement."""
        # Implémentation...
        
    def remove_environment(self, name, force=False):
        """Supprime un environnement virtuel existant."""
        # Implémentation...
        
    def list_environments(self):
        """Liste tous les environnements virtuels gérés."""
        # Implémentation...
        
    # Autres méthodes...
```

### package_manager.py

Le gestionnaire de packages est responsable de toutes les opérations liées aux packages Python :

```python
"""
Gestionnaire de packages pour les environnements virtuels.
"""

import subprocess
from gestvenv.utils import system_commands

class PackageManager:
    """Classe pour gérer les packages dans les environnements virtuels."""
    
    def __init__(self, env_manager):
        """Initialise le gestionnaire de packages."""
        self.env_manager = env_manager
        
    def install_packages(self, env_name, packages, options=None):
        """Installe des packages dans l'environnement spécifié."""
        # Implémentation...
        
    def uninstall_packages(self, env_name, packages, options=None):
        """Désinstalle des packages de l'environnement spécifié."""
        # Implémentation...
        
    def update_packages(self, env_name, packages=None, all_packages=False):
        """Met à jour des packages dans l'environnement spécifié."""
        # Implémentation...
        
    def list_packages(self, env_name, outdated=False):
        """Liste les packages installés dans l'environnement spécifié."""
        # Implémentation...
        
    # Autres méthodes...
```

### config_manager.py

Le gestionnaire de configuration est responsable de la gestion des configurations :

```python
"""
Gestionnaire de configuration pour GestVenv.
"""

import json
import os
from pathlib import Path
from gestvenv.utils import path_handler

class ConfigManager:
    """Classe pour gérer les configurations de GestVenv."""
    
    def __init__(self, config_path=None):
        """Initialise le gestionnaire de configuration."""
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        
    def _get_default_config_path(self):
        """Détermine le chemin par défaut du fichier de configuration."""
        # Implémentation...
        
    def _load_config(self):
        """Charge la configuration depuis le fichier."""
        # Implémentation...
        
    def save_config(self):
        """Sauvegarde la configuration dans le fichier."""
        # Implémentation...
        
    def get_env_config(self, env_name):
        """Récupère la configuration d'un environnement spécifique."""
        # Implémentation...
        
    def set_env_config(self, env_name, config_data):
        """Définit la configuration d'un environnement spécifique."""
        # Implémentation...
        
    # Autres méthodes...
```

## Module utils

### path_handler.py

Utilitaire pour gérer les chemins de fichiers :

```python
"""
Utilitaire de gestion des chemins pour GestVenv.
"""

import os
import platform
from pathlib import Path

def get_config_dir():
    """Récupère le répertoire de configuration spécifique au système."""
    # Implémentation...
    
def get_env_dir(base_dir, env_name):
    """Construit le chemin complet vers un environnement virtuel."""
    # Implémentation...
    
def ensure_dir_exists(path):
    """S'assure qu'un répertoire existe, le crée si nécessaire."""
    # Implémentation...
    
# Autres fonctions...
```

### system_commands.py

Utilitaire pour exécuter des commandes système :

```python
"""
Utilitaire pour exécuter des commandes système.
"""

import os
import platform
import subprocess
import sys

def get_os_type():
    """Détermine le type de système d'exploitation."""
    # Implémentation...
    
def run_command(cmd, env=None, cwd=None, capture_output=True):
    """Exécute une commande système avec gestion d'erreurs."""
    # Implémentation...
    
def get_python_path(version=None):
    """Récupère le chemin vers l'exécutable Python de la version spécifiée."""
    # Implémentation...
    
# Autres fonctions...
```

### validators.py

Utilitaire pour valider les entrées utilisateur :

```python
"""
Utilitaire de validation des entrées utilisateur.
"""

import re

def validate_env_name(name):
    """Valide un nom d'environnement."""
    # Implémentation...
    
def validate_package_name(name):
    """Valide un nom de package."""
    # Implémentation...
    
def validate_python_version(version):
    """Valide une version Python."""
    # Implémentation...
    
# Autres fonctions...
```

## Module commands

Ce module contient l'implémentation des commandes CLI qui font le lien entre l'interface utilisateur et la logique métier :

### env_commands.py

Implémentation des commandes de gestion d'environnements :

```python
"""
Implémentation des commandes de gestion d'environnements.
"""

from gestvenv.core.env_manager import EnvManager
from gestvenv.core.config_manager import ConfigManager

def create_env(args):
    """Implémente la commande 'create'."""
    # Implémentation...
    
def activate_env(args):
    """Implémente la commande 'activate'."""
    # Implémentation...
    
def remove_env(args):
    """Implémente la commande 'remove'."""
    # Implémentation...
    
def list_envs(args):
    """Implémente la commande 'list'."""
    # Implémentation...
    
# Autres fonctions de commande...
```

### package_commands.py

Implémentation des commandes de gestion de packages :

```python
"""
Implémentation des commandes de gestion de packages.
"""

from gestvenv.core.package_manager import PackageManager
from gestvenv.core.env_manager import EnvManager
from gestvenv.core.config_manager import ConfigManager

def install_packages(args):
    """Implémente la commande 'install'."""
    # Implémentation...
    
def uninstall_packages(args):
    """Implémente la commande 'uninstall'."""
    # Implémentation...
    
def update_packages(args):
    """Implémente la commande 'update'."""
    # Implémentation...
    
def list_packages(args):
    """Implémente la commande 'list'."""
    # Implémentation...
    
# Autres fonctions de commande...
```

## Conventions de codage

GestVenv suit les conventions Python standard (PEP 8) avec quelques règles spécifiques :

1. **Nommage** :
   - Classes en CamelCase
   - Fonctions et variables en snake_case
   - Constantes en MAJUSCULES_AVEC_UNDERSCORES

2. **Documentation** :
   - Docstrings pour tous les modules, classes et fonctions
   - Format Google-style pour les docstrings
   - Commentaires pour le code complexe

3. **Structure** :
   - Imports groupés par standard, tiers et locaux
   - Une classe par fichier pour les classes principales
   - Fonctions utilitaires regroupées par domaine

4. **Tests** :
   - Tests unitaires pour chaque classe et fonction principale
   - Nommage des tests avec le préfixe `test_`
   - Organisation des tests en miroir de la structure du code

## Flux de données

Comprendre comment les données circulent dans l'application est essentiel :

1. L'utilisateur entre une commande dans le terminal
2. `cli.py` analyse la commande et les arguments
3. `cli.py` appelle la fonction correspondante dans le module `commands`
4. La fonction de commande crée les instances nécessaires des classes de gestion
5. Les managers effectuent les opérations demandées
6. Les résultats sont formatés et affichés à l'utilisateur

## Gestion des erreurs

GestVenv utilise un système de gestion d'erreurs à plusieurs niveaux :

1. **Exceptions personnalisées** dans le répertoire `utils/exceptions.py`
2. **Validation précoce** des entrées utilisateur
3. **Journalisation détaillée** des erreurs
4. **Messages d'erreur conviviaux** pour l'utilisateur final

## Réutilisabilité

Pour favoriser la réutilisabilité du code :

1. Les composants sont conçus pour être indépendants
2. Les dépendances entre modules sont minimisées
3. Les interfaces sont clairement définies
4. La configuration est séparée de l'implémentation

Cette organisation permet d'utiliser les composants de GestVenv dans d'autres projets ou d'étendre facilement les fonctionnalités existantes.
