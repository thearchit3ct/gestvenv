"""
Interface en ligne de commande pour GestVenv
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gestvenv.core.environment_manager import EnvironmentManager
from gestvenv.core.exceptions import GestVenvError
from gestvenv.backends.backend_manager import BackendManager
from gestvenv.services.diagnostic_service import DiagnosticService
from gestvenv.services.template_service import TemplateService
from gestvenv.services.migration_service import MigrationService
from gestvenv import __version__

console = Console()

def setup_logging(verbose: bool) -> None:
    """Configure le logging selon le niveau de verbosité"""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="gestvenv")
@click.option('--verbose', '-v', is_flag=True, help='Mode verbeux')
@click.option('--offline', is_flag=True, help='Mode hors ligne')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, offline: bool) -> None:
    """🐍 GestVenv - Gestionnaire d'environnements virtuels Python moderne"""
    setup_logging(verbose)
    
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['offline'] = offline
    ctx.obj['env_manager'] = EnvironmentManager()
    
    if offline:
        ctx.obj['env_manager'].cache_service.set_offline_mode(True)
    
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            f"🐍 [bold green]GestVenv v{__version__}[/bold green]\n"
            f"Gestionnaire d'environnements virtuels Python moderne\n\n"
            f"Utilisez [bold cyan]gestvenv --help[/bold cyan] pour voir toutes les commandes",
            title="GestVenv"
        ))

@cli.command()
@click.argument('name')
@click.option('--python', help='Version Python à utiliser')
@click.option('--backend', type=click.Choice(['pip', 'uv', 'auto']), default='auto')
@click.option('--template', help='Template à utiliser')
@click.pass_context
def create(ctx: click.Context, name: str, python: Optional[str], backend: str, template: Optional[str]) -> None:
    """Créer un nouvel environnement virtuel"""
    env_manager = ctx.obj['env_manager']
    
    try:
        with console.status(f"[bold green]Création de l'environnement {name}..."):
            environment = env_manager.create_environment(
                name=name,
                python_version=python,
                backend=backend if backend != 'auto' else None,
                template=template
            )
        
        console.print(f"✅ Environnement [bold green]{name}[/bold green] créé avec succès!")
        console.print(f"📁 Chemin: {environment.path}")
        console.print(f"🐍 Python: {environment.python_version}")
        console.print(f"🔧 Backend: {environment.backend}")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur lors de la création: {e}")
        sys.exit(1)

@cli.command()
@click.option('--active-only', is_flag=True, help='Afficher seulement les environnements actifs')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def list(ctx: click.Context, active_only: bool, output_format: str) -> None:
    """Lister tous les environnements"""
    env_manager = ctx.obj['env_manager']
    
    try:
        environments = env_manager.list_environments(active_only=active_only)
        
        if output_format == 'json':
            import json
            data = [env.to_dict() for env in environments]
            console.print(json.dumps(data, indent=2))
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
        
        for env in environments:
            status = "🟢 Actif" if env.is_active else "⚪ Inactif"
            table.add_row(
                env.name,
                env.python_version or "inconnu",
                env.backend or "pip",
                str(len(env.packages)),
                status
            )
        
        console.print(table)
        
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
        env_manager.activate_environment(name)
        console.print(f"✅ Environnement [bold green]{name}[/bold green] activé")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.pass_context
def deactivate(ctx: click.Context) -> None:
    """Désactiver l'environnement actuel"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_manager.deactivate_environment()
        console.print("✅ Environnement désactivé")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Forcer la suppression')
@click.pass_context
def delete(ctx: click.Context, name: str, force: bool) -> None:
    """Supprimer un environnement"""
    env_manager = ctx.obj['env_manager']
    
    if not force:
        if not click.confirm(f"Êtes-vous sûr de vouloir supprimer '{name}' ?"):
            console.print("❌ Suppression annulée")
            return
    
    try:
        with console.status(f"[bold red]Suppression de {name}..."):
            env_manager.delete_environment(name)
        console.print(f"✅ Environnement [bold red]{name}[/bold red] supprimé")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.group()
def cache() -> None:
    """Gestion du cache"""
    pass

@cache.command(name='info')
@click.pass_context
def cache_info(ctx: click.Context) -> None:
    """Informations sur le cache"""
    env_manager = ctx.obj['env_manager']
    cache_service = env_manager.cache_service
    
    info = cache_service.get_cache_info()
    
    console.print(Panel.fit(
        f"📦 Taille: {info['size_mb']:.1f} MB\n"
        f"📄 Entrées: {info['entries']}\n"
        f"💾 Ratio compression: {info['compression_ratio']:.1f}%\n"
        f"📍 Chemin: {info['path']}",
        title="🗂️ Cache GestVenv"
    ))

@cache.command(name='clean')
@click.option('--older-than', type=int, help='Supprimer les entrées plus anciennes que N jours')
@click.option('--force', is_flag=True, help='Nettoyage sans confirmation')
@click.pass_context
def cache_clean(ctx: click.Context, older_than: Optional[int], force: bool) -> None:
    """Nettoyer le cache"""
    env_manager = ctx.obj['env_manager']
    cache_service = env_manager.cache_service
    
    if not force:
        if not click.confirm("Nettoyer le cache ?"):
            return
    
    try:
        with console.status("[bold yellow]Nettoyage du cache..."):
            cleaned = cache_service.clean_cache(older_than_days=older_than)
        console.print(f"✅ Cache nettoyé: {cleaned['freed_mb']:.1f} MB libérés")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.group()
def backend() -> None:
    """Gestion des backends"""
    pass

@backend.command(name='list')
def backend_list() -> None:
    """Lister les backends disponibles"""
    backend_manager = BackendManager()
    backends = backend_manager.list_backends()
    
    table = Table(title="🔧 Backends disponibles")
    table.add_column("Nom", style="cyan")
    table.add_column("Disponible", style="green")
    table.add_column("Version", style="yellow")
    table.add_column("Performance", style="magenta")
    
    for backend_info in backends:
        available = "✅" if backend_info['available'] else "❌"
        table.add_row(
            backend_info['name'],
            available,
            backend_info['version'] or "N/A",
            backend_info['performance_tier']
        )
    
    console.print(table)

@backend.command(name='set')
@click.argument('backend_name', type=click.Choice(['pip', 'uv', 'auto']))
def backend_set(backend_name: str) -> None:
    """Définir le backend par défaut"""
    try:
        backend_manager = BackendManager()
        backend_manager.set_default_backend(backend_name)
        console.print(f"✅ Backend par défaut: [bold green]{backend_name}[/bold green]")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name', required=False)
@click.option('--auto-fix', is_flag=True, help='Réparation automatique')
@click.pass_context
def doctor(ctx: click.Context, name: Optional[str], auto_fix: bool) -> None:
    """Diagnostic et réparation"""
    diagnostic_service = DiagnosticService()
    
    try:
        with console.status("[bold blue]Diagnostic en cours..."):
            if name:
                result = diagnostic_service.diagnose_environment(name)
            else:
                result = diagnostic_service.diagnose_system()
        
        if result['status'] == 'healthy':
            console.print("✅ [bold green]Système en bon état[/bold green]")
        else:
            console.print("⚠️ [bold yellow]Problèmes détectés[/bold yellow]")
            
            for issue in result['issues']:
                console.print(f"  - {issue['description']}")
                if auto_fix and issue['fixable']:
                    console.print(f"    🔧 Réparation: {issue['fix_description']}")
        
        if auto_fix and result['issues']:
            with console.status("[bold green]Réparation automatique..."):
                diagnostic_service.auto_fix_issues(result['issues'])
            console.print("✅ Réparations appliquées")
            
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.group()
def template() -> None:
    """Gestion des templates"""
    pass

@template.command(name='list')
def template_list() -> None:
    """Lister les templates disponibles"""
    template_service = TemplateService()
    templates = template_service.list_templates()
    
    table = Table(title="📋 Templates disponibles")
    table.add_column("Nom", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Description", style="yellow")
    
    for tmpl in templates:
        table.add_row(
            tmpl['name'],
            tmpl['type'],
            tmpl['description']
        )
    
    console.print(table)

@cli.command()
@click.argument('req_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Fichier de sortie')
@click.pass_context
def convert_to_pyproject(ctx: click.Context, req_file: str, output: Optional[str]) -> None:
    """Convertir requirements.txt vers pyproject.toml"""
    migration_service = MigrationService()
    
    try:
        req_path = Path(req_file)
        output_path = Path(output) if output else req_path.parent / "pyproject.toml"
        
        with console.status("[bold blue]Conversion en cours..."):
            migration_service.convert_requirements_to_pyproject(req_path, output_path)
        
        console.print(f"✅ Conversion réussie: {output_path}")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

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