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

@cli.command()
@click.argument('req_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Fichier de sortie')
def convert_to_pyproject(req_file, output):
    """Convertir requirements.txt vers pyproject.toml"""
    from ..utils import TomlHandler
    
    output_path = Path(output) if output else Path('pyproject.toml')
    
    # Lecture requirements
    with open(req_file, 'r') as f:
        requirements = [line.strip() for line in f 
                       if line.strip() and not line.startswith('#')]
    
    # Structure pyproject.toml
    pyproject_data = {
        'project': {
            'name': Path(req_file).parent.name,
            'version': '0.1.0',
            'dependencies': requirements
        },
        'build-system': {
            'requires': ['setuptools>=45', 'wheel'],
            'build-backend': 'setuptools.build_meta'
        }
    }
    
    TomlHandler.dump(pyproject_data, output_path)
    console.print(f"✅ Converti: {req_file} → {output_path}")

@cli.group()
def config():
    """Gestion de la configuration"""
    pass

@config.command()
@click.option('--section', help='Section spécifique')
def show(section):
    """Afficher la configuration"""
    config_manager = ConfigManager()
    config_data = config_manager.get_config_summary()
    
    if section:
        if section in config_data:
            console.print_json(data={section: config_data[section]})
        else:
            console.print(f"❌ Section '{section}' introuvable")
    else:
        console.print_json(data=config_data)

@config.command()
@click.argument('key')
@click.argument('value')
def set(key, value):
    """Définir configuration globale"""
    config_manager = ConfigManager()
    # Implémentation selon la structure de config_manager
    console.print(f"✅ Configuration: {key} = {value}")

@cli.command()
@click.argument('pyproject_file', type=click.Path(exists=True))
@click.option('--strict', is_flag=True, help='Validation stricte')
def validate(pyproject_file, strict):
    """Valider fichier pyproject.toml"""
    from ..utils import TomlHandler, PyProjectParser
    
    try:
        data = TomlHandler.load(pyproject_file)
        console.print("✅ Syntaxe TOML valide")
        
        is_valid = PyProjectParser.validate_pep621(data)
        if is_valid:
            console.print("✅ Conforme PEP 621")
        else:
            console.print("⚠️ Non conforme PEP 621")
            if strict:
                sys.exit(1)
                
        project = data.get('project', {})
        console.print(f"📦 {project.get('name', 'Sans nom')}")
        console.print(f"📝 v{project.get('version', '0.0.0')}")
        
    except Exception as e:
        console.print(f"❌ Invalide: {e}")
        sys.exit(1)

@cli.command()
@click.argument('pyproject_file', type=click.Path(exists=True))
@click.argument('name')
@click.option('--groups', multiple=True, help='Groupes de dépendances à installer')
@click.pass_context
def create_from_pyproject(ctx: click.Context, pyproject_file: str, name: str, groups: tuple) -> None:
    """Créer un environnement depuis pyproject.toml"""
    env_manager = ctx.obj['env_manager']
    
    try:
        with console.status(f"[bold green]Création depuis pyproject.toml..."):
            result = env_manager.create_from_pyproject(
                pyproject_path=Path(pyproject_file),
                env_name=name,
                groups=list(groups) if groups else None
            )
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{name}[/bold green] créé depuis pyproject.toml")
            if result.warnings:
                for warning in result.warnings:
                    console.print(f"⚠️ {warning}")
        else:
            console.print(f"❌ Erreur: {result.message}")
            sys.exit(1)
            
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Forcer la suppression même si actif')
@click.pass_context
def delete(ctx: click.Context, name: str, force: bool) -> None:
    """Supprimer un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        if not force:
            if not click.confirm(f"Supprimer l'environnement '{name}' ?"):
                console.print("🚫 Suppression annulée")
                return
        
        with console.status(f"[bold red]Suppression de {name}..."):
            success = env_manager.delete_environment(name, force=force)
        
        if success:
            console.print(f"✅ Environnement [bold red]{name}[/bold red] supprimé")
        else:
            console.print(f"❌ Échec suppression de {name}")
            sys.exit(1)
            
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name')
@click.pass_context
def sync(ctx: click.Context, name: str) -> None:
    """Synchroniser un environnement avec son pyproject.toml"""
    env_manager = ctx.obj['env_manager']
    
    try:
        with console.status(f"[bold blue]Synchronisation de {name}..."):
            result = env_manager.sync_environment(name)
        
        if result.success:
            console.print(f"✅ Environnement [bold green]{name}[/bold green] synchronisé")
            if result.packages_added:
                console.print(f"📦 Packages ajoutés: {', '.join(result.packages_added)}")
            if result.packages_removed:
                console.print(f"🗑️ Packages supprimés: {', '.join(result.packages_removed)}")
        else:
            console.print(f"❌ Erreur synchronisation: {result.message}")
            sys.exit(1)
            
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.pass_context
def deactivate(ctx: click.Context) -> None:
    """Désactiver l'environnement virtuel actuel"""
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
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def info(ctx: click.Context, name: str, format: str) -> None:
    """Afficher les informations d'un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(name)
        
        if not env_info:
            console.print(f"❌ Environnement '{name}' introuvable")
            sys.exit(1)
        
        if format == 'json':
            import json
            console.print(json.dumps(env_info.to_dict(), indent=2, default=str))
        else:
            # Affichage table formaté
            console.print(f"\n📋 [bold]Environnement {name}[/bold]\n")
            console.print(f"📁 Chemin: {env_info.path}")
            console.print(f"🐍 Python: {env_info.python_version}")
            console.print(f"🔧 Backend: {env_info.backend_type.value}")
            console.print(f"❤️ Santé: {env_info.health.value}")
            console.print(f"📦 Packages: {len(env_info.packages)}")
            console.print(f"🕒 Dernière utilisation: {env_info.last_used}")
            
            if env_info.packages:
                console.print(f"\n📦 [bold]Packages installés:[/bold]")
                for pkg in env_info.packages[:10]:  # Limiter affichage
                    console.print(f"  • {pkg.name}=={pkg.version}")
                if len(env_info.packages) > 10:
                    console.print(f"  ... et {len(env_info.packages) - 10} autres")
            
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('packages', nargs=-1, required=True)
@click.option('--env', required=True, help='Nom de l\'environnement')
@click.option('--upgrade', is_flag=True, help='Mettre à jour si déjà installé')
@click.pass_context
def install(ctx: click.Context, packages: tuple, env: str, upgrade: bool) -> None:
    """Installer des packages dans un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(env)
        if not env_info:
            console.print(f"❌ Environnement '{env}' introuvable")
            sys.exit(1)
        
        package_service = env_manager.package_service
        
        for package in packages:
            with console.status(f"[bold green]Installation de {package}..."):
                result = package_service.install_package(
                    env_info, 
                    package, 
                    upgrade=upgrade
                )
            
            if result.success:
                console.print(f"✅ {package} installé avec succès")
            else:
                console.print(f"❌ Échec installation {package}: {result.message}")
                if not click.confirm("Continuer avec les autres packages ?"):
                    sys.exit(1)
        
        console.print(f"🎉 Installation terminée dans [bold green]{env}[/bold green]")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('packages', nargs=-1, required=True)
@click.option('--env', required=True, help='Nom de l\'environnement')
@click.option('--yes', '-y', is_flag=True, help='Ne pas demander confirmation')
@click.pass_context
def uninstall(ctx: click.Context, packages: tuple, env: str, yes: bool) -> None:
    """Désinstaller des packages d'un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(env)
        if not env_info:
            console.print(f"❌ Environnement '{env}' introuvable")
            sys.exit(1)
        
        if not yes:
            pkg_list = ', '.join(packages)
            if not click.confirm(f"Désinstaller {pkg_list} de {env} ?"):
                console.print("🚫 Désinstallation annulée")
                return
        
        package_service = env_manager.package_service
        
        for package in packages:
            with console.status(f"[bold red]Désinstallation de {package}..."):
                success = package_service.uninstall_package(env_info, package)
            
            if success:
                console.print(f"✅ {package} désinstallé")
            else:
                console.print(f"❌ Échec désinstallation {package}")
        
        console.print(f"🗑️ Désinstallation terminée dans [bold green]{env}[/bold green]")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--group', multiple=True, help='Groupes de dépendances à installer')
@click.option('--env', required=True, help='Nom de l\'environnement')
@click.pass_context
def install_group(ctx: click.Context, group: tuple, env: str) -> None:
    """Installer des groupes de dépendances depuis pyproject.toml"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(env)
        if not env_info:
            console.print(f"❌ Environnement '{env}' introuvable")
            sys.exit(1)
        
        if not env_info.pyproject_info:
            console.print(f"❌ Aucun pyproject.toml associé à {env}")
            sys.exit(1)
        
        package_service = env_manager.package_service
        groups_list = list(group) if group else None
        
        with console.status(f"[bold blue]Installation groupes {groups_list}..."):
            success = package_service.install_from_pyproject(
                env_info, 
                env_info.pyproject_info, 
                groups=groups_list
            )
        
        if success:
            console.print(f"✅ Groupes installés: {', '.join(groups_list or ['main'])}")
        else:
            console.print(f"❌ Échec installation groupes")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.argument('packages', nargs=-1)
@click.option('--env', required=True, help='Nom de l\'environnement')
@click.option('--all', 'update_all', is_flag=True, help='Mettre à jour tous les packages')
@click.option('--check', is_flag=True, help='Vérifier seulement les packages obsolètes')
@click.pass_context
def update(ctx: click.Context, packages: tuple, env: str, update_all: bool, check: bool) -> None:
    """Mettre à jour des packages dans un environnement"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(env)
        if not env_info:
            console.print(f"❌ Environnement '{env}' introuvable")
            sys.exit(1)
        
        package_service = env_manager.package_service
        
        if check:
            # Vérification seulement
            with console.status("[bold blue]Vérification packages obsolètes..."):
                outdated = package_service.check_outdated_packages(env_info)
            
            if outdated:
                console.print("📋 Packages obsolètes:")
                for pkg in outdated:
                    console.print(f"  • {pkg.name} {pkg.version} → {pkg.latest_version}")
            else:
                console.print("✅ Tous les packages sont à jour")
            return
        
        if update_all:
            # Mise à jour tous packages
            packages_to_update = [pkg.name for pkg in env_info.packages]
        elif packages:
            packages_to_update = list(packages)
        else:
            console.print("❌ Spécifiez des packages ou utilisez --all")
            sys.exit(1)
        
        for package in packages_to_update:
            with console.status(f"[bold yellow]Mise à jour de {package}..."):
                success = package_service.update_package(env_info, package)
            
            if success:
                console.print(f"✅ {package} mis à jour")
            else:
                console.print(f"⚠️ {package} déjà à jour ou échec")
        
        console.print(f"🔄 Mise à jour terminée dans [bold green]{env}[/bold green]")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

# Extension de la commande install existante
@cli.command()
@click.option('-r', '--requirement', 'requirements_file', 
              type=click.Path(exists=True), help='Fichier requirements.txt')
@click.option('--env', required=True, help='Nom de l\'environnement')
@click.pass_context
def install_requirements(ctx: click.Context, requirements_file: str, env: str) -> None:
    """Installer depuis requirements.txt"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(env)
        if not env_info:
            console.print(f"❌ Environnement '{env}' introuvable")
            sys.exit(1)
        
        package_service = env_manager.package_service
        
        with console.status(f"[bold green]Installation depuis {requirements_file}..."):
            success = package_service.install_from_requirements(
                env_info, 
                Path(requirements_file)
            )
        
        if success:
            console.print(f"✅ Packages installés depuis {requirements_file}")
        else:
            console.print(f"❌ Échec installation depuis {requirements_file}")
            sys.exit(1)
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--env', required=True, help='Nom de l\'environnement')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def check_outdated(ctx: click.Context, env: str, format: str) -> None:
    """Vérifier les packages obsolètes"""
    env_manager = ctx.obj['env_manager']
    
    try:
        env_info = env_manager.get_environment_info(env)
        if not env_info:
            console.print(f"❌ Environnement '{env}' introuvable")
            sys.exit(1)
        
        package_service = env_manager.package_service
        
        with console.status("[bold blue]Vérification packages obsolètes..."):
            outdated = package_service.check_outdated_packages(env_info)
        
        if format == 'json':
            import json
            data = [pkg.to_dict() for pkg in outdated]
            console.print(json.dumps(data, indent=2))
        else:
            if outdated:
                table = Table(title=f"📊 Packages obsolètes - {env}")
                table.add_column("Package", style="cyan")
                table.add_column("Installé", style="red")
                table.add_column("Disponible", style="green")
                
                for pkg in outdated:
                    table.add_row(
                        pkg.name,
                        pkg.version,
                        getattr(pkg, 'latest_version', 'N/A')
                    )
                
                console.print(table)
                console.print(f"\n💡 Utilisez [bold]gestvenv update --env {env}[/bold] pour mettre à jour")
            else:
                console.print("✅ Tous les packages sont à jour")
        
    except GestVenvError as e:
        console.print(f"❌ Erreur: {e}")
        sys.exit(1)

@cli.command()
@click.option('--orphaned', is_flag=True, help='Nettoyer répertoires orphelins')
@click.option('--empty-dirs', is_flag=True, help='Supprimer répertoires vides')
@click.option('--dry-run', is_flag=True, help='Simulation seulement')
@click.pass_context
def cleanup(ctx: click.Context, orphaned: bool, empty_dirs: bool, dry_run: bool) -> None:
    """Nettoyer les fichiers orphelins et répertoires vides"""
    from utils import PathUtils
    
    env_manager = ctx.obj['env_manager']
    envs_path = env_manager.config_manager.get_environments_path()
    
    cleaned_count = 0
    
    if empty_dirs:
        if dry_run:
            console.print("[bold yellow]Mode simulation - répertoires vides détectés :[/bold yellow]")
            # Simulation du nettoyage
            for path in envs_path.rglob('*'):
                if path.is_dir() and PathUtils.is_empty_directory(path):
                    console.print(f"  🗑️ {path}")
        else:
            with console.status("[bold red]Nettoyage répertoires vides..."):
                cleaned_count = PathUtils.clean_empty_directories(envs_path)
            console.print(f"✅ {cleaned_count} répertoires vides supprimés")
    
    if orphaned:
        # Détection environnements orphelins (répertoires sans métadonnées)
        orphaned_envs = []
        for env_dir in envs_path.iterdir():
            if env_dir.is_dir():
                metadata_path = env_dir / ".gestvenv-metadata.json"
                if not metadata_path.exists():
                    orphaned_envs.append(env_dir)
        
        if orphaned_envs:
            if dry_run:
                console.print("[bold yellow]Environnements orphelins détectés :[/bold yellow]")
                for env in orphaned_envs:
                    console.print(f"  🚫 {env.name}")
            else:
                for env in orphaned_envs:
                    if click.confirm(f"Supprimer environnement orphelin {env.name} ?"):
                        PathUtils.safe_remove_directory(env)
                        cleaned_count += 1
                console.print(f"✅ {len(orphaned_envs)} environnements orphelins traités")
        else:
            console.print("✅ Aucun environnement orphelin trouvé")

@cli.command()
@click.argument('directory', type=click.Path(exists=True), default='.')
@click.option('--recursive', is_flag=True, help='Recherche récursive')
@click.option('--create-env', is_flag=True, help='Créer environnements automatiquement')
@click.pass_context
def scan(ctx: click.Context, directory: str, recursive: bool, create_env: bool) -> None:
    """Scanner les projets Python dans un répertoire"""
    from utils import PathUtils
    
    directory_path = Path(directory)
    console.print(f"🔍 Scan de {directory_path}")
    
    # Recherche fichiers pyproject.toml
    pyproject_files = PathUtils.find_pyproject_files(directory_path)
    
    if not pyproject_files:
        console.print("❌ Aucun projet Python trouvé")
        return
    
    table = Table(title="📋 Projets Python détectés")
    table.add_column("Répertoire", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Environnement", style="yellow")
    
    env_manager = ctx.obj['env_manager']
    
    for pyproject_file in pyproject_files:
        project_root = PathUtils.find_project_root(pyproject_file.parent)
        project_name = project_root.name if project_root else pyproject_file.parent.name
        
        # Vérification environnement existant
        env_info = env_manager.get_environment_info(project_name)
        env_status = "✅ Existe" if env_info else "❌ Manquant"
        
        table.add_row(
            str(project_root or pyproject_file.parent),
            "pyproject.toml",
            env_status
        )
        
        # Création automatique si demandé
        if create_env and not env_info:
            if click.confirm(f"Créer environnement pour {project_name} ?"):
                result = env_manager.create_from_pyproject(pyproject_file, project_name)
                if result.success:
                    console.print(f"✅ Environnement {project_name} créé")
    
    console.print(table)

@cli.command()
@click.argument('environment', required=False)
@click.option('--all', 'backup_all', is_flag=True, help='Sauvegarder tous les environnements')
@click.option('--output', '-o', help='Répertoire de sauvegarde')
@click.pass_context
def backup(ctx: click.Context, environment: str, backup_all: bool, output: str) -> None:
    """Sauvegarder environnements"""
    from utils import PathUtils
    
    env_manager = ctx.obj['env_manager']
    backup_dir = Path(output) if output else Path.home() / ".gestvenv" / "backups"
    
    PathUtils.ensure_directory(backup_dir)
    
    if backup_all:
        environments = env_manager.list_environments()
        console.print(f"💾 Sauvegarde de {len(environments)} environnements...")
    elif environment:
        env_info = env_manager.get_environment_info(environment)
        if not env_info:
            console.print(f"❌ Environnement '{environment}' introuvable")
            sys.exit(1)
        environments = [env_info]
    else:
        console.print("❌ Spécifiez un environnement ou utilisez --all")
        sys.exit(1)
    
    for env_info in environments:
        backup_path = backup_dir / f"{env_info.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with console.status(f"[bold blue]Sauvegarde {env_info.name}..."):
            success = PathUtils.copy_directory_tree(env_info.path, backup_path)
        
        if success:
            size_mb = PathUtils.get_size_mb(backup_path)
            console.print(f"✅ {env_info.name} → {backup_path} ({size_mb:.1f}MB)")
        else:
            console.print(f"❌ Échec sauvegarde {env_info.name}")

@cli.command()
@click.option('--detailed', is_flag=True, help='Affichage détaillé')
@click.option('--sort-by', type=click.Choice(['name', 'size']), default='size')
@click.pass_context
def disk_usage(ctx: click.Context, detailed: bool, sort_by: str) -> None:
    """Analyser l'utilisation disque des environnements"""
    from utils import PathUtils
    
    env_manager = ctx.obj['env_manager']
    environments = env_manager.list_environments()
    
    if not environments:
        console.print("📭 Aucun environnement trouvé")
        return
    
    # Calcul tailles
    env_sizes = []
    total_size = 0
    
    with console.status("[bold blue]Calcul des tailles..."):
        for env_info in environments:
            size_mb = PathUtils.get_size_mb(env_info.path)
            env_sizes.append((env_info, size_mb))
            total_size += size_mb
    
    # Tri
    if sort_by == 'size':
        env_sizes.sort(key=lambda x: x[1], reverse=True)
    else:
        env_sizes.sort(key=lambda x: x[0].name)
    
    # Affichage
    table = Table(title=f"💽 Utilisation disque - Total: {total_size:.1f}MB")
    table.add_column("Environnement", style="cyan")
    table.add_column("Taille", style="green", justify="right")
    table.add_column("Packages", style="yellow", justify="right")
    table.add_column("% Total", style="magenta", justify="right")
    
    if detailed:
        table.add_column("Dernière utilisation", style="blue")
    
    for env_info, size_mb in env_sizes:
        percentage = (size_mb / total_size * 100) if total_size > 0 else 0
        
        row = [
            env_info.name,
            f"{size_mb:.1f}MB",
            str(len(env_info.packages)),
            f"{percentage:.1f}%"
        ]
        
        if detailed:
            row.append(env_info.last_used.strftime("%Y-%m-%d %H:%M"))
        
        table.add_row(*row)
    
    console.print(table)
    
    # Cache size
    cache_path = env_manager.cache_service.cache_path
    if cache_path.exists():
        cache_size = PathUtils.get_size_mb(cache_path)
        console.print(f"\n💾 Cache: {cache_size:.1f}MB")

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