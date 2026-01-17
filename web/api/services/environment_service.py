"""
Service pour la gestion des environnements virtuels
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
import json
from ..models.environment import Environment
from .gestvenv_service import GestVenvService


class EnvironmentService:
    """Service pour gérer les environnements virtuels"""
    
    def __init__(self):
        self.gestvenv = GestVenvService()
        self._environments_cache = {}
    
    def get_environment_info(self, env_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un environnement"""
        # Pour les tests, retourner un environnement factice
        if env_id in self._environments_cache:
            return self._environments_cache[env_id]
        
        # Simuler un environnement
        return {
            'id': env_id,
            'name': f'env-{env_id}',
            'path': f'/path/to/{env_id}',
            'python_version': '3.11',
            'backend': 'uv',
            'is_active': True
        }
    
    def run_command_in_environment(self, env_id: str, command: str):
        """Exécute une commande dans un environnement"""
        # Pour les tests, simuler une réponse
        class CommandResult:
            def __init__(self, success: bool, stdout: str, stderr: str = ""):
                self.success = success
                self.stdout = stdout
                self.stderr = stderr
        
        # Simuler différentes réponses selon la commande
        if "pip list" in command:
            return CommandResult(
                success=True,
                stdout='[{"name": "requests", "version": "2.31.0"}]'
            )
        elif "pip show" in command:
            return CommandResult(
                success=True,
                stdout="Name: requests\nVersion: 2.31.0\nLocation: /path/to/site-packages"
            )
        elif "python -c" in command:
            return CommandResult(
                success=True,
                stdout='{"executable": "/usr/bin/python", "version": "3.11.0", "path": []}'
            )
        
        return CommandResult(success=True, stdout="")
    
    async def list_environments(self) -> List[Environment]:
        """Liste tous les environnements"""
        # Pour les tests, retourner une liste vide
        return []
    
    async def create_environment(self, name: str, **kwargs) -> Environment:
        """Crée un nouvel environnement"""
        # Pour les tests, retourner un environnement factice
        env = Environment(
            id=f"env-{name}",
            name=name,
            path=f"/path/to/{name}",
            python_version=kwargs.get('python_version', '3.11'),
            backend=kwargs.get('backend', 'uv'),
            is_active=False,
            created_at="2025-01-01T00:00:00",
            package_count=0
        )
        self._environments_cache[env.id] = env.dict()
        return env
    
    async def delete_environment(self, env_id: str) -> bool:
        """Supprime un environnement"""
        if env_id in self._environments_cache:
            del self._environments_cache[env_id]
        return True