"""
Tests unitaires de l'interface CLI
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from gestvenv.cli import cli, setup_logging
from gestvenv.core.exceptions import GestVenvError


class TestCLICommands:
    """Tests des commandes CLI principales"""

    def test_cli_version(self, cli_runner):
        """Test affichage version"""
        result = cli_runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert "gestvenv" in result.output.lower()

    def test_cli_help(self, cli_runner):
        """Test affichage aide"""
        result = cli_runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "GestVenv" in result.output

    def test_cli_no_command(self, cli_runner):
        """Test CLI sans commande affiche panneau d'accueil"""
        result = cli_runner.invoke(cli)
        assert result.exit_code == 0
        assert "GestVenv" in result.output

    @patch('gestvenv.cli.EnvironmentManager')
    def test_create_command_success(self, mock_env_manager_class, cli_runner):
        """Test commande create réussie"""
        mock_manager = Mock()
        mock_manager.create_environment.return_value = Mock(success=True)
        mock_env_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, ['create', 'testenv'])
        
        assert result.exit_code == 0
        assert "créé avec succès" in result.output
        mock_manager.create_environment.assert_called_once()

    @patch('gestvenv.cli.EnvironmentManager')
    def test_create_command_with_options(self, mock_env_manager_class, cli_runner):
        """Test commande create avec options"""
        mock_manager = Mock()
        mock_manager.create_environment.return_value = Mock(success=True)
        mock_env_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, [
            'create', 'testenv', 
            '--python', '3.9', 
            '--backend', 'uv',
            '--template', 'web'
        ])
        
        assert result.exit_code == 0
        mock_manager.create_environment.assert_called_once_with(
            name='testenv',
            python_version='3.9',
            backend='uv',
            template='web'
        )

    @patch('gestvenv.cli.EnvironmentManager')
    def test_create_command_failure(self, mock_env_manager_class, cli_runner):
        """Test commande create échouée"""
        mock_manager = Mock()
        mock_manager.create_environment.side_effect = GestVenvError("Création impossible")
        mock_env_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, ['create', 'testenv'])
        
        assert result.exit_code == 1
        assert "Erreur" in result.output

    @patch('gestvenv.cli.EnvironmentManager')
    def test_list_command_empty(self, mock_env_manager_class, cli_runner):
        """Test commande list sans environnements"""
        mock_manager = Mock()
        mock_manager.list_environments.return_value = []
        mock_env_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, ['list'])
        
        assert result.exit_code == 0
        assert "Aucun environnement" in result.output

    @patch('gestvenv.cli.EnvironmentManager')
    def test_list_command_with_environments(self, mock_env_manager_class, cli_runner):
        """Test commande list avec environnements"""
        mock_env = Mock()
        mock_env.name = "testenv"
        mock_env.python_version = "3.9.0"
        mock_env.backend_type.value = "pip"
        mock_env.is_active = False
        
        mock_manager = Mock()
        mock_manager.list_environments.return_value = [mock_env]
        mock_env_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, ['list'])
        
        assert result.exit_code == 0
        assert "testenv" in result.output
        assert "3.9.0" in result.output

    @patch('gestvenv.cli.EnvironmentManager')
    def test_delete_command_success(self, mock_env_manager_class, cli_runner):
        """Test commande delete réussie"""
        mock_manager = Mock()
        mock_manager.delete_environment.return_value = True
        mock_env_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, ['delete', 'testenv', '--force'])
        
        assert result.exit_code == 0
        assert "supprimé" in result.output
        mock_manager.delete_environment.assert_called_once_with('testenv', force=True)

    @patch('gestvenv.cli.EnvironmentManager')
    def test_activate_command(self, mock_env_manager_class, cli_runner):
        """Test commande activate"""
        mock_manager = Mock()
        mock_manager.activate_environment.return_value = True
        mock_env_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, ['activate', 'testenv'])
        
        assert result.exit_code == 0
        mock_manager.activate_environment.assert_called_once_with('testenv')

    @patch('gestvenv.cli.EnvironmentManager')
    def test_install_command(self, mock_env_manager_class, cli_runner):
        """Test commande install packages"""
        mock_manager = Mock()
        mock_package_service = Mock()
        mock_manager.package_service = mock_package_service
        mock_package_service.install_packages.return_value = True
        mock_env_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, ['install', 'requests', 'flask', '--env', 'testenv'])
        
        assert result.exit_code == 0

    @patch('gestvenv.cli.BackendManager')
    def test_backend_list_command(self, mock_backend_manager_class, cli_runner):
        """Test commande backend list"""
        mock_manager = Mock()
        mock_manager.get_available_backends.return_value = ['pip', 'uv']
        mock_backend_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(cli, ['backend', 'list'])
        
        assert result.exit_code == 0
        assert "pip" in result.output
        assert "uv" in result.output

    @patch('gestvenv.cli.DiagnosticService')
    def test_doctor_command(self, mock_diagnostic_class, cli_runner):
        """Test commande doctor"""
        mock_diagnostic = Mock()
        mock_diagnostic.run_full_diagnostic.return_value = Mock(overall_health=True)
        mock_diagnostic_class.return_value = mock_diagnostic
        
        result = cli_runner.invoke(cli, ['doctor'])
        
        assert result.exit_code == 0

    def test_verbose_flag(self, cli_runner):
        """Test flag verbose active logging"""
        with patch('gestvenv.cli.setup_logging') as mock_setup:
            result = cli_runner.invoke(cli, ['--verbose'])
            mock_setup.assert_called_once_with(True)

    def test_offline_flag(self, cli_runner):
        """Test flag offline configure mode hors ligne"""
        with patch('gestvenv.cli.EnvironmentManager') as mock_env_class:
            mock_manager = Mock()
            mock_cache_service = Mock()
            mock_manager.cache_service = mock_cache_service
            mock_env_class.return_value = mock_manager
            
            result = cli_runner.invoke(cli, ['--offline'])
            
            mock_cache_service.set_offline_mode.assert_called_once_with(True)


class TestLogging:
    """Tests configuration logging"""

    @patch('gestvenv.cli.logging.basicConfig')
    def test_setup_logging_verbose(self, mock_basic_config):
        """Test configuration logging verbeux"""
        setup_logging(True)
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        assert kwargs['level'] == pytest.importorskip('logging').DEBUG

    @patch('gestvenv.cli.logging.basicConfig')
    def test_setup_logging_normal(self, mock_basic_config):
        """Test configuration logging normal"""
        setup_logging(False)
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        assert kwargs['level'] == pytest.importorskip('logging').WARNING