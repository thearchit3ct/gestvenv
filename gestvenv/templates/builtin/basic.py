"""
Template de projet Python basique
"""

from typing import Dict, List, Any
from ..base_template import ProjectTemplate, TemplateFile


class BasicTemplate(ProjectTemplate):
    """Template pour un projet Python basique"""
    
    def __init__(self):
        super().__init__(
            name="basic",
            description="Projet Python basique avec structure standard",
            category="general",
            dependencies=[],
            dev_dependencies=[
                "pytest>=7.0.0",
                "pytest-cov>=4.0.0"
            ]
        )
        
    def get_files(self) -> List[TemplateFile]:
        return [
            TemplateFile(
                path="src/{{package_name}}/__init__.py",
                content='"""{{project_name}} - {{description}}"""\n\n__version__ = "{{version}}"\n'
            ),
            TemplateFile(
                path="src/{{package_name}}/main.py", 
                content='''"""Module principal de {{project_name}}"""


def main():
    """Point d'entrée principal"""
    print("Hello from {{project_name}}!")


if __name__ == "__main__":
    main()
'''
            ),
            TemplateFile(
                path="tests/__init__.py",
                content="",
                is_template=False
            ),
            TemplateFile(
                path="tests/test_main.py",
                content='''"""Tests pour le module principal"""

import pytest
from {{package_name}}.main import main


def test_main(capsys):
    """Test de la fonction main"""
    main()
    captured = capsys.readouterr()
    assert "Hello from {{project_name}}!" in captured.out
'''
            ),
            TemplateFile(
                path="README.md",
                content='''# {{project_name}}

{{description}}

## Installation

```bash
pip install -e .