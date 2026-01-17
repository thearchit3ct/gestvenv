"""
Configuration pytest pour les tests E2E de GestVenv
"""

import pytest
import sys
from pathlib import Path


# Ajouter le chemin racine au PYTHONPATH
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure les marqueurs pytest"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (requires real environment)"
    )
    config.addinivalue_line(
        "markers", "error_scenarios: mark test as error scenario test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
    config.addinivalue_line(
        "markers", "requires_uv: mark test as requiring uv to be installed"
    )


def pytest_collection_modifyitems(config, items):
    """Modifie la collection des tests"""
    # Par défaut, ignorer les tests E2E sauf si explicitement demandé
    if not config.getoption("--run-e2e", default=False):
        skip_e2e = pytest.mark.skip(reason="E2E tests not requested (use --run-e2e)")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)


def pytest_addoption(parser):
    """Ajoute les options CLI pytest"""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests"
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )


@pytest.fixture(scope="session")
def e2e_config():
    """Configuration pour les tests E2E"""
    return {
        "timeout": 300,  # 5 minutes par test
        "cleanup_on_failure": True,
        "verbose": True,
    }


@pytest.fixture(scope="session")
def check_uv_available():
    """Vérifie si uv est disponible"""
    import subprocess
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def check_network_available():
    """Vérifie si le réseau est disponible"""
    import socket
    try:
        socket.create_connection(("pypi.org", 443), timeout=5)
        return True
    except Exception:
        return False
