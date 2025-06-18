"""
Template d'application CLI
"""

from typing import Dict, List, Any
from ..base_template import ProjectTemplate, TemplateFile


class CLITemplate(ProjectTemplate):
    """Template pour applications en ligne de commande"""
    
    def __init__(self):
        super().__init__(
            name="cli",
            description="Application en ligne de commande avec Click",
            category="cli",
            dependencies=[
                "click>=8.1.0",
                "rich>=13.0.0"
            ],
            dev_dependencies=[
                "pytest>=7.0.0",
                "black>=23.0.0",
                "isort>=5.12.0"
            ]
        )
        
    def get_files(self) -> List[TemplateFile]:
        return [
            TemplateFile(
                path="{{package_name}}/__init__.py",
                content='"""{{project_name}} - Application CLI"""\n\n__version__ = "{{version}}"\n'
            ),
            TemplateFile(
                path="{{package_name}}/cli.py",
                content='''"""Interface en ligne de commande"""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option()
def cli():
    """{{description}}"""
    pass


@cli.command()
@click.option('--name', default='World', help='Nom à saluer')
def hello(name):
    """Commande de salutation"""
    console.print(f"Hello {name}!", style="bold green")


@cli.command()
def status():
    """Affiche le statut de l'application"""
    table = Table(title="{{project_name}} Status")
    table.add_column("Composant", style="cyan")
    table.add_column("Statut", style="green")
    
    table.add_row("Application", "✅ Actif")
    table.add_row("Version", "{{version}}")
    
    console.print(table)


if __name__ == '__main__':
    cli()
'''
            ),
            TemplateFile(
                path="{{package_name}}/main.py",
                content='''"""Point d'entrée principal"""

from .cli import cli

if __name__ == '__main__':
    cli()
'''
            ),
            TemplateFile(
                path="tests/test_cli.py",
                content='''"""Tests de l'interface CLI"""

from click.testing import CliRunner
from {{package_name}}.cli import cli


def test_hello():
    """Test commande hello"""
    runner = CliRunner()
    result = runner.invoke(cli, ['hello'])
    assert result.exit_code == 0
    assert 'Hello World!' in result.output


def test_hello_with_name():
    """Test commande hello avec nom"""
    runner = CliRunner()
    result = runner.invoke(cli, ['hello', '--name', 'Test'])
    assert result.exit_code == 0
    assert 'Hello Test!' in result.output


def test_status():
    """Test commande status"""
    runner = CliRunner()
    result = runner.invoke(cli, ['status'])
    assert result.exit_code == 0
'''
            )
        ]
        
    def get_pyproject_config(self) -> Dict[str, Any]:
        return {
            "project": {
                "name": "{{project_name}}",
                "version": "{{version}}",
                "description": "{{description}}",
                "authors": [{"name": "{{author}}", "email": "{{email}}"}],
                "license": {"text": "{{license}}"},
                "readme": "README.md", 
                "requires-python": ">=3.8",
                "dependencies": self.dependencies,
                "optional-dependencies": {
                    "dev": self.dev_dependencies
                },
                "scripts": {
                    "{{package_name}}": "{{package_name}}.cli:cli"
                }
            },
            "build-system": {
                "requires": ["setuptools>=61.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            }
        }