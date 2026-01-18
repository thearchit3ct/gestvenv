"""
Commande deps - Analyse des dépendances

Usage:
    gv deps tree [env]                   # Arbre de dépendances
    gv deps outdated [env]               # Packages obsolètes
    gv deps check [env]                  # Vérifier conflits
"""

import click
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class DependencyNode:
    """Noeud dans l'arbre de dépendances"""
    name: str
    version: str
    dependencies: List['DependencyNode'] = field(default_factory=list)
    required_by: List[str] = field(default_factory=list)


@dataclass
class OutdatedPackage:
    """Package obsolète"""
    name: str
    current_version: str
    latest_version: str
    package_type: str = "unknown"


def get_pip_path(env_path: Path) -> Path:
    """Trouve l'exécutable pip dans l'environnement"""
    if (env_path / "bin" / "pip").exists():
        return env_path / "bin" / "pip"
    elif (env_path / "Scripts" / "pip.exe").exists():
        return env_path / "Scripts" / "pip.exe"
    raise click.ClickException(f"pip non trouvé dans {env_path}")


def get_dependency_tree(env_path: Path) -> Dict[str, DependencyNode]:
    """Construit l'arbre de dépendances"""
    pip_path = get_pip_path(env_path)
    nodes = {}

    try:
        # Obtenir la liste des packages avec leurs dépendances
        result = subprocess.run(
            [str(pip_path), "show", "--files"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Obtenir les métadonnées détaillées
        list_result = subprocess.run(
            [str(pip_path), "list", "--format=json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if list_result.returncode == 0:
            packages = json.loads(list_result.stdout)
            for pkg in packages:
                name = pkg['name'].lower()
                nodes[name] = DependencyNode(
                    name=pkg['name'],
                    version=pkg['version']
                )

        # Obtenir les dépendances de chaque package
        for name in list(nodes.keys()):
            show_result = subprocess.run(
                [str(pip_path), "show", name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if show_result.returncode == 0:
                for line in show_result.stdout.split('\n'):
                    if line.startswith('Requires:'):
                        deps = line.split(':', 1)[1].strip()
                        if deps:
                            for dep in deps.split(','):
                                dep_name = dep.strip().lower()
                                if dep_name and dep_name in nodes:
                                    nodes[name].dependencies.append(nodes[dep_name])
                                    nodes[dep_name].required_by.append(name)

    except Exception as e:
        raise click.ClickException(f"Erreur analyse dépendances: {e}")

    return nodes


def get_outdated_packages(env_path: Path) -> List[OutdatedPackage]:
    """Liste les packages obsolètes"""
    pip_path = get_pip_path(env_path)
    outdated = []

    try:
        result = subprocess.run(
            [str(pip_path), "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120
        )

        if result.returncode == 0 and result.stdout.strip():
            packages = json.loads(result.stdout)
            for pkg in packages:
                outdated.append(OutdatedPackage(
                    name=pkg['name'],
                    current_version=pkg['version'],
                    latest_version=pkg['latest_version'],
                    package_type=pkg.get('latest_filetype', 'unknown')
                ))

    except subprocess.TimeoutExpired:
        raise click.ClickException("Timeout lors de la vérification des mises à jour")
    except Exception as e:
        raise click.ClickException(f"Erreur vérification mises à jour: {e}")

    return outdated


def check_dependency_conflicts(env_path: Path) -> List[str]:
    """Vérifie les conflits de dépendances"""
    pip_path = get_pip_path(env_path)
    conflicts = []

    try:
        result = subprocess.run(
            [str(pip_path), "check"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode != 0:
            # Parser les conflits
            for line in result.stdout.split('\n'):
                if line.strip():
                    conflicts.append(line.strip())

    except Exception as e:
        raise click.ClickException(f"Erreur vérification conflits: {e}")

    return conflicts


def format_tree(
    nodes: Dict[str, DependencyNode],
    output_json: bool = False
) -> str:
    """Formate l'arbre de dépendances"""
    if output_json:
        def node_to_dict(node: DependencyNode) -> dict:
            return {
                "name": node.name,
                "version": node.version,
                "dependencies": [d.name for d in node.dependencies],
                "required_by": node.required_by
            }
        return json.dumps({
            name: node_to_dict(node) for name, node in nodes.items()
        }, indent=2)

    lines = []
    lines.append("📦 Arbre de dépendances")
    lines.append("=" * 60)

    # Trouver les packages racine (non requis par d'autres)
    root_packages = [
        node for node in nodes.values()
        if not node.required_by
    ]

    def print_node(node: DependencyNode, prefix: str = "", is_last: bool = True, visited: Set[str] = None):
        if visited is None:
            visited = set()

        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{node.name}=={node.version}")

        if node.name.lower() in visited:
            return
        visited.add(node.name.lower())

        new_prefix = prefix + ("    " if is_last else "│   ")
        deps = node.dependencies
        for i, dep in enumerate(deps):
            is_last_dep = (i == len(deps) - 1)
            print_node(dep, new_prefix, is_last_dep, visited.copy())

    for i, node in enumerate(sorted(root_packages, key=lambda x: x.name)):
        is_last = (i == len(root_packages) - 1)
        print_node(node, "", is_last)

    lines.append(f"\n📊 Total: {len(nodes)} packages")
    lines.append(f"   Racines: {len(root_packages)}")

    return "\n".join(lines)


def format_outdated(packages: List[OutdatedPackage], output_json: bool = False) -> str:
    """Formate la liste des packages obsolètes"""
    if output_json:
        return json.dumps([
            {
                "name": p.name,
                "current": p.current_version,
                "latest": p.latest_version,
                "type": p.package_type
            } for p in packages
        ], indent=2)

    if not packages:
        return "✅ Tous les packages sont à jour!"

    lines = []
    lines.append("📦 Packages obsolètes")
    lines.append("=" * 60)
    lines.append(f"{'Package':<30} {'Actuel':<15} {'Dernier':<15}")
    lines.append("-" * 60)

    for pkg in sorted(packages, key=lambda x: x.name):
        lines.append(f"{pkg.name:<30} {pkg.current_version:<15} {pkg.latest_version:<15}")

    lines.append("-" * 60)
    lines.append(f"Total: {len(packages)} packages à mettre à jour")

    return "\n".join(lines)


@click.group(name='deps')
def deps_group():
    """Analyser les dépendances"""
    pass


@deps_group.command(name='tree')
@click.argument('env_name', required=False)
@click.option('--json', 'output_json', is_flag=True, help='Sortie au format JSON')
@click.pass_context
def deps_tree(ctx, env_name: Optional[str], output_json: bool):
    """Afficher l'arbre de dépendances"""
    env_manager = ctx.obj.get('env_manager') if ctx.obj else None

    if env_name:
        if env_manager:
            env_path = env_manager.get_environment_path(env_name)
        else:
            env_path = Path(env_name)
    else:
        # Utiliser l'environnement actif ou le venv local
        env_path = Path('.venv')
        if not env_path.exists():
            env_path = Path('venv')

    if not env_path.exists():
        raise click.ClickException(f"Environnement non trouvé: {env_path}")

    nodes = get_dependency_tree(env_path)
    output = format_tree(nodes, output_json)
    click.echo(output)


@deps_group.command(name='outdated')
@click.argument('env_name', required=False)
@click.option('--json', 'output_json', is_flag=True, help='Sortie au format JSON')
@click.pass_context
def deps_outdated(ctx, env_name: Optional[str], output_json: bool):
    """Lister les packages obsolètes"""
    env_manager = ctx.obj.get('env_manager') if ctx.obj else None

    if env_name:
        if env_manager:
            env_path = env_manager.get_environment_path(env_name)
        else:
            env_path = Path(env_name)
    else:
        env_path = Path('.venv')
        if not env_path.exists():
            env_path = Path('venv')

    if not env_path.exists():
        raise click.ClickException(f"Environnement non trouvé: {env_path}")

    click.echo("🔍 Vérification des mises à jour disponibles...")
    packages = get_outdated_packages(env_path)
    output = format_outdated(packages, output_json)
    click.echo(output)


@deps_group.command(name='check')
@click.argument('env_name', required=False)
@click.option('--json', 'output_json', is_flag=True, help='Sortie au format JSON')
@click.pass_context
def deps_check(ctx, env_name: Optional[str], output_json: bool):
    """Vérifier les conflits de dépendances"""
    env_manager = ctx.obj.get('env_manager') if ctx.obj else None

    if env_name:
        if env_manager:
            env_path = env_manager.get_environment_path(env_name)
        else:
            env_path = Path(env_name)
    else:
        env_path = Path('.venv')
        if not env_path.exists():
            env_path = Path('venv')

    if not env_path.exists():
        raise click.ClickException(f"Environnement non trouvé: {env_path}")

    conflicts = check_dependency_conflicts(env_path)

    if output_json:
        click.echo(json.dumps({"conflicts": conflicts, "has_conflicts": len(conflicts) > 0}, indent=2))
        return

    if not conflicts:
        click.echo("✅ Aucun conflit de dépendances détecté!")
    else:
        click.echo("⚠️ Conflits de dépendances détectés:")
        click.echo("=" * 60)
        for conflict in conflicts:
            click.echo(f"  ❌ {conflict}")
        click.echo(f"\nTotal: {len(conflicts)} conflits")
