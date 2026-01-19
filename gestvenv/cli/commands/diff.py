"""
Commande diff - Comparaison d'environnements

Usage:
    gv diff env1 env2                    # Comparer deux environnements
    gv diff env1 requirements.txt        # Comparer env vs fichier
    gv diff env1 pyproject.toml          # Comparer env vs pyproject
"""

import click
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class PackageInfo:
    """Information sur un package"""
    name: str
    version: str

    def __hash__(self):
        return hash((self.name.lower(), self.version))

    def __eq__(self, other):
        if isinstance(other, PackageInfo):
            return self.name.lower() == other.name.lower() and self.version == other.version
        return False


@dataclass
class DiffResult:
    """Résultat de comparaison"""
    only_in_first: List[PackageInfo]
    only_in_second: List[PackageInfo]
    version_diff: List[Tuple[PackageInfo, PackageInfo]]
    common: List[PackageInfo]


def get_env_packages(env_path: Path) -> Dict[str, str]:
    """Récupère les packages installés dans un environnement"""
    packages = {}

    # Trouver l'exécutable pip
    if (env_path / "bin" / "pip").exists():
        pip_path = env_path / "bin" / "pip"
    elif (env_path / "Scripts" / "pip.exe").exists():
        pip_path = env_path / "Scripts" / "pip.exe"
    else:
        raise click.ClickException(f"pip non trouvé dans {env_path}")

    try:
        result = subprocess.run(
            [str(pip_path), "list", "--format=json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            pkg_list = json.loads(result.stdout)
            for pkg in pkg_list:
                packages[pkg['name'].lower()] = pkg['version']
    except Exception as e:
        raise click.ClickException(f"Erreur lecture packages: {e}")

    return packages


def parse_requirements(file_path: Path) -> Dict[str, str]:
    """Parse un fichier requirements.txt"""
    packages = {}

    content = file_path.read_text(encoding='utf-8')
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue

        # Parser les différents formats
        if '==' in line:
            name, version = line.split('==', 1)
            packages[name.strip().lower()] = version.strip()
        elif '>=' in line:
            name = line.split('>=')[0]
            packages[name.strip().lower()] = f">={line.split('>=')[1].strip()}"
        elif '~=' in line:
            name = line.split('~=')[0]
            packages[name.strip().lower()] = f"~={line.split('~=')[1].strip()}"
        else:
            # Package sans version
            packages[line.lower()] = "*"

    return packages


def parse_pyproject(file_path: Path) -> Dict[str, str]:
    """Parse un fichier pyproject.toml"""
    packages = {}

    try:
        import toml
        data = toml.load(file_path)
    except ImportError:
        # Fallback sans toml
        content = file_path.read_text(encoding='utf-8')
        # Parser basique
        in_deps = False
        for line in content.split('\n'):
            if '[project.dependencies]' in line or '[tool.poetry.dependencies]' in line:
                in_deps = True
                continue
            if in_deps:
                if line.startswith('['):
                    break
                if '=' in line or '"' in line:
                    # Extraire le nom du package
                    parts = line.strip().strip('"').strip("'").split()
                    if parts:
                        pkg = parts[0].split('>=')[0].split('==')[0].split('<')[0]
                        packages[pkg.lower()] = "*"
        return packages

    # Avec toml
    deps = data.get('project', {}).get('dependencies', [])
    if not deps:
        deps = list(data.get('tool', {}).get('poetry', {}).get('dependencies', {}).keys())

    for dep in deps:
        if isinstance(dep, str):
            parts = dep.replace('>=', '==').replace('~=', '==').split('==')
            name = parts[0].strip()
            version = parts[1].strip() if len(parts) > 1 else "*"
            packages[name.lower()] = version

    return packages


def compare_packages(
    first: Dict[str, str],
    second: Dict[str, str],
    first_name: str,
    second_name: str
) -> DiffResult:
    """Compare deux ensembles de packages"""
    first_keys = set(first.keys())
    second_keys = set(second.keys())

    only_first = first_keys - second_keys
    only_second = second_keys - first_keys
    common_keys = first_keys & second_keys

    only_in_first = [PackageInfo(name, first[name]) for name in sorted(only_first)]
    only_in_second = [PackageInfo(name, second[name]) for name in sorted(only_second)]

    version_diff = []
    common = []

    for name in sorted(common_keys):
        v1, v2 = first[name], second[name]
        if v1 != v2 and v1 != "*" and v2 != "*":
            version_diff.append((
                PackageInfo(name, v1),
                PackageInfo(name, v2)
            ))
        else:
            common.append(PackageInfo(name, v1))

    return DiffResult(only_in_first, only_in_second, version_diff, common)


def format_diff_output(
    result: DiffResult,
    first_name: str,
    second_name: str,
    show_common: bool = False,
    output_json: bool = False
) -> str:
    """Formate le résultat de la comparaison"""
    if output_json:
        return json.dumps({
            "only_in_first": [{"name": p.name, "version": p.version} for p in result.only_in_first],
            "only_in_second": [{"name": p.name, "version": p.version} for p in result.only_in_second],
            "version_diff": [
                {"name": p1.name, "first": p1.version, "second": p2.version}
                for p1, p2 in result.version_diff
            ],
            "common_count": len(result.common)
        }, indent=2)

    lines = []

    # Header
    lines.append(f"Comparaison: {first_name} vs {second_name}")
    lines.append("=" * 60)

    # Seulement dans le premier
    if result.only_in_first:
        lines.append(f"\n📦 Uniquement dans {first_name} ({len(result.only_in_first)}):")
        for pkg in result.only_in_first:
            lines.append(f"  - {pkg.name}=={pkg.version}")

    # Seulement dans le second
    if result.only_in_second:
        lines.append(f"\n📦 Uniquement dans {second_name} ({len(result.only_in_second)}):")
        for pkg in result.only_in_second:
            lines.append(f"  + {pkg.name}=={pkg.version}")

    # Différences de versions
    if result.version_diff:
        lines.append(f"\n🔄 Versions différentes ({len(result.version_diff)}):")
        for pkg1, pkg2 in result.version_diff:
            lines.append(f"  ~ {pkg1.name}: {pkg1.version} → {pkg2.version}")

    # Communs
    if show_common and result.common:
        lines.append(f"\n✓ Packages identiques ({len(result.common)}):")
        for pkg in result.common:
            lines.append(f"  = {pkg.name}=={pkg.version}")

    # Résumé
    lines.append(f"\n📊 Résumé:")
    lines.append(f"  - Uniquement dans {first_name}: {len(result.only_in_first)}")
    lines.append(f"  - Uniquement dans {second_name}: {len(result.only_in_second)}")
    lines.append(f"  - Versions différentes: {len(result.version_diff)}")
    lines.append(f"  - Packages identiques: {len(result.common)}")

    return "\n".join(lines)


@click.group(name='diff')
def diff_group():
    """Comparer des environnements et fichiers de dépendances"""
    pass


@diff_group.command(name='envs')
@click.argument('env1')
@click.argument('env2')
@click.option('--show-common', is_flag=True, help='Afficher les packages communs')
@click.option('--json', 'output_json', is_flag=True, help='Sortie au format JSON')
@click.pass_context
def diff_envs(ctx, env1: str, env2: str, show_common: bool, output_json: bool):
    """Comparer deux environnements virtuels"""
    env_manager = ctx.obj.get('env_manager') if ctx.obj else None

    # Résoudre les chemins des environnements
    if env_manager:
        env1_path = env_manager.get_environment_path(env1)
        env2_path = env_manager.get_environment_path(env2)
    else:
        env1_path = Path(env1)
        env2_path = Path(env2)

    if not env1_path.exists():
        raise click.ClickException(f"Environnement non trouvé: {env1}")
    if not env2_path.exists():
        raise click.ClickException(f"Environnement non trouvé: {env2}")

    # Récupérer les packages
    packages1 = get_env_packages(env1_path)
    packages2 = get_env_packages(env2_path)

    # Comparer
    result = compare_packages(packages1, packages2, env1, env2)

    # Afficher
    output = format_diff_output(result, env1, env2, show_common, output_json)
    click.echo(output)


@diff_group.command(name='file')
@click.argument('env_name')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--show-common', is_flag=True, help='Afficher les packages communs')
@click.option('--json', 'output_json', is_flag=True, help='Sortie au format JSON')
@click.pass_context
def diff_file(ctx, env_name: str, file_path: str, show_common: bool, output_json: bool):
    """Comparer un environnement avec un fichier (requirements.txt ou pyproject.toml)"""
    env_manager = ctx.obj.get('env_manager') if ctx.obj else None
    file_path = Path(file_path)

    # Résoudre le chemin de l'environnement
    if env_manager:
        env_path = env_manager.get_environment_path(env_name)
    else:
        env_path = Path(env_name)

    if not env_path.exists():
        raise click.ClickException(f"Environnement non trouvé: {env_name}")

    # Récupérer les packages de l'environnement
    env_packages = get_env_packages(env_path)

    # Parser le fichier
    if file_path.suffix == '.txt' or 'requirements' in file_path.name:
        file_packages = parse_requirements(file_path)
    elif file_path.suffix == '.toml':
        file_packages = parse_pyproject(file_path)
    else:
        raise click.ClickException(f"Format de fichier non supporté: {file_path.suffix}")

    # Comparer
    result = compare_packages(env_packages, file_packages, env_name, file_path.name)

    # Afficher
    output = format_diff_output(result, env_name, file_path.name, show_common, output_json)
    click.echo(output)
