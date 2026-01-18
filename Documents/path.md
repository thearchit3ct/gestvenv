# Projet Python : GestVenv - Gestionnaire d'Environnements Virtuels

Je vous propose un projet de gestionnaire d'environnements virtuels Python qui simplifie la création, l'activation et la gestion des environnements virtuels. Cet outil pourrait servir d'alternative ou de complément aux outils existants comme venv, virtualenv ou pipenv.

## Objectifs du projet

- Créer une interface simple pour gérer plusieurs environnements virtuels
- Permettre la création rapide d'environnements avec des configurations prédéfinies
- Faciliter l'installation et la gestion des dépendances
- Offrir des fonctionnalités de sauvegarde et restauration d'environnements

## Fonctionnalités principales

1. Création d'environnements virtuels
2. Activation/désactivation d'environnements
3. Installation, mise à jour et suppression de packages
4. Export et import de configurations d'environnement
5. Gestion des versions Python par environnement
6. Interface en ligne de commande intuitive

## Structure du projet

```
gestvenv/
├── __init__.py
├── cli.py            # Interface en ligne de commande
├── core/
│   ├── __init__.py
│   ├── env_manager.py    # Gestion des environnements
│   ├── package_manager.py  # Gestion des packages
│   └── config_manager.py   # Gestion des configurations
├── utils/
│   ├── __init__.py
│   ├── path_handler.py     # Gestion des chemins
│   └── system_commands.py  # Commandes système
└── templates/
    └── default_config.json  # Configuration par défaut
```

## Code principal

Voici le code pour démarrer ce projet :

```python
# cli.py
import argparse
import sys
from core.env_manager import EnvManager

def main():
    parser = argparse.ArgumentParser(description="GestVenv - Gestionnaire d'environnements virtuels Python")
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")
    
    # Commande pour créer un environnement
    create_parser = subparsers.add_parser("create", help="Créer un nouvel environnement virtuel")
    create_parser.add_argument("name", help="Nom de l'environnement")
    create_parser.add_argument("--python", "-p", help="Version de Python à utiliser")
    create_parser.add_argument("--packages", "-pkg", help="Liste de packages à installer, séparés par des virgules")
    
    # Commande pour activer un environnement
    activate_parser = subparsers.add_parser("activate", help="Activer un environnement virtuel")
    activate_parser.add_argument("name", help="Nom de l'environnement à activer")
    
    # Commande pour lister les environnements
    list_parser = subparsers.add_parser("list", help="Lister tous les environnements virtuels")
    
    # Commande pour supprimer un environnement
    remove_parser = subparsers.add_parser("remove", help="Supprimer un environnement virtuel")
    remove_parser.add_argument("name", help="Nom de l'environnement à supprimer")
    
    # Commande pour installer des packages
    install_parser = subparsers.add_parser("install", help="Installer des packages dans l'environnement actif")
    install_parser.add_argument("packages", help="Liste de packages à installer, séparés par des virgules")
    
    # Commande pour exporter la configuration
    export_parser = subparsers.add_parser("export", help="Exporter la configuration d'un environnement")
    export_parser.add_argument("name", help="Nom de l'environnement")
    export_parser.add_argument("--output", "-o", help="Chemin du fichier de sortie")
    
    # Commande pour importer une configuration
    import_parser = subparsers.add_parser("import", help="Importer une configuration d'environnement")
    import_parser.add_argument("file", help="Chemin du fichier de configuration")
    import_parser.add_argument("--name", "-n", help="Nom du nouvel environnement")
    
    args = parser.parse_args()
    
    env_manager = EnvManager()
    
    if args.command == "create":
        env_manager.create_env(args.name, python_version=args.python, packages=args.packages)
    elif args.command == "activate":
        env_manager.activate_env(args.name)
    elif args.command == "list":
        env_manager.list_envs()
    elif args.command == "remove":
        env_manager.remove_env(args.name)
    elif args.command == "install":
        env_manager.install_packages(args.packages)
    elif args.command == "export":
        env_manager.export_config(args.name, output_path=args.output)
    elif args.command == "import":
        env_manager.import_config(args.file, name=args.name)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

```python
# core/env_manager.py
import os
import json
import subprocess
import platform
from pathlib import Path
import shutil
import venv

class EnvManager:
    def __init__(self):
        self.base_dir = Path.home() / ".gestvenv"
        self.envs_dir = self.base_dir / "environments"
        self.config_file = self.base_dir / "config.json"
        
        # Créer les répertoires nécessaires s'ils n'existent pas
        self.base_dir.mkdir(exist_ok=True)
        self.envs_dir.mkdir(exist_ok=True)
        
        # Charger ou créer la configuration
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "environments": {},
                "active_env": None,
                "default_python": "python3"
            }
            self._save_config()
    
    def _save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def create_env(self, name, python_version=None, packages=None):
        """Créer un nouvel environnement virtuel"""
        env_path = self.envs_dir / name
        
        if env_path.exists():
            print(f"L'environnement '{name}' existe déjà.")
            return False
        
        python_exec = python_version if python_version else self.config["default_python"]
        
        print(f"Création de l'environnement '{name}'...")
        
        try:
            # Créer l'environnement virtuel
            venv.create(env_path, with_pip=True)
            
            # Ajouter l'environnement à la configuration
            self.config["environments"][name] = {
                "path": str(env_path),
                "python_version": python_exec,
                "created_at": str(datetime.datetime.now()),
                "packages": []
            }
            
            # Installer les packages spécifiés
            if packages:
                pkg_list = [pkg.strip() for pkg in packages.split(",")]
                self._install_packages(name, pkg_list)
                self.config["environments"][name]["packages"] = pkg_list
            
            self._save_config()
            print(f"Environnement '{name}' créé avec succès.")
            return True
            
        except Exception as e:
            print(f"Erreur lors de la création de l'environnement: {e}")
            if env_path.exists():
                shutil.rmtree(env_path)
            return False
    
    def activate_env(self, name):
        """Activer un environnement virtuel"""
        if name not in self.config["environments"]:
            print(f"L'environnement '{name}' n'existe pas.")
            return False
        
        env_path = Path(self.config["environments"][name]["path"])
        
        if not env_path.exists():
            print(f"Le chemin de l'environnement '{name}' n'existe pas.")
            return False
        
        # Définir l'environnement actif dans la configuration
        self.config["active_env"] = name
        self._save_config()
        
        # Afficher les commandes pour activer l'environnement
        if platform.system() == "Windows":
            activate_script = env_path / "Scripts" / "activate.bat"
            print(f"\nPour activer l'environnement, exécutez:")
            print(f"{activate_script}")
        else:
            activate_script = env_path / "bin" / "activate"
            print(f"\nPour activer l'environnement, exécutez:")
            print(f"source {activate_script}")
        
        return True
    
    def list_envs(self):
        """Lister tous les environnements virtuels"""
        if not self.config["environments"]:
            print("Aucun environnement virtuel n'a été créé.")
            return
        
        print("\nEnvironnements virtuels disponibles:")
        print("-" * 50)
        
        for name, env_info in self.config["environments"].items():
            active = " (actif)" if name == self.config["active_env"] else ""
            print(f"{name}{active}")
            print(f"  Chemin: {env_info['path']}")
            print(f"  Python: {env_info['python_version']}")
            
            if env_info.get("packages"):
                print(f"  Packages: {', '.join(env_info['packages'])}")
            else:
                print("  Packages: Aucun")
            
            print("-" * 50)
    
    def remove_env(self, name):
        """Supprimer un environnement virtuel"""
        if name not in self.config["environments"]:
            print(f"L'environnement '{name}' n'existe pas.")
            return False
        
        env_path = Path(self.config["environments"][name]["path"])
        
        try:
            if env_path.exists():
                shutil.rmtree(env_path)
            
            # Supprimer l'environnement de la configuration
            del self.config["environments"][name]
            
            # Réinitialiser l'environnement actif si nécessaire
            if self.config["active_env"] == name:
                self.config["active_env"] = None
            
            self._save_config()
            print(f"Environnement '{name}' supprimé avec succès.")
            return True
            
        except Exception as e:
            print(f"Erreur lors de la suppression de l'environnement: {e}")
            return False
    
    def _install_packages(self, env_name, packages):
        """Installer des packages dans un environnement spécifique"""
        env_path = Path(self.config["environments"][env_name]["path"])
        
        if platform.system() == "Windows":
            pip_path = env_path / "Scripts" / "pip.exe"
        else:
            pip_path = env_path / "bin" / "pip"
        
        for package in packages:
            try:
                subprocess.run([str(pip_path), "install", package], check=True)
                print(f"Package '{package}' installé avec succès.")
            except subprocess.CalledProcessError:
                print(f"Erreur lors de l'installation du package '{package}'.")
    
    def install_packages(self, packages_str):
        """Installer des packages dans l'environnement actif"""
        if not self.config["active_env"]:
            print("Aucun environnement n'est actif. Activez un environnement d'abord.")
            return False
        
        active_env = self.config["active_env"]
        packages = [pkg.strip() for pkg in packages_str.split(",")]
        
        self._install_packages(active_env, packages)
        
        # Mettre à jour la liste des packages dans la configuration
        current_packages = self.config["environments"][active_env].get("packages", [])
        for pkg in packages:
            if pkg not in current_packages:
                current_packages.append(pkg)
        
        self.config["environments"][active_env]["packages"] = current_packages
        self._save_config()
        
        return True
    
    def export_config(self, name, output_path=None):
        """Exporter la configuration d'un environnement"""
        if name not in self.config["environments"]:
            print(f"L'environnement '{name}' n'existe pas.")
            return False
        
        env_config = self.config["environments"][name]
        
        if not output_path:
            output_path = f"{name}_config.json"
        
        with open(output_path, 'w') as f:
            json.dump(env_config, f, indent=4)
        
        print(f"Configuration de l'environnement '{name}' exportée vers '{output_path}'.")
        return True
    
    def import_config(self, config_file, name=None):
        """Importer une configuration d'environnement"""
        if not os.path.exists(config_file):
            print(f"Le fichier '{config_file}' n'existe pas.")
            return False
        
        try:
            with open(config_file, 'r') as f:
                env_config = json.load(f)
            
            if not name:
                # Utiliser le nom du fichier sans extension
                name = os.path.splitext(os.path.basename(config_file))[0]
            
            # Créer l'environnement
            self.create_env(name, python_version=env_config.get("python_version"))
            
            # Installer les packages
            if "packages" in env_config and env_config["packages"]:
                packages_str = ",".join(env_config["packages"])
                self.config["active_env"] = name
                self.install_packages(packages_str)
            
            print(f"Configuration importée avec succès pour l'environnement '{name}'.")
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'importation de la configuration: {e}")
            return False
```

## Comment utiliser ce projet

1. Installer le package (après développement) :
   ```
   pip install gestvenv
   ```

2. Créer un nouvel environnement virtuel :
   ```
   python -m gestvenv create mon_projet --python python3.9 --packages "flask,pytest"
   ```

3. Activer l'environnement :
   ```
   python -m gestvenv activate mon_projet
   ```

4. Installer des packages supplémentaires :
   ```
   python -m gestvenv install "pandas,matplotlib"
   ```

Ce projet peut être étendu avec des fonctionnalités supplémentaires comme une interface graphique, des analyses de dépendances, ou l'intégration avec des outils de gestion de projets.

Souhaitez-vous plus de détails sur une partie spécifique de ce projet ?