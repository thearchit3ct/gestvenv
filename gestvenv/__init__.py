# Package initialization
"""
GestVenv - Gestionnaire d'Environnements Virtuels Python.

GestVenv est un outil qui simplifie et centralise la gestion des environnements virtuels Python,
offrant une alternative unifiée aux outils existants comme venv, virtualenv et pipenv.
"""

__version__ = "1.0.0"
__author__ = "Votre nom"
__email__ = "votre.email@exemple.com"
__license__ = "MIT"

# Imports pour faciliter l'accès depuis l'extérieur
from .core.env_manager import EnvironmentManager

# Fonction pratique pour obtenir la version
def get_version():
    """Retourne la version actuelle de GestVenv."""
    return __version__