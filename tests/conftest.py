"""Configuration et fixtures pour les tests des services de GestVenv."""

import os
import sys
import pytest
import tempfile
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Generator, Tuple

# Ajouter le répertoire parent au chemin pour importer gestvenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Fixtures communes pour tous les tests de services
@pytest.fixture
def temp_dir():
    """Crée un répertoire temporaire pour les tests."""
    tmp_dir = tempfile.mkdtemp()
    yield Path(tmp_dir)
    # Nettoyer après les tests
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

@pytest.fixture
def temp_config_file(tmp_path):
    """Crée un fichier de configuration temporaire pour les tests."""
    config_file = tmp_path / "test_config.json"
    config_data = {
        "environments": {
            "test_env": {
                "name": "test_env",
                "path": str(tmp_path / "environments" / "test_env"),
                "python_version": "3.9.0",
                "created_at": datetime.now().isoformat(),
                "packages": []
            }
        },
        "active_env": None,
        "default_python": "python3",
        "settings": {
            "auto_activate": True,
            "package_cache_enabled": True,
            "check_updates_on_activate": True,
            "default_export_format": "json",
            "show_virtual_env_in_prompt": True,
            "version": "1.2.0",
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f)
    
    return config_file

@pytest.fixture
def mock_package_list() -> list[dict[str, str]]:
    """Retourne une liste simulée de packages installés."""
    return [
        {"name": "flask", "version": "2.0.1"},
        {"name": "pytest", "version": "6.2.5"},
        {"name": "requests", "version": "2.26.0"}
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

@pytest.fixture
def mock_subprocess_popen():
    """Simule subprocess.Popen pour les tests."""
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = "Process output"
        mock_process.stderr.read.return_value = ""
        mock_process.poll.return_value = 0
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        yield mock_popen

@pytest.fixture
def mock_environment_structure():
    """Crée une structure d'environnement virtuel simulée."""
    def create_env_structure(base_path: Path, env_name: str = "test_env") -> Path:
        """Crée la structure d'un environnement virtuel."""
        env_path = base_path / env_name
        env_path.mkdir(parents=True, exist_ok=True)
        
        # Créer la structure selon le système d'exploitation
        if os.name == "nt":  # Windows
            scripts_dir = env_path / "Scripts"
            scripts_dir.mkdir(exist_ok=True)
            
            # Créer les exécutables
            (scripts_dir / "python.exe").touch()
            (scripts_dir / "pip.exe").touch()
            (scripts_dir / "activate.bat").touch()
            
            # Créer les répertoires
            (env_path / "Lib").mkdir(exist_ok=True)
            (env_path / "Include").mkdir(exist_ok=True)
        else:  # Unix-like
            bin_dir = env_path / "bin"
            bin_dir.mkdir(exist_ok=True)
            
            # Créer les exécutables
            (bin_dir / "python").touch()
            (bin_dir / "pip").touch()
            (bin_dir / "activate").touch()
            
            # Créer les répertoires
            (env_path / "lib").mkdir(exist_ok=True)
            (env_path / "include").mkdir(exist_ok=True)
        
        # Créer pyvenv.cfg
        pyvenv_cfg = env_path / "pyvenv.cfg"
        pyvenv_cfg_content = f"""home = {sys.prefix}
implementation = CPython
version = 3.9.0
include-system-site-packages = false
base-prefix = {sys.prefix}
base-exec-prefix = {sys.prefix}
base-executable = {sys.executable}
"""
        pyvenv_cfg.write_text(pyvenv_cfg_content)
        
        return env_path
    
    return create_env_structure

@pytest.fixture
def mock_package_data():
    """Retourne des données de packages simulées."""
    return {
        "installed_packages": [
            {"name": "flask", "version": "2.0.1"},
            {"name": "pytest", "version": "6.2.5"},
            {"name": "click", "version": "8.0.1"},
            {"name": "werkzeug", "version": "2.0.2"}
        ],
        "outdated_packages": [
            {
                "name": "flask",
                "version": "2.0.1",
                "latest_version": "2.1.0"
            },
            {
                "name": "pytest",
                "version": "6.2.5",
                "latest_version": "7.0.0"
            }
        ],
        "package_info": {
            "flask": {
                "name": "flask",
                "version": "2.0.1",
                "summary": "A simple framework for building complex web applications.",
                "location": "/path/to/site-packages",
                "requires": ["click", "werkzeug"],
                "required_by": ["flask-restful"]
            }
        }
    }

@pytest.fixture
def mock_system_info():
    """Retourne des informations système simulées."""
    return {
        "os_name": "Linux",
        "os_version": "5.4.0",
        "architecture": "x86_64",
        "python_version": "3.9.7",
        "python_implementation": "CPython",
        "hostname": "test-machine",
        "username": "testuser",
        "cpu_count": 8,
        "memory_total": 16 * 1024 * 1024 * 1024,  # 16 GB
        "disk_total": 500 * 1024 * 1024 * 1024,   # 500 GB
        "disk_free": 100 * 1024 * 1024 * 1024,    # 100 GB
        "uptime": timedelta(hours=24, minutes=30),
        "timezone": "UTC"
    }

@pytest.fixture
def mock_cache_index():
    """Retourne un index de cache simulé."""
    return {
        "flask": {
            "versions": {
                "2.0.1": {
                    "name": "flask",
                    "version": "2.0.1",
                    "path": "packages/flask/flask-2.0.1-py3-none-any.whl",
                    "added_at": datetime.now().isoformat(),
                    "last_used": datetime.now().isoformat(),
                    "hash": "abc123def456",
                    "size": 1024000,
                    "dependencies": ["click", "werkzeug"],
                    "usage_count": 5
                },
                "2.1.0": {
                    "name": "flask",
                    "version": "2.1.0",
                    "path": "packages/flask/flask-2.1.0-py3-none-any.whl",
                    "added_at": datetime.now().isoformat(),
                    "last_used": datetime.now().isoformat(),
                    "hash": "def456ghi789",
                    "size": 1050000,
                    "dependencies": ["click", "werkzeug"],
                    "usage_count": 2
                }
            }
        },
        "pytest": {
            "versions": {
                "6.2.5": {
                    "name": "pytest",
                    "version": "6.2.5",
                    "path": "packages/pytest/pytest-6.2.5-py3-none-any.whl",
                    "added_at": (datetime.now() - timedelta(days=30)).isoformat(),
                    "last_used": (datetime.now() - timedelta(days=5)).isoformat(),
                    "hash": "ghi789jkl012",
                    "size": 512000,
                    "dependencies": ["pluggy", "py"],
                    "usage_count": 10
                }
            }
        }
    }

@pytest.fixture
def mock_diagnostic_report():
    """Retourne un rapport de diagnostic simulé."""
    return {
        "environment": "test_env",
        "path": "/path/to/test_env",
        "python_version": "3.9.0",
        "created_at": datetime.now().isoformat(),
        "diagnosed_at": datetime.now().isoformat(),
        "status": "healthy",
        "issues": [],
        "warnings": [],
        "info": [
            "Environnement physiquement présent",
            "Structure de répertoires correcte",
            "Python fonctionnel: Python 3.9.0",
            "pip fonctionnel: pip 21.0.1",
            "Script d'activation présent"
        ],
        "checks": {
            "physical_existence": True,
            "directory_structure": True,
            "python_executable": True,
            "pip_executable": True,
            "activation_script": True,
            "read_permission": True,
            "write_permission": True
        },
        "recommendations": [],
        "repair_actions": []
    }

@pytest.fixture 
def mock_config_data():
    """Retourne des données de configuration simulées."""
    return {
        "environments": {
            "test_env": {
                "name": "test_env",
                "path": "/path/to/test_env",
                "python_version": "3.9.0",
                "created_at": datetime.now().isoformat(),
                "packages": ["flask==2.0.1", "pytest==6.2.5"],
                "active": False,
                "metadata": {"description": "Environment de test"}
            },
            "prod_env": {
                "name": "prod_env", 
                "path": "/path/to/prod_env",
                "python_version": "3.10.0",
                "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
                "packages": ["django==4.0.0", "gunicorn==20.1.0"],
                "active": True,
                "metadata": {"description": "Environment de production"}
            }
        },
        "active_env": "prod_env",
        "default_python": "python3",
        "settings": {
            "auto_activate": True,
            "package_cache_enabled": True,
            "check_updates_on_activate": True,
            "default_export_format": "json",
            "show_virtual_env_in_prompt": True,
            "offline_mode": False,
            "use_package_cache": True
        }
    }

@pytest.fixture
def create_sample_wheel_file():
    """Fonction pour créer un fichier wheel de test."""
    def _create_wheel(temp_dir: Path, package_name: str = "flask", 
                     version: str = "2.0.1", content: bytes = b"fake wheel content") -> Path:
        """Crée un fichier wheel simulé."""
        filename = f"{package_name}-{version}-py3-none-any.whl"
        wheel_file = temp_dir / filename
        wheel_file.write_bytes(content)
        return wheel_file
    
    return _create_wheel

@pytest.fixture
def create_sample_requirements_file():
    """Fonction pour créer un fichier requirements.txt de test."""
    def _create_requirements(temp_dir: Path, packages: Optional[List[str]] = None) -> Path:
        """Crée un fichier requirements.txt simulé."""
        if packages is None:
            packages = [
                "flask==2.0.1",
                "pytest==6.2.5", 
                "click>=8.0.0",
                "werkzeug>=2.0.0"
            ]
        
        requirements_file = temp_dir / "requirements.txt"
        requirements_file.write_text("\n".join(packages) + "\n")
        return requirements_file
    
    return _create_requirements

@pytest.fixture
def mock_psutil():
    """Mock du module psutil pour les tests système."""
    with patch('psutil.Process') as mock_process_class, \
         patch('psutil.pid_exists') as mock_pid_exists, \
         patch('psutil.boot_time') as mock_boot_time, \
         patch('psutil.cpu_count') as mock_cpu_count, \
         patch('psutil.cpu_percent') as mock_cpu_percent, \
         patch('psutil.virtual_memory') as mock_virtual_memory, \
         patch('psutil.disk_usage') as mock_disk_usage:
        
        # Configurer les mocks avec des valeurs par défaut
        mock_boot_time.return_value = datetime.now().timestamp() - 3600  # 1h uptime
        mock_cpu_count.return_value = 4
        mock_cpu_percent.return_value = 25.5
        mock_pid_exists.return_value = True
        
        # Mock pour virtual_memory
        mock_memory = MagicMock()
        mock_memory.total = 8 * 1024 * 1024 * 1024  # 8 GB
        mock_memory.available = 4 * 1024 * 1024 * 1024  # 4 GB
        mock_memory.used = 4 * 1024 * 1024 * 1024  # 4 GB
        mock_memory.free = 3 * 1024 * 1024 * 1024  # 3 GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        # Mock pour disk_usage
        mock_disk = MagicMock()
        mock_disk.total = 100 * 1024 * 1024 * 1024  # 100 GB
        mock_disk.free = 50 * 1024 * 1024 * 1024   # 50 GB
        mock_disk_usage.return_value = mock_disk
        
        # Mock pour Process
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.name.return_value = "python"
        mock_process.cmdline.return_value = ["python", "script.py"]
        mock_process.status.return_value = "running"
        mock_process.cpu_percent.return_value = 15.0
        mock_process.memory_percent.return_value = 8.5
        mock_process.create_time.return_value = datetime.now().timestamp() - 1800  # 30min ago
        mock_process.cwd.return_value = "/home/user"
        mock_process_class.return_value = mock_process
        
        yield {
            'Process': mock_process_class,
            'pid_exists': mock_pid_exists,
            'boot_time': mock_boot_time,
            'cpu_count': mock_cpu_count,
            'cpu_percent': mock_cpu_percent,
            'virtual_memory': mock_virtual_memory,
            'disk_usage': mock_disk_usage
        }

@pytest.fixture
def mock_service_classes():
    """Mock de toutes les classes de services."""
    with patch('gestvenv.services.environment_service.EnvironmentService') as mock_env, \
         patch('gestvenv.services.package_service.PackageService') as mock_pkg, \
         patch('gestvenv.services.system_service.SystemService') as mock_sys, \
         patch('gestvenv.services.cache_service.CacheService') as mock_cache, \
         patch('gestvenv.services.diagnostic_services.DiagnosticService') as mock_diag:
        
        # Configurer les mocks avec des méthodes de base
        for service_mock in [mock_env, mock_pkg, mock_sys, mock_cache, mock_diag]:
            service_instance = service_mock.return_value
            service_instance.health_check.return_value = {"status": "healthy"}
        
        yield {
            'EnvironmentService': mock_env,
            'PackageService': mock_pkg,
            'SystemService': mock_sys,
            'CacheService': mock_cache,
            'DiagnosticService': mock_diag
        }

@pytest.fixture
def capture_logs():
    """Capture les logs pour les tests."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Ajouter le handler aux loggers de gestvenv
    logger = logging.getLogger('gestvenv')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # Nettoyer
    logger.removeHandler(handler)

# =====================================================================
# FIXTURES ADDITIONNELLES POUR COMPLÉTER LES TESTS
# =====================================================================

@pytest.fixture
def mock_environment_metrics():
    """Retourne des métriques d'environnement simulées."""
    return {
        "size": {
            "total": 250 * 1024 * 1024,  # 250 MB
            "packages": 200 * 1024 * 1024,  # 200 MB
            "cache": 30 * 1024 * 1024,  # 30 MB
            "other": 20 * 1024 * 1024   # 20 MB
        },
        "performance": {
            "startup_time": 0.5,
            "import_time": 0.2,
            "package_count": 45,
            "dependency_depth": 3
        },
        "health_score": 85.5,
        "last_updated": datetime.now().isoformat(),
        "usage_stats": {
            "activations": 127,
            "last_used": (datetime.now() - timedelta(hours=2)).isoformat(),
            "total_runtime": timedelta(hours=45, minutes=30).total_seconds()
        }
    }

@pytest.fixture
def mock_environment_snapshots():
    """Retourne des données de snapshots simulées."""
    return [
        {
            "name": "test_env_20231201_120000",
            "environment_name": "test_env",
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "size": 300 * 1024 * 1024,  # 300 MB
            "size_mb": 300.0,
            "file": "/snapshots/test_env_20231201_120000.tar.gz"
        },
        {
            "name": "test_env_20231215_150000",
            "environment_name": "test_env",
            "created_at": (datetime.now() - timedelta(days=15)).isoformat(),
            "size": 280 * 1024 * 1024,  # 280 MB
            "size_mb": 280.0,
            "file": "/snapshots/test_env_20231215_150000.tar.gz"
        }
    ]

@pytest.fixture
def mock_network_interfaces():
    """Retourne des informations d'interfaces réseau simulées."""
    return {
        "eth0": {
            "addresses": [
                {
                    "family": "AF_INET",
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "broadcast": "192.168.1.255"
                }
            ],
            "stats": {
                "isup": True,
                "duplex": "full",
                "speed": 1000,
                "mtu": 1500
            }
        },
        "lo": {
            "addresses": [
                {
                    "family": "AF_INET",
                    "address": "127.0.0.1",
                    "netmask": "255.0.0.0",
                    "broadcast": None
                }
            ],
            "stats": {
                "isup": True,
                "duplex": "unknown",
                "speed": 0,
                "mtu": 65536
            }
        }
    }

@pytest.fixture
def mock_process_tree():
    """Retourne une arborescence de processus simulée."""
    return [
        {
            "pid": 1234,
            "name": "python",
            "command": ["python", "app.py"],
            "status": "running",
            "cpu_percent": 5.2,
            "memory_percent": 3.1,
            "create_time": (datetime.now() - timedelta(hours=1)).isoformat(),
            "children": [
                {
                    "pid": 1235,
                    "name": "python",
                    "command": ["python", "worker.py"],
                    "status": "running",
                    "cpu_percent": 2.1,
                    "memory_percent": 1.5,
                    "create_time": (datetime.now() - timedelta(minutes=30)).isoformat()
                }
            ]
        }
    ]

@pytest.fixture
def mock_cache_statistics():
    """Retourne des statistiques de cache simulées."""
    return {
        "package_count": 25,
        "version_count": 45,
        "total_size_bytes": 500 * 1024 * 1024,  # 500 MB
        "total_size_mb": 500.0,
        "latest_package": "flask-2.1.0",
        "latest_added_at": datetime.now().isoformat(),
        "cache_dir": "/home/user/.gestvenv/cache",
        "disk_usage": {
            "total": 100 * 1024 * 1024 * 1024,  # 100 GB
            "used": 60 * 1024 * 1024 * 1024,    # 60 GB
            "free": 40 * 1024 * 1024 * 1024     # 40 GB
        },
        "hit_rate": 0.75,
        "miss_rate": 0.25,
        "cleanup_stats": {
            "last_cleanup": (datetime.now() - timedelta(days=7)).isoformat(),
            "packages_removed": 5,
            "space_freed": 50 * 1024 * 1024  # 50 MB
        }
    }

@pytest.fixture
def mock_integrity_report():
    """Retourne un rapport d'intégrité simulé."""
    return {
        "verified_at": datetime.now().isoformat(),
        "status": "healthy",
        "total_packages": 25,
        "verified_packages": 24,
        "corrupted_packages": [
            {
                "package": "broken-pkg-1.0.0",
                "path": "/cache/packages/broken-pkg/broken-pkg-1.0.0.whl",
                "expected_hash": "abc123",
                "actual_hash": "def456"
            }
        ],
        "missing_files": [],
        "orphaned_metadata": [],
        "orphaned_files": ["/cache/packages/orphan.whl"],
        "issues": ["1 package corrompu détecté"],
        "warnings": ["1 fichier orphelin trouvé"],
        "recommendations": [
            "Supprimer et re-télécharger les packages corrompus",
            "Nettoyer les fichiers orphelins"
        ]
    }

@pytest.fixture
def mock_dependency_analysis():
    """Retourne une analyse de dépendances simulée."""
    return {
        "analyzed_at": datetime.now().isoformat(),
        "environment": "test_env",
        "total_packages": 10,
        "top_level_packages": ["flask", "pytest", "requests"],
        "dependency_tree": {
            "flask": {
                "requires": ["click", "werkzeug", "jinja2"],
                "required_by": []
            },
            "click": {
                "requires": [],
                "required_by": ["flask"]
            },
            "werkzeug": {
                "requires": [],
                "required_by": ["flask"]
            }
        },
        "conflicts": [],
        "outdated": [
            {
                "name": "flask",
                "current_version": "2.0.1",
                "latest_version": "2.1.0"
            }
        ],
        "security_issues": []
    }

@pytest.fixture
def mock_environment_comparison():
    """Retourne une comparaison d'environnements simulée."""
    return {
        "compared_at": datetime.now().isoformat(),
        "environments": {
            "env1": {"name": "dev_env", "path": "/path/to/dev"},
            "env2": {"name": "prod_env", "path": "/path/to/prod"}
        },
        "differences": {
            "packages": {
                "only_in_env1": [{"name": "pytest", "version": "6.2.5"}],
                "only_in_env2": [{"name": "gunicorn", "version": "20.1.0"}],
                "version_differences": [
                    {
                        "name": "flask",
                        "env1_version": "2.0.1",
                        "env2_version": "2.1.0"
                    }
                ]
            },
            "python_version": {
                "env1": "3.9.0",
                "env2": "3.10.0"
            },
            "size": {
                "env1_bytes": 200 * 1024 * 1024,
                "env2_bytes": 150 * 1024 * 1024,
                "difference_bytes": 50 * 1024 * 1024,
                "difference_mb": 50.0
            }
        },
        "similarities": ["Packages communs: 8/10 (80.0%)"],
        "similarity_percentage": 80.0
    }

@pytest.fixture
def mock_export_data():
    """Retourne des données d'export simulées."""
    return {
        "metadata": {
            "name": "test_env",
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "exported_at": datetime.now().isoformat(),
            "export_format": "json",
            "gestvenv_version": "1.1.1"
        },
        "environment": {
            "name": "test_env",
            "python_version": "3.9.0",
            "path": "/path/to/test_env"
        },
        "packages": [
            {"name": "flask", "version": "2.0.1"},
            {"name": "click", "version": "8.0.1"},
            {"name": "werkzeug", "version": "2.0.2"}
        ],
        "requirements": "flask==2.0.1\nclick==8.0.1\nwerkzeug==2.0.2\n",
        "settings": {
            "auto_activate": True,
            "offline_mode": False
        }
    }

@pytest.fixture
def mock_validation_errors():
    """Retourne des erreurs de validation simulées."""
    return {
        "environment_name": [
            ("", "Le nom d'environnement ne peut pas être vide"),
            ("invalid@name", "Caractères invalides dans le nom"),
            ("a" * 100, "Nom trop long")
        ],
        "python_version": [
            ("python2.7", "Version Python non supportée"),
            ("invalid", "Format de version invalide"),
            ("", "Version requise")
        ],
        "package_names": [
            ("", "Nom de package vide"),
            ("invalid package name", "Caractères invalides"),
            ("missing==", "Spécification de version invalide")
        ],
        "paths": [
            ("", "Chemin vide"),
            ("/root", "Chemin système dangereux"),
            ("nonexistent/path", "Chemin inexistant")
        ]
    }

@pytest.fixture
def mock_performance_metrics():
    """Retourne des métriques de performance simulées."""
    return {
        "measurement_time": datetime.now().isoformat(),
        "environment": "test_env",
        "metrics": {
            "startup_time": {
                "mean": 0.45,
                "median": 0.42,
                "std_dev": 0.08,
                "min": 0.35,
                "max": 0.65,
                "samples": 50
            },
            "import_times": {
                "flask": 0.15,
                "pytest": 0.25,
                "requests": 0.12
            },
            "memory_usage": {
                "baseline": 25 * 1024 * 1024,  # 25 MB
                "peak": 45 * 1024 * 1024,      # 45 MB
                "average": 35 * 1024 * 1024    # 35 MB
            },
            "disk_io": {
                "read_bytes": 150 * 1024 * 1024,   # 150 MB
                "write_bytes": 50 * 1024 * 1024,   # 50 MB
                "read_operations": 1250,
                "write_operations": 450
            }
        },
        "benchmarks": {
            "package_installation": 15.5,  # seconds
            "environment_creation": 8.2,   # seconds
            "cache_operations": 2.1        # seconds
        }
    }

@pytest.fixture
def mock_security_scan():
    """Retourne un scan de sécurité simulé."""
    return {
        "scanned_at": datetime.now().isoformat(),
        "environment": "test_env",
        "vulnerabilities": [
            {
                "package": "urllib3",
                "version": "1.25.8",
                "vulnerability_id": "CVE-2021-33503",
                "severity": "medium",
                "description": "ReDoS vulnerability in URL parsing",
                "fixed_version": "1.26.5"
            }
        ],
        "outdated_packages": 3,
        "total_packages": 25,
        "security_score": 7.5,
        "recommendations": [
            "Mettre à jour urllib3 vers la version 1.26.5 ou supérieure",
            "Examiner les dépendances transitives",
            "Activer les alertes de sécurité automatiques"
        ]
    }

@pytest.fixture
def mock_backup_restore_data():
    """Retourne des données de sauvegarde et restauration simulées."""
    return {
        "backup": {
            "created_at": datetime.now().isoformat(),
            "environment": "test_env",
            "backup_file": "/backups/test_env_20231230_backup.tar.gz",
            "size": 200 * 1024 * 1024,  # 200 MB
            "checksum": "sha256:abc123def456...",
            "metadata": {
                "python_version": "3.9.0",
                "package_count": 25,
                "includes_cache": True
            }
        },
        "restore": {
            "restored_at": datetime.now().isoformat(),
            "source_backup": "/backups/test_env_20231230_backup.tar.gz",
            "target_environment": "test_env_restored",
            "target_path": "/environments/test_env_restored",
            "success": True,
            "duration": 45.2,  # seconds
            "files_restored": 1247
        }
    }

# Fonctions utilitaires pour les tests
def create_mock_environment_info(name: str = "test_env", 
                               path: Optional[Path] = None,
                               python_version: str = "3.9.0",
                               packages: Optional[List[str]] = None) -> Dict[str, Any]:
    """Crée des informations d'environnement simulées."""
    if path is None:
        path = Path(f"/tmp/{name}")
    
    if packages is None:
        packages = ["flask==2.0.1", "pytest==6.2.5"]
    
    return {
        "name": name,
        "path": str(path),
        "python_version": python_version,
        "created_at": datetime.now().isoformat(),
        "packages": packages,
        "active": False,
        "exists": True,
        "health": {
            "exists": True,
            "python_available": True,
            "pip_available": True,
            "activation_script_exists": True
        },
        "metadata": {
            "description": f"Environment {name}",
            "created_by": "test_user"
        }
    }

def create_mock_command_result(returncode: int = 0, 
                             stdout: str = "Success",
                             stderr: str = "",
                             duration: float = 0.1) -> Dict[str, Any]:
    """Crée un résultat de commande simulé."""
    return {
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "duration": duration,
        "command": ["mock", "command"],
        "state": "completed" if returncode == 0 else "failed"
    }

def create_mock_package_info(name: str = "flask", 
                           version: str = "2.0.1",
                           dependencies: Optional[List[str]] = None) -> Dict[str, Any]:
    """Crée des informations de package simulées."""
    if dependencies is None:
        dependencies = ["click", "werkzeug"] if name == "flask" else []
    
    return {
        "name": name,
        "version": version,
        "dependencies": dependencies,
        "required_by": [],
        "size": 1024 * 1024,  # 1 MB
        "installed_at": datetime.now().isoformat(),
        "summary": f"Mock package {name}",
        "homepage": f"https://pypi.org/project/{name}/",
        "license": "MIT"
    }

def create_mock_service_health_report(service_name: str, 
                                    status: str = "healthy") -> Dict[str, Any]:
    """Crée un rapport de santé de service simulé."""
    return {
        "service": service_name,
        "status": status,
        "checked_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "dependencies": {
            "required": ["python>=3.6"],
            "optional": ["psutil", "requests"]
        },
        "metrics": {
            "uptime": timedelta(hours=24).total_seconds(),
            "requests_handled": 1250,
            "errors_count": 5,
            "success_rate": 0.996
        },
        "issues": [] if status == "healthy" else ["Service connection timeout"],
        "recommendations": [] if status == "healthy" else ["Restart service"]
    }

# Marquer les fixtures comme session-scoped pour certaines qui sont coûteuses
@pytest.fixture(scope="session")
def session_temp_dir():
    """Répertoire temporaire pour toute la session de tests."""
    tmp_dir = tempfile.mkdtemp(prefix="gestvenv_test_session_")
    yield Path(tmp_dir)
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

@pytest.fixture(scope="session")
def test_data_dir():
    """Répertoire contenant les données de test statiques."""
    data_dir = Path(__file__).parent / "test_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

@pytest.fixture(scope="module")
def module_temp_dir():
    """Répertoire temporaire pour un module de tests."""
    tmp_dir = tempfile.mkdtemp(prefix="gestvenv_test_module_")
    yield Path(tmp_dir)
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

# Fixtures de configuration pour différents scénarios de test
@pytest.fixture(params=["windows", "linux", "darwin"])
def mock_os_platform(request):
    """Simule différentes plateformes OS."""
    platform_name = request.param
    
    with patch('platform.system') as mock_system, \
         patch('os.name') as mock_os_name:
        
        if platform_name == "windows":
            mock_system.return_value = "Windows"
            mock_os_name = "nt"
        elif platform_name == "linux":
            mock_system.return_value = "Linux"
            mock_os_name = "posix"
        elif platform_name == "darwin":
            mock_system.return_value = "Darwin"
            mock_os_name = "posix"
        
        yield platform_name

@pytest.fixture(params=["3.8", "3.9", "3.10", "3.11"])
def mock_python_versions(request):
    """Simule différentes versions Python."""
    version = request.param
    
    with patch('sys.version_info') as mock_version_info:
        major, minor = version.split(".")
        mock_version_info.major = int(major)
        mock_version_info.minor = int(minor)
        mock_version_info.micro = 0
        
        yield version

# Fixtures pour les tests d'erreurs et exceptions
@pytest.fixture
def mock_network_error():
    """Simule des erreurs réseau."""
    import urllib.error
    
    def raise_network_error(*args, **kwargs):
        raise urllib.error.URLError("Network unreachable")
    
    return raise_network_error

@pytest.fixture
def mock_permission_error():
    """Simule des erreurs de permission."""
    def raise_permission_error(*args, **kwargs):
        raise PermissionError("Access denied")
    
    return raise_permission_error

@pytest.fixture
def mock_disk_full_error():
    """Simule une erreur d'espace disque plein."""
    def raise_disk_full_error(*args, **kwargs):
        raise OSError("No space left on device")
    
    return raise_disk_full_error

# Configuration des paramètres de test
@pytest.fixture(autouse=True)
def configure_test_environment():
    """Configure automatiquement l'environnement de test."""
    # Désactiver les logs de débogage pendant les tests
    import logging
    logging.getLogger('gestvenv').setLevel(logging.WARNING)
    
    # Configurer les timeouts pour les tests
    original_timeout = os.environ.get('GESTVENV_TIMEOUT', '30')
    os.environ['GESTVENV_TIMEOUT'] = '5'  # Timeout plus court pour les tests
    
    yield
    
    # Restaurer l'environnement
    os.environ['GESTVENV_TIMEOUT'] = original_timeout

# Hooks de test pour la collecte de métadonnées
def pytest_configure(config):
    """Configuration globale de pytest."""
    # Ajouter des marqueurs personnalisés
    config.addinivalue_line("markers", "slow: marque les tests lents")
    config.addinivalue_line("markers", "integration: tests d'intégration")
    config.addinivalue_line("markers", "unit: tests unitaires")
    config.addinivalue_line("markers", "requires_network: tests nécessitant une connexion réseau")
    config.addinivalue_line("markers", "requires_admin: tests nécessitant des privilèges administrateur")

def pytest_collection_modifyitems(config, items):
    """Modifie la collection des tests."""
    # Marquer automatiquement les tests lents
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.slow)
        
        # Marquer les tests d'intégration
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Marquer les tests unitaires
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)