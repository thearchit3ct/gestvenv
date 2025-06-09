"""
Template de projet data science
"""

from typing import Dict, List, Any
from ..base_template import ProjectTemplate, TemplateFile


class DataScienceTemplate(ProjectTemplate):
    """Template pour projets de data science"""
    
    def __init__(self):
        super().__init__(
            name="data_science",
            description="Projet de data science avec Jupyter et librairies ML",
            category="data",
            dependencies=[
                "pandas>=2.0.0",
                "numpy>=1.24.0", 
                "matplotlib>=3.7.0",
                "seaborn>=0.12.0",
                "scikit-learn>=1.3.0",
                "jupyter>=1.0.0"
            ],
            dev_dependencies=[
                "pytest>=7.0.0",
                "black>=23.0.0",
                "isort>=5.12.0",
                "mypy>=1.0.0"
            ]
        )
        
    def get_files(self) -> List[TemplateFile]:
        return [
            TemplateFile(
                path="{{package_name}}/__init__.py",
                content='"""{{project_name}} - Projet de data science"""\n\n__version__ = "{{version}}"\n'
            ),
            TemplateFile(
                path="{{package_name}}/data/__init__.py",
                content="",
                is_template=False
            ),
            TemplateFile(
                path="{{package_name}}/models/__init__.py", 
                content="",
                is_template=False
            ),
            TemplateFile(
                path="{{package_name}}/utils/__init__.py",
                content="",
                is_template=False
            ),
            TemplateFile(
                path="notebooks/01_exploration.ipynb",
                content='''{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# {{project_name}} - Exploration des données\\n",
    "\\n",
    "Notebook d'exploration initial"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\\n",
    "import numpy as np\\n",
    "import matplotlib.pyplot as plt\\n",
    "import seaborn as sns\\n",
    "\\n",
    "# Configuration\\n",
    "plt.style.use('default')\\n",
    "sns.set_palette('husl')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python", 
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}''',
                is_template=False
            ),
            TemplateFile(
                path="data/.gitkeep",
                content="",
                is_template=False
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
                    "dev": self.dev_dependencies,
                    "viz": ["plotly>=5.0.0", "bokeh>=3.0.0"],
                    "ml": ["tensorflow>=2.13.0", "torch>=2.0.0"]
                }
            },
            "build-system": {
                "requires": ["setuptools>=61.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            }
        }