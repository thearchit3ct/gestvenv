"""
Interface en ligne de commande complète pour GestVenv v1.1
"""

import sys
import logging
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from gestvenv.core.environment_manager import EnvironmentManager
from gestvenv.core.models import ExportFormat, BackendType
from gestvenv.core.exceptions import GestVenvError
from gestvenv.backends.backend_manager import BackendManager
from gestvenv.services.diagnostic_service import DiagnosticService
from gestvenv.services.template_service import TemplateService
from gestvenv.services.migration_service import MigrationService
from gestvenv.services.cache_service import CacheService
from gestvenv.utils.toml_handler import TomlHandler
from gestvenv.utils.path_utils import PathUtils

# Import des commandes avancées
from gestvenv.cli.commands import diff_group, deps_group, security_group, python_group

# Version fixe pour GestVenv 2.0
__version__ = "2.0.0"

console = Console()

def setup_logging(verbose: bool) -> None:
    """Configure le logging selon le niveau de verbosité"""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def load_environment_variables() -> dict:
    """Charge les variables d'environnement GestVenv"""
    import os
    env_vars = {}
    
    # Variables d'environnement supportées
    gestvenv_vars = {
        'GESTVENV_BACKEND': 'preferred_backend',
        'GESTVENV_PYTHON_VERSION': 'default_python_version',
        'GESTVENV_CACHE_ENABLED': 'cache_enabled',
        'GESTVENV_CACHE_SIZE_MB': 'cache_size_mb',
        'GESTVENV_OFFLINE_MODE': 'offline_mode',
        'GESTVENV_AUTO_MIGRATE': 'auto_migrate',
        'GESTVENV_ENVIRONMENTS_PATH': 'environments_path',
        'GESTVENV_TEMPLATES_PATH': 'templates_path'
    }
    
    for env_var, config_key in gestvenv_vars.items():
        value = os.getenv(env_var)
        if value is not None:
            # Conversion de type automatique
            if config_key in ['cache_enabled', 'offline_mode', 'auto_migrate']:
                env_vars[config_key] = value.lower() in ['true', '1', 'yes', 'on']
            elif config_key in ['cache_size_mb']:
                try:
                    env_vars[config_key] = int(value)
                except ValueError:
                    pass
            else:
                env_vars[config_key] = value
    
    return env_vars

def check_critical_dependencies() -> List[str]:
    """Vérifie la disponibilité des dépendances critiques"""
    missing = []
    
    try:
        from gestvenv.core.environment_manager import EnvironmentManager
    except ImportError:
        missing.append("EnvironmentManager")
    
    try:
        from gestvenv.utils.toml_handler import TomlHandler
    except ImportError:
        missing.append("TomlHandler")
    
    try:
        from gestvenv.backends.uv_backend import UvBackend
    except ImportError:
        missing.append("UvBackend")
    
    return missing

@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="gestvenv")
@click.option('--verbose', '-v', is_flag=True, help='Mode verbeux')
@click.option('--offline', is_flag=True, help='Mode hors ligne')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, offline: bool) -> None:
    """🐍 GestVenv - Gestionnaire d'environnements virtuels Python moderne"""
    setup_logging(verbose)
    
    # Vérification des dépendances critiques
    missing_deps = check_critical_dependencies()
    if missing_deps and verbose:
        console.print(f"⚠️ Composants manquants: {', '.join(missing_deps)}", style="yellow")
    
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['offline'] = offline
    
    # Chargement des variables d'environnement
    env_vars = load_environment_variables()
    if env_vars and verbose:
        console.print(f"📋 Variables d'environnement chargées: {len(env_vars)}")
        for key, value in env_vars.items():
            console.print(f"  GESTVENV_{key.upper()}: {value}")
    
    # Appliquer le mode offline depuis les variables d'environnement
    if env_vars.get('offline_mode'):
        offline = True
        
    ctx.obj['env_manager'] = EnvironmentManager()
    
    # Appliquer les variables d'environnement à la configuration
    if env_vars:
        config = ctx.obj['env_manager'].config_manager.config
        for key, value in env_vars.items():
            if hasattr(config, key):
                setattr(config, key, value)
                if verbose:
                    console.print(f"🔧 Config {key}: {value}")
    
    if offline:
        ctx.obj['env_manager'].cache_service.set_offline_mode(True)
    
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            f"🐍 [bold green]GestVenv v{__version__}[/bold green]\n"
            f"Gestionnaire d'environnements virtuels Python moderne\n\n"
            f"Utilisez [bold cyan]gestvenv --help[/bold cyan] pour voir toutes les commandes",
            title="GestVenv"
        ))

# === COMMANDES ENVIRONNEMENTS ===

@cli.command()
@click.argument('name')
@click.option('--python', help='Version Python à utiliser')
@click.option('--backend', type=click.Choice(['pip', 'uv', 'auto']), default='auto')
@click.option('--template', help='Template à utiliser')
@click.option('--packages', help='Packages initiaux (séparés par des virgules)')
@click.option('--path', help='Chemin personnalisé pour l\'environnement')
@click.pass_context
def create(ctx: click.Context, name: str, python: Optional[str], backend: str, 
           template: Optional[str], packages: Optional[str], path: Optional[str]) -> None:
    """Créer un nouvel environnement virtuel"""
    env_manager = ctx.obj['env_manager']
    
    try:
        initial_packages = packages.split(',') if packages else None
        custom_path = Path(path) if path else None
        
        with console.status(f"[bold green]Création de l'environnement {name}..."):
            result = env_manager.create_environment(
                name=name,
                python_version=python,
                backend=backend if backend != 'auto' else None,
                initial_packages=initial_packages,
                custom_path=custom_path
            )
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{name}[/bold green] créé avec succès!")
            if result.environment:
                console.print(f"📁 Chemin: {result.environment.path}")
                console.print(f"🐍 Python: {result.environment.python_version}")
                console.print(f"🔧 Backend: {result.environment.backend_type.value}")
                
                if result.environment.packages:
                    console.print(f"📦 Packages installés: {len(result.environment.packages)}")
            
            for warning in result.warnings:
                console.print(f"⚠️ {warning}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur lors de la création: {e}")
        sys.exit(1)

@cli.command()
@click.argument('template_name')
@click.argument('env_name')
@click.option('--author', help='Nom de l\'auteur')
@click.option('--email', help='Email de l\'auteur')
@click.option('--version', default='0.1.0', help='Version initiale')
@click.option('--python', help='Version Python à utiliser')
@click.option('--backend', type=click.Choice(['pip', 'uv', 'auto']), default='auto')
@click.option('--output', help='Répertoire de sortie pour le projet')
@click.pass_context
def create_from_template(ctx: click.Context, template_name: str, env_name: str, 
                        author: Optional[str], email: Optional[str], version: str,
                        python: Optional[str], backend: str, output: Optional[str]) -> None:
    """Créer un environnement depuis un template"""
    env_manager = ctx.obj['env_manager']
    
    try:
        # Préparation des paramètres
        template_params = {
            'project_name': env_name,
            'package_name': env_name.lower().replace('-', '_'),
            'version': version
        }
        
        if author:
            template_params['author'] = author
        if email:
            template_params['email'] = email
        if python:
            template_params['python_version'] = python
        
        # Chemin de sortie pour le projet
        output_path = Path(output) if output else Path.cwd() / env_name
        
        with console.status(f"[bold green]Création depuis le template {template_name}..."):
            result = env_manager.create_from_template(
                template_name=template_name,
                env_name=env_name,
                output_path=output_path,
                template_params=template_params,
                backend=backend if backend != 'auto' else None,
                python_version=python
            )
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{env_name}[/bold green] créé depuis le template [bold blue]{template_name}[/bold blue]!")
            console.print(f"📁 Projet: {output_path}")
            console.print(f"📁 Environnement: {result.environment.path}")
            console.print(f"🐍 Python: {result.environment.python_version}")
            console.print(f"📦 Packages installés: {len(result.environment.packages)}")
            
            for warning in result.warnings:
                console.print(f"⚠️ {warning}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
            
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.argument('name', required=False)
@click.option('--backend', type=click.Choice(['pip', 'uv', 'auto']), default='auto')
@click.option('--groups', help='Groupes de dépendances (séparés par des virgules)')
@click.option('--python', help='Version Python à utiliser')
@click.pass_context
def create_from_pyproject(ctx: click.Context, file: str, name: Optional[str], 
                         backend: str, groups: Optional[str], python: Optional[str]) -> None:
    """Créer un environnement depuis pyproject.toml"""
    env_manager = ctx.obj['env_manager']
    
    try:
        pyproject_path = Path(file)
        
        # Validation du fichier pyproject.toml
        if not pyproject_path.name == 'pyproject.toml':
            console.print("❌ Le fichier doit être un pyproject.toml")
            sys.exit(1)
        
        # Lecture et validation du contenu
        try:
            toml_data = TomlHandler.load(pyproject_path)
            if 'project' not in toml_data:
                console.print("❌ Section [project] manquante dans pyproject.toml")
                sys.exit(1)
        except Exception as e:
            console.print(f"❌ Erreur lecture pyproject.toml: {e}")
            sys.exit(1)
        
        groups_list = groups.split(',') if groups else None
        
        with console.status(f"[bold green]Création depuis {file}..."):
            result = env_manager.create_from_pyproject(
                pyproject_path=pyproject_path,
                env_name=name,
                groups=groups_list,
                backend=backend if backend != 'auto' else None,
                python_version=python
            )
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{result.environment.name}[/bold green] créé depuis pyproject.toml!")
            console.print(f"📁 Chemin: {result.environment.path}")
            console.print(f"📦 Packages installés: {len(result.environment.packages)}")
            
            if result.environment.pyproject_info:
                console.print(f"📋 Projet: {result.environment.pyproject_info.name} v{result.environment.pyproject_info.version}")
            
            for warning in result.warnings:
                console.print(f"⚠️ {warning}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('conda_file', type=click.Path(exists=True))
@click.argument('name', required=False)
@click.option('--backend', type=click.Choice(['pip', 'uv', 'auto']), default='auto')
@click.option('--python', help='Version Python à utiliser')
@click.option('--skip-conda-only', is_flag=True, help='Ignorer les packages conda uniquement')
@click.pass_context
def create_from_conda(ctx: click.Context, conda_file: str, name: Optional[str], 
                     backend: str, python: Optional[str], skip_conda_only: bool) -> None:
    """Créer un environnement depuis environment.yml (conda)"""
    env_manager = ctx.obj['env_manager']
    
    try:
        conda_path = Path(conda_file)
        
        # Validation du fichier conda
        if not conda_path.name.endswith(('.yml', '.yaml')):
            console.print("❌ Le fichier doit être un environment.yml")
            sys.exit(1)
        
        with console.status(f"[bold green]Création depuis {conda_file}..."):
            result = env_manager.create_from_conda(
                conda_file=conda_path,
                env_name=name,
                backend=backend if backend != 'auto' else None,
                python_version=python,
                skip_conda_only=skip_conda_only
            )
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{result.environment.name}[/bold green] créé depuis conda!")
            console.print(f"📁 Chemin: {result.environment.path}")
            console.print(f"🐍 Python: {result.environment.python_version}")
            console.print(f"📦 Packages installés: {len(result.environment.packages)}")
            
            # Packages ignorés si conda-only
            if skip_conda_only and result.warnings:
                console.print(f"⚠️ Packages conda ignorés: {len([w for w in result.warnings if 'conda' in w])}")
            
            for warning in result.warnings:
                console.print(f"⚠️ {warning}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
            
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command(name='list')
@click.option('--active-only', is_flag=True, help='Afficher seulement les environnements actifs')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
@click.option('--backend', help='Filtrer par backend')
@click.option('--health', help='Filtrer par état de santé')
@click.option('--sort', type=click.Choice(['name', 'created', 'used', 'size']), default='used')
@click.pass_context
def list_environments(ctx: click.Context, active_only: bool, output_format: str,
                      backend: Optional[str], health: Optional[str], sort: str) -> None:
    """Lister tous les environnements"""
    env_manager = ctx.obj['env_manager']
    
    try:
        filters = {}
        if active_only:
            filters['active_only'] = True
        if backend:
            filters['backend'] = backend
        if health:
            filters['health'] = health
            
        environments = env_manager.list_environments(**filters)
        
        # Tri
        if sort == 'name':
            environments.sort(key=lambda x: x.name)
        elif sort == 'created':
            environments.sort(key=lambda x: x.created_at or x.last_used, reverse=True)
        elif sort == 'size':
            environments.sort(key=lambda x: len(x.packages), reverse=True)
        # sort == 'used' est déjà le tri par défaut
        
        if output_format == 'json':
            import json
            data = [env.to_dict() for env in environments]
            console.print(json.dumps(data, indent=2, default=str))
            return
        
        if not environments:
            console.print("📭 Aucun environnement trouvé")
            return
        
        table = Table(title="🐍 Environnements GestVenv")
        table.add_column("Nom", style="cyan", no_wrap=True)
        table.add_column("Python", style="green")
        table.add_column("Backend", style="yellow")
        table.add_column("Packages", justify="right", style="magenta")
        table.add_column("Statut", style="red")
        table.add_column("Santé", style="yellow")
        table.add_column("Taille", justify="right", style="dim")
        table.add_column("Dernière utilisation", style="dim")
        
        for env in environments:
            status = "🟢 Actif" if env.is_active else "⚪ Inactif"
            last_used = env.last_used.strftime("%d/%m %H:%M") if env.last_used else "Jamais"
            
            # État de santé
            health_icons = {
                'healthy': '✅ Sain',
                'needs_update': '🔄 MAJ',
                'has_warnings': '⚠️ Attention',
                'has_errors': '❌ Erreurs',
                'corrupted': '💥 Corrompu',
                'unknown': '❓ Inconnu'
            }
            health_status = health_icons.get(env.health.value if env.health else 'unknown', '❓ Inconnu')
            
            # Calcul taille avec PathUtils
            size_mb = PathUtils.get_size_mb(env.path) if env.path.exists() else 0
            size_str = f"{size_mb:.1f}MB" if size_mb > 0 else "-"
            
            table.add_row(
                env.name,
                env.python_version or "inconnu",
                env.backend_type.value if env.backend_type else "pip",
                str(len(env.packages)),
                status,
                health_status,
                size_str,
                last_used
            )
        
        console.print(table)
        console.print(f"\n📊 Total: {len(environments)} environnements")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name')
@click.pass_context
def activate(ctx: click.Context, name: str) -> None:
    """Activer un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        result = env_manager.activate_environment(name)
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{name}[/bold green] activé!")
            console.print(f"🔧 Commande: [bold]{result.activation_command}[/bold]")
            
            # Affichage des variables d'environnement
            if result.environment_variables:
                console.print("\n📋 Variables d'environnement configurées:")
                for key, value in result.environment_variables.items():
                    if key == 'PATH':
                        # Affichage simplifié du PATH
                        console.print(f"  {key}={value[:50]}...")
                    else:
                        console.print(f"  {key}={value}")
                        
            console.print("\n💡 Pour utiliser cet environnement dans votre shell:")
            console.print(f"   {result.activation_command}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.pass_context
def deactivate(ctx: click.Context) -> None:
    """Désactiver l'environnement actuel"""
    env_manager = ctx.obj['env_manager']
    
    try:
        success = env_manager.deactivate_environment()
        
        if success:
            console.print("✅ Environnement désactivé")
        else:
            console.print("⚠️ Aucun environnement actif")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Forcer la suppression même si actif')
@click.option('--backup', is_flag=True, help='Créer une sauvegarde avant suppression')
@click.pass_context
def delete(ctx: click.Context, name: str, force: bool, backup: bool) -> None:
    """Supprimer un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        # Vérification existence
        env_info = env_manager.get_environment_info(name)
        if not env_info:
            console.print(f"❌ Environnement '{name}' introuvable")
            sys.exit(1)
        
        # Sauvegarde optionnelle
        if backup:
            backup_result = env_manager.export_environment(name, ExportFormat.JSON)
            if backup_result.success:
                console.print(f"💾 Sauvegarde créée: {backup_result.output_path}")
        
        if not force:
            size_mb = PathUtils.get_size_mb(env_info.path)
            console.print(f"📊 Taille: {size_mb:.1f}MB, {len(env_info.packages)} packages")
            
            if not click.confirm(f"Êtes-vous sûr de vouloir supprimer l'environnement '{name}' ?"):
                console.print("❌ Suppression annulée")
                return
        
        with console.status(f"[bold red]Suppression de {name}..."):
            success = env_manager.delete_environment(name, force=force)
        
        if success:
            console.print(f"✅ Environnement [bold red]{name}[/bold red] supprimé")
        else:
            console.print(f"❌ Erreur lors de la suppression")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name')
@click.pass_context
def info(ctx: click.Context, name: str) -> None:
    """Afficher les informations détaillées d'un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(name)
        
        if not env_info:
            console.print(f"❌ Environnement '{name}' introuvable")
            sys.exit(1)
        
        # Informations générales
        table = Table(title=f"📋 Environnement '{name}'")
        table.add_column("Propriété", style="cyan")
        table.add_column("Valeur", style="green")
        
        table.add_row("Nom", env_info.name)
        table.add_row("Chemin", str(env_info.path))
        table.add_row("Python", env_info.python_version or "Inconnu")
        table.add_row("Backend", env_info.backend_type.value if env_info.backend_type else "pip")
        table.add_row("Statut", "🟢 Actif" if env_info.is_active else "⚪ Inactif")
        table.add_row("Santé", env_info.health.value if env_info.health else "Inconnu")
        
        # Calcul taille avec PathUtils
        if env_info.path.exists():
            size_mb = PathUtils.get_size_mb(env_info.path)
            table.add_row("Taille", f"{size_mb:.1f} MB")
        
        table.add_row("Créé le", env_info.created_at.strftime("%d/%m/%Y %H:%M") if env_info.created_at else "Inconnu")
        table.add_row("Modifié le", env_info.updated_at.strftime("%d/%m/%Y %H:%M") if env_info.updated_at else "Inconnu")
        table.add_row("Dernière utilisation", env_info.last_used.strftime("%d/%m/%Y %H:%M") if env_info.last_used else "Jamais")
        
        if env_info.pyproject_info:
            table.add_row("pyproject.toml", f"✅ {env_info.pyproject_info.name} v{env_info.pyproject_info.version}")
        
        if env_info.lock_file_path:
            table.add_row("Lock file", str(env_info.lock_file_path))
        
        console.print(table)
        
        # Packages installés
        if env_info.packages:
            packages_table = Table(title=f"📦 Packages ({len(env_info.packages)})")
            packages_table.add_column("Package", style="cyan")
            packages_table.add_column("Version", style="green")
            packages_table.add_column("Source", style="yellow")
            
            for package in sorted(env_info.packages, key=lambda p: p.name):
                packages_table.add_row(
                    package.name, 
                    package.version or "?",
                    package.source or "pypi"
                )
            
            console.print(packages_table)
        
        # Groupes de dépendances
        if env_info.dependency_groups:
            console.print(f"\n🔗 Groupes de dépendances: {', '.join(env_info.dependency_groups.keys())}")
        
        # Statistiques utilisation
        if env_info.path.exists():
            pyproject_files = PathUtils.find_files_by_pattern(env_info.path.parent, "pyproject.toml")
            if pyproject_files:
                console.print(f"\n📄 Fichiers pyproject.toml trouvés: {len(pyproject_files)}")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name')
@click.option('--groups', help='Groupes à synchroniser (séparés par des virgules)')
@click.option('--clean', is_flag=True, help='Nettoyer les packages non listés')
@click.option('--upgrade', is_flag=True, help='Mettre à jour les packages existants')
@click.pass_context
def sync(ctx: click.Context, name: str, groups: Optional[str], clean: bool, upgrade: bool) -> None:
    """Synchroniser un environnement avec pyproject.toml"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(name)
        if not env_info:
            console.print(f"❌ Environnement '{name}' introuvable")
            sys.exit(1)
        
        if not env_info.pyproject_info:
            console.print("❌ Aucun pyproject.toml associé à cet environnement")
            console.print("💡 Créez l'environnement avec create-from-pyproject")
            sys.exit(1)
        
        with console.status(f"[bold blue]Synchronisation de {name}..."):
            result = env_manager.sync_environment(name)
        
        if result.success:
            console.print(f"✅ Synchronisation de [bold green]{name}[/bold green] réussie!")
            
            if result.packages_added:
                console.print(f"➕ Packages ajoutés: {', '.join(result.packages_added)}")
            if result.packages_removed:
                console.print(f"➖ Packages supprimés: {', '.join(result.packages_removed)}")
            if result.packages_updated:
                console.print(f"🔄 Packages mis à jour: {', '.join(result.packages_updated)}")
            
            for warning in result.warnings:
                console.print(f"⚠️ {warning}")
                
            console.print(f"⏱️ Temps d'exécution: {result.execution_time:.2f}s")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('source')
@click.argument('target')
@click.option('--python', help='Version Python différente pour le clone')
@click.option('--backend', type=click.Choice(['pip', 'uv']), help='Backend différent pour le clone')
@click.pass_context
def clone(ctx: click.Context, source: str, target: str, python: Optional[str], backend: Optional[str]) -> None:
    """Cloner un environnement existant"""
    env_manager = ctx.obj['env_manager']
    
    try:
        with console.status(f"[bold blue]Clonage de {source} vers {target}..."):
            result = env_manager.clone_environment(source, target)
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{target}[/bold green] cloné depuis [bold blue]{source}[/bold blue]!")
            console.print(f"📦 Packages clonés: {len(result.environment.packages)}")
            console.print(f"📁 Chemin: {result.environment.path}")
            
            for warning in result.warnings:
                console.print(f"⚠️ {warning}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES PACKAGES ===

@cli.command()
@click.option('--env', help='Environnement à analyser')
@click.option('--group', help='Filtrer par groupe de dépendances')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
@click.option('--outdated', is_flag=True, help='Afficher seulement les packages obsolètes')
@click.pass_context
def list_packages(ctx: click.Context, env: Optional[str], group: Optional[str], 
                 format: str, outdated: bool) -> None:
    """Lister les packages d'un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        # Résolution environnement
        if not env:
            active_envs = [e for e in env_manager.list_environments() if e.is_active]
            if len(active_envs) == 1:
                target_env = active_envs[0]
            else:
                console.print("❌ Spécifiez l'environnement avec --env")
                sys.exit(1)
        else:
            target_env = env_manager.get_environment_info(env)
            if not target_env:
                console.print(f"❌ Environnement '{env}' introuvable")
                sys.exit(1)
        
        packages = target_env.packages
        
        # Filtrage par groupe
        if group:
            if group not in target_env.dependency_groups:
                console.print(f"❌ Groupe '{group}' introuvable")
                console.print(f"💡 Groupes disponibles: {', '.join(target_env.dependency_groups.keys())}")
                sys.exit(1)
            
            group_packages = set(target_env.dependency_groups[group])
            packages = [pkg for pkg in packages if pkg.name in group_packages]
        
        # Filtrage obsolètes (simulé pour l'exemple)
        if outdated:
            packages = [pkg for pkg in packages if pkg.is_development_package()]
        
        if format == 'json':
            import json
            data = [pkg.__dict__ for pkg in packages]
            console.print(json.dumps(data, indent=2, default=str))
            return
        
        if not packages:
            console.print("📭 Aucun package trouvé")
            return
        
        table = Table(title=f"📦 Packages - {target_env.name}")
        table.add_column("Package", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Source", style="yellow")
        table.add_column("Type", style="magenta")
        table.add_column("Installé le", style="dim")
        
        for pkg in sorted(packages, key=lambda p: p.name):
            package_type = "Éditable" if pkg.is_editable else "Standard"
            if pkg.is_development_package():
                package_type = "Développement"
            
            install_date = pkg.installed_at.strftime("%d/%m") if pkg.installed_at else "-"
            
            table.add_row(
                pkg.name,
                pkg.version,
                pkg.source,
                package_type,
                install_date
            )
        
        console.print(table)
        console.print(f"\n📊 Total: {len(packages)} packages")
        
        if group:
            console.print(f"🔗 Groupe: {group}")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('packages', nargs=-1, required=True)
@click.option('--env', help='Environnement cible')
@click.option('--group', help='Installer dans un groupe de dépendances')
@click.option('--backend', type=click.Choice(['pip', 'uv']), help='Backend à utiliser')
@click.option('--editable', '-e', is_flag=True, help='Installation en mode éditable')
@click.option('--upgrade', is_flag=True, help='Mettre à jour si déjà installé')
@click.pass_context
def install(ctx: click.Context, packages: tuple, env: Optional[str],
           group: Optional[str], backend: Optional[str], editable: bool, upgrade: bool) -> None:
    """Installer des packages"""
    env_manager = ctx.obj['env_manager']

    try:
        # Résolution environnement
        if not env:
            # Utiliser l'environnement actif ou demander
            active_envs = [e for e in env_manager.list_environments() if e.is_active]
            if len(active_envs) == 1:
                target_env = active_envs[0]
            elif len(active_envs) > 1:
                console.print("❌ Plusieurs environnements actifs. Spécifiez --env")
                sys.exit(1)
            else:
                console.print("❌ Aucun environnement actif. Spécifiez --env")
                sys.exit(1)
        else:
            target_env = env_manager.get_environment_info(env)
            if not target_env:
                console.print(f"❌ Environnement '{env}' introuvable")
                sys.exit(1)

        package_list = list(packages)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Installation dans {target_env.name}...", total=len(package_list))
            
            success_count = 0
            failed_packages = []
            
            for package in package_list:
                progress.update(task, description=f"Installation de {package}...")
                
                try:
                    result = env_manager.package_service.install_package(
                        target_env, package, 
                        group=group, 
                        backend=backend,
                        editable=editable,
                        upgrade=upgrade
                    )
                    
                    if result.success:
                        success_count += 1
                        progress.console.print(f"✅ {package} installé")
                    else:
                        failed_packages.append(package)
                        progress.console.print(f"❌ Échec {package}: {result.message}")
                except Exception as e:
                    failed_packages.append(package)
                    progress.console.print(f"❌ Erreur {package}: {e}")
                
                progress.advance(task)
        
        # Résumé
        console.print(f"\n📊 Résumé: {success_count}/{len(package_list)} packages installés")
        if failed_packages:
            console.print(f"❌ Échecs: {', '.join(failed_packages)}")
        
        # Mise à jour des métadonnées environnement
        if success_count > 0:
            target_env.updated_at = time.time()
            
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('packages', nargs=-1, required=True)
@click.option('--env', help='Environnement cible')
@click.option('--yes', is_flag=True, help='Confirmer automatiquement')
@click.pass_context
def uninstall(ctx: click.Context, packages: tuple, env: Optional[str], yes: bool) -> None:
    """Désinstaller des packages"""
    env_manager = ctx.obj['env_manager']
    
    try:
        # Résolution environnement (même logique que install)
        if not env:
            active_envs = [e for e in env_manager.list_environments() if e.is_active]
            if len(active_envs) == 1:
                target_env = active_envs[0]
            else:
                console.print("❌ Spécifiez l'environnement avec --env")
                sys.exit(1)
        else:
            target_env = env_manager.get_environment_info(env)
            if not target_env:
                console.print(f"❌ Environnement '{env}' introuvable")
                sys.exit(1)
        
        package_list = list(packages)
        
        # Confirmation
        if not yes:
            console.print(f"📦 Packages à désinstaller de '{target_env.name}': {', '.join(package_list)}")
            if not click.confirm("Continuer ?"):
                console.print("❌ Désinstallation annulée")
                return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Désinstallation dans {target_env.name}...", total=len(package_list))
            
            success_count = 0
            failed_packages = []
            
            for package in package_list:
                progress.update(task, description=f"Désinstallation de {package}...")
                
                try:
                    result = env_manager.package_service.uninstall_package(target_env, package)
                    
                    if result.success:
                        success_count += 1
                        progress.console.print(f"✅ {package} désinstallé")
                    else:
                        failed_packages.append(package)
                        progress.console.print(f"❌ Échec {package}: {result.message}")
                except Exception as e:
                    failed_packages.append(package)
                    progress.console.print(f"❌ Erreur {package}: {e}")
                
                progress.advance(task)
        
        console.print(f"\n📊 Résumé: {success_count}/{len(package_list)} packages désinstallés")
        if failed_packages:
            console.print(f"❌ Échecs: {', '.join(failed_packages)}")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--env', help='Environnement à mettre à jour')
@click.option('--all', 'update_all', is_flag=True, help='Mettre à jour tous les packages')
@click.option('--dry-run', is_flag=True, help='Simulation sans installation')
@click.argument('packages', nargs=-1)
@click.pass_context
def update(ctx: click.Context, env: Optional[str], update_all: bool, dry_run: bool, packages: tuple) -> None:
    """Mettre à jour des packages"""
    env_manager = ctx.obj['env_manager']
    
    try:
        if not env:
            active_envs = [e for e in env_manager.list_environments() if e.is_active]
            if len(active_envs) == 1:
                target_env = active_envs[0]
            else:
                console.print("❌ Spécifiez l'environnement avec --env")
                sys.exit(1)
        else:
            target_env = env_manager.get_environment_info(env)
            if not target_env:
                console.print(f"❌ Environnement '{env}' introuvable")
                sys.exit(1)
        
        if dry_run:
            console.print(f"🔍 Simulation mise à jour dans '{target_env.name}'")
        
        with console.status(f"[bold blue]Mise à jour dans {target_env.name}..."):
            if update_all:
                result = env_manager.package_service.update_all_packages(target_env)
            else:
                package_list = list(packages) if packages else []
                result = env_manager.package_service.update_packages(target_env, package_list)
        
        if result.success:
            console.print(f"✅ Mise à jour de [bold green]{target_env.name}[/bold green] réussie!")
            if hasattr(result, 'packages_updated') and result.packages_updated:
                console.print(f"🔄 Packages mis à jour: {', '.join(result.packages_updated)}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES CACHE ===

@cli.group()
def cache() -> None:
    """Gestion du cache"""
    pass

@cache.command(name='info')
@click.pass_context
def cache_info(ctx: click.Context) -> None:
    """Afficher les informations du cache"""
    env_manager = ctx.obj['env_manager']
    cache_service = env_manager.cache_service
    
    try:
        info = cache_service.get_cache_info()
        
        table = Table(title="💾 Informations du Cache")
        table.add_column("Propriété", style="cyan")
        table.add_column("Valeur", style="green")
        
        table.add_row("Statut", "✅ Activé" if info.enabled else "❌ Désactivé")
        table.add_row("Taille actuelle", f"{info.current_size_mb:.1f} MB")
        table.add_row("Taille maximale", f"{info.max_size_mb:.1f} MB")
        table.add_row("Utilisation", f"{info.usage_percent:.1f}%")
        table.add_row("Packages en cache", str(info.cached_packages_count))
        table.add_row("Taux de hit", f"{info.hit_rate:.1f}%")
        table.add_row("Localisation", str(info.cache_path))
        
        # Informations supplémentaires avec PathUtils
        if info.cache_path.exists():
            cache_size_actual = PathUtils.get_size_mb(info.cache_path)
            table.add_row("Taille réelle", f"{cache_size_actual:.1f} MB")
            
            # Analyse des fichiers
            cache_files = PathUtils.find_files_by_pattern(info.cache_path, "*", max_depth=2)
            table.add_row("Fichiers totaux", str(len(cache_files)))
        
        console.print(table)
        
        # Recommandations
        if info.usage_percent > 90:
            console.print("\n⚠️ Cache presque plein. Considérez un nettoyage: gestvenv cache clean")
        elif info.hit_rate < 50:
            console.print("\n💡 Taux de hit faible. Pré-chargez vos packages: gestvenv cache add <packages>")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cache.command(name='add')
@click.argument('packages', nargs=-1)
@click.option('-r', '--requirements', type=click.Path(exists=True), help='Fichier requirements.txt')
@click.option('--platforms', help='Plateformes cibles (séparées par des virgules)')
@click.option('--python-version', help='Version Python pour le cache')
@click.pass_context
def cache_add(ctx: click.Context, packages: tuple, requirements: Optional[str], 
              platforms: Optional[str], python_version: Optional[str]) -> None:
    """Ajouter des packages au cache"""
    env_manager = ctx.obj['env_manager']
    cache_service = env_manager.cache_service
    
    try:
        package_list = list(packages)
        
        # Lecture depuis fichier requirements si spécifié
        if requirements:
            req_path = Path(requirements)
            req_content = req_path.read_text(encoding='utf-8')
            req_packages = [
                line.strip() 
                for line in req_content.split('\n') 
                if line.strip() and not line.startswith('#')
            ]
            package_list.extend(req_packages)
            console.print(f"📄 {len(req_packages)} packages lus depuis {requirements}")
        
        if not package_list:
            console.print("❌ Aucun package spécifié. Utilisez --help pour l'aide")
            return
        
        platforms_list = platforms.split(',') if platforms else None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Mise en cache des packages...", total=len(package_list))
            
            success_count = 0
            total_size = 0
            
            for package in package_list:
                progress.update(task, description=f"Mise en cache de {package}...")
                
                try:
                    result = cache_service.add_package_to_cache(
                        package, 
                        platforms=platforms_list,
                        python_version=python_version
                    )
                    
                    if result.success:
                        success_count += 1
                        total_size += getattr(result, 'file_size', 0)
                        progress.console.print(f"✅ {package} mis en cache")
                    else:
                        progress.console.print(f"❌ Échec mise en cache de {package}")
                except Exception as e:
                    progress.console.print(f"❌ Erreur {package}: {e}")
                
                progress.advance(task)
        
        console.print(f"\n📊 {success_count}/{len(package_list)} packages mis en cache")
        if total_size > 0:
            console.print(f"💾 Taille ajoutée: {total_size / (1024*1024):.1f} MB")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cache.command(name='clean')
@click.option('--older-than', type=int, help='Nettoyer les éléments plus anciens que X jours')
@click.option('--size-limit', help='Nettoyer pour atteindre cette taille max (ex: 500MB)')
@click.option('--force', is_flag=True, help='Forcer le nettoyage sans confirmation')
@click.pass_context
def cache_clean(ctx: click.Context, older_than: Optional[int], size_limit: Optional[str], force: bool) -> None:
    """Nettoyer le cache"""
    env_manager = ctx.obj['env_manager']
    cache_service = env_manager.cache_service
    
    try:
        # Informations avant nettoyage
        info_before = cache_service.get_cache_info()
        
        if not force:
            console.print(f"📊 Cache actuel: {info_before.current_size_mb:.1f} MB")
            if not click.confirm("Êtes-vous sûr de vouloir nettoyer le cache ?"):
                console.print("❌ Nettoyage annulé")
                return
        
        with console.status("[bold yellow]Nettoyage du cache..."):
            result = cache_service.clean_cache(
                older_than_days=older_than,
                size_limit=size_limit
            )
        
        console.print(f"✅ Cache nettoyé: {result.get('freed_mb', 0):.1f} MB libérés")
        console.print(f"🗑️ {result.get('files_deleted', 0)} fichiers supprimés")
        
        # Nettoyage des répertoires vides avec PathUtils
        if info_before.cache_path.exists():
            empty_dirs_cleaned = PathUtils.clean_empty_directories(info_before.cache_path)
            if empty_dirs_cleaned > 0:
                console.print(f"📁 {empty_dirs_cleaned} répertoires vides supprimés")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cache.command(name='export')
@click.argument('output_file')
@click.option('--compress', is_flag=True, help='Compresser l\'archive')
@click.pass_context
def cache_export(ctx: click.Context, output_file: str, compress: bool) -> None:
    """Exporter le cache"""
    env_manager = ctx.obj['env_manager']
    cache_service = env_manager.cache_service
    
    try:
        output_path = Path(output_file)
        
        # Vérification espace disque
        cache_info = cache_service.get_cache_info()
        
        with console.status(f"[bold blue]Export du cache vers {output_file}..."):
            result = cache_service.export_cache(output_path, compress=compress)
        
        if result.success:
            console.print(f"✅ Cache exporté vers [bold green]{output_path}[/bold green]")
            console.print(f"📦 {result.items_exported} éléments exportés")
            
            # Taille du fichier exporté
            if output_path.exists():
                export_size = PathUtils.get_size_mb(output_path)
                console.print(f"💾 Taille export: {export_size:.1f} MB")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cache.command(name='import')
@click.argument('import_file', type=click.Path(exists=True))
@click.option('--merge', is_flag=True, help='Fusionner avec le cache existant')
@click.option('--verify', is_flag=True, help='Vérifier l\'intégrité après import')
@click.pass_context
def cache_import(ctx: click.Context, import_file: str, merge: bool, verify: bool) -> None:
    """Importer un cache"""
    env_manager = ctx.obj['env_manager']
    cache_service = env_manager.cache_service
    
    try:
        import_path = Path(import_file)
        
        # Vérification espace disque disponible
        if import_path.exists():
            import_size = PathUtils.get_size_mb(import_path)
            console.print(f"📦 Taille import: {import_size:.1f} MB")
        
        if not merge:
            console.print("⚠️ Cela remplacera complètement le cache existant")
            if not click.confirm("Continuer ?"):
                console.print("❌ Import annulé")
                return
        
        with console.status(f"[bold blue]Import du cache depuis {import_file}..."):
            result = cache_service.import_cache(import_path, merge=merge)
        
        if result.success:
            console.print(f"✅ Cache importé depuis [bold green]{import_path}[/bold green]")
            console.print(f"📦 {result.items_imported} éléments importés")
            
            # Vérification optionnelle
            if verify:
                with console.status("[bold yellow]Vérification de l'intégrité..."):
                    integrity_ok = cache_service.verify_cache_integrity()
                if integrity_ok:
                    console.print("✅ Intégrité du cache vérifiée")
                else:
                    console.print("⚠️ Problèmes d'intégrité détectés")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES BACKEND ===

@cli.group()
def backend() -> None:
    """Gestion des backends"""
    pass

@backend.command(name='list')
@click.option('--available-only', is_flag=True, help='Afficher seulement les backends disponibles')
@click.pass_context
def backend_list(ctx: click.Context, available_only: bool) -> None:
    """Lister les backends disponibles"""
    env_manager = ctx.obj['env_manager']
    backend_manager = env_manager.backend_manager
    
    try:
        backends_info = []
        
        for backend_name in ['pip', 'uv', 'poetry', 'pdm']:
            try:
                backend = backend_manager.backends.get(backend_name)
                if backend:
                    info = {
                        'name': backend_name,
                        'available': backend.available,
                        'version': getattr(backend, 'version', 'N/A'),
                        'performance_tier': getattr(backend, 'performance_tier', 'Standard'),
                        'capabilities': getattr(backend, 'capabilities', None)
                    }
                    
                    if not available_only or info['available']:
                        backends_info.append(info)
            except Exception:
                if not available_only:
                    backends_info.append({
                        'name': backend_name,
                        'available': False,
                        'version': 'N/A',
                        'performance_tier': 'N/A',
                        'capabilities': None
                    })
        
        table = Table(title="🔧 Backends de packages")
        table.add_column("Nom", style="cyan")
        table.add_column("Disponible", style="green")
        table.add_column("Version", style="yellow")
        table.add_column("Performance", style="magenta")
        table.add_column("Fonctionnalités", style="dim")
        
        for backend_info in backends_info:
            available = "✅" if backend_info['available'] else "❌"
            
            # Résumé des capacités
            caps_summary = ""
            if backend_info['capabilities']:
                caps = []
                if getattr(backend_info['capabilities'], 'supports_lock_files', False):
                    caps.append("lock")
                if getattr(backend_info['capabilities'], 'supports_dependency_groups', False):
                    caps.append("groups")
                if getattr(backend_info['capabilities'], 'supports_parallel_install', False):
                    caps.append("parallel")
                caps_summary = ", ".join(caps)
            
            table.add_row(
                backend_info['name'],
                available,
                backend_info['version'],
                backend_info['performance_tier'],
                caps_summary
            )
        
        console.print(table)
        
        # Backend actuel
        current_backend = env_manager.config_manager.config.preferred_backend
        console.print(f"\n🎯 Backend par défaut: [bold green]{current_backend}[/bold green]")
        
        # Recommandations
        uv_available = any(b['name'] == 'uv' and b['available'] for b in backends_info)
        if not uv_available:
            console.print("\n💡 Pour des performances optimales, installez uv: pip install uv")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@backend.command(name='set')
@click.argument('backend_name', type=click.Choice(['pip', 'uv', 'poetry', 'pdm', 'auto']))
@click.option('--global', 'is_global', is_flag=True, help='Définir comme backend global')
@click.pass_context
def backend_set(ctx: click.Context, backend_name: str, is_global: bool) -> None:
    """Définir le backend par défaut"""
    env_manager = ctx.obj['env_manager']
    
    try:
        # Vérification disponibilité
        if backend_name != 'auto':
            backend = env_manager.backend_manager.backends.get(backend_name)
            if not backend or not backend.available:
                console.print(f"❌ Backend '{backend_name}' non disponible")
                
                # Suggestions d'installation
                install_commands = {
                    'uv': 'pip install uv',
                    'poetry': 'pip install poetry',
                    'pdm': 'pip install pdm'
                }
                
                if backend_name in install_commands:
                    console.print(f"💡 Pour l'installer: {install_commands[backend_name]}")
                
                sys.exit(1)
        
        # Mise à jour configuration
        env_manager.config_manager.config.preferred_backend = backend_name
        env_manager.config_manager.save_config()
        
        console.print(f"✅ Backend par défaut: [bold green]{backend_name}[/bold green]")
        
        # Informations sur les bénéfices
        if backend_name == 'uv':
            console.print("🚀 uv offre des performances jusqu'à 10x supérieures à pip")
        elif backend_name == 'auto':
            console.print("🎯 Sélection automatique du backend optimal pour chaque opération")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@backend.command(name='info')
@click.argument('backend_name', required=False)
@click.option('--detailed', is_flag=True, help='Informations détaillées')
@click.pass_context
def backend_info(ctx: click.Context, backend_name: Optional[str], detailed: bool) -> None:
    """Informations sur un backend"""
    env_manager = ctx.obj['env_manager']
    backend_manager = env_manager.backend_manager
    
    try:
        if not backend_name:
            backend_name = env_manager.config_manager.config.preferred_backend
        
        backend = backend_manager.backends.get(backend_name)
        if not backend:
            console.print(f"❌ Backend '{backend_name}' introuvable")
            sys.exit(1)
        
        table = Table(title=f"🔧 Backend '{backend_name}'")
        table.add_column("Propriété", style="cyan")
        table.add_column("Valeur", style="green")
        
        table.add_row("Nom", backend.name)
        table.add_row("Disponible", "✅ Oui" if backend.available else "❌ Non")
        table.add_row("Version", getattr(backend, 'version', 'N/A'))
        
        if hasattr(backend, 'executable_path'):
            table.add_row("Exécutable", str(getattr(backend, 'executable_path', 'N/A')))
        
        # Capacités détaillées
        if detailed and hasattr(backend, 'capabilities'):
            caps = backend.capabilities
            table.add_row("Lock files", "✅" if caps.supports_lock_files else "❌")
            table.add_row("Groupes dépendances", "✅" if caps.supports_dependency_groups else "❌")
            table.add_row("Installation parallèle", "✅" if caps.supports_parallel_install else "❌")
            table.add_row("Mode éditable", "✅" if caps.supports_editable_installs else "❌")
            table.add_row("Workspace", "✅" if caps.supports_workspace else "❌")
            table.add_row("Sync pyproject", "✅" if caps.supports_pyproject_sync else "❌")
            
            if caps.supported_formats:
                table.add_row("Formats supportés", ", ".join(caps.supported_formats))
            
            if caps.max_parallel_jobs:
                table.add_row("Jobs parallèles max", str(caps.max_parallel_jobs))
        
        console.print(table)
        
        # Performance score
        if hasattr(backend, 'get_performance_score'):
            score = backend.get_performance_score()
            console.print(f"\n⚡ Score de performance: {score}/10")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES DIAGNOSTIC ===

@cli.command()
@click.argument('name', required=False)
@click.option('--auto-fix', is_flag=True, help='Réparation automatique')
@click.option('--full', is_flag=True, help='Diagnostic complet avec recommandations')
@click.option('--performance', is_flag=True, help='Focus sur l\'analyse de performance')
@click.pass_context
def doctor(ctx: click.Context, name: Optional[str], auto_fix: bool, full: bool, performance: bool) -> None:
    """Diagnostic et réparation"""
    env_manager = ctx.obj['env_manager']
    
    try:
        with console.status("[bold blue]Diagnostic en cours..."):
            if name:
                result = env_manager.doctor_environment(name)
            else:
                result = env_manager.doctor_environment()
        
        # Affichage du statut général
        status_icons = {
            'healthy': '✅',
            'warning': '⚠️',
            'error': '❌',
            'unknown': '❓'
        }
        
        status_icon = status_icons.get(result.overall_status.value, '❓')
        status_text = {
            'healthy': '[bold green]Système en bon état[/bold green]',
            'warning': '[bold yellow]Avertissements détectés[/bold yellow]', 
            'error': '[bold red]Problèmes critiques détectés[/bold red]',
            'unknown': '[bold dim]État indéterminé[/bold dim]'
        }.get(result.overall_status.value, 'État inconnu')
        
        console.print(f"{status_icon} {status_text}")
        
        # Affichage des problèmes
        if result.issues:
            issues_table = Table(title="🔍 Problèmes détectés")
            issues_table.add_column("Niveau", style="cyan")
            issues_table.add_column("Catégorie", style="yellow")
            issues_table.add_column("Description", style="white")
            issues_table.add_column("Réparable", style="green")
            
            for issue in result.issues:
                level_emoji = {
                    'error': '❌',
                    'warning': '⚠️',
                    'info': 'ℹ️'
                }.get(issue.level.value, '❓')
                
                fixable = "✅" if issue.auto_fixable else "❌"
                
                issues_table.add_row(
                    f"{level_emoji} {issue.level.value}",
                    issue.category,
                    issue.description,
                    fixable
                )
            
            console.print(issues_table)
        
        # Suggestions d'optimisation
        if result.recommendations and (full or performance):
            console.print("\n💡 [bold blue]Suggestions d'optimisation:[/bold blue]")
            for i, rec in enumerate(result.recommendations, 1):
                console.print(f"  {i}. {rec.description}")
                console.print(f"     Commande: [bold]{rec.command}[/bold]")
                if hasattr(rec, 'impact_score'):
                    console.print(f"     Impact: {rec.impact_score}/10")
        
        # Auto-réparation
        if auto_fix and result.issues:
            fixable_issues = [issue for issue in result.issues if issue.auto_fixable]
            if fixable_issues:
                console.print(f"\n🔧 {len(fixable_issues)} problèmes peuvent être réparés automatiquement")
                
                if click.confirm("Procéder à la réparation automatique ?"):
                    with console.status("[bold green]Réparation automatique..."):
                        fix_result = env_manager.diagnostic_service.auto_fix_issues(fixable_issues)
                    
                    if fix_result:
                        console.print(f"✅ {len(fixable_issues)} problèmes réparés automatiquement")
                    else:
                        console.print("❌ Échec de la réparation automatique")
        
        # Informations système supplémentaires
        if full:
            console.print(f"\n📊 Informations système:")
            console.print(f"   • Environnements totaux: {len(env_manager.list_environments())}")
            
            # Utilisation espace disque
            envs_path = env_manager.config_manager.get_environments_path()
            if envs_path.exists():
                total_size = PathUtils.get_size_mb(envs_path)
                console.print(f"   • Espace utilisé: {total_size:.1f} MB")
        
        console.print(f"\n⏱️ Temps d'exécution: {result.execution_time:.2f}s")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name', required=False)
@click.option('--fix-permissions', is_flag=True, help='Réparer les permissions')
@click.option('--rebuild-metadata', is_flag=True, help='Reconstruire les métadonnées')
@click.option('--fix-packages', is_flag=True, help='Réparer les packages corrompus')
@click.option('--all', 'fix_all', is_flag=True, help='Appliquer toutes les réparations')
@click.option('--dry-run', is_flag=True, help='Simulation sans modification')
@click.pass_context
def repair(ctx: click.Context, name: Optional[str], fix_permissions: bool, 
          rebuild_metadata: bool, fix_packages: bool, fix_all: bool, dry_run: bool) -> None:
    """Réparer un environnement corrompu"""
    env_manager = ctx.obj['env_manager']
    
    try:
        # Si aucune réparation spécifiée, utiliser --all
        if not any([fix_permissions, rebuild_metadata, fix_packages]):
            fix_all = True
        
        if fix_all:
            fix_permissions = fix_packages = rebuild_metadata = True
        
        if name:
            env_info = env_manager.get_environment_info(name)
            if not env_info:
                console.print(f"❌ Environnement '{name}' introuvable")
                sys.exit(1)
            environments = [env_info]
        else:
            # Réparer tous les environnements
            environments = env_manager.list_environments()
            console.print(f"🔧 Réparation de {len(environments)} environnements")
        
        if dry_run:
            console.print("🔍 Mode simulation - aucune modification ne sera effectuée")
        
        total_repairs = 0
        
        for env in environments:
            console.print(f"\n🔧 Réparation de {env.name}...")
            
            repairs_done = []
            
            # Réparation permissions
            if fix_permissions:
                if dry_run:
                    console.print("  [dry-run] Réparation des permissions")
                    repairs_done.append("permissions")
                else:
                    result = env_manager.repair_environment_permissions(env.name)
                    if result.success:
                        console.print("  ✅ Permissions réparées")
                        repairs_done.append("permissions")
                    else:
                        console.print(f"  ❌ Erreur permissions: {result.message}")
            
            # Reconstruction métadonnées
            if rebuild_metadata:
                if dry_run:
                    console.print("  [dry-run] Reconstruction des métadonnées")
                    repairs_done.append("metadata")
                else:
                    result = env_manager.rebuild_environment_metadata(env.name)
                    if result.success:
                        console.print("  ✅ Métadonnées reconstruites")
                        repairs_done.append("metadata")
                    else:
                        console.print(f"  ❌ Erreur métadonnées: {result.message}")
            
            # Réparation packages
            if fix_packages:
                if dry_run:
                    console.print("  [dry-run] Réparation des packages")
                    repairs_done.append("packages")
                else:
                    result = env_manager.repair_environment_packages(env.name)
                    if result.success:
                        console.print("  ✅ Packages réparés")
                        repairs_done.append("packages")
                    else:
                        console.print(f"  ❌ Erreur packages: {result.message}")
            
            if repairs_done:
                total_repairs += len(repairs_done)
                console.print(f"  📊 {len(repairs_done)} réparations effectuées: {', '.join(repairs_done)}")
            else:
                console.print("  ⚠️ Aucune réparation nécessaire")
        
        action_text = "seraient effectuées" if dry_run else "effectuées"
        console.print(f"\n✅ {total_repairs} réparations {action_text} au total")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES TEMPLATES ===

@cli.group()
def template() -> None:
    """Gestion des templates"""
    pass

@template.command(name='list')
@click.option('--category', help='Filtrer par catégorie')
@click.option('--builtin-only', is_flag=True, help='Afficher seulement les templates intégrés')
@click.pass_context
def template_list(ctx: click.Context, category: Optional[str], builtin_only: bool) -> None:
    """Lister les templates disponibles"""
    try:
        template_service = TemplateService()
        templates = template_service.list_templates()
        
        # Filtrage
        if category:
            templates = [t for t in templates if t.category.lower() == category.lower()]
        if builtin_only:
            templates = [t for t in templates if t.is_builtin]
        
        if not templates:
            console.print("📭 Aucun template trouvé")
            return
        
        table = Table(title="📋 Templates disponibles")
        table.add_column("Nom", style="cyan")
        table.add_column("Catégorie", style="green")
        table.add_column("Description", style="yellow")
        table.add_column("Type", style="magenta")
        table.add_column("Dépendances", style="dim")
        
        for tmpl in templates:
            template_type = "🏠 Intégré" if tmpl.is_builtin else "👤 Utilisateur"
            deps_count = len(getattr(tmpl, 'dependencies', []))
            
            table.add_row(
                tmpl.name,
                tmpl.category,
                tmpl.description,
                template_type,
                f"{deps_count} packages" if deps_count > 0 else "-"
            )
        
        console.print(table)
        
        # Catégories disponibles
        categories = list(set(t.category for t in templates))
        console.print(f"\n📂 Catégories: {', '.join(sorted(categories))}")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@template.command(name='create')
@click.argument('template_name')
@click.argument('project_name')
@click.option('--author', help='Nom de l\'auteur')
@click.option('--email', help='Email de l\'auteur')
@click.option('--version', default='0.1.0', help='Version initiale')
@click.option('--python-version', help='Version Python requise')
@click.option('--output', help='Répertoire de sortie')
@click.pass_context
def template_create(ctx: click.Context, template_name: str, project_name: str,
                   author: Optional[str], email: Optional[str], version: str,
                   python_version: Optional[str], output: Optional[str]) -> None:
    """Créer un projet depuis un template"""
    try:
        template_service = TemplateService()
        
        # Paramètres du template
        params = {
            'project_name': project_name,
            'package_name': project_name.lower().replace('-', '_'),
            'version': version
        }
        
        if author:
            params['author'] = author
        if email:
            params['email'] = email
        if python_version:
            params['python_version'] = python_version
        
        # Chemin de sortie
        output_path = Path(output) if output else Path.cwd() / project_name
        
        # Vérification que le répertoire n'existe pas
        if output_path.exists() and any(output_path.iterdir()):
            console.print(f"❌ Le répertoire {output_path} existe et n'est pas vide")
            if not click.confirm("Continuer quand même ?"):
                return
        
        with console.status(f"[bold green]Création du projet depuis le template {template_name}..."):
            result = template_service.create_from_template(
                template_name=template_name,
                project_name=project_name,
                output_path=output_path,
                **params
            )
        
        if result.success:
            console.print(f"✅ Projet [bold green]{project_name}[/bold green] créé depuis le template [bold blue]{template_name}[/bold blue]!")
            console.print(f"📁 Localisation: {result.output_path}")
            console.print(f"📄 {result.files_created} fichiers créés")
            
            # Suggestions pour la suite
            console.print(f"\n💡 Prochaines étapes:")
            console.print(f"   cd {output_path.name}")
            console.print(f"   gestvenv create-from-pyproject pyproject.toml {project_name}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES EXPORT/IMPORT ===

@cli.command()
@click.argument('name')
@click.argument('output_file', required=False)
@click.option('--format', 'export_format', 
              type=click.Choice(['json', 'requirements', 'pyproject']), 
              default='json')
@click.option('--include-cache', is_flag=True, help='Inclure le cache local')
@click.pass_context
def export(ctx: click.Context, name: str, output_file: Optional[str], 
          export_format: str, include_cache: bool) -> None:
    """Exporter un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        format_enum = ExportFormat(export_format)
        
        with console.status(f"[bold blue]Export de {name}..."):
            result = env_manager.export_environment(name, format_enum)
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{name}[/bold green] exporté!")
            console.print(f"📄 Fichier: {result.output_path}")
            console.print(f"📦 {result.items_exported} éléments exportés")
            
            # Taille du fichier
            if result.output_path.exists():
                file_size = PathUtils.get_size_mb(result.output_path)
                console.print(f"💾 Taille: {file_size:.1f} MB")
            
            # Copie vers fichier spécifié si demandé
            if output_file:
                import shutil
                target_path = Path(output_file)
                shutil.copy2(result.output_path, target_path)
                console.print(f"📋 Copié vers: {target_path}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command(name='import')
@click.argument('source_file', type=click.Path(exists=True))
@click.argument('env_name', required=False)
@click.option('--force', is_flag=True, help='Écraser l\'environnement existant')
@click.pass_context
def import_env(ctx: click.Context, source_file: str, env_name: Optional[str], force: bool) -> None:
    """Importer un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        source_path = Path(source_file)
        
        # Vérification format
        supported_formats = ['.json', '.toml', '.txt', '.yml', '.yaml']
        if source_path.suffix not in supported_formats:
            console.print(f"❌ Format non supporté: {source_path.suffix}")
            console.print(f"💡 Formats supportés: {', '.join(supported_formats)}")
            sys.exit(1)
        
        # Détection automatique du type
        import_type = "generic"
        if source_path.name == "Pipfile":
            import_type = "pipfile"
        elif source_path.name.startswith("environment") and source_path.suffix in ['.yml', '.yaml']:
            import_type = "conda"
        elif source_path.name == "pyproject.toml":
            import_type = "pyproject"
        
        with console.status(f"[bold blue]Import {import_type} depuis {source_file}..."):
            if import_type == "pipfile":
                result = env_manager.import_from_pipfile(source_path, name=env_name, force=force)
            elif import_type == "conda":
                result = env_manager.import_from_conda_env(source_path, name=env_name, force=force)
            else:
                result = env_manager.import_environment(source_path, name=env_name, force=force)
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{result.environment.name}[/bold green] importé!")
            console.print(f"📁 Chemin: {result.environment.path}")
            console.print(f"📦 Packages: {len(result.environment.packages)}")
            console.print(f"📋 Type: {import_type}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('pipfile_path', type=click.Path(exists=True))
@click.argument('env_name', required=False)
@click.option('--backend', type=click.Choice(['pip', 'uv', 'auto']), default='auto')
@click.option('--include-dev', is_flag=True, help='Inclure les dépendances de développement')
@click.pass_context
def import_from_pipfile(ctx: click.Context, pipfile_path: str, env_name: Optional[str], 
                       backend: str, include_dev: bool) -> None:
    """Importer depuis un Pipfile (Pipenv)"""
    env_manager = ctx.obj['env_manager']
    
    try:
        pipfile = Path(pipfile_path)
        
        # Validation fichier Pipfile
        if not pipfile.name == "Pipfile":
            console.print("❌ Le fichier doit être nommé 'Pipfile'")
            sys.exit(1)
        
        with console.status(f"[bold green]Import depuis Pipfile..."):
            result = env_manager.create_from_pipfile(
                pipfile_path=pipfile,
                env_name=env_name,
                backend=backend if backend != 'auto' else None,
                include_dev=include_dev
            )
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{result.environment.name}[/bold green] créé depuis Pipfile!")
            console.print(f"📁 Chemin: {result.environment.path}")
            console.print(f"🐍 Python: {result.environment.python_version}")
            console.print(f"📦 Packages installés: {len(result.environment.packages)}")
            
            if include_dev:
                dev_packages = [pkg for pkg in result.environment.packages if pkg.is_development_package()]
                console.print(f"🔧 Packages dev: {len(dev_packages)}")
            
            for warning in result.warnings:
                console.print(f"⚠️ {warning}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES CONFIGURATION ===

@cli.group()
def config() -> None:
    """Gestion de la configuration"""
    pass

@config.command(name='show')
@click.option('--section', help='Section spécifique à afficher')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def config_show(ctx: click.Context, section: Optional[str], format: str) -> None:
    """Afficher la configuration"""
    env_manager = ctx.obj['env_manager']
    config_manager = env_manager.config_manager
    
    try:
        config_data = config_manager.get_config_summary()
        
        if format == 'json':
            import json
            filtered_data = {k: v for k, v in config_data.items() 
                           if not section or section.lower() in k.lower()}
            console.print(json.dumps(filtered_data, indent=2, default=str))
            return
        
        table = Table(title="⚙️ Configuration GestVenv")
        table.add_column("Paramètre", style="cyan")
        table.add_column("Valeur", style="green")
        table.add_column("Description", style="dim")
        
        descriptions = {
            'version': 'Version de la configuration',
            'environments_path': 'Répertoire des environnements',
            'preferred_backend': 'Backend par défaut',
            'python_version': 'Version Python par défaut',
            'cache_enabled': 'Cache activé',
            'cache_size_mb': 'Taille max du cache',
            'auto_migrate': 'Migration automatique',
            'offline_mode': 'Mode hors ligne'
        }
        
        for key, value in config_data.items():
            if not section or section.lower() in key.lower():
                desc = descriptions.get(key, '')
                table.add_row(
                    key.replace('_', ' ').title(), 
                    str(value), 
                    desc
                )
        
        console.print(table)
        
        # Informations additionnelles
        config_path = config_manager.config_path
        if config_path.exists():
            config_size = PathUtils.get_size_mb(config_path)
            console.print(f"\n📄 Fichier config: {config_path} ({config_size*1024:.0f} KB)")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@config.command(name='set')
@click.argument('key')
@click.argument('value')
@click.option('--type', 'value_type', type=click.Choice(['str', 'int', 'bool', 'float']), 
              help='Type de la valeur')
@click.option('--local', is_flag=True, help='Configuration locale au projet')
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str, value_type: Optional[str], local: bool) -> None:
    """Définir une valeur de configuration"""
    env_manager = ctx.obj['env_manager']
    config_manager = env_manager.config_manager
    
    try:
        # Conversion automatique des types ou selon le type spécifié
        if value_type == 'bool' or (not value_type and value.lower() in ['true', 'false']):
            converted_value = value.lower() == 'true'
        elif value_type == 'int' or (not value_type and value.isdigit()):
            converted_value = int(value)
        elif value_type == 'float':
            converted_value = float(value)
        else:
            converted_value = value
        
        # Validation clés connues
        valid_keys = [
            'preferred_backend', 'default_python_version', 'auto_migrate',
            'offline_mode', 'cache_enabled', 'cache_size_mb'
        ]
        
        if key not in valid_keys:
            console.print(f"⚠️ Clé '{key}' non reconnue")
            console.print(f"💡 Clés valides: {', '.join(valid_keys)}")
            if not click.confirm("Continuer quand même ?"):
                return
        
        if local:
            # Configuration locale projet
            local_config_path = Path.cwd() / ".gestvenv" / "config.toml"
            local_config_path.parent.mkdir(exist_ok=True)
            
            # Charger ou créer la config locale
            if local_config_path.exists():
                from gestvenv.utils.toml_handler import TomlHandler
                local_config = TomlHandler.load(local_config_path)
            else:
                local_config = {}
            
            local_config[key] = converted_value
            
            # Sauvegarder
            from gestvenv.utils.toml_handler import TomlHandler
            TomlHandler.dump(local_config, local_config_path)
            
            console.print(f"✅ Configuration locale: {key} = [bold green]{converted_value}[/bold green]")
            console.print(f"📁 Fichier: {local_config_path}")
        else:
            # Configuration globale
            config = config_manager.config
            setattr(config, key, converted_value)
            config_manager.save_config()
            
            console.print(f"✅ Configuration globale: {key} = [bold green]{converted_value}[/bold green]")
        
        # Suggestions contextuelles
        if key == 'preferred_backend' and converted_value == 'uv':
            console.print("🚀 Excellent choix! uv offre des performances exceptionnelles")
        elif key == 'cache_enabled' and converted_value:
            console.print("💾 Cache activé. Utilisez 'gestvenv cache add' pour pré-charger des packages")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@config.command(name='reset')
@click.option('--backup', is_flag=True, help='Créer une sauvegarde avant reset')
@click.option('--force', is_flag=True, help='Forcer sans confirmation')
@click.pass_context
def config_reset(ctx: click.Context, backup: bool, force: bool) -> None:
    """Remettre la configuration par défaut"""
    env_manager = ctx.obj['env_manager']
    config_manager = env_manager.config_manager
    
    try:
        if not force:
            console.print("⚠️ Cela va remettre toute la configuration par défaut")
            if not click.confirm("Continuer ?"):
                return
        
        # Sauvegarde optionnelle
        if backup:
            backup_path = config_manager.backup_config()
            if backup_path:
                console.print(f"💾 Sauvegarde créée: {backup_path}")
        
        with console.status("[bold yellow]Reset de la configuration..."):
            success = config_manager.reset_config()
        
        if success:
            console.print("✅ Configuration remise par défaut")
        else:
            console.print("❌ Erreur lors du reset")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES ENVIRONNEMENTS ÉPHÉMÈRES ===

@cli.group()
def ephemeral() -> None:
    """Gestion des environnements éphémères"""
    pass

@ephemeral.command(name='create')
@click.argument('name', required=False)
@click.option('--backend', type=click.Choice(['uv', 'pip', 'pdm', 'poetry']), 
              default='uv', help='Backend à utiliser')
@click.option('--python', help='Version Python')
@click.option('--ttl', type=int, help='Durée de vie en secondes')
@click.option('--packages', help='Packages à installer (séparés par des virgules)')
@click.option('--requirements', type=click.Path(exists=True), help='Fichier requirements.txt')
@click.option('--interactive', is_flag=True, help='Mode interactif')
@click.pass_context
def ephemeral_create(ctx: click.Context, name: Optional[str], backend: str, python: Optional[str], 
                    ttl: Optional[int], packages: Optional[str], requirements: Optional[str], 
                    interactive: bool) -> None:
    """Créer un environnement éphémère"""
    try:
        import asyncio
        from gestvenv.core.ephemeral import ephemeral
        from gestvenv.core.models import Backend
        
        backend_map = {
            'uv': Backend.UV,
            'pip': Backend.PIP,
            'pdm': Backend.PDM,
            'poetry': Backend.POETRY
        }
        
        async def create_and_use():
            console.print(f"🚀 Création de l'environnement éphémère...")
            
            async with ephemeral(
                name=name,
                backend=backend_map[backend],
                python_version=python or "3.11",
                ttl=ttl
            ) as env:
                console.print(f"✅ Environnement créé: {env.name} (ID: {env.id[:8]})")
                console.print(f"📁 Stockage: {env.storage_path}")
                console.print(f"🐍 Python: {env.python_version}")
                console.print(f"⚙️ Backend: {env.backend.value}")
                
                # Installation de packages
                if packages:
                    package_list = [p.strip() for p in packages.split(',')]
                    console.print(f"📦 Installation de {len(package_list)} packages...")
                    result = await env.install(package_list)
                    if result.success:
                        console.print("✅ Packages installés avec succès")
                    else:
                        console.print(f"❌ Erreur installation: {result.stderr}")
                
                if requirements:
                    console.print(f"📦 Installation depuis {requirements}...")
                    result = await env.execute(f"pip install -r {requirements}")
                    if result.success:
                        console.print("✅ Requirements installés avec succès")
                    else:
                        console.print(f"❌ Erreur: {result.stderr}")
                
                if interactive:
                    console.print("\n💡 Mode interactif - tapez 'exit' pour quitter")
                    console.print("Commandes disponibles:")
                    console.print("  install <package>  - Installer un package")
                    console.print("  run <command>      - Exécuter une commande") 
                    console.print("  info               - Informations sur l'environnement")
                    console.print("  exit               - Quitter")
                    
                    while True:
                        try:
                            command = input(f"\n{env.name}> ").strip()
                            if command == 'exit':
                                break
                            elif command == 'info':
                                console.print(f"ID: {env.id}")
                                console.print(f"Nom: {env.name}")
                                console.print(f"Status: {env.status.value}")
                                console.print(f"Packages: {len(env.packages)}")
                                console.print(f"Âge: {env.age_seconds}s")
                            elif command.startswith('install '):
                                package = command[8:].strip()
                                result = await env.install([package])
                                if result.success:
                                    console.print(f"✅ {package} installé")
                                else:
                                    console.print(f"❌ Erreur: {result.stderr}")
                            elif command.startswith('run '):
                                cmd = command[4:].strip()
                                result = await env.execute(cmd)
                                if result.stdout:
                                    console.print(result.stdout)
                                if result.stderr:
                                    console.print(result.stderr, style="red")
                            else:
                                console.print("❌ Commande inconnue")
                        except KeyboardInterrupt:
                            break
                        except EOFError:
                            break
                
                console.print("🧹 Nettoyage automatique en cours...")
            
            console.print("✅ Environnement éphémère terminé")
        
        asyncio.run(create_and_use())
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@ephemeral.command(name='list')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def ephemeral_list(ctx: click.Context, format: str) -> None:
    """Lister les environnements éphémères actifs"""
    try:
        import asyncio
        from gestvenv.core.ephemeral import list_active_environments
        
        async def list_envs():
            environments = await list_active_environments()
            
            if format == 'json':
                import json
                env_data = []
                for env in environments:
                    env_data.append({
                        'id': env.id,
                        'name': env.name,
                        'status': env.status.value,
                        'backend': env.backend.value,
                        'python_version': env.python_version,
                        'age_seconds': env.age_seconds,
                        'packages_count': len(env.packages)
                    })
                console.print(json.dumps(env_data, indent=2))
                return
            
            if not environments:
                console.print("📭 Aucun environnement éphémère actif")
                return
            
            table = Table(title="🚀 Environnements Éphémères Actifs")
            table.add_column("ID", style="cyan")
            table.add_column("Nom", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Backend", style="blue")
            table.add_column("Python", style="magenta")
            table.add_column("Âge", style="red")
            table.add_column("Packages", style="white")
            
            for env in environments:
                table.add_row(
                    env.id[:8],
                    env.name or "sans-nom",
                    env.status.value,
                    env.backend.value,
                    env.python_version,
                    f"{env.age_seconds}s",
                    str(len(env.packages))
                )
            
            console.print(table)
        
        asyncio.run(list_envs())
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@ephemeral.command(name='cleanup')
@click.argument('env_id', required=False)
@click.option('--all', 'cleanup_all', is_flag=True, help='Nettoyer tous les environnements')
@click.option('--force', is_flag=True, help='Forcer le nettoyage')
@click.pass_context
def ephemeral_cleanup(ctx: click.Context, env_id: Optional[str], cleanup_all: bool, force: bool) -> None:
    """Nettoyer des environnements éphémères"""
    try:
        import asyncio
        from gestvenv.core.ephemeral import cleanup_environment, list_active_environments
        
        async def cleanup():
            if cleanup_all:
                environments = await list_active_environments()
                if not environments:
                    console.print("📭 Aucun environnement à nettoyer")
                    return
                
                console.print(f"🧹 Nettoyage de {len(environments)} environnements...")
                success_count = 0
                
                for env in environments:
                    try:
                        success = await cleanup_environment(env.id, force=force)
                        if success:
                            success_count += 1
                            console.print(f"✅ {env.name} nettoyé")
                        else:
                            console.print(f"❌ Échec: {env.name}")
                    except Exception as e:
                        console.print(f"❌ Erreur {env.name}: {e}")
                
                console.print(f"📊 {success_count}/{len(environments)} environnements nettoyés")
            
            elif env_id:
                console.print(f"🧹 Nettoyage de l'environnement {env_id}...")
                success = await cleanup_environment(env_id, force=force)
                if success:
                    console.print(f"✅ Environnement {env_id} nettoyé")
                else:
                    console.print(f"❌ Environnement {env_id} non trouvé")
            
            else:
                console.print("❌ Spécifiez un ID d'environnement ou --all")
                sys.exit(1)
        
        asyncio.run(cleanup())
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@ephemeral.command(name='stats')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def ephemeral_stats(ctx: click.Context, format: str) -> None:
    """Statistiques des environnements éphémères"""
    try:
        import asyncio
        from gestvenv.core.ephemeral import get_resource_usage
        
        async def show_stats():
            usage = await get_resource_usage()
            
            if format == 'json':
                import json
                console.print(json.dumps(usage, indent=2))
                return
            
            table = Table(title="📊 Statistiques Environnements Éphémères")
            table.add_column("Métrique", style="cyan")
            table.add_column("Valeur", style="green")
            
            table.add_row("Environnements actifs", str(usage["active_environments"]))
            table.add_row("Maximum concurrent", str(usage["max_concurrent"]))
            table.add_row("Mémoire utilisée", f"{usage['total_memory_mb']:.1f} MB")
            table.add_row("Mémoire maximum", f"{usage['max_total_memory_mb']:.1f} MB")
            table.add_row("Disque utilisé", f"{usage['total_disk_mb']:.1f} MB")
            table.add_row("Disque maximum", f"{usage['max_total_disk_mb']:.1f} MB")
            
            console.print(table)
        
        asyncio.run(show_stats())
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# === COMMANDES UTILITAIRES ===

@cli.command()
@click.argument('command', nargs=-1, required=True)
@click.option('--env', help='Environnement dans lequel exécuter')
@click.option('--cwd', help='Répertoire de travail')
@click.pass_context
def run(ctx: click.Context, command: tuple, env: Optional[str], cwd: Optional[str]) -> None:
    """Exécuter une commande dans un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        # Résolution environnement
        if not env:
            active_envs = [e for e in env_manager.list_environments() if e.is_active]
            if len(active_envs) == 1:
                target_env = active_envs[0]
            else:
                console.print("❌ Spécifiez l'environnement avec --env")
                sys.exit(1)
        else:
            target_env = env_manager.get_environment_info(env)
            if not target_env:
                console.print(f"❌ Environnement '{env}' introuvable")
                sys.exit(1)
        
        command_str = ' '.join(command)
        working_dir = Path(cwd) if cwd else Path.cwd()
        
        console.print(f"🚀 Exécution dans {target_env.name}: {command_str}")
        
        # Exécution de la commande
        result = env_manager.run_command_in_environment(
            target_env.name, 
            command_str, 
            working_directory=working_dir
        )
        
        if result.success:
            if result.stdout:
                console.print(result.stdout)
            console.print(f"✅ Commande exécutée (code: {result.return_code})")
        else:
            if result.stderr:
                console.print(result.stderr, style="red")
            console.print(f"❌ Échec (code: {result.return_code})")
            sys.exit(result.return_code)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--env', help='Environnement à activer')
@click.option('--shell', type=click.Choice(['bash', 'zsh', 'fish', 'powershell']), help='Shell cible')
@click.pass_context
def shell(ctx: click.Context, env: Optional[str], shell: Optional[str]) -> None:
    """Démarrer un shell avec l'environnement activé"""
    env_manager = ctx.obj['env_manager']
    
    try:
        # Résolution environnement
        if not env:
            active_envs = [e for e in env_manager.list_environments() if e.is_active]
            if len(active_envs) == 1:
                target_env = active_envs[0]
            else:
                console.print("❌ Spécifiez l'environnement avec --env")
                sys.exit(1)
        else:
            target_env = env_manager.get_environment_info(env)
            if not target_env:
                console.print(f"❌ Environnement '{env}' introuvable")
                sys.exit(1)
        
        console.print(f"🐚 Démarrage du shell avec {target_env.name}")
        
        # Activation et démarrage du shell
        result = env_manager.start_shell_with_environment(target_env.name, shell=shell)
        
        if result.success:
            console.print(f"✅ Shell démarré avec {target_env.name}")
            console.print(f"💡 Pour quitter: exit")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--message', help='Message de feedback')
@click.option('--type', 'feedback_type', type=click.Choice(['bug', 'feature', 'improvement', 'question']), 
              default='improvement')
@click.option('--anonymous', is_flag=True, help='Feedback anonyme')
@click.pass_context
def feedback(ctx: click.Context, message: Optional[str], feedback_type: str, anonymous: bool) -> None:
    """Envoyer du feedback aux développeurs"""
    try:
        import platform
        import sys
        
        if not message:
            message = click.edit('\n# Entrez votre feedback ici\n# Lignes commençant par # seront ignorées\n')
            if not message:
                console.print("❌ Aucun message fourni")
                return
            
            # Nettoyer les commentaires
            lines = [line for line in message.split('\n') if not line.strip().startswith('#')]
            message = '\n'.join(lines).strip()
        
        if not message:
            console.print("❌ Le message ne peut pas être vide")
            return
        
        # Collecte d'informations système
        system_info = {
            'gestvenv_version': __version__,
            'python_version': sys.version,
            'platform': platform.platform(),
            'feedback_type': feedback_type
        }
        
        console.print(f"📝 Type: {feedback_type}")
        console.print(f"📱 Système: {platform.system()} {platform.release()}")
        console.print(f"🐍 Python: {sys.version.split()[0]}")
        
        if not anonymous:
            console.print("💡 Ce feedback inclura des informations système pour le débogage")
        
        # Simulation d'envoi (dans une vraie implémentation, cela enverrait à un service)
        console.print("\n📤 Envoi du feedback...")
        
        # Ici on simule l'envoi
        feedback_data = {
            'message': message,
            'type': feedback_type,
            'anonymous': anonymous,
            'system_info': system_info if not anonymous else None
        }
        
        # Dans une vraie implémentation, on enverrait à une API
        console.print("✅ Feedback envoyé avec succès!")
        console.print("🙏 Merci pour votre contribution à l'amélioration de GestVenv!")
        
        # Créer un fichier local de feedback pour les développeurs
        feedback_dir = Path.home() / ".gestvenv" / "feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        
        feedback_file = feedback_dir / f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        import json
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, default=str)
        
        console.print(f"📄 Copie locale sauvée: {feedback_file}")
        
    except Exception as e:
        console.print(f"❌ Erreur lors de l'envoi: {e}")
        sys.exit(1)

@cli.command()
@click.argument('req_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Fichier de sortie')
@click.option('--interactive', is_flag=True, help='Mode interactif pour personnaliser')
@click.pass_context
def convert_to_pyproject(ctx: click.Context, req_file: str, output: Optional[str], interactive: bool) -> None:
    """Convertir requirements.txt vers pyproject.toml"""
    try:
        req_path = Path(req_file)
        output_path = Path(output) if output else req_path.parent / "pyproject.toml"
        
        # Vérification que requirements.txt existe et n'est pas vide
        if req_path.stat().st_size == 0:
            console.print("❌ Le fichier requirements.txt est vide")
            sys.exit(1)
        
        # Mode interactif pour personnalisation
        project_name = None
        author = None
        description = None
        
        if interactive:
            project_name = click.prompt("Nom du projet", default=req_path.parent.name)
            author = click.prompt("Auteur", default="")
            description = click.prompt("Description", default="")
        
        with console.status("[bold blue]Conversion en cours..."):
            # Utilisation TomlHandler pour la conversion
            requirements_content = req_path.read_text(encoding='utf-8')
            dependencies = [line.strip() for line in requirements_content.split('\n') 
                          if line.strip() and not line.startswith('#')]
            
            # Structure pyproject.toml basique
            pyproject_data = {
                'build-system': {
                    'requires': ['setuptools>=61.0', 'wheel'],
                    'build-backend': 'setuptools.build_meta'
                },
                'project': {
                    'name': project_name or req_path.parent.name,
                    'version': '0.1.0',
                    'dependencies': dependencies
                }
            }
            
            if author:
                pyproject_data['project']['authors'] = [{'name': author}]
            if description:
                pyproject_data['project']['description'] = description
            
            # Sauvegarde avec TomlHandler
            TomlHandler.dump(pyproject_data, output_path)
        
        console.print(f"✅ Conversion réussie: [bold green]{output_path}[/bold green]")
        console.print(f"📦 {len(dependencies)} dépendances converties")
        
        # Suggestions
        console.print(f"\n💡 Créez maintenant votre environnement:")
        console.print(f"   gestvenv create-from-pyproject {output_path} {project_name or 'myenv'}")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--detailed', is_flag=True, help='Statistiques détaillées')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def stats(ctx: click.Context, detailed: bool, format: str) -> None:
    """Afficher les statistiques d'utilisation"""
    env_manager = ctx.obj['env_manager']
    
    try:
        environments = env_manager.list_environments()
        
        # Calculs statistiques
        total_envs = len(environments)
        active_envs = len([env for env in environments if env.is_active])
        total_packages = sum(len(env.packages) for env in environments)
        
        # Répartition par backend
        backend_counts = {}
        for env in environments:
            backend = env.backend_type.value if env.backend_type else 'pip'
            backend_counts[backend] = backend_counts.get(backend, 0) + 1
        
        # Calcul taille totale avec PathUtils
        total_size_mb = 0
        for env in environments:
            if env.path.exists():
                total_size_mb += PathUtils.get_size_mb(env.path)
        
        stats_data = {
            'total_environments': total_envs,
            'active_environments': active_envs,
            'total_packages': total_packages,
            'total_size_mb': total_size_mb,
            'backend_distribution': backend_counts
        }
        
        if format == 'json':
            import json
            if detailed:
                # Informations détaillées par environnement
                env_details = []
                for env in environments:
                    size_mb = PathUtils.get_size_mb(env.path) if env.path.exists() else 0
                    env_details.append({
                        'name': env.name,
                        'packages_count': len(env.packages),
                        'size_mb': size_mb,
                        'backend': env.backend_type.value if env.backend_type else 'pip'
                    })
                stats_data['environments'] = env_details
            
            console.print(json.dumps(stats_data, indent=2))
            return
        
        # Affichage tableau
        stats_table = Table(title="📊 Statistiques GestVenv")
        stats_table.add_column("Métrique", style="cyan")
        stats_table.add_column("Valeur", style="green")
        
        stats_table.add_row("Environnements totaux", str(total_envs))
        stats_table.add_row("Environnements actifs", str(active_envs))
        stats_table.add_row("Packages totaux", str(total_packages))
        stats_table.add_row("Espace utilisé", f"{total_size_mb:.1f} MB")
        
        # Répartition par backend
        for backend, count in backend_counts.items():
            stats_table.add_row(f"Environments {backend}", str(count))
        
        console.print(stats_table)
        
        if detailed:
            # Cache statistics
            try:
                cache_info = env_manager.cache_service.get_cache_info()
                console.print(f"\n💾 Cache: {cache_info.current_size_mb:.1f}/{cache_info.max_size_mb:.1f} MB")
                console.print(f"📦 Packages en cache: {cache_info.cached_packages_count}")
                console.print(f"🎯 Taux de hit: {cache_info.hit_rate:.1f}%")
            except:
                pass
            
            # Top environnements par taille
            if environments:
                console.print(f"\n🏆 Top 5 environnements par taille:")
                sorted_envs = sorted(environments, 
                                   key=lambda e: PathUtils.get_size_mb(e.path) if e.path.exists() else 0, 
                                   reverse=True)[:5]
                for i, env in enumerate(sorted_envs, 1):
                    size = PathUtils.get_size_mb(env.path) if env.path.exists() else 0
                    console.print(f"   {i}. {env.name}: {size:.1f} MB ({len(env.packages)} packages)")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--orphaned', is_flag=True, help='Nettoyer seulement les environnements orphelins')
@click.option('--all', 'clean_all', is_flag=True, help='Nettoyer tous les environnements')
@click.option('--cache', 'clean_cache', is_flag=True, help='Nettoyer aussi le cache')
@click.option('--force', is_flag=True, help='Forcer sans confirmation')
@click.option('--dry-run', is_flag=True, help='Simulation sans suppression')
@click.pass_context
def cleanup(ctx: click.Context, orphaned: bool, clean_all: bool, clean_cache: bool, 
           force: bool, dry_run: bool) -> None:
    """Nettoyer les environnements et le cache"""
    env_manager = ctx.obj['env_manager']
    
    try:
        if clean_all:
            environments = env_manager.list_environments()
            total_size = sum(PathUtils.get_size_mb(env.path) for env in environments if env.path.exists())
            
            console.print(f"⚠️ Cela supprimera {len(environments)} environnements ({total_size:.1f} MB)")
            
            if not force and not dry_run:
                if not click.confirm("Continuer ?"):
                    console.print("❌ Nettoyage annulé")
                    return
            
            success_count = 0
            
            for env in environments:
                if dry_run:
                    console.print(f"[dry-run] Suppression de {env.name}")
                    success_count += 1
                else:
                    try:
                        env_manager.delete_environment(env.name, force=True)
                        success_count += 1
                        console.print(f"✅ {env.name} supprimé")
                    except Exception as e:
                        console.print(f"❌ Erreur suppression {env.name}: {e}")
            
            console.print(f"📊 {success_count}/{len(environments)} environnements {'seraient supprimés' if dry_run else 'supprimés'}")
        
        elif orphaned:
            console.print("🔍 Recherche d'environnements orphelins...")
            
            envs_path = env_manager.config_manager.get_environments_path()
            if envs_path.exists():
                orphaned_count = 0
                orphaned_size = 0
                
                for env_dir in envs_path.iterdir():
                    if env_dir.is_dir():
                        metadata_path = env_dir / ".gestvenv-metadata.json"
                        if not metadata_path.exists():
                            size_mb = PathUtils.get_size_mb(env_dir)
                            orphaned_size += size_mb
                            
                            if dry_run:
                                console.print(f"[dry-run] Environnement orphelin: {env_dir.name} ({size_mb:.1f} MB)")
                                orphaned_count += 1
                            else:
                                if not force:
                                    if click.confirm(f"Supprimer l'environnement orphelin '{env_dir.name}' ({size_mb:.1f} MB) ?"):
                                        if PathUtils.safe_remove_directory(env_dir):
                                            orphaned_count += 1
                                            console.print(f"✅ {env_dir.name} supprimé")
                                else:
                                    if PathUtils.safe_remove_directory(env_dir):
                                        orphaned_count += 1
                                        console.print(f"✅ {env_dir.name} supprimé")
                
                console.print(f"📊 {orphaned_count} environnements orphelins {'seraient supprimés' if dry_run else 'supprimés'} ({orphaned_size:.1f} MB)")
        
        # Nettoyage cache
        if clean_cache:
            if dry_run:
                console.print("[dry-run] Nettoyage du cache")
            else:
                cache_result = env_manager.cache_service.clean_cache()
                console.print(f"💾 Cache nettoyé: {cache_result.get('freed_mb', 0):.1f} MB libérés")
        
        # Nettoyage répertoires vides
        if not dry_run and not orphaned and not clean_all:
            envs_path = env_manager.config_manager.get_environments_path()
            if envs_path.exists():
                empty_dirs = PathUtils.clean_empty_directories(envs_path)
                if empty_dirs > 0:
                    console.print(f"📁 {empty_dirs} répertoires vides supprimés")
        
        if not orphaned and not clean_all and not clean_cache:
            console.print("❌ Spécifiez --orphaned, --all, ou --cache")
            console.print("💡 Utilisez --dry-run pour simuler")
        
    except Exception as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--from-v1', is_flag=True, help='Migration depuis GestVenv v1.x')
@click.option('--dry-run', is_flag=True, help='Simuler la migration sans modifications')
@click.option('--backup/--no-backup', default=True, help='Créer une sauvegarde avant migration')
@click.pass_context
def migrate(ctx: click.Context, from_v1: bool, dry_run: bool, backup: bool) -> None:
    """Migrer depuis une version antérieure de GestVenv

    Cette commande détecte et migre automatiquement les configurations
    et environnements depuis GestVenv v1.x vers v2.0.

    Exemples:
        gv migrate --from-v1
        gv migrate --dry-run
    """
    try:
        migration_service = MigrationService()

        console.print(Panel.fit(
            "[bold blue]Migration GestVenv[/bold blue]",
            subtitle="v1.x → v2.0"
        ))

        if dry_run:
            console.print("[yellow]Mode simulation (dry-run)[/yellow]\n")

        # Détection automatique
        v1_paths = [
            Path.home() / ".gestvenv_v1",
            Path.home() / ".gestvenv-v1",
            Path.home() / ".gestvenv" / "v1_backup"
        ]

        v1_found = None
        for path in v1_paths:
            if path.exists():
                v1_found = path
                break

        if from_v1 or v1_found:
            if v1_found:
                console.print(f"📁 Installation v1.x détectée: {v1_found}")
            else:
                console.print("[yellow]⚠️ Aucune installation v1.x trouvée[/yellow]")
                console.print("Chemins vérifiés:")
                for p in v1_paths:
                    console.print(f"  - {p}")
                return

            if dry_run:
                console.print("\n[bold]Actions qui seraient effectuées:[/bold]")
                console.print("  1. Sauvegarde des données v1.x")
                console.print("  2. Migration de la configuration")
                console.print("  3. Migration des environnements")
                console.print("  4. Validation de la migration")
                return

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Migration en cours...", total=None)

                result = migration_service.auto_migrate_if_needed()

                progress.update(task, completed=True)

            if result.success:
                console.print(f"\n✅ {result.message}")
                if result.backup_path:
                    console.print(f"💾 Sauvegarde créée: {result.backup_path}")
                if result.details:
                    console.print("\n[bold]Détails:[/bold]")
                    for key, value in result.details.items():
                        console.print(f"  • {key}: {value}")
            else:
                console.print(f"\n❌ Échec migration: {result.message}")
                sys.exit(1)
        else:
            # Vérification automatique
            result = migration_service.auto_migrate_if_needed()
            console.print(f"ℹ️ {result.message}")

    except Exception as e:
        console.print(f"❌ Erreur migration: {e}")
        sys.exit(1)


@cli.command('import-v1-environments')
@click.argument('source_path', type=click.Path(exists=True), required=False)
@click.option('--target', help='Répertoire cible pour les environnements importés')
@click.option('--dry-run', is_flag=True, help='Simuler l\'import sans modifications')
@click.option('--skip-existing', is_flag=True, help='Ignorer les environnements existants')
@click.pass_context
def import_v1_environments(ctx: click.Context, source_path: Optional[str],
                           target: Optional[str], dry_run: bool, skip_existing: bool) -> None:
    """Importer les environnements depuis GestVenv v1.x

    Cette commande importe les environnements virtuels créés avec
    GestVenv v1.x vers la nouvelle structure v2.0.

    Arguments:
        SOURCE_PATH: Chemin vers le répertoire v1.x (défaut: ~/.gestvenv-v1/)

    Exemples:
        gv import-v1-environments
        gv import-v1-environments ~/.gestvenv-v1/
        gv import-v1-environments --dry-run
    """
    try:
        env_manager = EnvironmentManager()

        console.print(Panel.fit(
            "[bold blue]Import Environnements v1.x[/bold blue]"
        ))

        # Déterminer le chemin source
        if source_path:
            v1_path = Path(source_path)
        else:
            # Chemins par défaut
            default_paths = [
                Path.home() / ".gestvenv-v1",
                Path.home() / ".gestvenv_v1",
                Path.home() / ".gestvenv" / "environments_v1"
            ]
            v1_path = None
            for p in default_paths:
                if p.exists():
                    v1_path = p
                    break

            if not v1_path:
                console.print("[yellow]⚠️ Aucun répertoire v1.x trouvé[/yellow]")
                console.print("\nChemins vérifiés:")
                for p in default_paths:
                    console.print(f"  - {p}")
                console.print("\n💡 Spécifiez le chemin: gv import-v1-environments /chemin/vers/v1/")
                return

        console.print(f"📁 Source: {v1_path}")

        # Lister les environnements v1.x
        envs_found = []
        if v1_path.is_dir():
            for item in v1_path.iterdir():
                if item.is_dir():
                    # Vérifier si c'est un environnement virtuel
                    if (item / "pyvenv.cfg").exists() or (item / "bin" / "python").exists():
                        envs_found.append(item)

        if not envs_found:
            console.print("[yellow]Aucun environnement trouvé dans ce répertoire[/yellow]")
            return

        console.print(f"🔍 {len(envs_found)} environnement(s) trouvé(s)\n")

        if dry_run:
            console.print("[yellow]Mode simulation (dry-run)[/yellow]\n")

        # Table des environnements
        table = Table(title="Environnements à importer")
        table.add_column("Nom", style="cyan")
        table.add_column("Python", style="green")
        table.add_column("Taille", style="yellow")
        table.add_column("Status", style="magenta")

        target_path = Path(target) if target else env_manager.config_manager.get_environments_path()

        imported = 0
        skipped = 0

        for env_path in envs_found:
            env_name = env_path.name

            # Détecter version Python
            pyvenv_cfg = env_path / "pyvenv.cfg"
            python_version = "?"
            if pyvenv_cfg.exists():
                try:
                    content = pyvenv_cfg.read_text()
                    for line in content.splitlines():
                        if line.startswith("version"):
                            python_version = line.split("=")[1].strip()
                            break
                except Exception:
                    pass

            # Calculer taille
            size_mb = sum(f.stat().st_size for f in env_path.rglob("*") if f.is_file()) / (1024 * 1024)

            # Vérifier si existe déjà
            target_env = target_path / env_name
            exists = target_env.exists()

            if exists and skip_existing:
                status = "⏭️ Ignoré (existe)"
                skipped += 1
            elif exists:
                status = "⚠️ Existe déjà"
                skipped += 1
            elif dry_run:
                status = "📋 À importer"
            else:
                # Effectuer l'import
                try:
                    shutil.copytree(env_path, target_env)
                    status = "✅ Importé"
                    imported += 1
                except Exception as e:
                    status = f"❌ Erreur: {e}"

            table.add_row(env_name, python_version, f"{size_mb:.1f} MB", status)

        console.print(table)

        console.print(f"\n📊 Résumé:")
        if dry_run:
            console.print(f"   {len(envs_found)} environnement(s) seraient importés")
        else:
            console.print(f"   ✅ {imported} importé(s)")
            console.print(f"   ⏭️ {skipped} ignoré(s)")
            if imported > 0:
                console.print(f"\n💡 Environnements disponibles dans: {target_path}")

    except Exception as e:
        console.print(f"❌ Erreur import: {e}")
        sys.exit(1)


# Enregistrement des groupes de commandes avancées
cli.add_command(diff_group)
cli.add_command(deps_group)
cli.add_command(security_group)
cli.add_command(python_group)


def main() -> None:
    """Point d'entrée principal"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n⚠️ Opération annulée")
        sys.exit(130)
    except Exception as e:
        console.print(f"💥 Erreur inattendue: {e}")
        if '--verbose' in sys.argv:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()