"""Configuration et fixtures pour les tests de GestVenv."""

import os
import sys
import pytest
from pathlib import Path
import shutil
import tempfile
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

# Ajouter le répertoire parent au chemin pour importer gestvenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Fixtures pour les tests
@pytest.fixture
def temp_dir():
    """Crée un répertoire temporaire pour les tests."""
    tmp_dir = tempfile.mkdtemp()
    yield Path(tmp_dir)
    # Nettoyer après les tests
    shutil.rmtree(tmp_dir)

@pytest.fixture
def temp_config_file(temp_dir):
    """Crée un fichier de configuration temporaire pour les tests."""
    config_file = temp_dir / "config.json"
    
    # Configuration par défaut pour les tests
    config = {
        "environments": {
            "test_env": {
                "path": str(temp_dir / "environments" / "test_env"),
                "python_version": "3.9.0",
                "created_at": datetime.now().isoformat(),
                "packages": ["pytest", "flask"]
            }
        },
        "active_env": "test_env",
        "default_python": "python3"
    }
    
    # Créer le répertoire parent si nécessaire
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Écrire la configuration
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    yield config_file
    
    # Nettoyage
    if config_file.exists():
        config_file.unlink()

@pytest.fixture
def mock_env_path(temp_dir):
    """Crée un faux environnement virtuel pour les tests."""
    env_path = temp_dir / "environments" / "test_env"
    
    # Créer la structure de base d'un environnement virtuel
    (env_path / "pyvenv.cfg").parent.mkdir(parents=True, exist_ok=True)
    with open(env_path / "pyvenv.cfg", 'w') as f:
        f.write("home = /usr/bin\nversion = 3.9.0\n")
    
    # Créer les répertoires bin/Scripts
    bin_dir = env_path / ("Scripts" if os.name == 'nt' else "bin")
    bin_dir.mkdir(exist_ok=True)
    
    # Créer des fichiers python et pip factices
    python_exe = bin_dir / ("python.exe" if os.name == 'nt' else "python")
    pip_exe = bin_dir / ("pip.exe" if os.name == 'nt' else "pip")
    activate_script = bin_dir / ("activate.bat" if os.name == 'nt' else "activate")
    
    python_exe.touch()
    pip_exe.touch()
    activate_script.touch()
    
    yield env_path

@pytest.fixture
def mock_package_list():
    """Retourne une liste simulée de packages installés."""
    return [
        {"name": "pytest", "version": "6.2.5"},
        {"name": "flask", "version": "2.0.1"},
        {"name": "click", "version": "8.0.1"}
    ]

@pytest.fixture
def mock_outdated_packages():
    """Retourne une liste simulée de packages pouvant être mis à jour."""
    return [
        {"name": "pytest", "version": "6.2.5", "latest_version": "7.0.0"},
        {"name": "flask", "version": "2.0.1", "latest_version": "2.1.0"}
    ]

@pytest.fixture
def mock_subprocess():
    """Simule les appels subprocess pour les tests."""
    with patch('subprocess.run') as mock_run:
        # Configurer le mock pour retourner un résultat réussi par défaut
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        yield mock_run