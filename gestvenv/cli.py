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
    cache       - Gère le cache de packages
    doctor      - Diagnostique et répare les environnements
    system-info - Affiche les informations système détaillées
    logs        - Gère et affiche les logs de GestVenv
    docs        - Affiche la documentation
"""

import os
import sys
import argparse
import logging
import textwrap
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
__version__ = "1.1.1"

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
                  gestvenv doctor mon_projet             # Diagnostique un environnement
                  
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
        create_parser.add_argument('--offline', action='store_true', help='Utilise uniquement les packages du cache (mode hors ligne)')
        create_parser.add_argument('-r', '--requirements', dest='requirements_file', help='Installe les packages depuis un fichier requirements.txt')
        create_parser.add_argument('--description', help='Description de l\'environnement')
        
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
        list_parser.add_argument('--health', action='store_true', help='Affiche l\'état de santé des environnements')
        
        # Commande: info
        info_parser = subparsers.add_parser('info', help='Affiche des informations sur un environnement')
        info_parser.add_argument('name', help='Nom de l\'environnement')
        info_parser.add_argument('--json', action='store_true', help='Affiche les résultats au format JSON')
        info_parser.add_argument('--packages', action='store_true', help='Liste tous les packages installés')
        
        # Commande: install
        install_parser = subparsers.add_parser('install', help='Installe des packages dans l\'environnement actif ou spécifié')
        install_parser.add_argument('packages', nargs='?', help='Liste de packages à installer, séparés par des virgules')
        install_parser.add_argument('--env', help='Nom de l\'environnement (utilise l\'environnement actif par défaut)')
        install_parser.add_argument('--offline', action='store_true', help='Utilise uniquement les packages du cache (mode hors ligne)')
        install_parser.add_argument('-r', '--requirements', help='Installe depuis un fichier requirements.txt')
        install_parser.add_argument('-e', '--editable', action='store_true', help='Installe en mode éditable (développement)')
        install_parser.add_argument('--dev', action='store_true', help='Installe les dépendances de développement')
        install_parser.add_argument('--upgrade', action='store_true', help='Met à jour les packages existants')
        
        # Commande: uninstall
        uninstall_parser = subparsers.add_parser('uninstall', help='Désinstalle des packages de l\'environnement actif ou spécifié')
        uninstall_parser.add_argument('packages', help='Liste de packages à désinstaller, séparés par des virgules')
        uninstall_parser.add_argument('--env', help='Nom de l\'environnement (utilise l\'environnement actif par défaut)')
        uninstall_parser.add_argument('--yes', '-y', action='store_true', help='Confirme automatiquement la désinstallation')
        uninstall_parser.add_argument('--with-dependencies', action='store_true', help='Désinstalle également les dépendances')
        
        # Commande: update
        update_parser = subparsers.add_parser('update', help='Met à jour des packages dans l\'environnement actif ou spécifié')
        update_parser.add_argument('packages', nargs='?', help='Liste de packages à mettre à jour, séparés par des virgules')
        update_parser.add_argument('--env', help='Nom de l\'environnement (utilise l\'environnement actif par défaut)')
        update_parser.add_argument('--all', action='store_true', help='Met à jour tous les packages')
        update_parser.add_argument('--offline', action='store_true', help='Utilise uniquement les packages du cache')
        
        # Commande: export
        export_parser = subparsers.add_parser('export', help='Exporte la configuration d\'un environnement')
        export_parser.add_argument('name', help='Nom de l\'environnement à exporter')
        export_parser.add_argument('--output', help='Chemin du fichier de sortie')
        export_parser.add_argument('--format', choices=['json', 'requirements'], default='json',
                                help='Format d\'export (json ou requirements.txt)')
        export_parser.add_argument('--add-metadata', dest='metadata',
                                help='Métadonnées supplémentaires au format "clé1:valeur1,clé2:valeur2"')
        export_parser.add_argument('--include-metadata', action='store_true',
                                help='Inclut toutes les métadonnées de l\'environnement')
        export_parser.add_argument('--production', action='store_true',
                                help='Optimise l\'export pour la production')
        
        # Commande: import
        import_parser = subparsers.add_parser('import', help='Importe une configuration d\'environnement')
        import_parser.add_argument('file', help='Chemin vers le fichier de configuration ou requirements.txt')
        import_parser.add_argument('--name', help='Nom à utiliser pour le nouvel environnement')
        import_parser.add_argument('--merge', action='store_true', help='Fusionne avec un environnement existant')
        import_parser.add_argument('--resolve-conflicts', action='store_true', help='Résout automatiquement les conflits')
        
        # Commande: clone
        clone_parser = subparsers.add_parser('clone', help='Clone un environnement existant')
        clone_parser.add_argument('source', help='Nom de l\'environnement source')
        clone_parser.add_argument('target', help='Nom du nouvel environnement')
        clone_parser.add_argument('--skip-packages', action='store_true', help='Ne copie pas les packages')
        clone_parser.add_argument('--description', help='Description du nouvel environnement')
        
        # Commande: run
        run_parser = subparsers.add_parser('run', help='Exécute une commande dans un environnement virtuel')
        run_parser.add_argument('name', help='Nom de l\'environnement')
        run_parser.add_argument('command', nargs='+', help='Commande à exécuter')
        run_parser.add_argument('--env', dest='env_vars', help='Variables d\'environnement au format "KEY1=value1,KEY2=value2"')
        run_parser.add_argument('--timeout', type=int, help='Timeout en secondes')
        run_parser.add_argument('--background', action='store_true', help='Exécute en arrière-plan')
        
        # Commande: config
        config_parser = subparsers.add_parser('config', help='Configure les paramètres par défaut')
        config_parser.add_argument('--set-python', dest='default_python',
                                help='Définit la commande Python par défaut')
        config_parser.add_argument('--show', action='store_true', help='Affiche la configuration actuelle')
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
        config_parser.add_argument('--backup', action='store_true', help='Crée une sauvegarde de la configuration')
        config_parser.add_argument('--restore', help='Restaure une sauvegarde de configuration')
        config_parser.add_argument('--reset', action='store_true', help='Réinitialise la configuration')
        config_parser.add_argument('--validate', action='store_true', help='Valide l\'intégrité de la configuration')
        
        # Commande: check
        check_parser = subparsers.add_parser('check', help='Vérifie les mises à jour disponibles pour les packages')
        check_parser.add_argument('name', nargs='?', help='Nom de l\'environnement (utilise l\'environnement actif par défaut)')
        check_parser.add_argument('--apply', action='store_true', help='Applique automatiquement les mises à jour')
        
        # Commande: pyversions
        subparsers.add_parser('pyversions', help='Liste les versions Python disponibles sur le système')
        
        # Commande: cache
        cache_parser = subparsers.add_parser('cache', help='Gère le cache de packages')
        cache_subparsers = cache_parser.add_subparsers(dest='cache_command', title='commandes', help='Commande de cache à exécuter')

        # Commande: cache list
        cache_list_parser = cache_subparsers.add_parser('list', help='Liste les packages disponibles dans le cache')
        cache_list_parser.add_argument('--detailed', action='store_true', help='Affiche des informations détaillées')

        # Commande: cache clean
        cache_clean_parser = cache_subparsers.add_parser('clean', help='Nettoie le cache en supprimant les packages obsolètes')
        cache_clean_parser.add_argument('--max-age', type=int, default=90, help='Âge maximum en jours pour les packages rarement utilisés')
        cache_clean_parser.add_argument('--max-size', type=int, default=5000, help='Taille maximale du cache en Mo')
        cache_clean_parser.add_argument('--force', action='store_true', help='Force le nettoyage sans confirmation')

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
        
        # Commande: cache verify
        cache_verify_parser = cache_subparsers.add_parser('verify', help='Vérifie l\'intégrité du cache')
        cache_verify_parser.add_argument('--fix', action='store_true', help='Corrige automatiquement les problèmes')
        
        # Commande: doctor
        doctor_parser = subparsers.add_parser('doctor', help='Diagnostique et répare les environnements')
        doctor_parser.add_argument('name', nargs='?', help='Nom de l\'environnement à diagnostiquer (tous si omis)')
        doctor_parser.add_argument('--fix', action='store_true', help='Applique automatiquement les réparations')
        doctor_parser.add_argument('--full', action='store_true', help='Effectue un diagnostic complet')
        doctor_parser.add_argument('--check-cache', action='store_true', help='Vérifie également le cache')
        
        # Commande: system-info
        system_info_parser = subparsers.add_parser('system-info', help='Affiche les informations système détaillées')
        system_info_parser.add_argument('--json', action='store_true', help='Affiche les résultats au format JSON')
        system_info_parser.add_argument('--export', help='Exporte les informations dans un fichier')
        
        # Commande: logs
        logs_parser = subparsers.add_parser('logs', help='Gère et affiche les logs de GestVenv')
        logs_subparsers = logs_parser.add_subparsers(dest='logs_command', title='commandes', help='Commande de logs à exécuter')
        
        # Commande: logs show
        logs_show_parser = logs_subparsers.add_parser('show', help='Affiche les logs')
        logs_show_parser.add_argument('--lines', '-n', type=int, default=50, help='Nombre de lignes à afficher')
        logs_show_parser.add_argument('--level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Niveau de log minimum')
        logs_show_parser.add_argument('--env', help='Filtre par environnement')
        logs_show_parser.add_argument('--follow', '-f', action='store_true', help='Suit les logs en temps réel')
        
        # Commande: logs clean
        logs_clean_parser = logs_subparsers.add_parser('clean', help='Nettoie les anciens logs')
        logs_clean_parser.add_argument('--days', type=int, default=30, help='Âge maximum des logs à conserver')
        logs_clean_parser.add_argument('--force', action='store_true', help='Force le nettoyage sans confirmation')
        
        # Commande: logs export
        logs_export_parser = logs_subparsers.add_parser('export', help='Exporte les logs')
        logs_export_parser.add_argument('output', help='Fichier de sortie')
        logs_export_parser.add_argument('--format', choices=['json', 'txt'], default='txt', help='Format d\'export')
        logs_export_parser.add_argument('--days', type=int, default=7, help='Nombre de jours à exporter')
        
        # Commande: docs
        docs_parser = subparsers.add_parser('docs', help='Affiche la documentation')
        docs_parser.add_argument('topic', nargs='?', help='Sujet spécifique de la documentation')
   
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
            
        if args.requirements_file:
            self.print_info(f"Fichier requirements: {args.requirements_file}")
        
        if args.path:
            self.print_info(f"Chemin personnalisé: {args.path}")
            
        if args.description:
            self.print_info(f"Description: {args.description}")
        
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
        
        # Préparer les métadonnées
        metadata = {}
        if args.description:
            metadata['description'] = args.description
        
        # Créer l'environnement
        success, message = self.env_manager.create_environment(
            args.name,
            python_version=args.python_version,
            packages=args.packages,
            path=args.path,
            offline=offline_mode,
            requirements_file=args.requirements_file,
            metadata=metadata
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
            health = env.get("health", {})
            
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
                
                if args.health and exists:
                    health_items = []
                    if health.get("python_available"):
                        health_items.append(f"{COLORS['green']}✓ Python{COLORS['reset']}")
                    else:
                        health_items.append(f"{COLORS['red']}✗ Python{COLORS['reset']}")
                        
                    if health.get("pip_available"):
                        health_items.append(f"{COLORS['green']}✓ pip{COLORS['reset']}")
                    else:
                        health_items.append(f"{COLORS['red']}✗ pip{COLORS['reset']}")
                        
                    print(f"  Santé: {', '.join(health_items)}")
                    
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
        
        # Description si présente
        if 'description' in env_info:
            print(f"Description: {env_info['description']}")
        
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
        if args.packages or not args.json:
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
        
        # Vérifier qu'au moins une source de packages est spécifiée
        if not args.packages and not args.requirements:
            self.print_error("Aucun package spécifié. Utilisez 'gestvenv install <packages>' ou '-r <requirements.txt>'")
            return 1
        
        self.print_header(f"Installation de packages dans '{env_name}'")
        
        if args.packages:
            self.print_info(f"Packages à installer: {args.packages}")
        if args.requirements:
            self.print_info(f"Fichier requirements: {args.requirements}")
        if args.editable:
            self.print_info("Installation en mode éditable")
        if args.dev:
            self.print_info("Installation des dépendances de développement")
        
        # Installer les packages
        success, message = self.env_manager.install_packages(
            env_name,
            packages=args.packages,
            requirements_file=args.requirements,
            editable=args.editable,
            dev=args.dev,
            offline=args.offline
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
        
        # Demander confirmation si pas de --yes
        if not args.yes:
            confirm = input(f"Êtes-vous sûr de vouloir désinstaller les packages suivants de '{env_name}' ?\n"
                           f"{args.packages}\n"
                           f"(o/N) ")
            
            if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
                self.print_info("Opération annulée.")
                return 0
        
        self.print_header(f"Désinstallation de packages de '{env_name}'")
        
        # Désinstaller les packages
        success, message = self.env_manager.uninstall_packages(
            env_name,
            args.packages,
            with_dependencies=args.with_dependencies,
            force=args.yes
        )
        
        if success:
            self.print_success(message)
            return 0
        else:
            self.print_error(message)
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
            all_packages=args.all,
            offline=args.offline
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
            metadata=args.metadata,
            include_metadata=args.include_metadata,
            production_ready=args.production
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
        if args.merge:
            self.print_info("Mode fusion activé")
        if args.resolve_conflicts:
            self.print_info("Résolution automatique des conflits activée")
        
        # Importer l'environnement
        success, message = self.env_manager.import_environment(
            args.file, 
            args.name,
            merge=args.merge,
            resolve_conflicts=args.resolve_conflicts
        )
        
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
        
        if args.skip_packages:
            self.print_info("Les packages ne seront pas copiés")
        
        # Cloner l'environnement
        success, message = self.env_manager.clone_environment(
            args.source, 
            args.target,
            include_packages=not args.skip_packages,
            description=args.description
        )
        
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
        
        # Parser les variables d'environnement si fournies
        env_vars = None
        if args.env_vars:
            try:
                env_vars = {}
                for pair in args.env_vars.split(','):
                    if '=' not in pair:
                        self.print_error(f"Format invalide pour la variable d'environnement: {pair}")
                        return 1
                    key, value = pair.split('=', 1)
                    env_vars[key.strip()] = value.strip()
            except Exception as e:
                self.print_error(f"Erreur lors du parsing des variables d'environnement: {str(e)}")
                return 1
        
        if args.background:
            self.print_info("Exécution en arrière-plan")
        
        # Exécuter la commande dans l'environnement
        ret_code, stdout, stderr = self.env_manager.run_command_in_environment(
            args.name, 
            command,
            env_vars=env_vars,
            timeout=args.timeout,
            background=args.background
        )
        
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
        
        # Gestion de la sauvegarde
        if args.backup:
            self.print_header("Création d'une sauvegarde de la configuration")
            success, path = self.config_manager.create_backup()
            if success:
                self.print_success(f"Sauvegarde créée: {path}")
            else:
                self.print_error(path)  # Le message d'erreur est dans 'path'
                return 1
            return 0
        
        # Gestion de la restauration
        if args.restore:
            self.print_header("Restauration de la configuration")
            success, message = self.config_manager.restore_from_backup(args.restore)
            if success:
                self.print_success(message)
            else:
                self.print_error(message)
            return 0 if success else 1
        
        # Gestion de la réinitialisation
        if args.reset:
            self.print_header("Réinitialisation de la configuration")
            confirm = input("Êtes-vous sûr de vouloir réinitialiser la configuration ? (o/N) ")
            if confirm.lower() in ['o', 'oui', 'y', 'yes']:
                success, message = self.config_manager.reset_config()
                if success:
                    self.print_success(message)
                else:
                    self.print_error(message)
                return 0 if success else 1
            else:
                self.print_info("Opération annulée.")
                return 0
        
        # Gestion de la validation
        if args.validate:
            self.print_header("Validation de la configuration")
            is_valid, issues = self.config_manager.validate_integrity()
            if is_valid:
                self.print_success("Configuration valide")
            else:
                self.print_error("Configuration invalide")
                for issue in issues:
                    self.print_error(f"  - {issue}")
            return 0 if is_valid else 1
        
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
            
            # Afficher le résumé de la configuration
            summary = self.config_manager.get_config_summary()
            
            print(f"Fichier de configuration: {summary['config_path']}")
            print(f"Version: {summary['version']}")
            print(f"Créé le: {summary['created_at']}")
            print(f"Dernière modification: {summary['last_modified']}")
            print(f"\nCommande Python par défaut: {summary['default_python']}")
            
            if summary['active_environment']:
                print(f"Environnement actif: {summary['active_environment']}")
            else:
                print("Aucun environnement actif")
            
            print(f"\nMode hors ligne: {get_color_for_terminal('green') if summary['offline_mode'] else get_color_for_terminal('red')}{summary['offline_mode']}{get_color_for_terminal('reset')}")
            print(f"Utilisation du cache: {get_color_for_terminal('green') if summary['cache_enabled'] else get_color_for_terminal('red')}{summary['cache_enabled']}{get_color_for_terminal('reset')}")
            
            # Afficher les paramètres du cache
            cache_max_size = self.config_manager.get_setting("cache_max_size_mb", 5000)
            cache_max_age = self.config_manager.get_setting("cache_max_age_days", 90)
            print(f"Taille maximale du cache: {cache_max_size} Mo")
            print(f"Âge maximal des packages: {cache_max_age} jours")
            
            print(f"\nNombre d'environnements: {summary['total_environments']}")
            print(f"Nombre de sauvegardes: {summary['backup_count']}")
            
            # Afficher les paramètres additionnels
            settings = self.config_manager.config.settings
            if settings:
                print("\nAutres paramètres:")
                for key, value in settings.items():
                    if key not in ["offline_mode", "use_package_cache", "cache_max_size_mb", 
                                   "cache_max_age_days", "version", "created_at", "last_modified"]:
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
        
        # Si --apply est spécifié, appliquer les mises à jour
        if args.apply:
            self.print_info("\nApplication des mises à jour...")
            packages_to_update = [pkg.get("name") for pkg in updates if pkg.get("name")]
            success, message = self.env_manager.update_packages(
                env_name,
                packages=",".join(packages_to_update),
                all_packages=False
            )
            
            if success:
                self.print_success(message)
            else:
                self.print_error(message)
                return 1
        else:
            self.print_info("\nPour mettre à jour tous les packages:")
            print(f"  gestvenv update --all --env {env_name}")
            
            self.print_info("\nPour appliquer automatiquement les mises à jour:")
            print(f"  gestvenv check {env_name} --apply")
        
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
        elif args.cache_command == 'verify':
            return self.cmd_cache_verify(args, cache_service)
        else:
            self.print_error(f"Sous-commande de cache non reconnue: {args.cache_command}")
            return 1
    
    def cmd_cache_list(self, args: argparse.Namespace, cache_service: Any) -> int:
        """
        Commande pour lister les packages dans le cache
        """
        try:
            self.print_header("Packages disponibles dans le cache")
            
            # Récupérer les packages disponibles
            available_packages = cache_service.get_available_packages()
            
            if not available_packages:
                self.print_info("Aucun package dans le cache.")
                self.print_info("\nUtilisez 'gestvenv cache add <package>' pour ajouter des packages.")
                return 0
            
            # Afficher les packages par ordre alphabétique
            for package_name in sorted(available_packages.keys()):
                versions = available_packages[package_name]
                
                # Trier les versions (version la plus récente en premier)
                try:
                    sorted_versions = sorted(
                        versions, 
                        key=lambda v: [int(x) if x.isdigit() else x for x in v.split('.')],
                        reverse=True
                    )
                except (ValueError, AttributeError):
                    sorted_versions = sorted(versions)
                
                self.print_colored(f"{package_name}", "bold")
                
                if args.detailed:
                    # Affichage détaillé
                    for version in sorted_versions:
                        # Récupérer les infos détaillées depuis l'index
                        if (package_name in cache_service.index and 
                            version in cache_service.index[package_name]["versions"]):
                            info = cache_service.index[package_name]["versions"][version]
                            size_mb = info.get("size", 0) / (1024 * 1024)
                            added_at = info.get("added_at", "Unknown")
                            usage_count = info.get("usage_count", 0)
                            
                            print(f"  - {version} ({size_mb:.1f} MB)")
                            print(f"    Ajouté le: {added_at}")
                            print(f"    Utilisations: {usage_count}")
                else:
                    # Affichage simple
                    versions_str = ", ".join(sorted_versions)
                    print(f"  Versions: {versions_str}")
            
            # Afficher les statistiques
            stats = cache_service.get_cache_stats()
            package_count = len(available_packages)
            version_count = sum(len(versions) for versions in available_packages.values())
            total_size = stats.get('total_size_bytes', 0)
            
            self.print_info(f"\nTotal: {package_count} package(s), {version_count} version(s)")
            if total_size > 0:
                size_formatted = self.format_size(total_size)
                self.print_info(f"Taille totale: {size_formatted}")
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la liste des packages du cache: {str(e)}")
            return 1
    
    def cmd_cache_clean(self, args: argparse.Namespace, cache_service: Any) -> int:
        """
        Commande pour nettoyer le cache
        """
        try:
            self.print_header("Nettoyage du cache")
            
            # Récupérer les paramètres de nettoyage
            max_age = getattr(args, 'max_age', 90)
            max_size = getattr(args, 'max_size', 5000)
            
            # Demander confirmation si pas en mode force
            force_clean = getattr(args, 'force', False)
            if not force_clean:
                # Afficher les statistiques actuelles
                stats = cache_service.get_cache_stats()
                current_size_mb = stats.get('total_size_bytes', 0) / (1024 * 1024)
                
                print(f"Taille actuelle du cache: {current_size_mb:.1f} MB")
                print(f"Paramètres de nettoyage:")
                print(f"  • Âge maximum: {max_age} jours")
                print(f"  • Taille maximale: {max_size} MB")
                
                confirm = input("\nÊtes-vous sûr de vouloir nettoyer le cache ? (o/N) ")
                if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
                    self.print_info("Opération annulée.")
                    return 0
            
            self.print_info(f"Nettoyage du cache (âge max: {max_age} jours, taille max: {max_size} MB)")
            
            # Nettoyer le cache
            try:
                removed_count, freed_space = cache_service.clean_cache(max_age, max_size)
                
                if removed_count > 0:
                    freed_mb = freed_space / (1024 * 1024)
                    self.print_success(f"{removed_count} package(s) supprimé(s)")
                    self.print_success(f"{freed_mb:.1f} MB libéré(s)")
                else:
                    self.print_info("Aucun package à supprimer. Le cache est déjà optimisé.")
                
                return 0
                
            except Exception as e:
                self.print_error(f"Erreur lors du nettoyage du cache: {str(e)}")
                return 1
                
        except Exception as e:
            self.print_error(f"Erreur dans la commande de nettoyage: {str(e)}")
            return 1
    
    def cmd_cache_info(self, args: argparse.Namespace, cache_service: Any) -> int:
        """
        Commande pour afficher des informations sur le cache
        """
        try:
            self.print_header("Informations sur le cache")
            
            # Récupérer les statistiques du cache
            stats = cache_service.get_cache_stats()
            
            # Afficher les informations de base
            print(f"Répertoire du cache: {stats.get('cache_dir', 'Inconnu')}")
            print(f"Nombre de packages: {stats.get('package_count', 0)}")
            print(f"Nombre de versions: {stats.get('version_count', 0)}")
            
            # Formater la taille totale
            total_size = stats.get('total_size_bytes', 0)
            if total_size > 0:
                size_formatted = self.format_size(total_size)
                print(f"Taille totale: {size_formatted}")
            else:
                print("Taille totale: 0 B")
            
            # Afficher le package le plus récent si disponible
            latest_package = stats.get('latest_package')
            if latest_package:
                latest_date = stats.get('latest_added_at', '')
                if latest_date:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(latest_date)
                        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"Package le plus récent: {latest_package}")
                        print(f"Ajouté le: {formatted_date}")
                    except Exception:
                        print(f"Package le plus récent: {latest_package}")
            
            # Récupérer l'état du mode hors ligne
            try:
                from gestvenv.core.config_manager import ConfigManager
                config = ConfigManager()
                offline_mode = config.get_setting("offline_mode", False)
                use_cache = config.get_setting("use_package_cache", True)
                
                print(f"\nMode hors ligne: {'Activé' if offline_mode else 'Désactivé'}")
                print(f"Utilisation du cache: {'Activée' if use_cache else 'Désactivée'}")
            except Exception as e:
                self.print_warning(f"Impossible de récupérer la configuration: {e}")
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la récupération des informations du cache: {str(e)}")
            return 1
    
    def cmd_cache_add(self, args: argparse.Namespace, cache_service: Any) -> int:
        """
        Commande pour ajouter des packages au cache
        
        Args:
            args: Arguments de ligne de commande
            cache_service: Service de cache
            
        Returns:
            int: Code de retour (0 = succès, 1 = erreur)
        """
        try:
            self.print_header("Ajout de packages au cache")
            
            # Récupérer la liste des packages depuis les arguments
            packages_str = getattr(args, 'packages', '')
            
            if not packages_str:
                self.print_error("Aucun package spécifié")
                return 1
            
            # Parser et valider les packages
            packages = [pkg.strip() for pkg in packages_str.split(',') if pkg.strip()]
            
            if not packages:
                self.print_error("Aucun package valide spécifié")
                return 1
            
            self.print_info(f"Téléchargement et mise en cache de {len(packages)} package(s)")
            
            # Utiliser le service de cache
            try:
                added_count, errors = cache_service.download_and_cache_packages(packages)
                
                # Afficher les résultats
                if added_count > 0:
                    self.print_success(f"{added_count} package(s) ajouté(s) au cache avec succès")
                    
                    # Afficher les erreurs s'il y en a, mais ne pas faire échouer complètement
                    if errors:
                        self.print_warning(f"{len(errors)} erreur(s) rencontrée(s):")
                        for error in errors[:5]:  # Limiter à 5 erreurs affichées
                            self.print_warning(f"  • {error}")
                        if len(errors) > 5:
                            self.print_warning(f"  • ... et {len(errors) - 5} autres erreurs")
                    
                    return 0  # Succès partiel acceptable
                else:
                    self.print_error("Aucun package n'a pu être ajouté au cache")
                    
                    # Afficher les erreurs pour diagnostic
                    if errors:
                        self.print_error("Erreurs rencontrées:")
                        for error in errors[:10]:  # Limiter à 10 erreurs
                            self.print_error(f"  • {error}")
                        if len(errors) > 10:
                            self.print_error(f"  • ... et {len(errors) - 10} autres erreurs")
                    
                    return 1
                    
            except Exception as e:
                self.print_error(f"Erreur lors de l'ajout des packages au cache: {str(e)}")
                return 1
                
        except Exception as e:
            self.print_error(f"Erreur générale dans la commande cache add: {str(e)}")
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
            errors = []
            
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
                    self.print_info(f"Téléchargement de {package_name}=={version}")
                    
                    try:
                        result = cache_service.download_and_cache_packages([f"{package_name}=={version}"])
                        if result[0] > 0:
                            imported_packages += 1
                        else:
                            errors.extend(result[1])
                    except Exception as e:
                        errors.append(f"Erreur pour {package_name}=={version}: {str(e)}")
            
            # Afficher le résumé
            if imported_packages > 0:
                self.print_success(f"{imported_packages}/{total_packages} package(s) importé(s) avec succès")
            else:
                self.print_warning("Aucun package n'a été importé")
            
            if errors:
                self.print_warning(f"{len(errors)} erreur(s) rencontrée(s)")
                for error in errors[:5]:
                    self.print_warning(f"  • {error}")
            
            return 0
        except json.JSONDecodeError as e:
            self.print_error(f"Erreur lors de la lecture du fichier JSON: {str(e)}")
            return 1
        except Exception as e:
            self.print_error(f"Erreur lors de l'import du cache: {str(e)}")
            return 1
    
    def cmd_cache_remove(self, args: argparse.Namespace, cache_service: Any) -> int:
        """
        Commande pour supprimer des packages spécifiques du cache
        """
        try:
            self.print_header("Suppression de packages du cache")
            
            # Récupérer la liste des packages
            packages_str = getattr(args, 'packages', '')
            if not packages_str:
                self.print_error("Aucun package spécifié")
                return 1
            
            packages = [pkg.strip() for pkg in packages_str.split(',') if pkg.strip()]
            
            if not packages:
                self.print_error("Aucun package valide spécifié")
                return 1
            
            # Demander confirmation
            packages_display = ", ".join(packages)
            confirm = input(f"Êtes-vous sûr de vouloir supprimer ces packages du cache ?\n{packages_display}\n(o/N) ")
            
            if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
                self.print_info("Opération annulée.")
                return 0
            
            # Supprimer les packages
            removed_count = 0
            errors = []
            
            for package_spec in packages:
                try:
                    # Parser le nom et la version du package
                    if "==" in package_spec:
                        package_name, version = package_spec.split("==", 1)
                    else:
                        package_name, version = package_spec, None
                    
                    package_name = package_name.strip()
                    
                    if version:
                        # Supprimer une version spécifique
                        success, message = cache_service.remove_package(package_name, version)
                        if success:
                            self.print_success(message)
                            removed_count += 1
                        else:
                            self.print_warning(message)
                            errors.append(message)
                    else:
                        # Supprimer toutes les versions du package
                        success, message = cache_service.remove_package(package_name)
                        if success:
                            self.print_success(message)
                            removed_count += 1
                        else:
                            self.print_warning(message)
                            errors.append(message)
                            
                except Exception as e:
                    error_msg = f"Erreur lors de la suppression de {package_spec}: {str(e)}"
                    self.print_error(error_msg)
                    errors.append(error_msg)
            
            # Résumé des résultats
            if removed_count > 0:
                self.print_success(f"{removed_count} package(s) supprimé(s) du cache avec succès")
            else:
                self.print_warning("Aucun package n'a été supprimé du cache")
            
            if errors:
                self.print_warning(f"{len(errors)} erreur(s) rencontrée(s)")
            
            return 0 if removed_count > 0 else 1
            
        except Exception as e:
            self.print_error(f"Erreur lors de la suppression des packages: {str(e)}")
            return 1
    
    def cmd_cache_verify(self, args: argparse.Namespace, cache_service: Any) -> int:
        """
        Commande pour vérifier l'intégrité du cache
        """
        try:
            self.print_header("Vérification de l'intégrité du cache")
            
            # Vérifier si le service de diagnostic est disponible
            try:
                from gestvenv.services.diagnostic_services import DiagnosticService
                diagnostic_service = DiagnosticService()
                
                # Vérifier l'intégrité du cache
                report = diagnostic_service.verify_cache_integrity()
                
                # Afficher le statut
                status = report.get("status", "unknown")
                if status == "healthy":
                    self.print_success("Cache en bonne santé")
                elif status == "corrupted":
                    self.print_error("Cache corrompu")
                elif status == "incomplete":
                    self.print_warning("Cache incomplet")
                
                # Afficher les statistiques
                print(f"\nPackages vérifiés: {report.get('verified_packages', 0)}/{report.get('total_packages', 0)}")
                
                # Afficher les problèmes
                corrupted = report.get("corrupted_packages", [])
                missing = report.get("missing_files", [])
                orphaned = report.get("orphaned_metadata", [])
                
                if corrupted:
                    self.print_error(f"\nPackages corrompus: {len(corrupted)}")
                    for pkg in corrupted[:5]:
                        print(f"  - {pkg['package']}")
                    if len(corrupted) > 5:
                        print(f"  ... et {len(corrupted) - 5} autres")
                
                if missing:
                    self.print_warning(f"\nFichiers manquants: {len(missing)}")
                    for file in missing[:5]:
                        print(f"  - {file['package']}")
                    if len(missing) > 5:
                        print(f"  ... et {len(missing) - 5} autres")
                
                if orphaned:
                    self.print_info(f"\nMétadonnées orphelines: {len(orphaned)}")
                
                # Appliquer les réparations si demandé
                if args.fix and (corrupted or missing or orphaned):
                    self.print_info("\nApplication des réparations...")
                    
                    # Supprimer les packages corrompus et les métadonnées orphelines
                    fixed_count = 0
                    for pkg in corrupted:
                        try:
                            package_name = pkg['package'].split('-')[0]
                            success, _ = cache_service.remove_package(package_name)
                            if success:
                                fixed_count += 1
                        except Exception:
                            pass
                    
                    if fixed_count > 0:
                        self.print_success(f"{fixed_count} package(s) corrompu(s) supprimé(s)")
                    
                    # Nettoyer l'index
                    cache_service._save_index()
                    self.print_success("Index du cache nettoyé")
                
                # Recommandations
                if report.get("recommendations"):
                    print("\nRecommandations:")
                    for rec in report["recommendations"]:
                        print(f"  • {rec}")
                
                return 0 if status == "healthy" else 1
                
            except ImportError:
                # Si le service de diagnostic n'est pas disponible, faire une vérification basique
                self.print_warning("Service de diagnostic non disponible, vérification basique...")
                
                stats = cache_service.get_cache_stats()
                self.print_info(f"Packages dans le cache: {stats.get('package_count', 0)}")
                self.print_info(f"Versions totales: {stats.get('version_count', 0)}")
                
                return 0
                
        except Exception as e:
            self.print_error(f"Erreur lors de la vérification du cache: {str(e)}")
            return 1
    
    def cmd_doctor(self, args: argparse.Namespace) -> int:
        """
        Commande pour diagnostiquer et réparer les environnements.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        try:
            # Vérifier si le service de diagnostic est disponible
            try:
                from gestvenv.services.diagnostic_services import DiagnosticService
                diagnostic_service = DiagnosticService()
            except ImportError:
                # Utiliser les fonctionnalités de diagnostic de base
                self.print_warning("Service de diagnostic avancé non disponible")
                return self._basic_doctor(args)
            
            if args.name:
                # Diagnostiquer un environnement spécifique
                self.print_header(f"Diagnostic de l'environnement '{args.name}'")
                
                result = diagnostic_service.diagnose_environment(args.name, full_check=args.full)
                
                # Afficher le statut
                status = result.get("status", "unknown")
                if status == "healthy":
                    self.print_success(f"L'environnement '{args.name}' est en bonne santé")
                elif status == "unhealthy":
                    self.print_error(f"L'environnement '{args.name}' a des problèmes")
                elif status == "degraded":
                    self.print_warning(f"L'environnement '{args.name}' est dégradé")
                
                # Afficher les problèmes
                issues = result.get("issues", [])
                warnings = result.get("warnings", [])
                
                if issues:
                    print("\nProblèmes détectés:")
                    for issue in issues:
                        severity_color = "red" if issue.get("severity") == "critical" else "yellow"
                        self.print_colored(f"  • [{issue.get('severity', 'unknown').upper()}] {issue.get('message', '')}", severity_color)
                
                if warnings:
                    print("\nAvertissements:")
                    for warning in warnings:
                        self.print_warning(f"  • {warning.get('message', '')}")
                
                # Afficher les recommandations
                recommendations = result.get("recommendations", [])
                if recommendations:
                    print("\nRecommandations:")
                    for rec in recommendations:
                        self.print_info(f"  • {rec}")
                
                # Appliquer les réparations si demandé
                if args.fix and status != "healthy":
                    print("\nApplication des réparations...")
                    success, actions = diagnostic_service.repair_environment(args.name, auto_fix=True)
                    
                    for action in actions:
                        if action.startswith("✓"):
                            self.print_success(action)
                        elif action.startswith("✗"):
                            self.print_error(action)
                        else:
                            self.print_info(action)
                    
                    if success:
                        self.print_success("Réparation terminée avec succès")
                    else:
                        self.print_warning("Réparation partielle - certains problèmes persistent")
            else:
                # Diagnostiquer tous les environnements
                self.print_header("Diagnostic de tous les environnements")
                
                environments = self.env_manager.list_environments()
                if not environments:
                    self.print_info("Aucun environnement à diagnostiquer")
                    return 0
                
                total_issues = 0
                
                for env in environments:
                    env_name = env["name"]
                    print(f"\n{COLORS['bold']}{env_name}{COLORS['reset']}")
                    
                    result = diagnostic_service.diagnose_environment(env_name, full_check=args.full)
                    status = result.get("status", "unknown")
                    
                    if status == "healthy":
                        self.print_success("  ✓ En bonne santé")
                    elif status == "unhealthy":
                        self.print_error("  ✗ Problèmes détectés")
                        total_issues += len(result.get("issues", []))
                    elif status == "degraded":
                        self.print_warning("  ! Dégradé")
                        total_issues += len(result.get("warnings", []))
                
                # Diagnostic du système si demandé
                if args.check_cache:
                    print(f"\n{COLORS['bold']}Cache{COLORS['reset']}")
                    cache_report = diagnostic_service.verify_cache_integrity()
                    cache_status = cache_report.get("status", "unknown")
                    
                    if cache_status == "healthy":
                        self.print_success("  ✓ Cache en bonne santé")
                    else:
                        self.print_warning("  ! Problèmes dans le cache")
                
                # Résumé
                print("\n" + "=" * 50)
                if total_issues == 0:
                    self.print_success("Tous les environnements sont en bonne santé")
                else:
                    self.print_warning(f"{total_issues} problème(s) détecté(s)")
                    if args.fix:
                        self.print_info("\nUtilisez 'gestvenv doctor <env_name> --fix' pour réparer un environnement spécifique")
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors du diagnostic: {str(e)}")
            return 1
    
    def _basic_doctor(self, args: argparse.Namespace) -> int:
        """
        Diagnostic basique quand le service de diagnostic avancé n'est pas disponible.
        """
        if args.name:
            # Diagnostic basique d'un environnement
            self.print_header(f"Diagnostic basique de l'environnement '{args.name}'")
            
            success, diagnosis = self.env_manager.diagnose_environment(args.name, full_check=args.full)
            
            if not success:
                self.print_error("Environnement non sain")
                
                # Afficher les vérifications
                for check, result in diagnosis.get("checks", {}).items():
                    status = result.get("status", "unknown")
                    message = result.get("message", check)
                    
                    if status == "ok":
                        self.print_success(f"  ✓ {message}")
                    elif status == "error":
                        self.print_error(f"  ✗ {message}")
                    else:
                        self.print_warning(f"  ! {message}")
                
                # Appliquer les réparations si demandé
                if args.fix:
                    print("\nTentative de réparation...")
                    repair_success, actions = self.env_manager.repair_environment(args.name, auto_fix=True)
                    
                    for action in actions:
                        self.print_info(f"  • {action}")
                    
                    if repair_success:
                        self.print_success("Réparation terminée")
                    else:
                        self.print_error("Échec de la réparation")
            else:
                self.print_success("Environnement en bonne santé")
        else:
            # Lister tous les environnements avec leur santé
            self.print_header("État de santé des environnements")
            
            environments = self.env_manager.list_environments()
            if not environments:
                self.print_info("Aucun environnement trouvé")
                return 0
            
            for env in environments:
                name = env["name"]
                exists = env["exists"]
                health = env.get("health", {})
                
                if not exists:
                    self.print_error(f"{name}: ✗ N'existe pas")
                elif health.get("python_available") and health.get("pip_available"):
                    self.print_success(f"{name}: ✓ En bonne santé")
                else:
                    self.print_warning(f"{name}: ! Problèmes détectés")
        
        return 0
    
    def cmd_system_info(self, args: argparse.Namespace) -> int:
        """
        Commande pour afficher les informations système détaillées.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        try:
            self.print_header("Informations système")
            
            # Get system info from SystemService directly
            from gestvenv.services.system_service import SystemService
            system_service = SystemService()
            sys_info = system_service.get_system_info()
            
            if args.json:
                import json
                # Convert SystemInfo dataclass to dict for JSON serialization
                sys_info_dict = {
                    "system": {
                        "system": sys_info.os_name,
                        "release": sys_info.os_release, 
                        "version": sys_info.os_version,
                        "machine": sys_info.architecture,
                        "processor": sys_info.processor
                    },
                    "python_versions": system_service.get_available_python_versions(),
                    "gestvenv_config": {
                        "default_python": self.config_manager.get_default_python(),
                        "total_environments": len(self.config_manager.get_all_environments()),
                        "active_environment": self.config_manager.get_active_environment(),
                        "offline_mode": self.config_manager.get_setting("offline_mode", False),
                        "cache_enabled": self.config_manager.get_setting("use_package_cache", True)
                    }
                }
                print(json.dumps(sys_info_dict, indent=2))
                return 0
            
            # Afficher les informations système
            print(f"\n{COLORS['bold']}Système d'exploitation{COLORS['reset']}")
            print(f"  OS: {sys_info.os_name} {sys_info.os_release}")
            print(f"  Version: {sys_info.os_version}")
            print(f"  Architecture: {sys_info.architecture}")
            print(f"  Processeur: {sys_info.processor}")
        ####
        # try:
        #     self.print_header("Informations système")
            
        #     # Récupérer les informations système
        #     sys_info = self.env_manager.get_system_info()
            
        #     if args.json:
        #         # Afficher au format JSON
        #         import json
        #         print(json.dumps(sys_info, indent=2))
        #         return 0
            
        #     # Afficher les informations système
        #     system = sys_info.get("system", {})
        #     print(f"\n{COLORS['bold']}Système d'exploitation{COLORS['reset']}")
        #     print(f"  OS: {system.get('system', 'Unknown')} {system.get('release', '')}")
        #     print(f"  Version: {system.get('version', 'Unknown')}")
        #     print(f"  Architecture: {system.get('machine', 'Unknown')}")
        #     print(f"  Processeur: {system.get('processor', 'Unknown')}")
            
            # Afficher les informations Python
            python_info = sys_info.get("python_versions", [])
            print(f"\n{COLORS['bold']}Python{COLORS['reset']}")
            if python_info:
                for version in python_info:
                    print(f"  • {version['command']}: {version['version']}")
            else:
                print("  Aucune version Python trouvée")
            
            # Configuration GestVenv
            config = sys_info.get("gestvenv_config", {})
            print(f"\n{COLORS['bold']}Configuration GestVenv{COLORS['reset']}")
            print(f"  Python par défaut: {config.get('default_python', 'Non défini')}")
            print(f"  Environnements: {config.get('total_environments', 0)}")
            print(f"  Environnement actif: {config.get('active_environment', 'Aucun')}")
            print(f"  Mode hors ligne: {'Oui' if config.get('offline_mode') else 'Non'}")
            print(f"  Cache activé: {'Oui' if config.get('cache_enabled') else 'Non'}")
            
            # Résumé des environnements
            environments = sys_info.get("environments", [])
            if environments:
                print(f"\n{COLORS['bold']}État des environnements{COLORS['reset']}")
                healthy = sum(1 for e in environments if e.get("healthy"))
                exists = sum(1 for e in environments if e.get("exists"))
                print(f"  Total: {len(environments)}")
                print(f"  Existants: {exists}")
                print(f"  En bonne santé: {healthy}")
                
                if exists < len(environments):
                    missing = [e["name"] for e in environments if not e.get("exists")]
                    self.print_warning(f"  Manquants: {', '.join(missing)}")
            
            # Exporter si demandé
            if args.export:
                try:
                    import json
                    with open(args.export, 'w', encoding='utf-8') as f:
                        json.dump(sys_info, f, indent=2, ensure_ascii=False)
                    self.print_success(f"\nInformations exportées vers: {args.export}")
                except Exception as e:
                    self.print_error(f"\nErreur lors de l'export: {str(e)}")
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la récupération des informations système: {str(e)}")
            return 1
    
    def cmd_logs(self, args: argparse.Namespace) -> int:
        """
        Commande pour gérer et afficher les logs de GestVenv.
        
        Args:
            args: Arguments de ligne de commande
            
        Returns:
            int: Code de retour (0 pour succès, autre pour erreur)
        """
        # Vérifier si une sous-commande a été spécifiée
        if not hasattr(args, 'logs_command') or not args.logs_command:
            self.print_error("Sous-commande de logs non spécifiée")
            return 1
        
        try:
            # Essayer d'importer le module de logging
            try:
                from gestvenv.utils.logging_utils import get_log_manager
                log_manager = get_log_manager()
            except ImportError:
                self.print_error("Module de gestion des logs non disponible")
                return 1
            
            # Exécuter la sous-commande appropriée
            if args.logs_command == 'show':
                return self.cmd_logs_show(args, log_manager)
            elif args.logs_command == 'clean':
                return self.cmd_logs_clean(args, log_manager)
            elif args.logs_command == 'export':
                return self.cmd_logs_export(args, log_manager)
            else:
                self.print_error(f"Sous-commande de logs non reconnue: {args.logs_command}")
                return 1
                
        except Exception as e:
            self.print_error(f"Erreur dans la gestion des logs: {str(e)}")
            return 1
    
    def cmd_logs_show(self, args: argparse.Namespace, log_manager: Any) -> int:
        """Affiche les logs."""
        try:
            self.print_header("Logs de GestVenv")
            
            # Lire les entrées de log
            from gestvenv.utils.logging_utils import LogCategory, LogLevel
            
            # Déterminer la catégorie
            category = LogCategory.GENERAL
            if args.env:
                category = LogCategory.ENVIRONMENT
            
            # Déterminer le niveau de log
            filter_level = None
            if args.level:
                filter_level = LogLevel[args.level]
            
            # Lire les logs
            entries = log_manager.read_log_entries(
                category,
                lines=args.lines,
                filter_level=filter_level,
                filter_environment=args.env
            )
            
            if not entries:
                self.print_info("Aucune entrée de log trouvée")
                return 0
            
            # Afficher les logs
            for entry in entries:
                timestamp = entry.get("timestamp", "")
                level = entry.get("level", "INFO")
                message = entry.get("message", "")
                
                # Colorer selon le niveau
                if level == "ERROR" or level == "CRITICAL":
                    color = "red"
                elif level == "WARNING":
                    color = "yellow"
                elif level == "DEBUG":
                    color = "blue"
                else:
                    color = "reset"
                
                self.print_colored(f"[{timestamp}] {level}: {message}", color)
            
            if args.follow:
                self.print_info("\nSuivi des logs en temps réel... (Ctrl+C pour arrêter)")
                # Note: Le suivi en temps réel nécessiterait une implémentation plus complexe
                self.print_warning("Le suivi en temps réel n'est pas encore implémenté")
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de l'affichage des logs: {str(e)}")
            return 1
    
    def cmd_logs_clean(self, args: argparse.Namespace, log_manager: Any) -> int:
        """Nettoie les anciens logs."""
        try:
            self.print_header("Nettoyage des logs")
            
            if not args.force:
                confirm = input(f"Supprimer les logs de plus de {args.days} jours ? (o/N) ")
                if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
                    self.print_info("Opération annulée.")
                    return 0
            
            # Nettoyer les logs
            deleted_count, freed_space = log_manager.clean_old_logs(days=args.days)
            
            if deleted_count > 0:
                freed_kb = freed_space / 1024
                self.print_success(f"{deleted_count} fichier(s) de log supprimé(s)")
                self.print_success(f"{freed_kb:.1f} KB libéré(s)")
            else:
                self.print_info("Aucun log à nettoyer")
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors du nettoyage des logs: {str(e)}")
            return 1
    
    def cmd_logs_export(self, args: argparse.Namespace, log_manager: Any) -> int:
        """Exporte les logs."""
        try:
            self.print_header("Export des logs")
            
            # Exporter les logs
            success = log_manager.export_logs(
                args.output,
                days=args.days,
                format_type=args.format
            )
            
            if success:
                self.print_success(f"Logs exportés vers: {args.output}")
            else:
                self.print_error("Échec de l'export des logs")
                return 1
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de l'export des logs: {str(e)}")
            return 1
    
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
- Gestion du cache de packages pour le mode hors ligne
- Diagnostic et réparation automatique des environnements

Pour plus d'informations sur des sujets spécifiques, utilisez:
  gestvenv docs <sujet>

Sujets disponibles: commandes, environnements, packages, export, workflow, cache, diagnostic
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
cache       - Gère le cache de packages
doctor      - Diagnostique et répare les environnements
system-info - Affiche les informations système
logs        - Gère les logs de GestVenv
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
  gestvenv create mon_env --description "Environnement de développement web"
  gestvenv create mon_env -r requirements.txt

Activation d'un environnement:
  gestvenv activate mon_env
  # Suivre les instructions affichées

Désactivation de l'environnement actif:
  gestvenv deactivate
  # Suivre les instructions affichées

Suppression d'un environnement:
  gestvenv delete mon_env
  gestvenv delete mon_env --force  # Sans confirmation

Listing des environnements:
  gestvenv list
  gestvenv list --verbose  # Informations détaillées
  gestvenv list --health   # Avec état de santé

Informations sur un environnement:
  gestvenv info mon_env
  gestvenv info mon_env --packages  # Liste tous les packages

Clonage d'un environnement:
  gestvenv clone source_env nouveau_env
  gestvenv clone source_env nouveau_env --skip-packages

Exécution de commandes dans un environnement:
  gestvenv run mon_env python script.py
  gestvenv run mon_env --timeout 60 python long_script.py
  gestvenv run mon_env --env "DEBUG=1,API_KEY=secret" python app.py
            """
            },
            "packages": {
                "title": "Gestion des packages",
                "content": """
Gestion des packages avec GestVenv:

Installation de packages:
  gestvenv install "flask,pytest"  # Dans l'environnement actif
  gestvenv install "flask==2.0.1,pytest" --env mon_env  # Dans un environnement spécifique
  gestvenv install -r requirements.txt  # Depuis un fichier requirements
  gestvenv install -e ./mon_projet  # Installation en mode éditable
  gestvenv install --dev "pytest,black,flake8"  # Dépendances de développement

Désinstallation de packages:
  gestvenv uninstall "flask,pytest"  # Dans l'environnement actif
  gestvenv uninstall "flask" --env mon_env  # Dans un environnement spécifique
  gestvenv uninstall "flask" --with-dependencies  # Avec les dépendances

Mise à jour de packages:
  gestvenv update "flask,pytest"  # Dans l'environnement actif
  gestvenv update --all  # Tous les packages de l'environnement actif
  gestvenv update --all --env mon_env  # Tous les packages d'un environnement spécifique

Vérification des mises à jour disponibles:
  gestvenv check  # Pour l'environnement actif
  gestvenv check mon_env  # Pour un environnement spécifique
  gestvenv check mon_env --apply  # Applique automatiquement les mises à jour
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
  gestvenv export mon_env --add-metadata "description:Mon projet web,auteur:John Doe"
  gestvenv export mon_env --include-metadata  # Inclut toutes les métadonnées
  gestvenv export mon_env --production  # Optimise pour la production

Import d'une configuration:
  gestvenv import /chemin/vers/fichier.json  # Import depuis un fichier JSON
  gestvenv import /chemin/vers/requirements.txt --name nouveau_env  # Import depuis requirements.txt
  gestvenv import config.json --merge  # Fusionne avec un environnement existant
  gestvenv import config.json --merge --resolve-conflicts  # Résout automatiquement les conflits
            """
            },
            "workflow": {
                "title": "Flux de travail recommandé",
                "content": """
Flux de travail recommandé avec GestVenv:

1. Création d'un environnement pour un nouveau projet:
   gestvenv create mon_projet --python python3.9 --packages "flask,pytest" --description "API REST"

2. Activation de l'environnement:
   gestvenv activate mon_projet
   # Exécuter la commande affichée

3. Installation de packages supplémentaires:
   gestvenv install "pandas,matplotlib"

4. Travail sur le projet avec l'environnement activé

5. Export de la configuration pour partage:
   gestvenv export mon_projet --output "mon_projet_config.json" --include-metadata

6. Partage de la configuration avec l'équipe

7. Import de la configuration par un membre de l'équipe:
   gestvenv import mon_projet_config.json

8. Mise à jour régulière des packages:
   gestvenv check
   gestvenv update --all

9. Création d'un environnement de développement basé sur l'environnement de production:
   gestvenv clone mon_projet mon_projet_dev

10. Diagnostic régulier de la santé des environnements:
    gestvenv doctor --full
            """
            },
            "cache": {
                "title": "Gestion du cache de packages",
                "content": """
Gestion du cache de packages avec GestVenv:

Le cache permet de travailler en mode hors ligne et d'accélérer les installations.

Configuration du cache:
  gestvenv config --enable-cache  # Active le cache
  gestvenv config --offline       # Active le mode hors ligne
  gestvenv config --cache-max-size 10000  # Taille max en Mo
  gestvenv config --cache-max-age 180     # Âge max en jours

Gestion du cache:
  gestvenv cache info     # Informations sur le cache
  gestvenv cache list     # Liste les packages en cache
  gestvenv cache list --detailed  # Avec détails

Ajout de packages au cache:
  gestvenv cache add "flask,django,pytest"
  gestvenv cache add "numpy==1.21.0,pandas"

Nettoyage du cache:
  gestvenv cache clean    # Nettoie selon les paramètres par défaut
  gestvenv cache clean --max-age 30 --max-size 1000

Export/Import du cache:
  gestvenv cache export --output cache_backup.json
  gestvenv cache import cache_backup.json

Suppression de packages:
  gestvenv cache remove "old_package"
  gestvenv cache remove "flask==1.0.0"  # Version spécifique

Vérification de l'intégrité:
  gestvenv cache verify
  gestvenv cache verify --fix  # Corrige les problèmes
            """
            },
            "diagnostic": {
                "title": "Diagnostic et réparation",
                "content": """
Diagnostic et réparation avec GestVenv:

Diagnostic d'un environnement:
  gestvenv doctor mon_env        # Diagnostic basique
  gestvenv doctor mon_env --full # Diagnostic complet
  gestvenv doctor mon_env --fix  # Applique les réparations

Diagnostic de tous les environnements:
  gestvenv doctor
  gestvenv doctor --check-cache  # Vérifie aussi le cache

Problèmes courants détectés:
- Environnement physiquement manquant
- Exécutable Python manquant ou cassé
- pip manquant ou non fonctionnel
- Packages corrompus
- Permissions incorrectes
- Incohérences de configuration

Réparations automatiques disponibles:
- Recréation de l'environnement
- Réinstallation de pip
- Réinstallation des packages manquants
- Correction des permissions
- Nettoyage de la configuration

Informations système:
  gestvenv system-info       # Affiche les infos système
  gestvenv system-info --json
  gestvenv system-info --export system_report.json

Gestion des logs:
  gestvenv logs show         # Affiche les logs récents
  gestvenv logs show -n 100  # Dernières 100 lignes
  gestvenv logs show --level ERROR --env mon_env
  gestvenv logs clean --days 30
  gestvenv logs export logs_backup.txt --days 7
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
    
    # Fonction utilitaire pour formater la taille
    def format_size(self, size_bytes: int) -> str:
        """
        Formate une taille en octets en une chaîne lisible.
        
        Args:
            size_bytes: Taille en octets
            
        Returns:
            str: Taille formatée
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KiB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MiB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GiB"
    
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
            "cache": self.cmd_cache,
            "doctor": self.cmd_doctor,
            "system-info": self.cmd_system_info,
            "logs": self.cmd_logs,
            "docs": self.cmd_docs
        }
        
        if hasattr(parsed_args, 'command') and parsed_args.command:
            command = parsed_args.command
            if isinstance(command, list):
                command = command[0] if command else None
                
            if command in commands:
                try:
                    return commands[command](parsed_args)
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
        return 0


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