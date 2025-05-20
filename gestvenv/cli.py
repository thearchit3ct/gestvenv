#!/usr/bin/env python3
"""
GestVenv - Gestionnaire d'Environnements Virtuels Python

Interface en ligne de commande pour créer, gérer et partager des environnements virtuels Python.
"""

import os
import sys
import json
import argparse
import logging
import platform
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import des modules internes
from .core.env_manager import EnvironmentManager
from .utils.path_handler import (
    get_config_file_path,
    get_environment_path,
    resolve_path,
    get_default_venv_dir
)
from .utils.validators import (
    validate_env_name,
    validate_packages_list,
    validate_output_format
)
from .utils.system_commands import (
    get_available_python_versions,
    check_python_version,
    get_activation_command
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger("gestvenv")

# Version du programme
__version__ = "1.0.0"

# Couleurs pour le terminal (si disponibles)
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "red": "\033[31m",
    "cyan": "\033[36m",
    "magenta": "\033[35m"
}

# Désactiver les couleurs si le terminal ne les supporte pas
if platform.system() == "Windows" and not os.environ.get("TERM") == "xterm":
    for key in COLORS:
        COLORS[key] = ""

def print_colored(text: str, color: str = "reset") -> None:
    """
    Affiche du texte coloré dans le terminal.
    
    Args:
        text (str): Texte à afficher
        color (str): Couleur à utiliser
    """
    print(f"{COLORS.get(color, '')}{text}{COLORS['reset']}")

def print_success(message: str) -> None:
    """Affiche un message de succès."""
    print_colored(f"✓ {message}", "green")

def print_error(message: str) -> None:
    """Affiche un message d'erreur."""
    print_colored(f"✗ {message}", "red")

def print_warning(message: str) -> None:
    """Affiche un message d'avertissement."""
    print_colored(f"! {message}", "yellow")

def print_info(message: str) -> None:
    """Affiche un message d'information."""
    print_colored(message, "blue")

def print_header(message: str) -> None:
    """Affiche un en-tête."""
    print_colored(f"\n{message}", "bold")
    print_colored("=" * len(message))

def wrap_text(text: str, width: int = 80) -> str:
    """Enveloppe le texte à la largeur spécifiée."""
    return "\n".join(textwrap.wrap(text, width))

def create_parser() -> argparse.ArgumentParser:
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
    pyversions_parser = subparsers.add_parser('pyversions', help='Liste les versions Python disponibles sur le système')
    
    # Commande: docs
    docs_parser = subparsers.add_parser('docs', help='Affiche la documentation')
    docs_parser.add_argument('topic', nargs='?', help='Sujet spécifique de la documentation')
    
    return parser

def cmd_create(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour créer un nouvel environnement virtuel.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    print_header(f"Création de l'environnement '{args.name}'")
    
    # Valider le nom de l'environnement
    valid, error = validate_env_name(args.name)
    if not valid:
        print_error(error)
        return 1
    
    # Informations sur l'environnement en cours de création
    print_info(f"Nom de l'environnement: {args.name}")
    
    if args.python_version:
        python_version = args.python_version
        print_info(f"Version Python spécifiée: {python_version}")
    else:
        python_version = env_manager.config["default_python"]
        print_info(f"Utilisation de la version Python par défaut: {python_version}")
    
    if args.packages:
        print_info(f"Packages à installer: {args.packages}")
    
    if args.path:
        print_info(f"Chemin personnalisé: {args.path}")
    
    # Créer l'environnement
    success, message = env_manager.create_environment(
        args.name,
        python_version=args.python_version,
        packages=args.packages,
        path=args.path
    )
    
    if success:
        print_success(message)
        
        # Afficher comment activer l'environnement
        env_path = get_environment_path(args.name)
        activate_cmd = get_activation_command(args.name)
        
        if activate_cmd:
            print_info("\nPour activer cet environnement, utilisez:")
            if platform.system() == "Windows":
                print(f"\n    {activate_cmd}")
            else:
                print(f"\n    {activate_cmd}")
            
            print_info("\nOu utilisez la commande intégrée:")
            print(f"\n    gestvenv activate {args.name}")
        
        return 0
    else:
        print_error(message)
        return 1

def cmd_activate(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour activer un environnement virtuel.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    success, message = env_manager.activate_environment(args.name)
    
    if success:
        # Comme nous ne pouvons pas réellement modifier l'environnement du processus parent,
        # nous affichons la commande que l'utilisateur doit exécuter
        print_info(f"\nPour activer l'environnement '{args.name}', exécutez:")
        
        if platform.system() == "Windows":
            print(f"\n    {message}\n")
        else:
            print(f'\n    eval "$(gestvenv activate-script {args.name})"\n')
            # Ou alternative plus simple
            print(f"    Ou directement:\n    {message}\n")
        
        return 0
    else:
        print_error(message)
        return 1

def cmd_activate_script(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande interne pour générer le script d'activation.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    success, message = env_manager.activate_environment(args.name)
    
    if success:
        # Simplement afficher la commande sans formatage
        print(message)
        return 0
    else:
        print_error(message)
        return 1

def cmd_deactivate(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour désactiver l'environnement actif.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    success, message = env_manager.deactivate_environment()
    
    if success:
        print_info("\nPour désactiver l'environnement actif, exécutez:")
        
        if platform.system() == "Windows":
            print(f"\n    {message}\n")
        else:
            print(f"\n    {message}\n")
        
        return 0
    else:
        print_error(message)
        return 1

def cmd_delete(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour supprimer un environnement virtuel.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    # Si --force n'est pas utilisé, demander confirmation
    if not args.force:
        confirm = input(f"Êtes-vous sûr de vouloir supprimer l'environnement '{args.name}' ? (o/N) ")
        if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
            print_info("Opération annulée.")
            return 0
    
    print_header(f"Suppression de l'environnement '{args.name}'")
    
    success, message = env_manager.delete_environment(args.name, force=args.force)
    
    if success:
        print_success(message)
        return 0
    else:
        print_error(message)
        return 1

def cmd_list(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour lister tous les environnements virtuels.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    environments = env_manager.list_environments()
    active_env = env_manager.get_active_environment()
    
    if args.json:
        # Afficher au format JSON
        print(json.dumps(environments, indent=2))
        return 0
    
    if not environments:
        print_info("Aucun environnement trouvé.")
        print_info("\nUtilisez 'gestvenv create <nom>' pour créer un nouvel environnement.")
        return 0
    
    print_header("Environnements virtuels disponibles")
    
    for env in environments:
        name = env["name"]
        python_version = env["python_version"]
        path = env["path"]
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
            print(f"  Chemin: {path}")
            print()
    
    total = len(environments)
    print_info(f"\nTotal: {total} environnement(s)")
    
    if active_env:
        print_info(f"Environnement actif: {active_env}")
    
    return 0

def cmd_info(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour afficher des informations détaillées sur un environnement.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    env_info = env_manager.get_environment_info(args.name)
    
    if not env_info:
        print_error(f"L'environnement '{args.name}' n'existe pas.")
        return 1
    
    if args.json:
        # Afficher au format JSON
        print(json.dumps(env_info, indent=2))
        return 0
    
    print_header(f"Informations sur l'environnement '{args.name}'")
    
    # Statut
    if env_info["active"]:
        status = f"{COLORS['green']}● ACTIF{COLORS['reset']}"
    elif not env_info["exists"]:
        status = f"{COLORS['red']}✗ MANQUANT{COLORS['reset']}"
    else:
        status = f"{COLORS['blue']}○ inactif{COLORS['reset']}"
    
    print(f"Statut: {status}")
    print(f"Python: {env_info['python_version']}")
    print(f"Créé le: {env_info['created_at']}")
    print(f"Chemin: {env_info['path']}")
    
    # Santé de l'environnement
    health = env_info["health"]
    if env_info["exists"]:
        health_status = []
        for check, result in health.items():
            icon = "✓" if result else "✗"
            color = "green" if result else "red"
            health_status.append(f"{COLORS[color]}{icon}{COLORS['reset']} {check}")
        
        print("\nSanté de l'environnement:")
        print("  " + ", ".join(health_status))
    
    # Packages
    print_header("Packages installés")
    
    if not env_info["packages_installed"]:
        print_info("Aucun package installé.")
    else:
        packages = sorted(env_info["packages_installed"], key=lambda x: x["name"])
        
        for pkg in packages:
            print(f"{pkg['name']} {COLORS['cyan']}=={COLORS['reset']} {pkg['version']}")
    
    return 0

def cmd_install(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour installer des packages dans un environnement.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    # Déterminer l'environnement cible
    env_name = args.env
    if not env_name:
        env_name = env_manager.get_active_environment()
        if not env_name:
            print_error("Aucun environnement actif. Spécifiez un environnement avec --env.")
            return 1
    
    # Valider la liste de packages
    valid, package_list, error = validate_packages_list(args.packages)
    if not valid:
        print_error(error)
        return 1
    
    print_header(f"Installation de packages dans '{env_name}'")
    print_info(f"Packages à installer: {', '.join(package_list)}")
    
    # Installer les packages
    from .utils.system_commands import install_packages
    success = install_packages(env_name, package_list)
    
    if success:
        print_success(f"Packages installés avec succès dans l'environnement '{env_name}'")
        return 0
    else:
        print_error(f"Erreur lors de l'installation des packages")
        return 1

def cmd_uninstall(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour désinstaller des packages d'un environnement.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    # Déterminer l'environnement cible
    env_name = args.env
    if not env_name:
        env_name = env_manager.get_active_environment()
        if not env_name:
            print_error("Aucun environnement actif. Spécifiez un environnement avec --env.")
            return 1
    
    # Valider la liste de packages
    valid, package_list, error = validate_packages_list(args.packages)
    if not valid:
        print_error(error)
        return 1
    
    # Demander confirmation
    confirm = input(f"Êtes-vous sûr de vouloir désinstaller les packages suivants de '{env_name}' ?\n"
                   f"{', '.join(package_list)}\n"
                   f"(o/N) ")
    
    if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
        print_info("Opération annulée.")
        return 0
    
    print_header(f"Désinstallation de packages de '{env_name}'")
    
    # Désinstaller les packages
    from .utils.system_commands import uninstall_packages
    success = uninstall_packages(env_name, package_list)
    
    if success:
        print_success(f"Packages désinstallés avec succès de l'environnement '{env_name}'")
        return 0
    else:
        print_error(f"Erreur lors de la désinstallation des packages")
        return 1

def cmd_update(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour mettre à jour des packages dans un environnement.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    # Déterminer l'environnement cible
    env_name = args.env
    if not env_name:
        env_name = env_manager.get_active_environment()
        if not env_name:
            print_error("Aucun environnement actif. Spécifiez un environnement avec --env.")
            return 1
    
    if not args.packages and not args.all:
        print_error("Vous devez spécifier des packages à mettre à jour ou utiliser --all")
        return 1
    
    print_header(f"Mise à jour de packages dans '{env_name}'")
    
    if args.all:
        print_info("Mise à jour de tous les packages")
    else:
        print_info(f"Packages à mettre à jour: {args.packages}")
    
    # Mettre à jour les packages
    success, message = env_manager.update_packages(env_name, args.packages, args.all)
    
    if success:
        print_success(message)
        return 0
    else:
        print_error(message)
        return 1

def cmd_export(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour exporter la configuration d'un environnement.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    print_header(f"Export de l'environnement '{args.name}'")
    
    format_type = args.format
    print_info(f"Format d'export: {format_type}")
    
    if args.output:
        print_info(f"Fichier de sortie: {args.output}")
    
    # Exporter l'environnement
    success, message = env_manager.export_environment(
        args.name,
        output_path=args.output,
        format_type=format_type,
        metadata=args.metadata
    )
    
    if success:
        print_success(message)
        return 0
    else:
        print_error(message)
        return 1

def cmd_import(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour importer une configuration d'environnement.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    print_header("Import d'environnement")
    
    print_info(f"Fichier source: {args.file}")
    if args.name:
        print_info(f"Nom de l'environnement: {args.name}")
    
    # Importer l'environnement
    success, message = env_manager.import_environment(args.file, args.name)
    
    if success:
        print_success(message)
        return 0
    else:
        print_error(message)
        return 1

def cmd_clone(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour cloner un environnement existant.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    print_header(f"Clonage de l'environnement '{args.source}' vers '{args.target}'")
    
    # Cloner l'environnement
    success, message = env_manager.clone_environment(args.source, args.target)
    
    if success:
        print_success(message)
        return 0
    else:
        print_error(message)
        return 1

def cmd_run(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour exécuter une commande dans un environnement virtuel.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    command = args.command
    
    print_header(f"Exécution dans l'environnement '{args.name}'")
    print_info(f"Commande: {' '.join(command)}")
    
    # Exécuter la commande dans l'environnement
    ret_code, stdout, stderr = env_manager.run_command_in_environment(args.name, command)
    
    if stdout:
        print(stdout)
    if stderr:
        print_error(stderr)
    
    return ret_code

def cmd_config(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour configurer les paramètres par défaut.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    if args.default_python:
        print_header("Configuration de Python par défaut")
        
        # Définir la commande Python par défaut
        success, message = env_manager.set_default_python(args.default_python)
        
        if success:
            print_success(message)
        else:
            print_error(message)
            return 1
    
    if args.show or (not args.default_python):
        print_header("Configuration actuelle")
        
        print(f"Fichier de configuration: {env_manager.config_path}")
        print(f"Commande Python par défaut: {env_manager.config.get('default_python', 'Non définie')}")
        
        active_env = env_manager.get_active_environment()
        if active_env:
            print(f"Environnement actif: {active_env}")
        else:
            print("Aucun environnement actif")
        
        print()
        print("Répertoire des environnements:")
        print(f"  {get_default_venv_dir()}")
        
        # Afficher les paramètres additionnels
        if "settings" in env_manager.config:
            print("\nParamètres:")
            for key, value in env_manager.config["settings"].items():
                print(f"  {key}: {value}")
    
    return 0

def cmd_check(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour vérifier les mises à jour disponibles pour les packages.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    # Déterminer l'environnement cible
    env_name = args.name
    if not env_name:
        env_name = env_manager.get_active_environment()
        if not env_name:
            print_error("Aucun environnement actif. Spécifiez un nom d'environnement.")
            return 1
    
    print_header(f"Vérification des mises à jour pour '{env_name}'")
    
    # Vérifier les mises à jour
    success, updates, message = env_manager.check_for_updates(env_name)
    
    if not success:
        print_error(message)
        return 1
    
    if not updates:
        print_success("Tous les packages sont à jour.")
        return 0
    
    print_info(f"{len(updates)} package(s) peuvent être mis à jour:")
    
    for pkg in updates:
        name = pkg["name"]
        current = pkg["current_version"]
        latest = pkg["latest_version"]
        
        print(f"{name}: {COLORS['yellow']}{current}{COLORS['reset']} → {COLORS['green']}{latest}{COLORS['reset']}")
    
    print_info("\nPour mettre à jour tous les packages:")
    print(f"  gestvenv update --all --env {env_name}")
    
    return 0

def cmd_pyversions(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour lister les versions Python disponibles sur le système.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
    Returns:
        int: Code de retour (0 pour succès, autre pour erreur)
    """
    print_header("Versions Python disponibles")
    
    # Obtenir les versions Python disponibles
    versions = get_available_python_versions()
    
    if not versions:
        print_warning("Aucune version Python trouvée sur le système.")
        return 1
    
    for v in versions:
        cmd = v["command"]
        version = v["version"]
        
        is_default = cmd == env_manager.config.get("default_python", "")
        if is_default:
            print(f"{COLORS['green']}✓{COLORS['reset']} {COLORS['bold']}{cmd}{COLORS['reset']} - Version {version} (défaut)")
        else:
            print(f"  {cmd} - Version {version}")
    
    print_info(f"\nTotal: {len(versions)} version(s) trouvée(s)")
    print_info("\nPour définir la version par défaut:")
    print("  gestvenv config --set-python <commande>")
    
    return 0

def cmd_docs(args: argparse.Namespace, env_manager: EnvironmentManager) -> int:
    """
    Commande pour afficher la documentation.
    
    Args:
        args (argparse.Namespace): Arguments de ligne de commande
        env_manager (EnvironmentManager): Gestionnaire d'environnements
        
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
  # Exécuter la commande affichée

Désactivation de l'environnement actif:
  gestvenv deactivate
  # Exécuter la commande affichée

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
        print_error(f"Sujet de documentation '{topic}' non trouvé.")
        print_info("Sujets disponibles: " + ", ".join(doc_topics.keys()))
        return 1
    
    doc = doc_topics[topic]
    print_header(doc["title"])
    print(doc["content"].strip())
    
    return 0

def main():
    """
    Fonction principale d'entrée du programme.
    """
    # Créer le parseur d'arguments
    parser = create_parser()
    
    # Analyser les arguments
    args = parser.parse_args()
    
    # Configurer le logging en mode debug si demandé
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Mode debug activé")
    
    # Cas spécial: pas de commande spécifiée
    if not hasattr(args, 'command') or not args.command:
        parser.print_help()
        return 1
    
    # Initialiser le gestionnaire d'environnements
    env_manager = EnvironmentManager()
    
    # Ajouter le handler pour activate-script (commande interne)
    if args.command == "activate-script":
        return cmd_activate_script(args, env_manager)
    
    # Exécuter la commande appropriée
    commands = {
        "create": cmd_create,
        "activate": cmd_activate,
        "deactivate": cmd_deactivate,
        "delete": cmd_delete,
        "list": cmd_list,
        "info": cmd_info,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "update": cmd_update,
        "export": cmd_export,
        "import": cmd_import,
        "clone": cmd_clone,
        "run": cmd_run,
        "config": cmd_config,
        "check": cmd_check,
        "pyversions": cmd_pyversions,
        "docs": cmd_docs
    }
    
    if args.command in commands:
        try:
            return commands[args.command](args, env_manager)
        except KeyboardInterrupt:
            print("\nOpération interrompue.")
            return 130  # Code standard pour SIGINT
        except Exception as e:
            if args.debug:
                # En mode debug, afficher la trace complète
                import traceback
                traceback.print_exc()
            else:
                # En mode normal, afficher un message d'erreur plus convivial
                print_error(f"Erreur: {str(e)}")
                print_info("Pour plus de détails, exécutez la commande avec --debug")
            return 1
    else:
        print_error(f"Commande inconnue: {args.command}")
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())