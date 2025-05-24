#!/usr/bin/env python3
"""
GestVenv - Gestionnaire d'Environnements Virtuels Python.

Interface en ligne de commande pour créer, gérer et partager des environnements virtuels Python.
GestVenv offre une alternative unifiée aux outils existants comme venv, virtualenv et pipenv.

Usage:
    gestvenv <commande> [options] [arguments]

Commandes disponibles:
    create      - Crée un nouvel environnement virtuel
    activate    - Active un environnement virtuel
    deactivate  - Désactive l'environnement actif
    delete      - Supprime un environnement virtuel
    list        - Liste tous les environnements virtuels
    info        - Affiche des informations sur un environnement
    install     - Installe des packages dans un environnement
    uninstall   - Désinstalle des packages d'un environnement
    update      - Met à jour des packages dans un environnement
    export      - Exporte la configuration d'un environnement
    import      - Importe une configuration d'environnement
    clone       - Clone un environnement existant
    run         - Exécute une commande dans un environnement
    config      - Configure les paramètres par défaut
    check       - Vérifie les mises à jour disponibles
    pyversions  - Liste les versions Python disponibles
    docs        - Affiche la documentation
"""

import os
import sys
import argparse
import logging
import textwrap
# import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Callable

# Imports des modules core
from gestvenv.core.env_manager import EnvironmentManager
from gestvenv.core.config_manager import ConfigManager

# Imports des modules utils
from gestvenv.utils.format_utils import (
    get_color_for_terminal, format_timestamp, format_list_as_table, 
    truncate_string, format_size, format_duration
)
from gestvenv.utils.system_utils import get_terminal_size, get_current_username
from gestvenv.utils.validation_utils import parse_key_value_string

# Version de l'application
__version__ = "1.0.0"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger("gestvenv")

# Couleurs pour le terminal
COLORS = {
    "reset": get_color_for_terminal("reset"),
    "bold": get_color_for_terminal("bold"),
    "green": get_color_for_terminal("green"),
    "yellow": get_color_for_terminal("yellow"),
    "blue": get_color_for_terminal("blue"),
    "red": get_color_for_terminal("red"),
    "cyan": get_color_for_terminal("cyan"),
    "magenta": get_color_for_terminal("magenta")
}

# Classe principale pour gérer l'interface en ligne de commande
class CLI:
    """Classe pour gérer l'interface en ligne de commande de GestVenv."""
    
    def __init__(self) -> None:
        """Initialise l'interface en ligne de commande."""
        self.env_manager = EnvironmentManager()
        self.config_manager = ConfigManager()
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Crée et configure le parseur d'arguments.
        
        Returns:
            argparse.ArgumentParser: Parseur configuré
        """
        # Créer le parseur principal
        parser = argparse.ArgumentParser(
            description="GestVenv - Gestionnaire d'Environnements Virtuels Python",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent(f"""
                exemples:
                  gestvenv create mon_projet              # Crée un nouvel environnement
                  gestvenv activate mon_projet            # Active un environnement
                  gestvenv install "flask,pytest"         # Installe des packages
                  gestvenv list                          # Liste tous les environnements
                  gestvenv export mon_projet              # Exporte la configuration
                  
                Pour plus d'informations sur une commande:
                  gestvenv <commande> --help
                
                Version: {__version__}
            """)
        )
        
        parser.add_argument('--version', action='version', version=f'GestVenv {__version__}')
        parser.add_argument('--debug', action='store_true', help='Active le mode debug pour les logs détaillés')
        
        # Créer des sous-parseurs pour chaque commande
        subparsers = parser.add_subparsers(dest='command', title='commandes', help='Commande à exécuter')
        
        # Commande: create
        create_parser = subparsers.add_parser('create', help='Crée un nouvel environnement virtuel')
        create_parser.add_argument('name', help='Nom de l\'environnement à créer')
        create_parser.add_argument('--python', dest='python_version', help='Version Python à utiliser (ex: python3.9)')
        create_parser.add_argument('--packages', help='Liste de packages à installer, séparés par des virgules')
        create_parser.add_argument('--path', help='Chemin personnalisé pour l\'environnement')
        
        # Commande: activate
        activate_parser = subparsers.add_parser('activate', help='Active un environnement virtuel')
        activate_parser.add_argument('name', help='Nom de l\'environnement à activer')
        
        # Commande: deactivate
        subparsers.add_parser('deactivate', help='Désactive l\'environnement actif')
        
        # Commande: delete
        delete_parser = subparsers.add_parser('delete', help='Supprime un environnement virtuel')
        delete_parser.add_argument('name', help='Nom de l\'environnement à supprimer')
        delete_parser.add_argument('--force', action='store_true', help='Force la suppression sans confirmation')
        
        # Commande: list
        list_parser = subparsers.add_parser('list', help='Liste tous les environnements virtuels')
        list_parser.add_argument('--verbose', '-v', action='store_true', help='Affiche des informations détaillées')
        list_parser.add_argument('--json', action='store_true', help='Affiche les résultats au format JSON')
        
        # Commande: info
        info_parser = subparsers.add_parser('info', help='Affiche des informations sur un environnement')
        info_parser.add_argument('name', help='Nom de l\'environnement')
        info_parser.add_argument('--json', action='store_true', help='Affiche les résultats au format JSON')
        
        # Commande: install
        install_parser = subparsers.add_parser('install', help='Installe des packages dans l\'environnement actif ou spécifié')
        install_parser.add_argument('packages', help='Liste de packages à installer, séparés par des virgules')
        install_parser.add_argument('--env', help='Nom de l\'environnement (utilise l\'environnement actif par défaut)')
        
        # Commande: uninstall
        uninstall_parser = subparsers.add_parser('uninstall', help='Désinstalle des packages de l\'environnement actif ou spécifié')
        uninstall_parser.add_argument('packages', help='Liste de packages à désinstaller, séparés par des virgules')
        uninstall_parser.add_argument('--env', help='Nom de l\'environnement (utilise l\'environnement actif par défaut)')
        
        # Commande: update
        update_parser = subparsers.add_parser('update', help='Met à jour des packages dans l\'environnement actif ou spécifié')
        update_parser.add_argument('packages', nargs='?', help='Liste de packages à mettre à jour, séparés par des virgules')
        update_parser.add_argument('--env', help='Nom de l\'environnement (utilise l\'environnement actif par défaut)')
        update_parser.add_argument('--all', action='store_true', help='Met à jour tous les packages')
        
        # Commande: export
        export_parser = subparsers.add_parser('export', help='Exporte la configuration d\'un environnement')
        export_parser.add_argument('name', help='Nom de l\'environnement à exporter')
        export_parser.add_argument('--output', help='Chemin du fichier de sortie')
        export_parser.add_argument('--format', choices=['json', 'requirements'], default='json',
                                help='Format d\'export (json ou requirements.txt)')
        export_parser.add_argument('--add-metadata', dest='metadata',
                                help='Métadonnées supplémentaires au format "clé1:valeur1,clé2:valeur2"')
        
        # Commande: import
        import_parser = subparsers.add_parser('import', help='Importe une configuration d\'environnement')
        import_parser.add_argument('file', help='Chemin vers le fichier de configuration ou requirements.txt')
        import_parser.add_argument('--name', help='Nom à utiliser pour le nouvel environnement')
        
        # Commande: clone
        clone_parser = subparsers.add_parser('clone', help='Clone un environnement existant')
        clone_parser.add_argument('source', help='Nom de l\'environnement source')
        clone_parser.add_argument('target', help='Nom du nouvel environnement')
        
        # Commande: run
        run_parser = subparsers.add_parser('run', help='Exécute une commande dans un environnement virtuel')
        run_parser.add_argument('name', help='Nom de l\'environnement')
        run_parser.add_argument('command', nargs='+', help='Commande à exécuter')
        
        # Commande: config
        config_parser = subparsers.add_parser('config', help='Configure les paramètres par défaut')
        config_parser.add_argument('--set-python', dest='default_python',
                                help='Définit la commande Python par défaut')
        config_parser.add_argument('--show', action='store_true', help='Affiche la configuration actuelle')
        
        # Commande: check
        check_parser = subparsers.add_parser('check', help='Vérifie les mises à jour disponibles pour les packages')
        check_parser.add_argument('name', nargs='?', help='Nom de l\'environnement (utilise l\'environnement actif par défaut)')
        
        # Commande: pyversions
        subparsers.add_parser('pyversions', help='Liste les versions Python disponibles sur le système')
        
        # Commande: docs
        docs_parser = subparsers.add_parser('docs', help='Affiche la documentation')
        docs_parser.add_argument('topic', nargs='?', help='Sujet spécifique de la documentation')
        
        # Commande: cache
        cache_parser = subparsers.add_parser('cache', help='Gère le cache de packages')
        cache_subparsers = cache_parser.add_subparsers(dest='cache_command', title='commandes', help='Commande de cache à exécuter')

        # Commande: cache list
        cache_subparsers.add_parser('list', help='Liste les packages disponibles dans le cache')

        # Commande: cache clean
        cache_clean_parser = cache_subparsers.add_parser('clean', help='Nettoie le cache en supprimant les packages obsolètes')
        cache_clean_parser.add_argument('--max-age', type=int, default=90, help='Âge maximum en jours pour les packages rarement utilisés')
        cache_clean_parser.add_argument('--max-size', type=int, default=5000, help='Taille maximale du cache en Mo')

        # Commande: cache info
        cache_subparsers.add_parser('info', help='Affiche des informations sur le cache')

        # Commande: cache add
        cache_add_parser = cache_subparsers.add_parser('add', help='Ajoute un package au cache')
        cache_add_parser.add_argument('packages', help='Liste de packages à ajouter au cache, séparés par des virgules')

        # Commande: cache export
        cache_export_parser = cache_subparsers.add_parser('export', help='Exporte le contenu du cache')
        cache_export_parser.add_argument('--output', help='Chemin du fichier de sortie')

        # Commande: cache import
        cache_import_parser = cache_subparsers.add_parser('import', help='Importe des packages dans le cache')
        cache_import_parser.add_argument('file', help='Chemin vers le fichier d\'export')

        # Commande: cache remove
        cache_remove_parser = cache_subparsers.add_parser('remove', help='Supprime des packages du cache')
        cache_remove_parser.add_argument('packages', help='Liste de packages à supprimer du cache, séparés par des virgules')

        # Options pour le mode hors ligne dans les commandes existantes
        for cmd_parser in [create_parser, install_parser, update_parser]:
            cmd_parser.add_argument('--offline', action='store_true', help='Utilise uniquement les packages du cache (mode hors ligne)')
   
        # Modifier le parseur pour la commande 'config'
        # config_parser = subparsers.add_parser('config', help='Configure les paramètres par défaut')
        # config_parser.add_argument('--set-python', dest='default_python',
                                # help='Définit la commande Python par défaut')
        config_parser.add_argument('--offline', dest='offline_mode', action='store_true',
                                help='Active le mode hors ligne (utilise uniquement les packages du cache)')
        config_parser.add_argument('--online', dest='online_mode', action='store_true',
                                help='Désactive le mode hors ligne')
        config_parser.add_argument('--enable-cache', dest='enable_cache', action='store_true',
                                help='Active l\'utilisation du cache de packages')
        config_parser.add_argument('--disable-cache', dest='disable_cache', action='store_true',
                                help='Désactive l\'utilisation du cache de packages')
        config_parser.add_argument('--cache-max-size', dest='cache_max_size', type=int,
                                help='Définit la taille maximale du cache en Mo')
        config_parser.add_argument('--cache-max-age', dest='cache_max_age', type=int,
                                help='Définit l\'âge maximal des packages dans le cache en jours')
   
        return parser
    
    def print_colored(self, text: str, color: str = "reset") -> None:
        """
        Affiche du texte coloré dans le terminal.
        
        Args:
            text: Texte à afficher
            color: Couleur à utiliser
        """
        print(f"{COLORS.get(color, '')}{text}{COLORS['reset']}")
    
    def print_success(self, message: str) -> None:
        """Affiche un message de succès."""
        self.print_colored(f"✓ {message}", "green")
    
    def print_error(self, message: str) -> None:
        """Affiche un message d'erreur."""
        self.print_colored(f"✗ {message}", "red")
    
    def print_warning(self, message: str) -> None:
        """Affiche un message d'avertissement."""
        self.print_colored(f"! {message}", "yellow")
    
    def print_info(self, message: str) -> None:
        """Affiche un message d'information."""
        self.print_colored(message, "blue")
    
    def print_header(self, message: str) -> None:
        """Affiche un en-tête."""
        self.print_colored(f"\n{message}", "bold")
        self.print_colored("=" * len(message))
    

    def cmd_create(self, args: argparse.Namespace) -> int:
        """
        Commande pour créer un nouvel environnement virtuel.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        self.print_header(f"Création de l'environnement '{args.name}'")
        
        # Informations sur l'environnement en cours de création
        self.print_info(f"Nom de l'environnement: {args.name}")
        
        if args.python_version:
            self.print_info(f"Version Python spécifiée: {args.python_version}")
        else:
            default_python = self.config_manager.get_default_python()
            self.print_info(f"Utilisation de la version Python par défaut: {default_python}")
        
        if args.packages:
            self.print_info(f"Packages à installer: {args.packages}")
        
        if args.path:
            self.print_info(f"Chemin personnalisé: {args.path}")
        
        # Vérifier si le mode hors ligne est spécifié ou actif globalement
        offline_mode = args.offline if hasattr(args, 'offline') and args.offline else self.config_manager.get_offline_mode()
        
        if offline_mode:
            self.print_info("Mode hors ligne activé - utilisation uniquement des packages du cache")
            
            # Vérifier si les packages sont disponibles dans le cache
            if args.packages:
                from gestvenv.services.cache_service import CacheService
                cache_service = CacheService()
                
                packages = [pkg.strip() for pkg in args.packages.split(',') if pkg.strip()]
                missing_packages = []
                
                for pkg in packages:
                    # Extraire le nom et la version du package
                    pkg_name = pkg.split('==')[0].split('>')[0].split('<')[0].strip()
                    pkg_version = None
                    
                    if '==' in pkg:
                        pkg_version = pkg.split('==')[1].strip()
                    
                    if not cache_service.has_package(pkg_name, pkg_version):
                        missing_packages.append(pkg)
                
                if missing_packages:
                    self.print_error(f"Mode hors ligne activé mais les packages suivants ne sont pas disponibles dans le cache: {', '.join(missing_packages)}")
                    
                    # Proposer des solutions
                    self.print_info("\nSolutions possibles:")
                    self.print_info("1. Désactiver le mode hors ligne: gestvenv config --online")
                    self.print_info("2. Ajouter les packages manquants au cache: gestvenv cache add \"" + ','.join(missing_packages) + "\"")
                    self.print_info("3. Créer l'environnement sans packages: gestvenv create " + args.name + " (puis installer les packages plus tard)")
                    
                    return 1
        
        # Créer l'environnement
        success, message = self.env_manager.create_environment(
            args.name,
            python_version=args.python_version,
            packages=args.packages,
            path=args.path,
            offline=offline_mode
        )
        
        if success:
            self.print_success(message)
            
            # Afficher comment activer l'environnement
            active_cmd = self.env_manager.activate_environment(args.name)[1]
            
            if active_cmd:
                self.print_info("\nPour activer cet environnement, utilisez:")
                print(f"\n    {active_cmd}\n")
                
                self.print_info("Ou utilisez la commande intégrée:")
                print(f"\n    gestvenv activate {args.name}\n")
            
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_activate(self, args: argparse.Namespace) -> int:
        """
        Commande pour activer un environnement virtuel.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        success, message = self.env_manager.activate_environment(args.name)
        
        if success:
            # Comme nous ne pouvons pas réellement modifier l'environnement du processus parent,
            # nous affichons la commande que l'utilisateur doit exécuter
            self.print_info(f"\nPour activer l'environnement '{args.name}', exécutez:")
            print(f"\n    {message}\n")
            
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_deactivate(self, args: argparse.Namespace) -> int:
        """
        Commande pour désactiver l'environnement actif.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        success, message = self.env_manager.deactivate_environment()
        
        if success:
            self.print_info("\nPour désactiver l'environnement actif, exécutez:")
            print(f"\n    {message}\n")
            
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_delete(self, args: argparse.Namespace) -> int:
        """
        Commande pour supprimer un environnement virtuel.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        # Si --force n'est pas utilisé, demander confirmation
        if not args.force:
            confirm = input(f"Êtes-vous sûr de vouloir supprimer l'environnement '{args.name}' ? (o/N) ")
            if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
                self.print_info("Opération annulée.")
                return 0
        
        self.print_header(f"Suppression de l'environnement '{args.name}'")
        
        success, message = self.env_manager.delete_environment(args.name, force=args.force)
        
        if success:
            self.print_success(message)
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_list(self, args: argparse.Namespace) -> int:
        """
        Commande pour lister tous les environnements virtuels.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        environments = self.env_manager.list_environments()
        
        if args.json:
            # Afficher au format JSON
            import json
            print(json.dumps(environments, indent=2))
            return 0
        
        if not environments:
            self.print_info("Aucun environnement trouvé.")
            self.print_info("\nUtilisez 'gestvenv create <nom>' pour créer un nouvel environnement.")
            return 0
        
        self.print_header("Environnements virtuels disponibles")
        
        for env in environments:
            name = env["name"]
            python_version = env["python_version"]
            packages_count = env["packages_count"]
            is_active = env["active"]
            exists = env["exists"]
            
            if is_active:
                status = f"{COLORS['green']}● ACTIF{COLORS['reset']}"
            elif not exists:
                status = f"{COLORS['red']}✗ MANQUANT{COLORS['reset']}"
            else:
                status = f"{COLORS['blue']}○ inactif{COLORS['reset']}"
            
            print(f"{status}  {COLORS['bold']}{name}{COLORS['reset']}")
            
            if args.verbose:
                print(f"  Python: {python_version}")
                print(f"  Packages: {packages_count}")
                print(f"  Chemin: {env['path']}")
                print()
        
        total = len(environments)
        self.print_info(f"\nTotal: {total} environnement(s)")
        
        active_env = self.env_manager.get_active_environment()
        if active_env:
            self.print_info(f"Environnement actif: {active_env}")
        
        return 0
    
    def cmd_info(self, args: argparse.Namespace) -> int:
        """
        Commande pour afficher des informations détaillées sur un environnement.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        env_info = self.env_manager.get_environment_info(args.name)
        
        if not env_info:
            self.print_error(f"L'environnement '{args.name}' n'existe pas.")
            return 1
        
        if args.json:
            # Afficher au format JSON
            import json
            print(json.dumps(env_info, indent=2))
            return 0
        
        self.print_header(f"Informations sur l'environnement '{args.name}'")
        
        # Statut
        if env_info["active"]:
            status = f"{COLORS['green']}● ACTIF{COLORS['reset']}"
        elif not env_info["exists"]:
            status = f"{COLORS['red']}✗ MANQUANT{COLORS['reset']}"
        else:
            status = f"{COLORS['blue']}○ inactif{COLORS['reset']}"
        
        print(f"Statut: {status}")
        print(f"Python: {env_info['python_version']}")
        
        # Formater la date de création si elle est présente
        if 'created_at' in env_info:
            created_at = format_timestamp(env_info['created_at'])
            print(f"Créé le: {created_at}")
        
        print(f"Chemin: {env_info['path']}")
        
        # Santé de l'environnement
        health = env_info.get("health", {})
        if env_info["exists"]:
            health_status = []
            for check, result in health.items():
                icon = "✓" if result else "✗"
                color = "green" if result else "red"
                health_status.append(f"{COLORS[color]}{icon}{COLORS['reset']} {check}")
            
            print("\nSanté de l'environnement:")
            print("  " + ", ".join(health_status))
        
        # Packages
        self.print_header("Packages installés")
        
        packages_installed = env_info.get("packages_installed", [])
        if not packages_installed:
            self.print_info("Aucun package installé.")
        else:
            # Trier les packages par nom
            packages = sorted(packages_installed, key=lambda x: x["name"])
            
            for pkg in packages:
                print(f"{pkg['name']} {COLORS['cyan']}=={COLORS['reset']} {pkg['version']}")
        
        return 0
    
    def cmd_install(self, args: argparse.Namespace) -> int:
        """
        Commande pour installer des packages dans un environnement.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        # Déterminer l'environnement cible
        env_name = args.env
        if not env_name:
            env_name = self.env_manager.get_active_environment()
            if not env_name:
                self.print_error("Aucun environnement actif. Spécifiez un environnement avec --env.")
                return 1
        
        self.print_header(f"Installation de packages dans '{env_name}'")
        self.print_info(f"Packages à installer: {args.packages}")
        
        # Installer les packages
        success, message = self.env_manager.update_packages(
            env_name, 
            packages=args.packages, 
            all_packages=False
        )
        
        if success:
            self.print_success(message)
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_uninstall(self, args: argparse.Namespace) -> int:
        """
        Commande pour désinstaller des packages d'un environnement.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        # Déterminer l'environnement cible
        env_name = args.env
        if not env_name:
            env_name = self.env_manager.get_active_environment()
            if not env_name:
                self.print_error("Aucun environnement actif. Spécifiez un environnement avec --env.")
                return 1
        
        # Demander confirmation
        confirm = input(f"Êtes-vous sûr de vouloir désinstaller les packages suivants de '{env_name}' ?\n"
                       f"{args.packages}\n"
                       f"(o/N) ")
        
        if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
            self.print_info("Opération annulée.")
            return 0
        
        self.print_header(f"Désinstallation de packages de '{env_name}'")
        
        # TODO: Implémenter la méthode uninstall_packages dans l'EnvironmentManager
        # Pour l'instant, nous utilisons un message temporaire
        self.print_error("La désinstallation de packages n'est pas encore implémentée.")
        return 1
    
    def cmd_update(self, args: argparse.Namespace) -> int:
        """
        Commande pour mettre à jour des packages dans un environnement.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        # Déterminer l'environnement cible
        env_name = args.env
        if not env_name:
            env_name = self.env_manager.get_active_environment()
            if not env_name:
                self.print_error("Aucun environnement actif. Spécifiez un environnement avec --env.")
                return 1
        
        if not args.packages and not args.all:
            self.print_error("Vous devez spécifier des packages à mettre à jour ou utiliser --all")
            return 1
        
        self.print_header(f"Mise à jour de packages dans '{env_name}'")
        
        if args.all:
            self.print_info("Mise à jour de tous les packages")
        else:
            self.print_info(f"Packages à mettre à jour: {args.packages}")
        
        # Mettre à jour les packages
        success, message = self.env_manager.update_packages(
            env_name, 
            packages=args.packages, 
            all_packages=args.all
        )
        
        if success:
            self.print_success(message)
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_export(self, args: argparse.Namespace) -> int:
        """
        Commande pour exporter la configuration d'un environnement.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        self.print_header(f"Export de l'environnement '{args.name}'")
        
        format_type = args.format
        self.print_info(f"Format d'export: {format_type}")
        
        if args.output:
            self.print_info(f"Fichier de sortie: {args.output}")
        
        # Exporter l'environnement
        success, message = self.env_manager.export_environment(
            args.name,
            output_path=args.output,
            format_type=format_type,
            metadata=args.metadata
        )
        
        if success:
            self.print_success(message)
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_import(self, args: argparse.Namespace) -> int:
        """
        Commande pour importer une configuration d'environnement.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        self.print_header("Import d'environnement")
        
        self.print_info(f"Fichier source: {args.file}")
        if args.name:
            self.print_info(f"Nom de l'environnement: {args.name}")
        
        # Importer l'environnement
        success, message = self.env_manager.import_environment(args.file, args.name)
        
        if success:
            self.print_success(message)
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_clone(self, args: argparse.Namespace) -> int:
        """
        Commande pour cloner un environnement existant.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        self.print_header(f"Clonage de l'environnement '{args.source}' vers '{args.target}'")
        
        # Cloner l'environnement
        success, message = self.env_manager.clone_environment(args.source, args.target)
        
        if success:
            self.print_success(message)
            return 0
        else:
            self.print_error(message)
            return 1
    
    def cmd_run(self, args: argparse.Namespace) -> int:
        """
        Commande pour exécuter une commande dans un environnement virtuel.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        command = args.command
        
        self.print_header(f"Exécution dans l'environnement '{args.name}'")
        self.print_info(f"Commande: {' '.join(command)}")
        
        # Exécuter la commande dans l'environnement
        ret_code, stdout, stderr = self.env_manager.run_command_in_environment(args.name, command)
        
        if stdout:
            print(stdout)
        if stderr:
            self.print_error(stderr)
        
        return int(ret_code) if ret_code is not None else 1
    
    def cmd_config(self, args: argparse.Namespace) -> int:
       """
       Commande pour configurer les paramètres par défaut.
    
       Args:
           args: Arguments de ligne de commande

       Returns:
           int: Code de retour (0 pour succès, autre pour erreur)
       """
       # Variables pour suivre si des modifications ont été effectuées
       modified = False
    
       if args.default_python:
           self.print_header("Configuration de Python par défaut")

           # Définir la commande Python par défaut
           success, message = self.env_manager.set_default_python(args.default_python)

           if success:
               self.print_success(message)
               modified = True
           else:
               self.print_error(message)
               return 1
    
       # Gestion du mode hors ligne
       if args.offline_mode and args.online_mode:
           self.print_error("Options incompatibles: --offline et --online ne peuvent pas être utilisées ensemble")
           return 1
    
       if args.offline_mode:
           self.print_header("Activation du mode hors ligne")

           if self.config_manager.set_offline_mode(True):
               self.print_success("Mode hors ligne activé")
               modified = True
           else:
               self.print_error("Échec de l'activation du mode hors ligne")
               return 1
    
       if args.online_mode:
           self.print_header("Désactivation du mode hors ligne")

           if self.config_manager.set_offline_mode(False):
               self.print_success("Mode hors ligne désactivé")
               modified = True
           else:
               self.print_error("Échec de la désactivation du mode hors ligne")
               return 1
    
       # Gestion du cache
       if args.enable_cache and args.disable_cache:
           self.print_error("Options incompatibles: --enable-cache et --disable-cache ne peuvent pas être utilisées ensemble")
           return 1
    
       if args.enable_cache:
           self.print_header("Activation du cache de packages")

           if self.config_manager.set_cache_enabled(True):
               self.print_success("Cache de packages activé")
               modified = True
           else:
               self.print_error("Échec de l'activation du cache de packages")
               return 1
    
       if args.disable_cache:
           self.print_header("Désactivation du cache de packages")

           if self.config_manager.set_cache_enabled(False):
               self.print_success("Cache de packages désactivé")
               modified = True
           else:
               self.print_error("Échec de la désactivation du cache de packages")
               return 1
    
       # Configuration de la taille maximale du cache
       if args.cache_max_size:
           self.print_header(f"Configuration de la taille maximale du cache: {args.cache_max_size} Mo")

           if self.config_manager.set_setting("cache_max_size_mb", args.cache_max_size):
               self.print_success(f"Taille maximale du cache définie à {args.cache_max_size} Mo")
               modified = True
           else:
               self.print_error("Échec de la configuration de la taille maximale du cache")
               return 1
    
       # Configuration de l'âge maximal des packages dans le cache
       if args.cache_max_age:
           self.print_header(f"Configuration de l'âge maximal des packages: {args.cache_max_age} jours")

           if self.config_manager.set_setting("cache_max_age_days", args.cache_max_age):
               self.print_success(f"Âge maximal des packages défini à {args.cache_max_age} jours")
               modified = True
           else:
               self.print_error("Échec de la configuration de l'âge maximal des packages")
               return 1
    
       # Afficher la configuration actuelle
       if args.show or not modified:
           self.print_header("Configuration actuelle")

           # Afficher les informations de configuration
           default_python = self.config_manager.get_default_python()
           active_env = self.env_manager.get_active_environment()

           print(f"Commande Python par défaut: {default_python}")

           if active_env:
               print(f"Environnement actif: {active_env}")
           else:
               print("Aucun environnement actif")

           # Afficher l'état du mode hors ligne et du cache
           offline_mode = self.config_manager.get_offline_mode()
           use_cache = self.config_manager.get_cache_enabled()
           cache_max_size = self.config_manager.get_setting("cache_max_size_mb", 5000)
           cache_max_age = self.config_manager.get_setting("cache_max_age_days", 90)

           print(f"\nMode hors ligne: {get_color_for_terminal('green') if offline_mode else get_color_for_terminal('red')}{offline_mode}{get_color_for_terminal('reset')}")
           print(f"Utilisation du cache: {get_color_for_terminal('green') if use_cache else get_color_for_terminal('red')}{use_cache}{get_color_for_terminal('reset')}")
           print(f"Taille maximale du cache: {cache_max_size} Mo")
           print(f"Âge maximal des packages: {cache_max_age} jours")

           # Afficher les paramètres additionnels
           settings = self.config_manager.config.settings
           if settings:
               print("\nAutres paramètres:")
               for key, value in settings.items():
                   if key not in ["offline_mode", "use_package_cache", "cache_max_size_mb", "cache_max_age_days"]:
                       print(f"  {key}: {value}")
    
       return 0
    
    def cmd_check(self, args: argparse.Namespace) -> int:
        """
        Commande pour vérifier les mises à jour disponibles pour les packages.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        # Déterminer l'environnement cible
        env_name = args.name
        if not env_name:
            env_name = self.env_manager.get_active_environment()
            if not env_name:
                self.print_error("Aucun environnement actif. Spécifiez un nom d'environnement.")
                return 1
        
        self.print_header(f"Vérification des mises à jour pour '{env_name}'")
        
        # Vérifier les mises à jour
        success, updates, message = self.env_manager.check_for_updates(env_name)
        
        if not success:
            self.print_error(message)
            return 1
        
        if not updates:
            self.print_success("Tous les packages sont à jour.")
            return 0
        
        self.print_info(f"{len(updates)} package(s) peuvent être mis à jour:")
        
        for pkg in updates:
            try:
                name = pkg.get("name", "Inconnu")
                current = pkg.get("current_version", "?")
                latest = pkg.get("latest_version", "?")
                
                print(f"{name}: {COLORS['yellow']}{current}{COLORS['reset']} → {COLORS['green']}{latest}{COLORS['reset']}")
            except Exception as e:
                self.print_error(f"Erreur lors de l'affichage du package: {str(e)}")
        
        self.print_info("\nPour mettre à jour tous les packages:")
        print(f"  gestvenv update --all --env {env_name}")
        
        return 0
    
    def cmd_pyversions(self, args: argparse.Namespace) -> int:
        """
        Commande pour lister les versions Python disponibles sur le système.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        from gestvenv.services.system_service import SystemService
        system_service = SystemService()
        
        self.print_header("Versions Python disponibles")
        
        # Obtenir les versions Python disponibles
        versions = system_service.get_available_python_versions()
        
        if not versions:
            self.print_warning("Aucune version Python trouvée sur le système.")
            return 1
        
        default_python = self.config_manager.get_default_python()
        
        for v in versions:
            cmd = v["command"]
            version = v["version"]
            
            is_default = cmd == default_python
            if is_default:
                print(f"{COLORS['green']}✓{COLORS['reset']} {COLORS['bold']}{cmd}{COLORS['reset']} - Version {version} (défaut)")
            else:
                print(f"  {cmd} - Version {version}")
        
        self.print_info(f"\nTotal: {len(versions)} version(s) trouvée(s)")
        self.print_info("\nPour définir la version par défaut:")
        print("  gestvenv config --set-python <commande>")
        
        return 0
    
    def cmd_docs(self, args: argparse.Namespace) -> int:
        """
        Commande pour afficher la documentation.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        topic = args.topic.lower() if args.topic else "general"
        
        doc_topics = {
            "general": {
                "title": "Documentation générale",
                "content": """
GestVenv - Gestionnaire d'Environnements Virtuels Python

GestVenv est un outil qui simplifie la gestion des environnements virtuels Python. Il offre une
interface unifiée pour créer, activer et gérer vos environnements virtuels et leurs packages.

Principales fonctionnalités:
- Création et suppression d'environnements virtuels
- Activation et désactivation d'environnements
- Installation, mise à jour et suppression de packages
- Export et import de configurations d'environnements
- Clonage d'environnements existants

Pour plus d'informations sur des sujets spécifiques, utilisez:
  gestvenv docs <sujet>

Sujets disponibles: commandes, environnements, packages, export, workflow
            """
            },
            "commandes": {
                "title": "Documentation des commandes",
                "content": """
Principales commandes de GestVenv:

create      - Crée un nouvel environnement virtuel
activate    - Active un environnement virtuel
deactivate  - Désactive l'environnement actif
delete      - Supprime un environnement virtuel
list        - Liste tous les environnements virtuels
info        - Affiche des informations sur un environnement
install     - Installe des packages dans un environnement
uninstall   - Désinstalle des packages d'un environnement
update      - Met à jour des packages dans un environnement
export      - Exporte la configuration d'un environnement
import      - Importe une configuration d'environnement
clone       - Clone un environnement existant
run         - Exécute une commande dans un environnement
config      - Configure les paramètres par défaut
check       - Vérifie les mises à jour disponibles pour les packages
pyversions  - Liste les versions Python disponibles
docs        - Affiche la documentation

Pour plus d'informations sur une commande spécifique:
  gestvenv <commande> --help
            """
            },
            "environnements": {
                "title": "Gestion des environnements",
                "content": """
Gestion des environnements virtuels avec GestVenv:

Création d'un environnement:
  gestvenv create mon_env --python python3.9 --packages "flask,pytest"

Activation d'un environnement:
  gestvenv activate mon_env
  # Suivre les instructions affichées

Désactivation de l'environnement actif:
  gestvenv deactivate
  # Suivre les instructions affichées

Suppression d'un environnement:
  gestvenv delete mon_env

Listing des environnements:
  gestvenv list
  gestvenv list --verbose  # Informations détaillées

Informations sur un environnement:
  gestvenv info mon_env

Clonage d'un environnement:
  gestvenv clone source_env nouveau_env

Exécution de commandes dans un environnement:
  gestvenv run mon_env python script.py
            """
            },
            "packages": {
                "title": "Gestion des packages",
                "content": """
Gestion des packages avec GestVenv:

Installation de packages:
  gestvenv install "flask,pytest"  # Dans l'environnement actif
  gestvenv install "flask==2.0.1,pytest" --env mon_env  # Dans un environnement spécifique

Désinstallation de packages:
  gestvenv uninstall "flask,pytest"  # Dans l'environnement actif
  gestvenv uninstall "flask" --env mon_env  # Dans un environnement spécifique

Mise à jour de packages:
  gestvenv update "flask,pytest"  # Dans l'environnement actif
  gestvenv update --all  # Tous les packages de l'environnement actif
  gestvenv update --all --env mon_env  # Tous les packages d'un environnement spécifique

Vérification des mises à jour disponibles:
  gestvenv check  # Pour l'environnement actif
  gestvenv check mon_env  # Pour un environnement spécifique
            """
            },
            "export": {
                "title": "Export et import de configurations",
                "content": """
Export et import de configurations avec GestVenv:

Export d'une configuration:
  gestvenv export mon_env  # Export au format JSON par défaut
  gestvenv export mon_env --format requirements  # Export au format requirements.txt
  gestvenv export mon_env --output "/chemin/vers/fichier.json"  # Chemin personnalisé
  gestvenv export mon_env --add-metadata "description:Mon projet web,auteur:John Doe"  # Avec métadonnées

Import d'une configuration:
  gestvenv import /chemin/vers/fichier.json  # Import depuis un fichier JSON
  gestvenv import /chemin/vers/requirements.txt --name nouveau_env  # Import depuis requirements.txt
            """
            },
            "workflow": {
                "title": "Flux de travail recommandé",
                "content": """
Flux de travail recommandé avec GestVenv:

1. Création d'un environnement pour un nouveau projet:
   gestvenv create mon_projet --python python3.9 --packages "flask,pytest"

2. Activation de l'environnement:
   gestvenv activate mon_projet
   # Exécuter la commande affichée

3. Installation de packages supplémentaires:
   gestvenv install "pandas,matplotlib"

4. Travail sur le projet avec l'environnement activé

5. Export de la configuration pour partage:
   gestvenv export mon_projet --output "mon_projet_config.json"

6. Partage de la configuration avec l'équipe

7. Import de la configuration par un membre de l'équipe:
   gestvenv import mon_projet_config.json

8. Mise à jour régulière des packages:
   gestvenv check
   gestvenv update --all

9. Création d'un environnement de développement basé sur l'environnement de production:
   gestvenv clone mon_projet mon_projet_dev
            """
            }
        }
        
        if topic not in doc_topics:
            self.print_error(f"Sujet de documentation '{topic}' non trouvé.")
            self.print_info("Sujets disponibles: " + ", ".join(doc_topics.keys()))
            return 1
        
        doc = doc_topics[topic]
        self.print_header(doc["title"])
        print(doc["content"].strip())
        
        return 0
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Exécute la commande en ligne de commande.
        
        Args:
            args: Arguments de ligne de commande (optionnel)
            
        Returns:
            int: Code de retour
        """
        # Analyser les arguments
        parsed_args = self.parser.parse_args(args)
        
        # Configurer le logging en mode debug si demandé
        if parsed_args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Mode debug activé")
        
        # Cas spécial: pas de commande spécifiée
        if not hasattr(parsed_args, 'command') or not parsed_args.command:
            self.parser.print_help()
            return 1
        
        # Exécuter la commande appropriée
        commands = {
            "create": self.cmd_create,
            "activate": self.cmd_activate,
            "deactivate": self.cmd_deactivate,
            "delete": self.cmd_delete,
            "list": self.cmd_list,
            "info": self.cmd_info,
            "install": self.cmd_install,
            "uninstall": self.cmd_uninstall,
            "update": self.cmd_update,
            "export": self.cmd_export,
            "import": self.cmd_import,
            "clone": self.cmd_clone,
            "run": self.cmd_run,
            "config": self.cmd_config,
            "check": self.cmd_check,
            "pyversions": self.cmd_pyversions,
            "docs": self.cmd_docs
        }
        if hasattr(parsed_args, 'command') and parsed_args.command:
            command = parsed_args.command
            if isinstance(command, list):
                command = command[0] if command else None
                
            if command in commands:
        # if parsed_args.command in commands:
                try:
                    return commands[parsed_args.command](parsed_args)
                except KeyboardInterrupt:
                    print("\nOpération interrompue.")
                    return 130  # Code standard pour SIGINT
                except Exception as e:
                    if parsed_args.debug:
                        # En mode debug, afficher la trace complète
                        import traceback
                        traceback.print_exc()
                    else:
                        # En mode normal, afficher un message d'erreur plus convivial
                        self.print_error(f"Erreur: {str(e)}")
                        self.print_info("Pour plus de détails, exécutez la commande avec --debug")
            return 1
        else:
            self.print_error(f"Commande inconnue: {parsed_args.command}")
            self.parser.print_help()
            return 1

    def cmd_cache(self, args: argparse.Namespace) -> int:
        """
        Commande pour gérer le cache de packages.

        Args:
            args: Arguments de ligne de commande

        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        # Vérifier si une sous-commande a été spécifiée
        if not hasattr(args, 'cache_command') or not args.cache_command:
            self.print_error("Sous-commande de cache non spécifiée")
            return 1

        # Importer le service de cache
        from gestvenv.services.cache_service import CacheService
        cache_service = CacheService()

        # Exécuter la sous-commande appropriée
        if args.cache_command == 'list':
            return self.cmd_cache_list(args, cache_service)
        elif args.cache_command == 'clean':
            return self.cmd_cache_clean(args, cache_service)
        elif args.cache_command == 'info':
            return self.cmd_cache_info(args, cache_service)
        elif args.cache_command == 'add':
            return self.cmd_cache_add(args, cache_service)
        elif args.cache_command == 'export':
            return self.cmd_cache_export(args, cache_service)
        elif args.cache_command == 'import':
            return self.cmd_cache_import(args, cache_service)
        elif args.cache_command == 'remove':
            return self.cmd_cache_remove(args, cache_service)
        else:
            self.print_error(f"Sous-commande de cache non reconnue: {args.cache_command}")
            return 1

    def cmd_cache_list(self, args: argparse.Namespace, cache_service: Any) -> int:
       """
       Commande pour lister les packages dans le cache.
    
       Args:
           args: Arguments de ligne de commande
           cache_service: Service de gestion du cache

       Returns:
           int: Code de retour (0 pour succès, autre pour erreur)
       """
       self.print_header("Packages disponibles dans le cache")
    
       # Récupérer les packages disponibles
       available_packages = cache_service.get_available_packages()
    
       if not available_packages:
           self.print_info("Aucun package dans le cache.")
           return 0
    
       # Afficher les packages par ordre alphabétique
       for package_name in sorted(available_packages.keys()):
           versions = available_packages[package_name]
           versions_str = ", ".join(sorted(versions, key=lambda v: [int(x) for x in v.split('.')]))

           self.print_colored(f"{package_name}", "bold")
           print(f"  Versions: {versions_str}")
    
       # Afficher les statistiques
       stats = cache_service.get_cache_stats()
       self.print_info(f"\nTotal: {stats['package_count']} package(s), {stats['version_count']} version(s)")
       self.print_info(f"Taille totale: {self.format_size(stats['total_size_bytes'])}")
    
       return 0

    def cmd_cache_clean(self, args: argparse.Namespace, cache_service: Any) -> int:
       """
       Commande pour nettoyer le cache.
    
       Args:
           args: Arguments de ligne de commande
           cache_service: Service de gestion du cache

       Returns:
           int: Code de retour (0 pour succès, autre pour erreur)
       """
       self.print_header("Nettoyage du cache")
    
       # Demander confirmation
       confirm = input("Êtes-vous sûr de vouloir nettoyer le cache ? (o/N) ")
       if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
           self.print_info("Opération annulée.")
           return 0
    
       # Récupérer les paramètres
       max_age_days = args.max_age
       max_size_mb = args.max_size
    
       self.print_info(f"Nettoyage du cache (âge max: {max_age_days} jours, taille max: {max_size_mb} Mo)")
    
       # Nettoyer le cache
       removed_count, freed_space = cache_service.clean_cache(max_age_days, max_size_mb)
    
       if removed_count > 0:
           self.print_success(f"{removed_count} package(s) supprimé(s), {self.format_size(freed_space)} libéré(s)")
       else:
           self.print_info("Aucun package à supprimer.")
    
       return 0

    def cmd_cache_info(self, args: argparse.Namespace, cache_service: Any) -> int:
       """
       Commande pour afficher des informations sur le cache.
    
       Args:
           args: Arguments de ligne de commande
           cache_service: Service de gestion du cache

       Returns:
           int: Code de retour (0 pour succès, autre pour erreur)
       """
       self.print_header("Informations sur le cache")
    
       # Récupérer les statistiques du cache
       stats = cache_service.get_cache_stats()
    
       from datetime import datetime
       print(f"Répertoire du cache: {stats['cache_dir']}")
       print(f"Nombre de packages: {stats['package_count']}")
       print(f"Nombre de versions: {stats['version_count']}")
       print(f"Taille totale: {self.format_size(stats['total_size_bytes'])}")
    
       if stats['package_count'] > 0:
           print(f"Package le plus récent: {stats['latest_package']}")
           latest_date = datetime.fromisoformat(stats['latest_added_at'])
           print(f"Ajouté le: {format_timestamp(latest_date)}")
    
       # Récupérer l'état du mode hors ligne
       from gestvenv.core.config_manager import ConfigManager
       config = ConfigManager()
       offline_mode = config.get_setting("offline_mode", False)
       use_cache = config.get_setting("use_package_cache", True)
    
       print(f"\nMode hors ligne: {'Activé' if offline_mode else 'Désactivé'}")
       print(f"Utilisation du cache: {'Activée' if use_cache else 'Désactivée'}")
    
       return 0

    def cmd_cache_add(self, args: argparse.Namespace, cache_service: Any) -> int:
       """
       Commande pour ajouter des packages au cache.
    
       Args:
           args: Arguments de ligne de commande
           cache_service: Service de gestion du cache

       Returns:
           int: Code de retour (0 pour succès, autre pour erreur)
       """
       self.print_header("Ajout de packages au cache")
    
       # Récupérer la liste des packages
       packages = [pkg.strip() for pkg in args.packages.split(',') if pkg.strip()]
    
       if not packages:
           self.print_error("Aucun package spécifié")
           return 1
    
       self.print_info(f"Téléchargement et mise en cache de {len(packages)} package(s)")
    
       # Créer un répertoire temporaire pour le téléchargement
       import tempfile
       import subprocess
       import shutil
       from pathlib import Path
    
       with tempfile.TemporaryDirectory() as temp_dir:
           # Télécharger les packages
           cmd = ["pip", "download", "--dest", temp_dir] + packages

           self.print_info(f"Exécution de la commande: {' '.join(cmd)}")

           try:
               result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)

               if result.returncode != 0:
                   self.print_error(f"Échec du téléchargement des packages: {result.stderr}")
                   return 1

               # Mettre en cache les packages téléchargés
               added_count = 0

               for file_name in os.listdir(temp_dir):
                   file_path = Path(temp_dir) / file_name

                   if file_path.suffix.lower() in ['.whl', '.tar.gz', '.zip']:
                       # Obtenir les informations du package
                       show_cmd = ["pip", "show", file_path.stem.split('-')[0]]
                       show_result = subprocess.run(show_cmd, capture_output=True, text=True, shell=False, check=False)

                       if show_result.returncode == 0:
                           # Extraire les informations du package
                           pkg_info = {}
                           dependencies = []

                           for line in show_result.stdout.splitlines():
                               if ': ' in line:
                                   key, value = line.split(': ', 1)
                                   pkg_info[key.lower()] = value.strip()

                                   # Récupérer les dépendances
                                   if key.lower() == 'requires':
                                       dependencies = [dep.strip() for dep in value.split(',') if dep.strip()]

                           # Ajouter le package au cache
                           if 'name' in pkg_info and 'version' in pkg_info:
                               success = cache_service.add_package(
                                   file_path,
                                   pkg_info['name'],
                                   pkg_info['version'],
                                   dependencies
                               )

                               if success:
                                   self.print_success(f"Package mis en cache: {pkg_info['name']}-{pkg_info['version']}")
                                   added_count += 1
                               else:
                                   self.print_error(f"Échec de la mise en cache du package: {pkg_info['name']}-{pkg_info['version']}")

               if added_count > 0:
                   self.print_success(f"{added_count} package(s) ajouté(s) au cache avec succès")
               else:
                   self.print_warning("Aucun package n'a été ajouté au cache")

               return 0 if added_count > 0 else 1

           except Exception as e:
               self.print_error(f"Erreur lors de l'ajout des packages au cache: {str(e)}")
               return 1

    def cmd_cache_export(self, args: argparse.Namespace, cache_service: Any) -> int:
       """
       Commande pour exporter le contenu du cache.
    
       Args:
           args: Arguments de ligne de commande
           cache_service: Service de gestion du cache

       Returns:
           int: Code de retour (0 pour succès, autre pour erreur)
       """
       self.print_header("Export du cache")
    
       # Récupérer les packages disponibles
       available_packages = cache_service.get_available_packages()
    
       if not available_packages:
           self.print_error("Aucun package dans le cache à exporter.")
           return 1
    
       # Déterminer le chemin de sortie
       import json
       from datetime import datetime
    
       output_path = args.output
       if not output_path:
           # Générer un nom de fichier par défaut
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           output_path = f"gestvenv_cache_export_{timestamp}.json"
    
       # Préparer les données d'export
       export_data = {
           "metadata": {
               "version": "1.0",
               "exported_at": datetime.now().isoformat(),
               "packages_count": sum(len(versions) for versions in available_packages.values()),
               "cache_stats": cache_service.get_cache_stats()
           },
           "packages": {}
       }
    
       # Ajouter les packages au export
       for package_name, versions in available_packages.items():
           export_data["packages"][package_name] = {
               "versions": {}
           }

           for version in versions:
               # Récupérer les informations du package
               package_info = cache_service.index.get(package_name, {}).get("versions", {}).get(version, {})

               if package_info:
                   export_data["packages"][package_name]["versions"][version] = {
                       "added_at": package_info.get("added_at", ""),
                       "dependencies": package_info.get("dependencies", []),
                       "size": package_info.get("size", 0),
                       "hash": package_info.get("hash", "")
                   }
    
       # Écrire le fichier d'export
       try:
           with open(output_path, 'w', encoding='utf-8') as f:
               json.dump(export_data, f, indent=2, ensure_ascii=False)

           self.print_success(f"Export du cache réussi: {output_path}")

           # Afficher les statistiques
           stats = cache_service.get_cache_stats()
           self.print_info(f"{stats['package_count']} package(s), {stats['version_count']} version(s) exporté(s)")

           return 0
       except Exception as e:
           self.print_error(f"Erreur lors de l'export du cache: {str(e)}")
           return 1

    def cmd_cache_import(self, args: argparse.Namespace, cache_service: Any) -> int:
       """
       Commande pour importer des packages dans le cache.
    
       Args:
           args: Arguments de ligne de commande
           cache_service: Service de gestion du cache

       Returns:
           int: Code de retour (0 pour succès, autre pour erreur)
       """
       self.print_header("Import de packages dans le cache")
    
       # Vérifier si le fichier existe
       import json
       from pathlib import Path
    
       file_path = Path(args.file)
       if not file_path.exists():
           self.print_error(f"Le fichier d'export n'existe pas: {file_path}")
           return 1
    
       # Charger le fichier d'export
       try:
           with open(file_path, 'r', encoding='utf-8') as f:
               import_data = json.load(f)

           # Valider le format du fichier
           if "packages" not in import_data:
               self.print_error("Format de fichier d'export invalide: clé 'packages' manquante")
               return 1

           # Compteurs pour les statistiques
           total_packages = 0
           imported_packages = 0

           # Parcourir les packages à importer
           for package_name, package_data in import_data["packages"].items():
               if "versions" not in package_data:
                   continue
               
               for version, version_data in package_data["versions"].items():
                   total_packages += 1

                   # Vérifier si le package existe déjà dans le cache
                   if cache_service.has_package(package_name, version):
                       self.print_info(f"Package déjà en cache: {package_name}-{version}")
                       continue
                   
                   # Télécharger et ajouter le package au cache
                   self.print_info(f"Téléchargement et mise en cache de {package_name}=={version}")

                   # Créer un répertoire temporaire pour le téléchargement
                   import tempfile
                   import subprocess

                   with tempfile.TemporaryDirectory() as temp_dir:
                       # Télécharger le package
                       cmd = ["pip", "download", "--dest", temp_dir, f"{package_name}=={version}"]

                       try:
                           result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)

                           if result.returncode != 0:
                               self.print_error(f"Échec du téléchargement du package {package_name}=={version}: {result.stderr}")
                               continue
                           
                           # Trouver le fichier téléchargé
                           downloaded_files = list(Path(temp_dir).glob(f"{package_name.replace('-', '_')}*"))

                           if not downloaded_files:
                               self.print_error(f"Aucun fichier téléchargé pour {package_name}=={version}")
                               continue
                           
                           # Ajouter le package au cache
                           dependencies = version_data.get("dependencies", [])
                           success = cache_service.add_package(
                               downloaded_files[0],
                               package_name,
                               version,
                               dependencies
                           )

                           if success:
                               self.print_success(f"Package mis en cache: {package_name}-{version}")
                               imported_packages += 1
                           else:
                               self.print_error(f"Échec de la mise en cache du package: {package_name}-{version}")

                       except Exception as e:
                           self.print_error(f"Erreur lors de l'import du package {package_name}=={version}: {str(e)}")

           if imported_packages > 0:
               self.print_success(f"{imported_packages}/{total_packages} package(s) importé(s) avec succès")
           else:
               self.print_warning("Aucun package n'a été importé")

           return 0
       except Exception as e:
           self.print_error(f"Erreur lors de l'import du cache: {str(e)}")
           return 1

    def cmd_cache_remove(self, args: argparse.Namespace, cache_service: Any) -> int:
       """
       Commande pour supprimer des packages du cache.
    
       Args:
           args: Arguments de ligne de commande
           cache_service: Service de gestion du cache

       Returns:
           int: Code de retour (0 pour succès, autre pour erreur)
       """
       self.print_header("Suppression de packages du cache")
    
       # Récupérer la liste des packages
       packages = [pkg.strip() for pkg in args.packages.split(',') if pkg.strip()]
    
       if not packages:
           self.print_error("Aucun package spécifié")
           return 1
    
       # Demander confirmation
       packages_str = ", ".join(packages)
       confirm = input(f"Êtes-vous sûr de vouloir supprimer ces packages du cache ?\n{packages_str}\n(o/N) ")
    
       if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
           self.print_info("Opération annulée.")
           return 0
    
       # Supprimer les packages
       removed_count = 0
       for package_spec in packages:
           # Extraire le nom et la version du package
           if "==" in package_spec:
               package_name, version = package_spec.split("==", 1)
           else:
               package_name, version = package_spec, None

           package_name = package_name.strip()

           if version:
               # Supprimer une version spécifique
               if package_name in cache_service.index and version in cache_service.index[package_name]["versions"]:
                   # Récupérer le chemin du package
                   package_info = cache_service.index[package_name]["versions"][version]
                   package_path = cache_service.cache_dir / package_info["path"]

                   # Supprimer le fichier
                   if package_path.exists():
                       try:
                           package_path.unlink()

                           # Mettre à jour l'index
                           del cache_service.index[package_name]["versions"][version]

                           # Si c'était la dernière version, supprimer complètement le package
                           if not cache_service.index[package_name]["versions"]:
                               del cache_service.index[package_name]

                           cache_service._save_index()

                           self.print_success(f"Package supprimé du cache: {package_name}-{version}")
                           removed_count += 1
                       except Exception as e:
                           self.print_error(f"Erreur lors de la suppression du package {package_name}-{version}: {str(e)}")
                   else:
                       self.print_warning(f"Fichier manquant pour {package_name}-{version}")
               else:
                   self.print_warning(f"Package non trouvé dans le cache: {package_name}-{version}")
           else:
               # Supprimer toutes les versions du package
               if package_name in cache_service.index:
                   versions = list(cache_service.index[package_name]["versions"].keys())

                   for version in versions:
                       # Récupérer le chemin du package
                       package_info = cache_service.index[package_name]["versions"][version]
                       package_path = cache_service.cache_dir / package_info["path"]

                       # Supprimer le fichier
                       if package_path.exists():
                           try:
                               package_path.unlink()
                               removed_count += 1
                           except Exception as e:
                               self.print_error(f"Erreur lors de la suppression du package {package_name}-{version}: {str(e)}")

                   # Supprimer le package de l'index
                   del cache_service.index[package_name]
                   cache_service._save_index()

                   self.print_success(f"Toutes les versions de {package_name} supprimées du cache ({len(versions)} version(s))")
               else:
                   self.print_warning(f"Package non trouvé dans le cache: {package_name}")
    
       if removed_count > 0:
           self.print_success(f"{removed_count} package(s) supprimé(s) du cache avec succès")
       else:
           self.print_warning("Aucun package n'a été supprimé du cache")
    
       return 0

    # Fonction utilitaire pour formater la taille
    def format_size(self, size_bytes: int) -> str:
       """
       Formate une taille en octets en une chaîne lisible.
    
       Args:
           size_bytes: Taille en octets

       Returns:
           str: Taille formatée
       """
       from gestvenv.utils.format_utils import format_size
       return format_size(size_bytes)


def main() -> int:
    """
    Point d'entrée principal de GestVenv.
    
    Returns:
        int: Code de retour
    """
    cli = CLI()
    return cli.run()

if __name__ == "__main__":
    sys.exit(main())