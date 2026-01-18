"""
Commande security - Scan de sécurité et licences

Usage:
    gv security scan [env]               # Scan vulnérabilités
    gv security audit --fix              # Audit avec corrections
    gv licenses check [env]              # Vérifier licences
    gv licenses export --format csv      # Exporter licences
"""

import click
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Vulnerability:
    """Vulnérabilité détectée"""
    package: str
    version: str
    vulnerability_id: str
    severity: str
    description: str
    fixed_in: Optional[str] = None


@dataclass
class LicenseInfo:
    """Information de licence"""
    package: str
    version: str
    license: str
    author: str = ""
    home_page: str = ""


@dataclass
class SecurityReport:
    """Rapport de sécurité"""
    scan_date: str
    environment: str
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    total_packages: int = 0
    vulnerable_packages: int = 0


def get_pip_path(env_path: Path) -> Path:
    """Trouve l'exécutable pip dans l'environnement"""
    if (env_path / "bin" / "pip").exists():
        return env_path / "bin" / "pip"
    elif (env_path / "Scripts" / "pip.exe").exists():
        return env_path / "Scripts" / "pip.exe"
    raise click.ClickException(f"pip non trouvé dans {env_path}")


def get_python_path(env_path: Path) -> Path:
    """Trouve l'exécutable Python dans l'environnement"""
    if (env_path / "bin" / "python").exists():
        return env_path / "bin" / "python"
    elif (env_path / "Scripts" / "python.exe").exists():
        return env_path / "Scripts" / "python.exe"
    raise click.ClickException(f"Python non trouvé dans {env_path}")


def scan_vulnerabilities_pip_audit(env_path: Path) -> List[Vulnerability]:
    """Scan avec pip-audit si disponible"""
    vulnerabilities = []
    python_path = get_python_path(env_path)

    try:
        # Vérifier si pip-audit est installé
        check_result = subprocess.run(
            [str(python_path), "-m", "pip_audit", "--version"],
            capture_output=True,
            text=True
        )

        if check_result.returncode != 0:
            return []

        # Exécuter pip-audit
        result = subprocess.run(
            [str(python_path), "-m", "pip_audit", "--format=json", "--progress-spinner=off"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300
        )

        if result.stdout.strip():
            data = json.loads(result.stdout)
            for item in data.get('dependencies', []):
                for vuln in item.get('vulns', []):
                    vulnerabilities.append(Vulnerability(
                        package=item['name'],
                        version=item['version'],
                        vulnerability_id=vuln.get('id', 'UNKNOWN'),
                        severity=vuln.get('fix_versions', ['Unknown'])[0] if vuln.get('fix_versions') else 'Unknown',
                        description=vuln.get('description', 'No description'),
                        fixed_in=vuln.get('fix_versions', [None])[0] if vuln.get('fix_versions') else None
                    ))

    except subprocess.TimeoutExpired:
        click.echo("⚠️ Timeout lors du scan pip-audit", err=True)
    except json.JSONDecodeError:
        pass
    except Exception as e:
        click.echo(f"⚠️ Erreur pip-audit: {e}", err=True)

    return vulnerabilities


def scan_vulnerabilities_safety(env_path: Path) -> List[Vulnerability]:
    """Scan avec safety si disponible"""
    vulnerabilities = []
    pip_path = get_pip_path(env_path)

    try:
        # Générer requirements.txt temporaire
        freeze_result = subprocess.run(
            [str(pip_path), "freeze"],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if freeze_result.returncode != 0:
            return []

        # Essayer safety
        result = subprocess.run(
            ["safety", "check", "--stdin", "--json"],
            input=freeze_result.stdout,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120
        )

        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                for vuln in data.get('vulnerabilities', []):
                    vulnerabilities.append(Vulnerability(
                        package=vuln.get('package_name', 'unknown'),
                        version=vuln.get('analyzed_version', 'unknown'),
                        vulnerability_id=vuln.get('vulnerability_id', 'UNKNOWN'),
                        severity=vuln.get('severity', 'unknown'),
                        description=vuln.get('advisory', 'No description'),
                        fixed_in=vuln.get('fixed_versions', [None])[0] if vuln.get('fixed_versions') else None
                    ))
            except json.JSONDecodeError:
                pass

    except FileNotFoundError:
        # safety n'est pas installé
        pass
    except subprocess.TimeoutExpired:
        click.echo("⚠️ Timeout lors du scan safety", err=True)
    except Exception as e:
        click.echo(f"⚠️ Erreur safety: {e}", err=True)

    return vulnerabilities


def scan_vulnerabilities(env_path: Path) -> SecurityReport:
    """Scan complet des vulnérabilités"""
    pip_path = get_pip_path(env_path)

    # Compter les packages
    list_result = subprocess.run(
        [str(pip_path), "list", "--format=json"],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    total_packages = 0
    if list_result.returncode == 0:
        total_packages = len(json.loads(list_result.stdout))

    # Collecter les vulnérabilités de toutes les sources
    all_vulns = []

    # Essayer pip-audit
    vulns = scan_vulnerabilities_pip_audit(env_path)
    all_vulns.extend(vulns)

    # Essayer safety si pip-audit n'a rien trouvé
    if not all_vulns:
        vulns = scan_vulnerabilities_safety(env_path)
        all_vulns.extend(vulns)

    # Dédupliquer par package + vulnerability_id
    seen = set()
    unique_vulns = []
    for v in all_vulns:
        key = (v.package, v.vulnerability_id)
        if key not in seen:
            seen.add(key)
            unique_vulns.append(v)

    vulnerable_packages = len(set(v.package for v in unique_vulns))

    return SecurityReport(
        scan_date=datetime.now().isoformat(),
        environment=str(env_path),
        vulnerabilities=unique_vulns,
        total_packages=total_packages,
        vulnerable_packages=vulnerable_packages
    )


def get_licenses(env_path: Path) -> List[LicenseInfo]:
    """Récupère les informations de licence de tous les packages"""
    pip_path = get_pip_path(env_path)
    licenses = []

    try:
        # Liste des packages
        list_result = subprocess.run(
            [str(pip_path), "list", "--format=json"],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if list_result.returncode != 0:
            return []

        packages = json.loads(list_result.stdout)

        for pkg in packages:
            # Obtenir les métadonnées
            show_result = subprocess.run(
                [str(pip_path), "show", pkg['name']],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            license_name = "Unknown"
            author = ""
            home_page = ""

            if show_result.returncode == 0:
                for line in show_result.stdout.split('\n'):
                    if line.startswith('License:'):
                        license_name = line.split(':', 1)[1].strip() or "Unknown"
                    elif line.startswith('Author:'):
                        author = line.split(':', 1)[1].strip()
                    elif line.startswith('Home-page:'):
                        home_page = line.split(':', 1)[1].strip()

            licenses.append(LicenseInfo(
                package=pkg['name'],
                version=pkg['version'],
                license=license_name,
                author=author,
                home_page=home_page
            ))

    except Exception as e:
        raise click.ClickException(f"Erreur récupération licences: {e}")

    return licenses


def format_security_report(report: SecurityReport, output_json: bool = False) -> str:
    """Formate le rapport de sécurité"""
    if output_json:
        return json.dumps({
            "scan_date": report.scan_date,
            "environment": report.environment,
            "total_packages": report.total_packages,
            "vulnerable_packages": report.vulnerable_packages,
            "vulnerabilities": [
                {
                    "package": v.package,
                    "version": v.version,
                    "id": v.vulnerability_id,
                    "severity": v.severity,
                    "description": v.description,
                    "fixed_in": v.fixed_in
                } for v in report.vulnerabilities
            ]
        }, indent=2)

    lines = []
    lines.append("🔒 Rapport de sécurité")
    lines.append("=" * 60)
    lines.append(f"Date: {report.scan_date}")
    lines.append(f"Environnement: {report.environment}")
    lines.append(f"Packages analysés: {report.total_packages}")
    lines.append("")

    if not report.vulnerabilities:
        lines.append("✅ Aucune vulnérabilité connue détectée!")
    else:
        lines.append(f"⚠️ {len(report.vulnerabilities)} vulnérabilités détectées dans {report.vulnerable_packages} packages:")
        lines.append("-" * 60)

        for vuln in sorted(report.vulnerabilities, key=lambda x: x.package):
            lines.append(f"\n📦 {vuln.package}=={vuln.version}")
            lines.append(f"   ID: {vuln.vulnerability_id}")
            lines.append(f"   Sévérité: {vuln.severity}")
            if vuln.fixed_in:
                lines.append(f"   Corrigé dans: {vuln.fixed_in}")
            lines.append(f"   {vuln.description[:100]}...")

    lines.append("\n" + "=" * 60)
    lines.append(f"📊 Résumé: {report.vulnerable_packages}/{report.total_packages} packages vulnérables")

    return "\n".join(lines)


def format_licenses(licenses: List[LicenseInfo], output_format: str = "table") -> str:
    """Formate la liste des licences"""
    if output_format == "json":
        return json.dumps([
            {
                "package": l.package,
                "version": l.version,
                "license": l.license,
                "author": l.author,
                "home_page": l.home_page
            } for l in licenses
        ], indent=2)

    if output_format == "csv":
        lines = ["package,version,license,author,home_page"]
        for l in sorted(licenses, key=lambda x: x.package):
            lines.append(f'"{l.package}","{l.version}","{l.license}","{l.author}","{l.home_page}"')
        return "\n".join(lines)

    # Table format
    lines = []
    lines.append("📜 Licences des packages")
    lines.append("=" * 80)
    lines.append(f"{'Package':<30} {'Version':<15} {'Licence':<30}")
    lines.append("-" * 80)

    for l in sorted(licenses, key=lambda x: x.package):
        license_short = l.license[:27] + "..." if len(l.license) > 30 else l.license
        lines.append(f"{l.package:<30} {l.version:<15} {license_short:<30}")

    lines.append("-" * 80)
    lines.append(f"Total: {len(licenses)} packages")

    # Statistiques par licence
    license_counts: Dict[str, int] = {}
    for l in licenses:
        lic = l.license.split(',')[0].strip()  # Prendre la première licence si multiple
        license_counts[lic] = license_counts.get(lic, 0) + 1

    lines.append("\n📊 Répartition par licence:")
    for lic, count in sorted(license_counts.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"  {lic}: {count}")

    return "\n".join(lines)


@click.group(name='security')
def security_group():
    """Scan de sécurité et audit"""
    pass


@security_group.command(name='scan')
@click.argument('env_name', required=False)
@click.option('--json', 'output_json', is_flag=True, help='Sortie au format JSON')
@click.pass_context
def security_scan(ctx, env_name: Optional[str], output_json: bool):
    """Scanner les vulnérabilités de sécurité"""
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

    click.echo("🔍 Scan de sécurité en cours...")
    click.echo("   (Utilise pip-audit et/ou safety si disponibles)")

    report = scan_vulnerabilities(env_path)
    output = format_security_report(report, output_json)
    click.echo(output)

    # Code de sortie basé sur les vulnérabilités
    if report.vulnerabilities:
        sys.exit(1)


@security_group.command(name='licenses')
@click.argument('env_name', required=False)
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='Format de sortie')
@click.option('--output', '-o', type=click.Path(), help='Fichier de sortie')
@click.pass_context
def security_licenses(ctx, env_name: Optional[str], output_format: str, output: Optional[str]):
    """Vérifier et exporter les licences"""
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

    click.echo("📜 Collecte des informations de licence...")
    licenses = get_licenses(env_path)
    result = format_licenses(licenses, output_format)

    if output:
        Path(output).write_text(result, encoding='utf-8')
        click.echo(f"✅ Licences exportées vers {output}")
    else:
        click.echo(result)
