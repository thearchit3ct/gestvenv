#!/usr/bin/env python3
"""
GestVenv v1.1 - Interface Ligne de Commande (CLI)
================================================

Interface moderne pour la gestion d'environnements virtuels Python avec:
- Support pyproject.toml (PEP 621, 517, 518)
- Backends multiples (pip, uv, poetry, pdm)
- Migration automatique v1.0 → v1.1
- Cache intelligent et mode hors ligne
- Templates et alias d'environnements

Usage:
    gestvenv <command> [options]
    
Commandes principales:
    create          Créer un nouvel environnement
    list            Lister les environnements
    activate        Activer un environnement
    delete          Supprimer un environnement
    install         Installer des packages
    sync            Synchroniser avec pyproject.toml
    
Voir 'gestvenv --help' pour la liste complète.
"""

import sys
import argparse
import logging
import json
import os
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

# Imports avec gestion d'erreurs pour compatibilité
try:
    from gestvenv import get_environment_manager, get_config_manager, check_dependencies
    from gestvenv import EnvironmentManager, ConfigManager
    from gestvenv import __version__, configure_logging
except ImportError as e:
    print(f"❌ Erreur d'import GestVenv: {e}")
    print("Vérifiez que GestVenv est correctement installé.")
    sys.exit(1)

# ===== CONFIGURATION COULEURS ET STYLE =====

class Colors:
    """Codes ANSI pour couleurs terminal (désactivables avec --no-color)."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Couleurs de base
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Couleurs brillantes
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'

class UIFormatter:
    """Gestionnaire d'affichage avec support couleurs et formatage."""
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and sys.stdout.isatty()
        self.colors = Colors() if self.use_colors else self._create_no_color()
    
    def _create_no_color(self):
        """Crée un objet Colors sans couleurs."""
        class NoColor:
            def __getattr__(self, name):
                return ''
        return NoColor()
    
    def success(self, message: str) -> str:
        """Formate un message de succès."""
        return f"{self.colors.BRIGHT_GREEN}✅ {message}{self.colors.RESET}"
    
    def error(self, message: str) -> str:
        """Formate un message d'erreur."""
        return f"{self.colors.BRIGHT_RED}❌ {message}{self.colors.RESET}"
    
    def warning(self, message: str) -> str:
        """Formate un message d'avertissement."""
        return f"{self.colors.BRIGHT_YELLOW}⚠️  {message}{self.colors.RESET}"
    
    def info(self, message: str) -> str:
        """Formate un message d'information."""
        return f"{self.colors.BRIGHT_BLUE}ℹ️  {message}{self.colors.RESET}"
    
    def highlight(self, text: str) -> str:
        """Met en surbrillance du texte."""
        return f"{self.colors.BOLD}{self.colors.CYAN}{text}{self.colors.RESET}"
    
    def dim(self, text: str) -> str:
        """Affiche du texte atténué."""
        return f"{self.colors.DIM}{text}{self.colors.RESET}"

# ===== CLASSE CLI PRINCIPALE =====

class GestVenvCLI:
    """
    Interface ligne de commande principale pour GestVenv v1.1.
    
    Gère toutes les commandes utilisateur et coordonne avec les services backend.
    """
    
    def __init__(self):
        self.ui = UIFormatter()
        self.env_manager: Optional[EnvironmentManager] = None
        self.config_manager: Optional[ConfigManager] = None
        self.logger = logging.getLogger(__name__)
        
        # Configuration par défaut
        self.verbose = False
        self.quiet = False
        self.offline_mode = False
        self.preferred_backend = None
        
    def setup_logging(self, verbose: bool = False, quiet: bool = False):
        """Configure le logging selon les options utilisateur."""
        if quiet:
            level = logging.ERROR
        elif verbose:
            level = logging.DEBUG
        else:
            level = logging.INFO
            
        configure_logging(level)
        self.verbose = verbose
        self.quiet = quiet
    
    def initialize_managers(self, config_path: Optional[str] = None):
        """Initialise les gestionnaires avec gestion d'erreurs."""
        try:
            self.env_manager = get_environment_manager(config_path)
            self.config_manager = get_config_manager(config_path)
        except Exception as e:
            if self.verbose:
                import traceback
                traceback.print_exc()
            self.print_error(f"Impossible d'initialiser GestVenv: {e}")
            sys.exit(1)
    
    # ===== MÉTHODES D'AFFICHAGE =====
    
    def print_success(self, message: str):
        """Affiche un message de succès."""
        if not self.quiet:
            print(self.ui.success(message))
    
    def print_error(self, message: str):
        """Affiche un message d'erreur."""
        print(self.ui.error(message), file=sys.stderr)
    
    def print_warning(self, message: str):
        """Affiche un avertissement."""
        if not self.quiet:
            print(self.ui.warning(message))
    
    def print_info(self, message: str):
        """Affiche une information."""
        if not self.quiet:
            print(self.ui.info(message))
    
    def print_json(self, data: Any):
        """Affiche des données au format JSON."""
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    
    # ===== COMMANDES ENVIRONNEMENTS =====
    
    def cmd_create(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv create <name> [options]"""
        try:
            # Validation du nom
            if not args.name or not args.name.strip():
                self.print_error("Le nom de l'environnement est requis")
                return 1
            
            # Préparation des options
            create_options = {
                'name': args.name.strip(),
                'python_version': args.python,
                'backend': args.backend or self.preferred_backend,
                'custom_path': Path(args.path) if args.path else None,
                'offline_mode': self.offline_mode or args.offline,
            }
            
            # Packages initiaux
            if args.packages:
                packages = [pkg.strip() for pkg in args.packages.split(',') if pkg.strip()]
                create_options['initial_packages'] = packages
            
            # Création depuis pyproject.toml
            if args.from_pyproject:
                pyproject_path = Path(args.from_pyproject)
                if not pyproject_path.exists():
                    self.print_error(f"Fichier pyproject.toml introuvable: {pyproject_path}")
                    return 1
                
                groups = None
                if args.groups:
                    groups = [g.strip() for g in args.groups.split(',') if g.strip()]
                
                env_info = self.env_manager.create_from_pyproject(
                    pyproject_path=pyproject_path,
                    env_name=args.name,
                    dependency_groups=groups,
                    backend=create_options['backend']
                )
            else:
                # Création standard
                env_info = self.env_manager.create_environment(**create_options)
            
            # Affichage du résultat
            self.print_success(f"Environnement '{env_info.name}' créé avec succès")
            self.print_info(f"Chemin: {self.ui.highlight(str(env_info.path))}")
            self.print_info(f"Python: {self.ui.highlight(env_info.python_version)}")
            if hasattr(env_info, 'backend_type'):
                self.print_info(f"Backend: {self.ui.highlight(env_info.backend_type.value)}")
            
            if create_options.get('initial_packages'):
                self.print_info(f"Packages installés: {', '.join(create_options['initial_packages'])}")
            
            # Instructions d'activation
            print()
            self.print_info(f"Pour activer: {self.ui.highlight(f'gestvenv activate {args.name}')}")
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la création: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def cmd_list(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv list [options]"""
        try:
            environments = self.env_manager.list_environments()
            
            if not environments:
                self.print_info("Aucun environnement trouvé.")
                return 0
            
            # Filtrage si demandé
            if args.filter:
                filter_term = args.filter.lower()
                environments = [
                    env for env in environments 
                    if filter_term in env.name.lower()
                ]
            
            # Format JSON
            if args.format == 'json':
                env_data = [self._env_to_dict(env) for env in environments]
                self.print_json(env_data)
                return 0
            
            # Format tableau
            self._print_environments_table(environments, verbose=args.verbose)
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors du listage: {e}")
            return 1
    
    def cmd_activate(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv activate <name>"""
        try:
            success, message = self.env_manager.activate_environment(args.name)
            
            if success:
                self.print_success(f"Environnement '{args.name}' activé")
                
                # Instructions pour l'utilisateur
                env_info = self.env_manager.get_environment_info(args.name)
                if env_info:
                    activate_script = env_info.path / "Scripts" / "activate" if os.name == 'nt' else env_info.path / "bin" / "activate"
                    print()
                    self.print_info("Pour activer dans votre shell:")
                    if os.name == 'nt':
                        print(f"  {self.ui.highlight(str(activate_script))}")
                    else:
                        print(f"  {self.ui.highlight(f'source {activate_script}')}")
            else:
                self.print_error(message)
                return 1
                
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de l'activation: {e}")
            return 1
    
    def cmd_deactivate(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv deactivate"""
        try:
            success, message = self.env_manager.deactivate_environment()
            
            if success:
                self.print_success("Environnement désactivé")
            else:
                self.print_error(message)
                return 1
                
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la désactivation: {e}")
            return 1
    
    def cmd_delete(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv delete <name> [--force]"""
        try:
            # Confirmation si pas de --force
            if not args.force:
                response = input(f"⚠️  Supprimer l'environnement '{args.name}' ? [y/N]: ")
                if response.lower() not in ['y', 'yes', 'oui']:
                    self.print_info("Suppression annulée")
                    return 0
            
            success, message = self.env_manager.delete_environment(args.name, force=args.force)
            
            if success:
                self.print_success(f"Environnement '{args.name}' supprimé")
            else:
                self.print_error(message)
                return 1
                
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la suppression: {e}")
            return 1
    
    def cmd_info(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv info <name>"""
        try:
            env_info = self.env_manager.get_environment_info(args.name)
            
            if not env_info:
                self.print_error(f"Environnement '{args.name}' introuvable")
                return 1
            
            if args.format == 'json':
                self.print_json(self._env_to_dict(env_info))
                return 0
            
            # Affichage détaillé
            self._print_environment_details(env_info)
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la récupération des informations: {e}")
            return 1
    
    # ===== COMMANDES PACKAGES =====
    
    def cmd_install(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv install <env> <packages> [options]"""
        try:
            packages = [pkg.strip() for pkg in args.packages if pkg.strip()]
            if not packages:
                self.print_error("Aucun package spécifié")
                return 1
            
            install_options = {
                'backend': args.backend or self.preferred_backend,
                'offline_mode': self.offline_mode or args.offline,
                'upgrade': args.upgrade,
                'dev_dependencies': args.dev,
            }
            
            self.print_info(f"Installation de {len(packages)} package(s) dans '{args.env_name}'...")
            
            success, results = self.env_manager.install_packages(
                env_name=args.env_name,
                packages=packages,
                **install_options
            )
            
            if success:
                self.print_success(f"Packages installés avec succès dans '{args.env_name}'")
                for pkg in packages:
                    print(f"  ✓ {pkg}")
            else:
                self.print_error(f"Erreur lors de l'installation: {results}")
                return 1
                
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de l'installation: {e}")
            return 1
    
    def cmd_sync(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv sync <env> [options]"""
        try:
            sync_options = {
                'groups': args.groups.split(',') if args.groups else None,
                'strict_mode': args.strict,
                'update_lock': args.update_lock,
            }
            
            self.print_info(f"Synchronisation de l'environnement '{args.env_name}'...")
            
            success, message = self.env_manager.sync_environment(
                env_name=args.env_name,
                **sync_options
            )
            
            if success:
                self.print_success(f"Environnement '{args.env_name}' synchronisé")
            else:
                self.print_error(message)
                return 1
                
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la synchronisation: {e}")
            return 1
    
    # ===== COMMANDES CONFIGURATION =====
    
    def cmd_config(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv config [options]"""
        try:
            if args.show:
                config = self.config_manager.export_config()
                if args.format == 'json':
                    self.print_json(config)
                else:
                    self._print_config_summary(config)
                return 0
            
            # Modification de configuration
            if args.set_python:
                self.config_manager.set_setting('default_python_version', args.set_python)
                self.print_success(f"Version Python par défaut: {args.set_python}")
            
            if args.set_backend:
                self.config_manager.set_setting('preferred_backend', args.set_backend)
                self.print_success(f"Backend préféré: {args.set_backend}")
            
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur de configuration: {e}")
            return 1
    
    def cmd_backend(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv backend [list|set|info]"""
        try:
            if args.action == 'list':
                self._print_available_backends()
            elif args.action == 'set' and args.backend:
                self.config_manager.set_setting('preferred_backend', args.backend)
                self.print_success(f"Backend par défaut: {args.backend}")
            elif args.action == 'info' and args.backend:
                self._print_backend_info(args.backend)
            else:
                self.print_error("Action ou backend manquant")
                return 1
                
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur backend: {e}")
            return 1
    
    # ===== COMMANDES UTILITAIRES =====
    
    def cmd_check(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv check <env>"""
        try:
            health_info = self.env_manager.check_environment_health(args.env_name)
            
            if args.format == 'json':
                self.print_json(health_info.__dict__)
                return 0
            
            self._print_health_check(args.env_name, health_info)
            return 0 if health_info.is_healthy else 1
            
        except Exception as e:
            self.print_error(f"Erreur lors de la vérification: {e}")
            return 1
    
    def cmd_migrate(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv migrate [options]"""
        try:
            if args.analyze:
                # Analyse des configurations existantes
                self.print_info("Analyse de la migration...")
                # Logique d'analyse à implémenter
                return 0
            
            # Migration automatique
            self.print_info("Migration des configurations v1.0 vers v1.1...")
            from gestvenv import migrate_from_v1_0
            
            success = migrate_from_v1_0(args.config_path)
            if success:
                self.print_success("Migration réussie !")
            else:
                self.print_error("Échec de la migration")
                return 1
                
            return 0
            
        except Exception as e:
            self.print_error(f"Erreur lors de la migration: {e}")
            return 1
    
    def cmd_version(self, args: argparse.Namespace) -> int:
        """Commande: gestvenv version"""
        print(f"GestVenv v{__version__}")
        
        if args.verbose:
            print(f"Python: {sys.version}")
            print(f"Plateforme: {sys.platform}")
            
            # État des dépendances
            deps = check_dependencies()
            print("\nDépendances:")
            for dep, available in deps.items():
                status = "✓" if available else "✗"
                print(f"  {status} {dep}")
        
        return 0
    
    # ===== MÉTHODES D'AFFICHAGE SPÉCIALISÉES =====
    
    def _print_environments_table(self, environments: List[Any], verbose: bool = False):
        """Affiche une table des environnements."""
        if verbose:
            # Table détaillée
            print(f"\n{'Nom':<20} {'Actif':<6} {'Python':<10} {'Backend':<8} {'Packages':<10} {'Santé':<8}")
            print("─" * 85)
            
            for env in environments:
                active = "✓" if getattr(env, 'is_active', False) else ""
                backend = getattr(env, 'backend_type', 'pip').name if hasattr(getattr(env, 'backend_type', None), 'name') else 'pip'
                pkg_count = len(getattr(env, 'packages', []))
                health = "✓" if getattr(env, 'health', None) and getattr(env.health, 'is_healthy', False) else "⚠"
                
                print(f"{env.name:<20} {active:<6} {env.python_version:<10} {backend:<8} {pkg_count:<10} {health:<8}")
        else:
            # Table simple
            print(f"\n{'Nom':<20} {'Actif':<6} {'Python':<10} {'Packages':<10}")
            print("─" * 50)
            
            for env in environments:
                active = "✓" if getattr(env, 'is_active', False) else ""
                pkg_count = len(getattr(env, 'packages', []))
                
                print(f"{env.name:<20} {active:<6} {env.python_version:<10} {pkg_count:<10}")
        
        print(f"\nTotal: {len(environments)} environnement(s)")
    
    def _print_environment_details(self, env_info: Any):
        """Affiche les détails d'un environnement."""
        print(f"\n{self.ui.highlight('📦 Environnement:')} {env_info.name}")
        print(f"   {self.ui.dim('Chemin:')} {env_info.path}")
        print(f"   {self.ui.dim('Python:')} {env_info.python_version}")
        print(f"   {self.ui.dim('Créé:')} {getattr(env_info, 'created_at', 'Inconnu')}")
        print(f"   {self.ui.dim('Actif:')} {'Oui' if getattr(env_info, 'is_active', False) else 'Non'}")
        
        if hasattr(env_info, 'backend_type'):
            print(f"   {self.ui.dim('Backend:')} {env_info.backend_type.value}")
        
        # Packages installés
        packages = getattr(env_info, 'packages', [])
        if packages:
            print(f"\n{self.ui.highlight('📚 Packages installés:')} ({len(packages)})")
            for pkg in packages[:10]:  # Limiter l'affichage
                print(f"   • {pkg.name} {pkg.version}" if hasattr(pkg, 'version') else f"   • {pkg}")
            if len(packages) > 10:
                print(f"   ... et {len(packages) - 10} autres")
        
        # Informations pyproject.toml
        if hasattr(env_info, 'pyproject_info') and env_info.pyproject_info:
            print(f"\n{self.ui.highlight('📋 Configuration pyproject.toml:')}")
            pyproject = env_info.pyproject_info
            print(f"   {self.ui.dim('Nom du projet:')} {pyproject.name}")
            if hasattr(pyproject, 'version'):
                print(f"   {self.ui.dim('Version:')} {pyproject.version}")
            if hasattr(pyproject, 'description'):
                print(f"   {self.ui.dim('Description:')} {pyproject.description}")
        
        # Santé de l'environnement
        if hasattr(env_info, 'health') and env_info.health:
            health = env_info.health
            print(f"\n{self.ui.highlight('🔍 État de santé:')}")
            score = getattr(health, 'health_score', 0)
            status = "✅ Excellent" if score >= 0.9 else "⚠️ Attention" if score >= 0.7 else "❌ Problème"
            print(f"   {self.ui.dim('Score général:')} {status} ({score:.1%})")
    
    def _print_health_check(self, env_name: str, health_info: Any):
        """Affiche les résultats d'un check de santé."""
        print(f"\n{self.ui.highlight(f'🔍 Vérification de {env_name}:')}")
        
        checks = [
            ("Environnement existe", getattr(health_info, 'exists', False)),
            ("Python disponible", getattr(health_info, 'python_available', False)),
            ("pip disponible", getattr(health_info, 'pip_available', False)),
            ("Script d'activation", getattr(health_info, 'activation_script_exists', False)),
            ("Backend disponible", getattr(health_info, 'backend_available', False)),
            ("Dépendances synchronisées", getattr(health_info, 'dependencies_synchronized', True)),
        ]
        
        for check_name, status in checks:
            symbol = "✅" if status else "❌"
            print(f"   {symbol} {check_name}")
        
        # Score global
        score = getattr(health_info, 'health_score', 0)
        print(f"\n   {self.ui.highlight('Score global:')} {score:.1%}")
        
        # Problèmes de sécurité
        security_issues = getattr(health_info, 'security_issues', [])
        if security_issues:
            print(f"\n{self.ui.warning('Problèmes de sécurité détectés:')}")
            for issue in security_issues:
                print(f"   ⚠️  {issue}")
    
    def _print_available_backends(self):
        """Affiche les backends disponibles."""
        print(f"\n{self.ui.highlight('🔧 Backends disponibles:')}")
        
        backends_info = [
            ("pip", "Backend standard Python", True),
            ("uv", "Backend ultra-rapide (10x plus rapide)", check_dependencies().get('uv', False)),
            ("poetry", "Gestionnaire de dépendances moderne", check_dependencies().get('poetry', False)),
            ("pdm", "Gestionnaire moderne basé sur PEP 582", check_dependencies().get('pdm', False)),
        ]
        
        for name, description, available in backends_info:
            status = "✅" if available else "❌"
            print(f"   {status} {self.ui.highlight(name)}: {description}")
            if not available and name != "pip":
                print(f"      {self.ui.dim(f'Installation: pip install {name}')}")
    
    def _print_backend_info(self, backend_name: str):
        """Affiche les informations d'un backend spécifique."""
        backend_details = {
            'pip': {
                'description': 'Backend standard Python',
                'features': ['Installation de packages', 'Gestion des dépendances', 'Freeze/Export'],
                'performance': 'Standard',
                'available': True,
            },
            'uv': {
                'description': 'Backend ultra-rapide développé en Rust',
                'features': ['Installation ultra-rapide', 'Résolution optimisée', 'Cache avancé', 'Lock files'],
                'performance': '10x plus rapide que pip',
                'available': check_dependencies().get('uv', False),
            },
            'poetry': {
                'description': 'Gestionnaire de dépendances et packaging',
                'features': ['Gestion pyproject.toml', 'Lock files', 'Publication', 'Environnements virtuels'],
                'performance': 'Optimisé pour les projets',
                'available': check_dependencies().get('poetry', False),
            },
            'pdm': {
                'description': 'Gestionnaire moderne basé sur les standards PEP',
                'features': ['Support PEP 582', 'Lock files', 'Scripts', 'Plugins'],
                'performance': 'Rapide et moderne',
                'available': check_dependencies().get('pdm', False),
            },
        }
        
        if backend_name not in backend_details:
            self.print_error(f"Backend '{backend_name}' inconnu")
            return
        
        info = backend_details[backend_name]
        status = "✅ Disponible" if info['available'] else "❌ Non installé"
        
        print(f"\n{self.ui.highlight(f'🔧 Backend: {backend_name}')}")
        print(f"   {self.ui.dim('État:')} {status}")
        print(f"   {self.ui.dim('Description:')} {info['description']}")
        print(f"   {self.ui.dim('Performance:')} {info['performance']}")
        print(f"   {self.ui.dim('Fonctionnalités:')}")
        for feature in info['features']:
            print(f"     • {feature}")
        
        if not info['available'] and backend_name != 'pip':
            print(f"\n   {self.ui.info(f'Installation: pip install {backend_name}')}")
    
    def _print_config_summary(self, config: Dict[str, Any]):
        """Affiche un résumé de la configuration."""
        print(f"\n{self.ui.highlight('⚙️ Configuration GestVenv:')}")
        
        # Paramètres principaux
        print(f"   {self.ui.dim('Version:')} {config.get('config_version', 'Inconnue')}")
        print(f"   {self.ui.dim('Python par défaut:')} {config.get('default_python', 'python3')}")
        print(f"   {self.ui.dim('Backend préféré:')} {config.get('preferred_backend', 'pip')}")
        print(f"   {self.ui.dim('Environnement actif:')} {config.get('active_env', 'Aucun')}")
        
        # Environnements
        environments = config.get('environments', {})
        print(f"   {self.ui.dim('Environnements:')} {len(environments)}")
        
        # Cache
        cache_settings = config.get('cache_settings', {})
        cache_enabled = cache_settings.get('enabled', False)
        print(f"   {self.ui.dim('Cache:')} {'Activé' if cache_enabled else 'Désactivé'}")
    
    def _env_to_dict(self, env_info: Any) -> Dict[str, Any]:
        """Convertit un EnvironmentInfo en dictionnaire pour JSON."""
        return {
            'name': env_info.name,
            'path': str(env_info.path),
            'python_version': env_info.python_version,
            'is_active': getattr(env_info, 'is_active', False),
            'created_at': getattr(env_info, 'created_at', None),
            'packages': [
                {'name': pkg.name, 'version': pkg.version} if hasattr(pkg, 'version') else str(pkg)
                for pkg in getattr(env_info, 'packages', [])
            ],
            'backend_type': getattr(env_info, 'backend_type', 'pip').value if hasattr(getattr(env_info, 'backend_type', None), 'value') else 'pip',
            'health_score': getattr(getattr(env_info, 'health', None), 'health_score', None),
        }
    
    # ===== CONFIGURATION ARGPARSE =====
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Crée le parser principal avec toutes les commandes."""
        parser = argparse.ArgumentParser(
            prog='gestvenv',
            description='GestVenv v1.1 - Gestionnaire d\'environnements virtuels Python moderne',
            epilog='Voir "gestvenv <command> --help" pour l\'aide spécifique à chaque commande.',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Options globales
        parser.add_argument(
            '--version', action='version', version=f'GestVenv v{__version__}'
        )
        parser.add_argument(
            '--verbose', '-v', action='store_true',
            help='Mode verbeux avec logs détaillés'
        )
        parser.add_argument(
            '--quiet', '-q', action='store_true',
            help='Mode silencieux (erreurs uniquement)'
        )
        parser.add_argument(
            '--no-color', action='store_true',
            help='Désactive les couleurs'
        )
        parser.add_argument(
            '--config', type=str,
            help='Fichier de configuration personnalisé'
        )
        parser.add_argument(
            '--offline', action='store_true',
            help='Mode hors ligne (utilise le cache)'
        )
        parser.add_argument(
            '--backend', choices=['pip', 'uv', 'poetry', 'pdm'],
            help='Force un backend spécifique'
        )
        
        # Sous-commandes
        subparsers = parser.add_subparsers(
            dest='command', 
            title='Commandes disponibles',
            description='Liste des commandes GestVenv',
            help='Commande à exécuter'
        )
        
        # Commande: create
        create_parser = subparsers.add_parser(
            'create', help='Créer un nouvel environnement'
        )
        create_parser.add_argument('name', help='Nom de l\'environnement')
        create_parser.add_argument(
            '--python', '-p', default='python3',
            help='Version de Python (par défaut: python3)'
        )
        create_parser.add_argument(
            '--packages', help='Packages à installer (séparés par des virgules)'
        )
        create_parser.add_argument(
            '--path', help='Chemin personnalisé pour l\'environnement'
        )
        create_parser.add_argument(
            '--from-pyproject', help='Créer depuis un fichier pyproject.toml'
        )
        create_parser.add_argument(
            '--groups', help='Groupes de dépendances pyproject.toml (séparés par des virgules)'
        )
        create_parser.add_argument(
            '--offline', action='store_true', help='Mode hors ligne'
        )
        create_parser.add_argument(
            '--backend', choices=['pip', 'uv', 'poetry', 'pdm'],
            help='Backend à utiliser'
        )
        
        # Commande: list
        list_parser = subparsers.add_parser(
            'list', help='Lister les environnements'
        )
        list_parser.add_argument(
            '--verbose', '-v', action='store_true',
            help='Affichage détaillé'
        )
        list_parser.add_argument(
            '--filter', help='Filtrer par nom'
        )
        list_parser.add_argument(
            '--format', choices=['table', 'json'], default='table',
            help='Format de sortie'
        )
        
        # Commande: activate
        activate_parser = subparsers.add_parser(
            'activate', help='Activer un environnement'
        )
        activate_parser.add_argument('name', help='Nom de l\'environnement')
        
        # Commande: deactivate
        subparsers.add_parser(
            'deactivate', help='Désactiver l\'environnement actuel'
        )
        
        # Commande: delete
        delete_parser = subparsers.add_parser(
            'delete', help='Supprimer un environnement'
        )
        delete_parser.add_argument('name', help='Nom de l\'environnement')
        delete_parser.add_argument(
            '--force', '-f', action='store_true',
            help='Suppression sans confirmation'
        )
        
        # Commande: info
        info_parser = subparsers.add_parser(
            'info', help='Informations sur un environnement'
        )
        info_parser.add_argument('name', help='Nom de l\'environnement')
        info_parser.add_argument(
            '--format', choices=['text', 'json'], default='text',
            help='Format de sortie'
        )
        
        # Commande: install
        install_parser = subparsers.add_parser(
            'install', help='Installer des packages'
        )
        install_parser.add_argument('env_name', help='Nom de l\'environnement')
        install_parser.add_argument('packages', nargs='+', help='Packages à installer')
        install_parser.add_argument(
            '--upgrade', '-U', action='store_true',
            help='Mettre à jour les packages existants'
        )
        install_parser.add_argument(
            '--dev', action='store_true',
            help='Installer les dépendances de développement'
        )
        install_parser.add_argument(
            '--offline', action='store_true', help='Mode hors ligne'
        )
        install_parser.add_argument(
            '--backend', choices=['pip', 'uv', 'poetry', 'pdm'],
            help='Backend à utiliser'
        )
        
        # Commande: sync
        sync_parser = subparsers.add_parser(
            'sync', help='Synchroniser avec pyproject.toml'
        )
        sync_parser.add_argument('env_name', help='Nom de l\'environnement')
        sync_parser.add_argument(
            '--groups', help='Groupes de dépendances (séparés par des virgules)'
        )
        sync_parser.add_argument(
            '--strict', action='store_true',
            help='Mode strict (supprime les packages non listés)'
        )
        sync_parser.add_argument(
            '--update-lock', action='store_true',
            help='Mettre à jour le fichier de verrouillage'
        )
        
        # Commande: config
        config_parser = subparsers.add_parser(
            'config', help='Gérer la configuration'
        )
        config_parser.add_argument(
            '--show', action='store_true',
            help='Afficher la configuration actuelle'
        )
        config_parser.add_argument(
            '--set-python', help='Définir la version Python par défaut'
        )
        config_parser.add_argument(
            '--set-backend', choices=['pip', 'uv', 'poetry', 'pdm'],
            help='Définir le backend par défaut'
        )
        config_parser.add_argument(
            '--format', choices=['text', 'json'], default='text',
            help='Format de sortie'
        )
        
        # Commande: backend
        backend_parser = subparsers.add_parser(
            'backend', help='Gérer les backends'
        )
        backend_parser.add_argument(
            'action', choices=['list', 'set', 'info'],
            help='Action à effectuer'
        )
        backend_parser.add_argument(
            'backend', nargs='?', choices=['pip', 'uv', 'poetry', 'pdm'],
            help='Backend (pour set/info)'
        )
        
        # Commande: check
        check_parser = subparsers.add_parser(
            'check', help='Vérifier la santé d\'un environnement'
        )
        check_parser.add_argument('env_name', help='Nom de l\'environnement')
        check_parser.add_argument(
            '--format', choices=['text', 'json'], default='text',
            help='Format de sortie'
        )
        
        # Commande: migrate
        migrate_parser = subparsers.add_parser(
            'migrate', help='Migration depuis v1.0'
        )
        migrate_parser.add_argument(
            '--analyze', action='store_true',
            help='Analyser les configurations existantes'
        )
        migrate_parser.add_argument(
            '--config-path', help='Chemin vers l\'ancienne configuration'
        )
        
        # Commande: version
        version_parser = subparsers.add_parser(
            'version', help='Afficher les informations de version'
        )
        version_parser.add_argument(
            '--verbose', '-v', action='store_true',
            help='Informations détaillées'
        )
        
        return parser
    
    # ===== MÉTHODE PRINCIPALE =====
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Point d'entrée principal du CLI.
        
        Args:
            args: Arguments en ligne de commande (None = sys.argv)
            
        Returns:
            int: Code de retour (0 = succès, autre = erreur)
        """
        try:
            parser = self.create_parser()
            parsed_args = parser.parse_args(args)
            
            # Configuration UI et logging
            if parsed_args.no_color:
                self.ui = UIFormatter(use_colors=False)
            
            self.setup_logging(
                verbose=getattr(parsed_args, 'verbose', False),
                quiet=getattr(parsed_args, 'quiet', False)
            )
            
            # Configuration globale
            self.offline_mode = getattr(parsed_args, 'offline', False)
            self.preferred_backend = getattr(parsed_args, 'backend', None)
            
            # Initialisation des gestionnaires
            config_path = getattr(parsed_args, 'config', None)
            self.initialize_managers(config_path)
            
            # Dispatch des commandes
            command_map = {
                'create': self.cmd_create,
                'list': self.cmd_list,
                'activate': self.cmd_activate,
                'deactivate': self.cmd_deactivate,
                'delete': self.cmd_delete,
                'info': self.cmd_info,
                'install': self.cmd_install,
                'sync': self.cmd_sync,
                'config': self.cmd_config,
                'backend': self.cmd_backend,
                'check': self.cmd_check,
                'migrate': self.cmd_migrate,
                'version': self.cmd_version,
            }
            
            if not parsed_args.command:
                parser.print_help()
                return 1
            
            if parsed_args.command not in command_map:
                self.print_error(f"Commande inconnue: {parsed_args.command}")
                return 1
            
            # Exécution de la commande
            return command_map[parsed_args.command](parsed_args)
            
        except KeyboardInterrupt:
            self.print_error("Opération interrompue par l'utilisateur")
            return 130
        except Exception as e:
            if self.verbose:
                import traceback
                traceback.print_exc()
            else:
                self.print_error(f"Erreur inattendue: {e}")
            return 1

# ===== POINT D'ENTRÉE =====

def main() -> int:
    """Point d'entrée principal du script CLI."""
    cli = GestVenvCLI()
    return cli.run()

if __name__ == '__main__':
    sys.exit(main())

# ===== NOTES DÉVELOPPEURS =====
"""
ARCHITECTURE CLI v1.1:

1. GESTION DES COMMANDES:
   - Parser modulaire avec argparse
   - Dispatch centralisé via dictionnaire
   - Gestion d'erreurs robuste avec codes de retour

2. INTERFACE UTILISATEUR:
   - Support couleurs avec désactivation possible
   - Formatage JSON/texte selon contexte
   - Messages d'erreur informatifs et contextuels

3. INTÉGRATION SERVICES:
   - Lazy loading des gestionnaires
   - Configuration globale partagée
   - Support backends multiples avec fallback

4. COMPATIBILITÉ:
   - Support Python 3.9+
   - Gestion des dépendances optionnelles
   - Migration transparente v1.0 → v1.1

5. EXTENSIBILITÉ:
   - Nouveau commandes via méthodes cmd_*
   - Formatage personnalisable
   - Plugin system préparé pour v1.2
"""