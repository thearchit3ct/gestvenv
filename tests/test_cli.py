import unittest
# from unittest.mock import AsyncMock, patch_default_new, patch, MagicMock
from unittest.mock import patch, MagicMock, AsyncMock
import argparse
import tempfile
import os
import json
import sys
from pathlib import Path

# Import du module CLI à tester
# Assurez-vous que le chemin d'importation est correct
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gestvenv import cli
from gestvenv.core import EnvironmentManager, config_manager


class TestCLI(unittest.TestCase):
    """Tests pour l'interface en ligne de commande de GestVenv."""

    def setUp(self) -> None:
        """Préparation de l'environnement de test."""
        # Création d'un répertoire temporaire pour les tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / 'config.json'
        
        # Configuration de test
        self.test_config = {
            "environments": {
                "test_env": {
                    "path": str(Path(self.temp_dir.name) / "envs" / "test_env"),
                    "python_version": "3.9",
                    "created_at": "2025-05-18T14:30:00",
                    "packages": ["pytest==6.2.5"]
                }
            },
            "active_env": None,
            "default_python": "python3"
        }
        
        # Écriture de la configuration de test
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
        
        # Patch pour utiliser la configuration de test
        patcher = patch('gestvenv.core.config_manager')
        self.mock_get_config_path: MagicMock | AsyncMock = patcher.start()
        self.mock_get_config_path.return_value = self.config_path
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        """Nettoyage après les tests."""
        self.temp_dir.cleanup()

    @patch('gestvenv.core.EnvironmentManager.create_environment')
    def test_create_command(self, mock_create_env) -> None:
        """Test de la commande 'create'."""
        # Configurer le mock pour retourner un succès
        mock_create_env.return_value = (True, "Environnement créé avec succès")

        test_args: list[str] = ['create', 'new_project', '--python', 'python3.10', '--packages', 'flask,pytest']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()

        # Vérifier que la fonction a été appelée
        mock_create_env.assert_called_once()
        # Vérifier les arguments d'appel (nom, python_version, packages, path)
        call_args = mock_create_env.call_args
        assert call_args[0][0] == 'new_project'  # nom
        assert call_args[1]['python_version'] == 'python3.10'  # keyword arg
        assert call_args[1]['packages'] == 'flask,pytest'  # keyword arg

    @patch('gestvenv.core.EnvironmentManager.activate_environment')
    def test_activate_command(self, mock_activate) -> None:
        """Test de la commande 'activate'."""
        test_args: list[str] = ['activate', 'test_env']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_activate.assert_called_once_with('test_env')

    @patch('gestvenv.core.EnvironmentManager.list_environments')
    def test_list_command(self, mock_list) -> None:
        """Test de la commande 'list'."""
        mock_list.return_value = ['test_env']
        
        test_args: list[str] = ['list']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_list.assert_called_once()

    @patch('gestvenv.core.EnvironmentManager.delete_environment')
    def test_delete_command(self, mock_delete) -> None:
        """Test de la commande 'delete'."""
        test_args: list[str] = ['delete', 'test_env', '--force']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_delete.assert_called_once_with('test_env', force=True)

    @patch('gestvenv.services.PackageService.install_packages')
    def test_install_command(self, mock_install) -> None:
        """Test de la commande 'install'."""
        test_args: list[str] = ['install', 'pandas,matplotlib', '--env', 'test_env']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_install.assert_called_once()
        args, _ = mock_install.call_args
        self.assertEqual(args[0], ['pandas', 'matplotlib'])
        self.assertEqual(args[1], 'test_env')

    @patch('gestvenv.services.PackageService.update_packages')
    def test_update_command(self, mock_update) -> None:
        """Test de la commande 'update'."""
        test_args: list[str] = ['update', '--all', '--env', 'test_env']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_update.assert_called_once_with(None, 'test_env', all_packages=True)

    @patch('gestvenv.core.EnvironmentManager.export_environment')
    def test_export_command(self, mock_export):
        """Test de la commande 'export'."""
        output_path: Path = Path(self.temp_dir.name) / 'export.json'
        test_args: list[str] = ['export', 'test_env', '--output', str(output_path), '--format', 'json']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_export.assert_called_once_with('test_env', str(output_path), 'json', {})

    @patch('gestvenv.core.EnvironmentManager.import_environment')
    def test_import_command(self, mock_import) -> None:
        """Test de la commande 'import'."""
        config_path = Path(self.temp_dir.name) / 'import.json'
        with open(config_path, 'w') as f:
            json.dump({"name": "imported_env", "python_version": "3.8", "packages": []}, f)
            
        test_args = ['import', str(config_path), '--name', 'new_import']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_import.assert_called_once()

    @patch('gestvenv.core.EnvironmentManager.clone_environment')
    def test_clone_command(self, mock_clone):
        """Test de la commande 'clone'."""
        test_args = ['clone', 'test_env', 'test_env_clone']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_clone.assert_called_once_with('test_env', 'test_env_clone')

    @patch('gestvenv.core.EnvironmentManager.get_environment_info')
    def test_info_command(self, mock_info) -> None:
        """Test de la commande 'info'."""
        mock_info.return_value = {
            'name': 'test_env',
            'path': '/path/to/env',
            'python_version': '3.9',
            'packages': ['pytest==6.2.5']
        }
        
        test_args = ['info', 'test_env']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_info.assert_called_once_with('test_env')

    @patch('gestvenv.services.PackageService.check_for_updates')
    def test_check_command(self, mock_check) -> None:
        """Test de la commande 'check'."""
        test_args = ['check', 'test_env', '--verbose']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_check.assert_called_once_with('test_env', verbose=True)

    @patch('subprocess.run')
    @patch('gestvenv.core.EnvironmentManager.run_command_in_environment')
    def test_run_command(self, mock_get_path, mock_run) -> None:
        """Test de la commande 'run'."""
        mock_get_path.return_value = '/path/to/test_env'
        
        test_args = ['run', 'test_env', 'python', 'script.py']
        with patch('sys.argv', ['gestvenv'] + test_args):
            cli.main()
            
        mock_get_path.assert_called_once_with('test_env')
        mock_run.assert_called_once()

    def test_invalid_command(self) -> None:
        """Test avec une commande invalide."""
        test_args = ['invalid_command']
        with patch('sys.argv', ['gestvenv'] + test_args):
            with self.assertRaises(SystemExit):
                cli.main()

    def test_pyversions_command(self) -> None:
        """Test de la commande 'pyversions'."""
        with patch('gestvenv.services.system_service.SystemService.get_available_python_versions') as mock_get_versions:
            mock_get_versions.return_value = [
                {"command": "python3.9", "version": "3.9.0"},
                {"command": "python3.10", "version": "3.10.0"}
            ]
            
            test_args = ['pyversions']
            with patch('sys.argv', ['gestvenv'] + test_args):
                cli.main()


# Exécution des tests si le script est exécuté directement
if __name__ == '__main__':
    unittest.main()