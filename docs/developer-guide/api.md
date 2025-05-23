# Documentation de l'API

Ce document détaille l'API interne de GestVenv, fournissant une référence complète pour les développeurs souhaitant étendre ou intégrer GestVenv dans leurs propres projets.

## Vue d'ensemble

GestVenv est structuré autour de trois classes principales qui exposent des API pour gérer différents aspects du système :

1. **EnvManager** : gestion des environnements virtuels
2. **PackageManager** : gestion des packages dans les environnements
3. **ConfigManager** : gestion de la configuration

Ces classes peuvent être utilisées de manière programmatique pour intégrer les fonctionnalités de GestVenv dans d'autres applications ou scripts.

## EnvManager

La classe `EnvManager` gère la création, l'activation et la suppression des environnements virtuels.

### Initialisation

```python
from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.env_manager import EnvManager

# Initialiser avec un gestionnaire de configuration existant
config_manager = ConfigManager()
env_manager = EnvManager(config_manager)

# Ou initialiser avec un chemin de configuration personnalisé
env_manager = EnvManager(ConfigManager("/chemin/vers/config.json"))
```

### Méthodes

#### create_environment

Crée un nouvel environnement virtuel.

```python
def create_environment(self, name, python_version=None, packages=None, system_site_packages=False, prompt=None, location=None):
    """
    Crée un nouvel environnement virtuel.
    
    Args:
        name (str): Nom de l'environnement.
        python_version (str, optional): Version Python à utiliser. Par défaut None.
        packages (list, optional): Liste de packages à installer. Par défaut None.
        system_site_packages (bool, optional): Permettre l'accès aux packages système. Par défaut False.
        prompt (str, optional): Invite de commande personnalisée. Par défaut None.
        location (str, optional): Emplacement personnalisé. Par défaut None.
        
    Returns:
        dict: Configuration de l'environnement créé.
        
    Raises:
        EnvExistsError: Si l'environnement existe déjà.
        InvalidNameError: Si le nom d'environnement est invalide.
        PythonVersionError: Si la version Python spécifiée n'est pas disponible.
    """
```

#### remove_environment

Supprime un environnement virtuel existant.

```python
def remove_environment(self, name, force=False):
    """
    Supprime un environnement virtuel existant.
    
    Args:
        name (str): Nom de l'environnement à supprimer.
        force (bool, optional): Forcer la suppression sans confirmation. Par défaut False.
        
    Returns:
        bool: True si l'environnement a été supprimé avec succès, False sinon.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
    """
```

#### activate_environment

Génère les commandes pour activer un environnement.

```python
def activate_environment(self, name):
    """
    Génère les commandes nécessaires pour activer un environnement.
    
    Args:
        name (str): Nom de l'environnement à activer.
        
    Returns:
        dict: Commandes d'activation pour différents shells.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
    """
```

#### list_environments

Liste tous les environnements disponibles.

```python
def list_environments(self, detailed=False):
    """
    Liste tous les environnements disponibles.
    
    Args:
        detailed (bool, optional): Inclure des informations détaillées. Par défaut False.
        
    Returns:
        dict: Dictionnaire des environnements avec leurs informations.
    """
```

#### get_environment_info

Récupère les informations détaillées sur un environnement.

```python
def get_environment_info(self, name):
    """
    Récupère les informations détaillées sur un environnement.
    
    Args:
        name (str): Nom de l'environnement.
        
    Returns:
        dict: Informations détaillées sur l'environnement.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
    """
```

#### clone_environment

Clone un environnement existant.

```python
def clone_environment(self, source_name, target_name, python_version=None, packages_only=False):
    """
    Clone un environnement existant.
    
    Args:
        source_name (str): Nom de l'environnement source.
        target_name (str): Nom de l'environnement cible.
        python_version (str, optional): Version Python pour le nouvel environnement. Par défaut None.
        packages_only (bool, optional): Copier uniquement les packages. Par défaut False.
        
    Returns:
        dict: Configuration du nouvel environnement.
        
    Raises:
        EnvNotFoundError: Si l'environnement source n'existe pas.
        EnvExistsError: Si l'environnement cible existe déjà.
    """
```

#### rename_environment

Renomme un environnement existant.

```python
def rename_environment(self, old_name, new_name):
    """
    Renomme un environnement existant.
    
    Args:
        old_name (str): Nom actuel de l'environnement.
        new_name (str): Nouveau nom pour l'environnement.
        
    Returns:
        bool: True si l'environnement a été renommé avec succès, False sinon.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
        EnvExistsError: Si un environnement avec le nouveau nom existe déjà.
    """
```

#### run_in_environment

Exécute une commande dans un environnement spécifique.

```python
def run_in_environment(self, name, command, args=None, capture_output=False):
    """
    Exécute une commande dans un environnement spécifique.
    
    Args:
        name (str): Nom de l'environnement.
        command (str): Commande à exécuter.
        args (list, optional): Arguments pour la commande. Par défaut None.
        capture_output (bool, optional): Capturer la sortie. Par défaut False.
        
    Returns:
        tuple: Code de retour et sortie (si capture_output=True).
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
    """
```

## PackageManager

La classe `PackageManager` gère l'installation, la mise à jour et la suppression des packages dans les environnements virtuels.

### Initialisation

```python
from gestvenv.core.env_manager import EnvManager
from gestvenv.core.package_manager import PackageManager

# Initialiser avec un gestionnaire d'environnements existant
env_manager = EnvManager(ConfigManager())
package_manager = PackageManager(env_manager)
```

### Méthodes

#### install_packages

Installe des packages dans un environnement.

```python
def install_packages(self, env_name, packages, options=None):
    """
    Installe des packages dans un environnement.
    
    Args:
        env_name (str): Nom de l'environnement.
        packages (list): Liste de packages à installer.
        options (dict, optional): Options d'installation. Par défaut None.
            Peut inclure:
            - editable (bool): Mode d'installation éditable
            - no_deps (bool): Ne pas installer les dépendances
            - upgrade (bool): Mettre à jour si déjà installé
            - index_url (str): URL de l'index de packages
        
    Returns:
        bool: True si l'installation a réussi, False sinon.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
        PackageInstallError: Si l'installation a échoué.
    """
```

#### uninstall_packages

Désinstalle des packages d'un environnement.

```python
def uninstall_packages(self, env_name, packages, options=None):
    """
    Désinstalle des packages d'un environnement.
    
    Args:
        env_name (str): Nom de l'environnement.
        packages (list): Liste de packages à désinstaller.
        options (dict, optional): Options de désinstallation. Par défaut None.
            Peut inclure:
            - yes (bool): Confirmer automatiquement
            - no_deps (bool): Ne pas désinstaller les dépendances
        
    Returns:
        bool: True si la désinstallation a réussi, False sinon.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
        PackageUninstallError: Si la désinstallation a échoué.
    """
```

#### update_packages

Met à jour des packages dans un environnement.

```python
def update_packages(self, env_name, packages=None, all_packages=False, options=None):
    """
    Met à jour des packages dans un environnement.
    
    Args:
        env_name (str): Nom de l'environnement.
        packages (list, optional): Liste de packages à mettre à jour. Par défaut None.
        all_packages (bool, optional): Mettre à jour tous les packages. Par défaut False.
        options (dict, optional): Options de mise à jour. Par défaut None.
            Peut inclure:
            - latest (bool): Forcer la dernière version
            - index_url (str): URL de l'index de packages
        
    Returns:
        dict: Informations sur les packages mis à jour.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
        PackageUpdateError: Si la mise à jour a échoué.
    """
```

#### list_packages

Liste les packages installés dans un environnement.

```python
def list_packages(self, env_name, outdated=False):
    """
    Liste les packages installés dans un environnement.
    
    Args:
        env_name (str): Nom de l'environnement.
        outdated (bool, optional): Lister uniquement les packages obsolètes. Par défaut False.
        
    Returns:
        list: Liste des packages avec leurs informations.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
    """
```

#### check_dependencies

Vérifie les dépendances et conflits potentiels.

```python
def check_dependencies(self, env_name, fix=False):
    """
    Vérifie les dépendances et conflits potentiels.
    
    Args:
        env_name (str): Nom de l'environnement.
        fix (bool, optional): Tenter de résoudre les conflits. Par défaut False.
        
    Returns:
        dict: Résultats de la vérification.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
    """
```

#### freeze_requirements

Génère un fichier requirements.txt à partir des packages installés.

```python
def freeze_requirements(self, env_name, output=None, no_version=False, dev=False):
    """
    Génère un fichier requirements.txt à partir des packages installés.
    
    Args:
        env_name (str): Nom de l'environnement.
        output (str, optional): Chemin du fichier de sortie. Par défaut None.
        no_version (bool, optional): Ne pas inclure les versions. Par défaut False.
        dev (bool, optional): Inclure les packages de développement. Par défaut False.
        
    Returns:
        str: Contenu du fichier requirements ou chemin du fichier créé.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
    """
```

## ConfigManager

La classe `ConfigManager` gère le chargement, la sauvegarde et la manipulation des configurations.

### Initialisation

```python
from gestvenv.core.config_manager import ConfigManager

# Initialiser avec le chemin par défaut
config_manager = ConfigManager()

# Ou avec un chemin personnalisé
config_manager = ConfigManager("/chemin/vers/config.json")
```

### Méthodes

#### get_config

Récupère la configuration complète.

```python
def get_config(self):
    """
    Récupère la configuration complète.
    
    Returns:
        dict: Configuration complète.
    """
```

#### save_config

Sauvegarde la configuration actuelle.

```python
def save_config(self):
    """
    Sauvegarde la configuration actuelle.
    
    Returns:
        bool: True si la sauvegarde a réussi, False sinon.
    """
```

#### get_env_config

Récupère la configuration d'un environnement spécifique.

```python
def get_env_config(self, env_name):
    """
    Récupère la configuration d'un environnement spécifique.
    
    Args:
        env_name (str): Nom de l'environnement.
        
    Returns:
        dict: Configuration de l'environnement.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas dans la configuration.
    """
```

#### set_env_config

Définit la configuration d'un environnement.

```python
def set_env_config(self, env_name, config_data):
    """
    Définit la configuration d'un environnement.
    
    Args:
        env_name (str): Nom de l'environnement.
        config_data (dict): Données de configuration.
        
    Returns:
        bool: True si la configuration a été définie avec succès.
    """
```

#### remove_env_config

Supprime la configuration d'un environnement.

```python
def remove_env_config(self, env_name):
    """
    Supprime la configuration d'un environnement.
    
    Args:
        env_name (str): Nom de l'environnement.
        
    Returns:
        bool: True si la configuration a été supprimée avec succès.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas dans la configuration.
    """
```

#### export_config

Exporte la configuration d'un environnement.

```python
def export_config(self, env_name, format_type="json", output=None, metadata=None):
    """
    Exporte la configuration d'un environnement.
    
    Args:
        env_name (str): Nom de l'environnement.
        format_type (str, optional): Format d'export ("json" ou "requirements"). Par défaut "json".
        output (str, optional): Chemin du fichier de sortie. Par défaut None.
        metadata (dict, optional): Métadonnées supplémentaires. Par défaut None.
        
    Returns:
        str: Contenu exporté ou chemin du fichier créé.
        
    Raises:
        EnvNotFoundError: Si l'environnement n'existe pas.
        ValueError: Si le format spécifié n'est pas supporté.
    """
```

#### import_config

Importe une configuration.

```python
def import_config(self, source, env_name=None, python_version=None):
    """
    Importe une configuration.
    
    Args:
        source (str): Chemin du fichier source ou contenu JSON.
        env_name (str, optional): Nom pour le nouvel environnement. Par défaut None.
        python_version (str, optional): Version Python à utiliser. Par défaut None.
        
    Returns:
        dict: Configuration importée.
        
    Raises:
        FileNotFoundError: Si le fichier source n'existe pas.
        ValueError: Si le format du fichier n'est pas supporté.
    """
```

#### get_default_python

Récupère la version Python par défaut.

```python
def get_default_python(self):
    """
    Récupère la version Python par défaut.
    
    Returns:
        str: Version Python par défaut.
    """
```

#### set_default_python

Définit la version Python par défaut.

```python
def set_default_python(self, python_version):
    """
    Définit la version Python par défaut.
    
    Args:
        python_version (str): Version Python.
        
    Returns:
        bool: True si la version a été définie avec succès.
    """
```

## Exceptions personnalisées

GestVenv définit plusieurs exceptions personnalisées pour gérer les erreurs de manière structurée.

```python
from gestvenv.utils.exceptions import (
    EnvNotFoundError, 
    EnvExistsError, 
    InvalidNameError, 
    PythonVersionError,
    PackageInstallError,
    PackageUninstallError,
    PackageUpdateError,
    ConfigError
)
```

### Hiérarchie des exceptions

```
Exception
└── GestVenvError
    ├── EnvError
    │   ├── EnvNotFoundError
    │   ├── EnvExistsError
    │   └── InvalidNameError
    ├── PackageError
    │   ├── PackageInstallError
    │   ├── PackageUninstallError
    │   └── PackageUpdateError
    ├── ConfigError
    └── PythonVersionError
```

## Exemple d'utilisation de l'API

Voici un exemple complet d'utilisation programmatique de l'API GestVenv :

```python
from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.env_manager import EnvManager
from gestvenv.core.package_manager import PackageManager
from gestvenv.utils.exceptions import EnvNotFoundError, EnvExistsError

def main():
    # Initialiser les gestionnaires
    config_manager = ConfigManager()
    env_manager = EnvManager(config_manager)
    package_manager = PackageManager(env_manager)
    
    try:
        # Créer un environnement
        env_config = env_manager.create_environment(
            name="mon_projet",
            python_version="3.9",
            packages=["flask", "pytest"]
        )
        print(f"Environnement créé : {env_config}")
        
        # Lister les environnements
        envs = env_manager.list_environments()
        print(f"Environnements disponibles : {list(envs.keys())}")
        
        # Installer des packages supplémentaires
        package_manager.install_packages(
            env_name="mon_projet",
            packages=["pandas", "matplotlib"]
        )
        
        # Lister les packages installés
        packages = package_manager.list_packages("mon_projet")
        print(f"Packages installés : {packages}")
        
        # Exporter la configuration
        config = config_manager.export_config(
            env_name="mon_projet",
            output="mon_projet_config.json",
            metadata={"description": "Mon environnement de projet"}
        )
        print(f"Configuration exportée vers : {config}")
        
    except EnvExistsError:
        print("L'environnement existe déjà.")
    except EnvNotFoundError:
        print("L'environnement n'existe pas.")
    except Exception as e:
        print(f"Erreur : {str(e)}")

if __name__ == "__main__":
    main()
```

## Intégration avec d'autres applications

L'API GestVenv peut être facilement intégrée dans d'autres applications Python :

### Dans un script d'automatisation

```python
from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.env_manager import EnvManager

def setup_project_environments():
    config_manager = ConfigManager()
    env_manager = EnvManager(config_manager)
    
    # Créer un environnement de développement
    env_manager.create_environment(
        name="dev",
        packages=["flask", "pytest", "black", "flake8"]
    )
    
    # Créer un environnement de production
    env_manager.create_environment(
        name="prod",
        packages=["flask", "gunicorn"]
    )
    
    print("Environnements configurés avec succès !")

if __name__ == "__main__":
    setup_project_environments()
```

### Dans une application GUI

```python
import tkinter as tk
from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.env_manager import EnvManager

class GestVenvGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GestVenv GUI")
        
        self.config_manager = ConfigManager()
        self.env_manager = EnvManager(self.config_manager)
```
