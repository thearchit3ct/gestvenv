"""
Template Data Science
"""

from typing import Dict, List, Any
from ..base_template import ProjectTemplate, TemplateFile


class DataScienceTemplate(ProjectTemplate):
    """Template pour projets de Data Science"""
    
    def __init__(self):
        super().__init__(
            name="data-science",
            description="Projet Data Science avec Jupyter et librairies ML",
            category="data",
            dependencies=[
                "pandas>=2.0.0",
                "numpy>=1.24.0",
                "matplotlib>=3.7.0",
                "seaborn>=0.12.0",
                "scikit-learn>=1.3.0",
                "jupyter>=1.0.0",
                "ipykernel>=6.25.0",
                "jupyterlab>=4.0.0"
            ],
            dev_dependencies=[
                "pytest>=7.0.0",
                "black>=23.0.0",
                "isort>=5.12.0",
                "nbstripout>=0.6.0",
                "pre-commit>=3.0.0"
            ]
        )
        
    def get_files(self) -> List[TemplateFile]:
        return [
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
    "Notebook d'exploration pour le projet {{project_name}}"
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
    "plt.style.use('seaborn-v0_8')\\n",
    "sns.set_palette('husl')\\n",
    "%matplotlib inline"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Chargement des données"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Charger vos données ici\\n",
    "# df = pd.read_csv('data/raw/dataset.csv')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.11.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}''',
                is_template=True
            ),
            TemplateFile(
                path="{{package_name}}/__init__.py",
                content='"""{{project_name}} - Projet Data Science"""\n\n__version__ = "{{version}}"\n'
            ),
            TemplateFile(
                path="{{package_name}}/data/__init__.py",
                content='"""Module de gestion des données"""'
            ),
            TemplateFile(
                path="{{package_name}}/data/loader.py",
                content='''"""Chargement et préparation des données"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class DataLoader:
    """Classe pour charger et préparer les données"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        
    def load_raw_data(self, filename: str) -> pd.DataFrame:
        """Charge les données brutes"""
        filepath = self.raw_dir / filename
        if filepath.suffix == '.csv':
            return pd.read_csv(filepath)
        elif filepath.suffix == '.parquet':
            return pd.read_parquet(filepath)
        else:
            raise ValueError(f"Format non supporté: {filepath.suffix}")
    
    def save_processed_data(self, df: pd.DataFrame, filename: str) -> None:
        """Sauvegarde les données traitées"""
        self.processed_dir.mkdir(exist_ok=True)
        filepath = self.processed_dir / filename
        
        if filepath.suffix == '.csv':
            df.to_csv(filepath, index=False)
        elif filepath.suffix == '.parquet':
            df.to_parquet(filepath, index=False)
        else:
            raise ValueError(f"Format non supporté: {filepath.suffix}")
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prépare les features pour le ML"""
        # Votre logique de préparation ici
        return df
    
    def split_data(self, df: pd.DataFrame, target_col: str, 
                  test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Divise les données en train/test"""
        from sklearn.model_selection import train_test_split
        
        X = df.drop(columns=[target_col])
        y = df[target_col]
        
        return train_test_split(X, y, test_size=test_size, random_state=42)
'''
            ),
            TemplateFile(
                path="{{package_name}}/models/__init__.py",
                content='"""Module des modèles ML"""'
            ),
            TemplateFile(
                path="{{package_name}}/visualization/__init__.py",
                content='"""Module de visualisation"""'
            ),
            TemplateFile(
                path="data/raw/.gitkeep",
                content="",
                is_template=False
            ),
            TemplateFile(
                path="data/processed/.gitkeep", 
                content="",
                is_template=False
            ),
            TemplateFile(
                path="data/external/.gitkeep",
                content="",
                is_template=False
            ),
            TemplateFile(
                path="models/.gitkeep",
                content="",
                is_template=False
            ),
            TemplateFile(
                path="reports/.gitkeep",
                content="",
                is_template=False
            ),
            TemplateFile(
                path=".gitignore",
                content='''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Data files
data/raw/*
!data/raw/.gitkeep
data/processed/*
!data/processed/.gitkeep
data/external/*
!data/external/.gitkeep

# Models
models/*
!models/.gitkeep

# Jupyter Notebook
.ipynb_checkpoints

# Virtual environments
venv/
env/
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
''',
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
                    "ml": ["xgboost>=1.7.0", "lightgbm>=4.0.0"],
                    "deep": ["tensorflow>=2.13.0", "torch>=2.0.0"],
                    "nlp": ["spacy>=3.6.0", "transformers>=4.30.0"]
                }
            },
            "build-system": {
                "requires": ["setuptools>=61.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            },
            "tool": {
                "black": {
                    "line-length": 88,
                    "target-version": ["py38"]
                },
                "isort": {
                    "profile": "black",
                    "line_length": 88
                }
            }
        }