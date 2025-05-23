# Guide de test

Ce document détaille la stratégie de test pour GestVenv, expliquant les différents niveaux de tests, les outils utilisés et les bonnes pratiques à suivre pour maintenir la qualité du code.

## Philosophie de test

GestVenv suit une approche de développement guidée par les tests (TDD) et vise une couverture de test élevée. L'objectif est de garantir que :

1. Chaque fonctionnalité fonctionne comme prévu
2. Les régressions sont détectées rapidement
3. Le code est modulaire et testable
4. La documentation reste synchronisée avec le comportement réel

## Types de tests

### Tests unitaires

Les tests unitaires vérifient le comportement de composants individuels en isolation.

**Localisation** : `tests/unit/`

**Exemples** :
- Tests des validateurs
- Tests des gestionnaires de chemins
- Tests des fonctions utilitaires

```python
# tests/unit/test_validators.py
import unittest
from gestvenv.utils.validators import validate_env_name

class TestValidators(unittest.TestCase):
    def test_validate_env_name_valid(self):
        # Noms valides
        self.assertTrue(validate_env_name("projet_test"))
        self.assertTrue(validate_env_name("projet-test"))
        self.assertTrue(validate_env_name("projet123"))
        
    def test_validate_env_name_invalid(self):
        # Noms invalides
        self.assertFalse(validate_env_name(""))
        self.assertFalse(validate_env_name(" "))
        self.assertFalse(validate_env_name("projet/test"))
        self.assertFalse(validate_env_name("projet\\test"))
```

### Tests d'intégration

Les tests d'intégration vérifient l'interaction entre plusieurs composants.

**Localisation** : `tests/integration/`

**Exemples** :
- Tests de l'interaction entre EnvManager et ConfigManager
- Tests de l'interaction entre PackageManager et EnvManager
- Tests des commandes CLI avec les managers

```python
# tests/integration/test_env_creation.py
import unittest
import tempfile
import shutil
from pathlib import Path
from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.env_manager import EnvManager

class TestEnvCreation(unittest.TestCase):
    def setUp(self):
        # Créer un répertoire temporaire pour les tests
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_path = self.test_dir / "config.json"
        
        # Initialiser les managers
        self.config_manager = ConfigManager(self.config_path)
        self.env_manager = EnvManager(self.config_manager)
    
    def tearDown(self):
        # Nettoyer après les tests
        shutil.rmtree(self.test_dir)
    
    def test_create_and_list_environment(self):
        # Créer un environnement
        self.env_manager.create_environment("test_env")
        
        # Vérifier qu'il apparaît dans la liste
        envs = self.env_manager.list_environments()
        self.assertIn("test_env", envs)
        
        # Vérifier que le répertoire existe
        env_path = self.config_manager.get_env_config("test_env").get("path")
        self.assertTrue(Path(env_path).exists())
```

### Tests système

Les tests système vérifient le comportement de l'application dans son ensemble.

**Localisation** : `tests/system/`

**Exemples** :
- Tests de flux complets (création, installation, suppression)
- Tests de scénarios d'utilisation réels
- Tests d'interface CLI de bout en bout

```python
# tests/system/test_workflow.py
import unittest
import subprocess
import tempfile
import os
import shutil

class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_dir = os.getcwd()
        os.chdir(self.test_dir)
        os.environ["GESTVENV_CONFIG_DIR"] = self.test_dir
        
    def tearDown(self):
        os.chdir(self.old_dir)
        shutil.rmtree(self.test_dir)
        
    def test_create_install_export_workflow(self):
        # Créer un environnement
        result = subprocess.run(
            ["gestvenv", "create", "test_project"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Installer des packages
        result = subprocess.run(
            ["gestvenv", "install", "pytest", "--env", "test_project"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Exporter la configuration
        result = subprocess.run(
            ["gestvenv", "export", "test_project", "--output", "config.json"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.exists("config.json"))
```

### Tests de performances

Les tests de performances mesurent l'efficacité de l'application dans différentes conditions.

**Localisation** : `tests/performance/`

**Exemples** :
- Tests de temps de création d'environnements
- Tests de consommation mémoire
- Tests de comportement avec de nombreux environnements

```python
# tests/performance/test_creation_time.py
import unittest
import time
import tempfile
import shutil
from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.env_manager import EnvManager

class TestCreationPerformance(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(f"{self.test_dir}/config.json")
        self.env_manager = EnvManager(self.config_manager)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_environment_creation_time(self):
        start_time = time.time()
        self.env_manager.create_environment("perf_test")
        end_time = time.time()
        
        creation_time = end_time - start_time
        print(f"Environment creation time: {creation_time:.2f} seconds")
        
        # La création ne devrait pas prendre plus de 10 secondes
        self.assertLess(creation_time, 10.0)
```

## Outils de test

### pytest

GestVenv utilise pytest comme framework de test principal.

**Installation** :
```bash
pip install pytest pytest-cov
```

**Exécution des tests** :
```bash
# Exécuter tous les tests
pytest

# Exécuter un module spécifique
pytest tests/unit/test_validators.py

# Exécuter avec couverture de code
pytest --cov=gestvenv
```

### tox

tox est utilisé pour tester sur différentes versions de Python et dans des environnements isolés.

**Configuration** : `tox.ini`
```ini
[tox]
envlist = py37, py38, py39, py310
isolated_build = True

[testenv]
deps =
    pytest
    pytest-cov
commands =
    pytest --cov=gestvenv {posargs:tests}
```

**Exécution** :
```bash
# Tester sur toutes les versions configurées
tox

# Tester sur une version spécifique
tox -e py39
```

### mock

Le module `unittest.mock` est utilisé pour isoler les composants lors des tests unitaires.

**Exemple d'utilisation** :
```python
from unittest.mock import patch, MagicMock

# Mocker une fonction
@patch('gestvenv.utils.system_commands.run_command')
def test_install_packages(mock_run):
    mock_run.return_value = (0, "Successfully installed pytest")
    # Test code here...

# Mocker une classe entière
@patch('gestvenv.core.env_manager.EnvManager')
def test_create_command(mock_env_manager):
    mock_instance = MagicMock()
    mock_env_manager.return_value = mock_instance
    mock_instance.create_environment.return_value = True
    # Test code here...
```

## Structure des tests

La structure des répertoires de test reflète celle du code source :

```
tests/
├── unit/                      # Tests unitaires
│   ├── core/
│   │   ├── test_env_manager.py
│   │   ├── test_package_manager.py
│   │   └── test_config_manager.py
│   └── utils/
│       ├── test_path_handler.py
│       ├── test_system_commands.py
│       └── test_validators.py
├── integration/               # Tests d'intégration
│   ├── test_env_creation.py
│   ├── test_package_management.py
│   └── test_config_import_export.py
├── system/                    # Tests système
│   ├── test_workflow.py
│   ├── test_cli.py
│   └── test_error_handling.py
├── performance/               # Tests de performance
│   ├── test_creation_time.py
│   └── test_multi_env_performance.py
└── fixtures/                  # Données de test partagées
    ├── sample_config.json
    └── requirements_sample.txt
```

## Fixtures

Les fixtures sont des données ou états prédéfinis utilisés dans les tests.

**Exemple de fixture pytest** :
```python
import pytest
import tempfile
import json
from pathlib import Path

@pytest.fixture
def sample_config():
    """Retourne un dictionnaire de configuration d'exemple."""
    return {
        "environments": {
            "test_env": {
                "path": "/path/to/env",
                "python_version": "3.9",
                "created_at": "2025-05-18T14:30:00",
                "packages": ["flask==2.0.1", "pytest==6.2.5"]
            }
        },
        "active_env": None,
        "default_python": "python3"
    }

@pytest.fixture
def config_file():
    """Crée un fichier de configuration temporaire."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        config = {
            "environments": {},
            "active_env": None,
            "default_python": "python3"
        }
        json.dump(config, f)
    
    yield Path(f.name)
    Path(f.name).unlink()
```

## Bonnes pratiques

### Nommage des tests

- Les noms de fichiers de test doivent commencer par `test_`
- Les noms de fonctions de test doivent commencer par `test_`
- Les noms de test doivent être descriptifs et indiquer ce qui est testé

### AAA Pattern (Arrange-Act-Assert)

Structurez vos tests selon le pattern AAA :

```python
def test_validate_env_name():
    # Arrange (Préparer)
    valid_names = ["projet_test", "projet-test", "projet123"]
    invalid_names = ["", " ", "projet/test"]
    
    # Act & Assert (Agir et Vérifier)
    for name in valid_names:
        self.assertTrue(validate_env_name(name))
        
    for name in invalid_names:
        self.assertFalse(validate_env_name(name))
```

### Isolement des tests

- Chaque test doit être indépendant des autres
- Évitez les dépendances entre tests
- Utilisez `setUp` et `tearDown` pour préparer et nettoyer l'environnement de test

### Tests paramétrés

Utilisez les tests paramétrés pour tester plusieurs entrées :

```python
@pytest.mark.parametrize("env_name,expected", [
    ("projet_test", True),
    ("projet-test", True),
    ("projet123", True),
    ("", False),
    (" ", False),
    ("projet/test", False)
])
def test_validate_env_name(env_name, expected):
    assert validate_env_name(env_name) == expected
```

## Intégration continue

Les tests sont automatiquement exécutés dans le pipeline CI à chaque commit :

1. **Pull Requests** : Tous les tests sont exécutés pour vérifier que les modifications ne cassent pas la fonctionnalité existante
2. **Branches principales** : Les tests de couverture sont exécutés pour s'assurer que la couverture de code reste élevée
3. **Releases** : Des tests supplémentaires sur différentes plateformes sont exécutés

## Stratégie de mocking

### Quand mocker

- Lors des tests unitaires pour isoler le composant testé
- Lors des appels à des API externes
- Pour simuler des erreurs ou cas limites difficiles à reproduire

### Quand ne pas mocker

- Dans les tests d'intégration où l'interaction réelle est importante
- Quand le mocking rend le test plus complexe que l'implémentation
- Pour les fonctions utilitaires simples et sans effets secondaires

## Mesure de la couverture

La couverture de code est mesurée avec pytest-cov :

```bash
pytest --cov=gestvenv --cov-report=html
```

L'objectif est de maintenir une couverture d'au moins 80% pour l'ensemble du code, avec une couverture plus élevée pour les composants critiques.

## Déboguer les tests

### Avec pytest

```bash
# Afficher la sortie standard pendant les tests
pytest -v

# Afficher les détails complets des échecs
pytest -vv

# Arrêter au premier échec
pytest -x

# Entrer dans pdb au premier échec
pytest --pdb
```

### Avec pdb

Insérez le code suivant dans votre test pour entrer dans le débogueur :

```python
import pdb; pdb.set_trace()
```

## Tests de vulnérabilités

Des tests spécifiques sont effectués pour vérifier les vulnérabilités potentielles :

- Injection de commandes dans les entrées utilisateur
- Accès à des chemins de fichiers non autorisés
- Manipulation incorrecte des permissions de fichiers

## Documentation des tests

Chaque test doit être documenté pour expliquer ce qu'il teste et pourquoi :

```python
def test_env_activation_commands():
    """
    Teste que les commandes d'activation appropriées sont générées pour
    différents systèmes d'exploitation.
    
    Vérifie que:
    1. Les commandes Windows utilisent 'Scripts\activate.bat'
    2. Les commandes Unix utilisent 'bin/activate'
    3. Les chemins sont correctement échappés
    """
    # Code de test...
```

## Test manuel

Certains aspects doivent être testés manuellement :

1. **Expérience utilisateur** : Fluidité de l'interface, clarté des messages
2. **Installation réelle** : Installation depuis PyPI, installation depuis le code source
3. **Comportement sur différents systèmes** : Test sur Windows, macOS et Linux

Un plan de test manuel est disponible dans `tests/manual/test_plan.md`.