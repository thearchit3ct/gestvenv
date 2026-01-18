"""
Commande python - Gestionnaire de versions Python

Usage:
    gv python install 3.12           # Installer Python 3.12
    gv python list                   # Versions installées
    gv python list --available       # Versions disponibles
    gv python use 3.11              # Définir version par défaut
    gv python remove 3.10           # Supprimer une version
    gv python which                  # Version active
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from ...python import PythonVersionManager, PythonVersion


def get_manager() -> PythonVersionManager:
    """Récupère le gestionnaire de versions Python"""
    return PythonVersionManager()


def format_version_table(versions, installed_versions=None, active_version=None) -> str:
    """Formate un tableau de versions"""
    lines = []
    lines.append("┌─────────────┬──────────┬──────────────┐")
    lines.append("│ Version     │ Status   │ Path         │")
    lines.append("├─────────────┼──────────┼──────────────┤")

    installed_set = {str(i.version) for i in (installed_versions or [])}
    active_str = str(active_version.version) if active_version else None

    for v in versions:
        v_str = str(v)
        if v_str == active_str:
            status = "✓ active"
            color = "\033[32m"  # Green
        elif v_str in installed_set:
            status = "installed"
            color = "\033[33m"  # Yellow
        else:
            status = "available"
            color = ""

        reset = "\033[0m" if color else ""
        lines.append(f"│ {color}{v_str:<11}{reset} │ {status:<8} │              │")

    lines.append("└─────────────┴──────────┴──────────────┘")
    return "\n".join(lines)


@click.group(name='python')
def python_group():
    """Gérer les versions Python"""
    pass


@python_group.command(name='install')
@click.argument('version')
@click.option('--force', is_flag=True, help='Forcer la réinstallation')
def python_install(version: str, force: bool):
    """Installer une version de Python"""
    manager = get_manager()

    # Vérifier si déjà installée
    if not force and manager.is_installed(version):
        click.echo(f"✓ Python {version} est déjà installé")
        return

    click.echo(f"📥 Installation de Python {version}...")

    def progress_callback(progress):
        pct = progress.percent
        bar_width = 30
        filled = int(pct / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        mb_done = progress.downloaded_bytes / (1024 * 1024)
        mb_total = progress.total_bytes / (1024 * 1024)
        click.echo(f"\r  [{bar}] {pct:.1f}% ({mb_done:.1f}/{mb_total:.1f} MB)", nl=False)

    result = manager.install(version, progress_callback)
    click.echo()  # Nouvelle ligne après la barre de progression

    if result.success:
        click.echo(f"✅ {result.message}")
        if result.installation:
            click.echo(f"   📍 Chemin: {result.installation.path}")
    else:
        click.echo(f"❌ {result.message}")
        sys.exit(1)


@python_group.command(name='list')
@click.option('--available', '-a', is_flag=True, help='Afficher les versions disponibles')
@click.option('--prerelease', is_flag=True, help='Inclure les versions préliminaires')
@click.option('--json', 'output_json', is_flag=True, help='Sortie JSON')
def python_list(available: bool, prerelease: bool, output_json: bool):
    """Lister les versions Python"""
    manager = get_manager()

    if available:
        versions = manager.list_available(include_prerelease=prerelease)
        installed = manager.list_installed()
        active = manager.get_active()

        if output_json:
            data = {
                "available": [str(v) for v in versions],
                "installed": [str(i.version) for i in installed],
                "active": str(active.version) if active else None
            }
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo("📦 Versions Python disponibles:")
            click.echo(format_version_table(versions, installed, active))
            click.echo(f"\nTotal: {len(versions)} versions")
    else:
        installed = manager.list_installed()
        active = manager.get_active()

        if output_json:
            data = {
                "installed": [
                    {
                        "version": str(i.version),
                        "path": str(i.path),
                        "active": active and str(i.version) == str(active.version),
                        "source": i.source
                    }
                    for i in installed
                ],
                "active": str(active.version) if active else None
            }
            click.echo(json.dumps(data, indent=2))
        else:
            if not installed:
                click.echo("📦 Aucune version Python installée via GestVenv")
                click.echo("   Utilisez 'gv python install 3.12' pour installer")
                return

            click.echo("📦 Versions Python installées:")
            click.echo("┌─────────────┬──────────┬─────────────────────────────────┐")
            click.echo("│ Version     │ Status   │ Path                            │")
            click.echo("├─────────────┼──────────┼─────────────────────────────────┤")

            for inst in sorted(installed, key=lambda x: x.version, reverse=True):
                is_active = active and str(inst.version) == str(active.version)
                status = "✓ active" if is_active else "installed"
                path_str = str(inst.path)
                if len(path_str) > 30:
                    path_str = "..." + path_str[-27:]
                click.echo(f"│ {str(inst.version):<11} │ {status:<8} │ {path_str:<31} │")

            click.echo("└─────────────┴──────────┴─────────────────────────────────┘")
            click.echo(f"\nTotal: {len(installed)} versions installées")


@python_group.command(name='use')
@click.argument('version')
def python_use(version: str):
    """Définir la version Python par défaut"""
    manager = get_manager()

    if not manager.is_installed(version):
        click.echo(f"❌ Python {version} n'est pas installé")
        click.echo(f"   Utilisez 'gv python install {version}' pour l'installer")
        sys.exit(1)

    if manager.use(version):
        click.echo(f"✅ Python {version} est maintenant la version par défaut")
    else:
        click.echo(f"❌ Impossible de définir Python {version} comme version par défaut")
        sys.exit(1)


@python_group.command(name='remove')
@click.argument('version')
@click.option('--force', is_flag=True, help='Forcer la suppression même si active')
@click.confirmation_option(prompt='Êtes-vous sûr de vouloir supprimer cette version?')
def python_remove(version: str, force: bool):
    """Supprimer une version de Python"""
    manager = get_manager()

    result = manager.remove(version, force=force)

    if result.success:
        click.echo(f"✅ {result.message}")
    else:
        click.echo(f"❌ {result.message}")
        sys.exit(1)


@python_group.command(name='which')
def python_which():
    """Afficher le chemin de la version Python active"""
    manager = get_manager()

    path = manager.which()

    if path:
        click.echo(f"🐍 Python actif: {path}")

        # Afficher la version
        active = manager.get_active()
        if active:
            click.echo(f"   Version: {active.version}")
    else:
        click.echo("❌ Aucune version Python active")
        click.echo("   Utilisez 'gv python install 3.12' puis 'gv python use 3.12'")
        sys.exit(1)


@python_group.command(name='detect')
@click.option('--json', 'output_json', is_flag=True, help='Sortie JSON')
def python_detect(output_json: bool):
    """Détecter les installations Python système"""
    manager = get_manager()

    click.echo("🔍 Détection des installations Python...")
    detected = manager.detect_system_pythons()

    if output_json:
        data = [
            {
                "version": str(d.version),
                "path": str(d.path),
                "source": d.source
            }
            for d in detected
        ]
        click.echo(json.dumps(data, indent=2))
    else:
        if not detected:
            click.echo("   Aucune installation Python détectée")
            return

        click.echo(f"   {len(detected)} installation(s) détectée(s):")
        for d in detected:
            click.echo(f"   • Python {d.version} - {d.path} ({d.source})")
