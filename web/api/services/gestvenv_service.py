"""
Service pour interfacer avec GestVenv CLI.
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, Any, List, AsyncGenerator, Optional
from pathlib import Path

from api.core.config import settings
from api.models.schemas import (
    Environment, EnvironmentStatus, Package, PackageStatus,
    BackendType, CacheInfo, SystemInfo, TemplateInfo
)

logger = logging.getLogger(__name__)


class GestVenvService:
    """Service pour exécuter les commandes GestVenv CLI."""
    
    def __init__(self):
        self.cli_path = settings.GESTVENV_CLI_PATH
    
    async def execute_command(
        self, 
        command: List[str], 
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Exécute une commande GestVenv de manière asynchrone.
        
        Args:
            command: Liste des arguments de la commande
            timeout: Timeout en secondes
            
        Returns:
            Dict contenant returncode, stdout, stderr
        """
        full_command = [self.cli_path] + command
        logger.info(f"Executing command: {' '.join(full_command)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            result = {
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8').strip(),
                "stderr": stderr.decode('utf-8').strip()
            }
            
            logger.debug(f"Command result: {result}")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Command timeout: {' '.join(full_command)}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timeout after {timeout} seconds"
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    async def stream_command(
        self, 
        command: List[str]
    ) -> AsyncGenerator[str, None]:
        """
        Exécute une commande et stream la sortie en temps réel.
        
        Args:
            command: Liste des arguments de la commande
            
        Yields:
            Lignes de sortie de la commande
        """
        full_command = [self.cli_path] + command
        logger.info(f"Streaming command: {' '.join(full_command)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode('utf-8').rstrip()
                
            await process.wait()
            
        except Exception as e:
            logger.error(f"Streaming command failed: {e}")
            yield f"Error: {str(e)}"
    
    # ===== Méthodes pour les environnements =====
    
    async def list_environments(self) -> List[Environment]:
        """Liste tous les environnements."""
        result = await self.execute_command(["list", "--format", "json"])
        
        if result["returncode"] != 0:
            logger.error(f"Failed to list environments: {result['stderr']}")
            return []
        
        try:
            data = json.loads(result["stdout"]) if result["stdout"] else []
            environments = []
            
            for env_data in data:
                env = Environment(
                    name=env_data.get("name", ""),
                    path=env_data.get("path", ""),
                    python_version=env_data.get("python_version"),
                    backend=BackendType(env_data.get("backend", "pip")),
                    status=EnvironmentStatus(env_data.get("status", "healthy")),
                    created_at=env_data.get("created_at", "2024-01-01T00:00:00"),
                    last_used=env_data.get("last_used"),
                    package_count=env_data.get("package_count", 0),
                    size_mb=env_data.get("size_mb", 0.0),
                    active=env_data.get("active", False)
                )
                environments.append(env)
            
            return environments
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse environments JSON: {e}")
            return []
    
    async def get_environment(self, name: str) -> Optional[Environment]:
        """Récupère les détails d'un environnement."""
        result = await self.execute_command(["info", name])
        
        if result["returncode"] != 0:
            return None
        
        # Parser les informations de l'environnement
        # TODO: Implémenter le parsing des détails
        return None
    
    async def create_environment(
        self, 
        name: str, 
        python_version: Optional[str] = None,
        backend: Optional[BackendType] = None,
        template: Optional[str] = None,
        packages: Optional[List[str]] = None
    ) -> bool:
        """Crée un nouvel environnement."""
        command = ["create", name]
        
        if python_version:
            command.extend(["--python", python_version])
        
        if backend and backend != BackendType.AUTO:
            command.extend(["--backend", backend.value])
        
        if template:
            command.extend(["--template", template])
        
        if packages:
            command.extend(["--packages", ",".join(packages)])
        
        result = await self.execute_command(command)
        return result["returncode"] == 0
    
    async def delete_environment(self, name: str, force: bool = False) -> bool:
        """Supprime un environnement."""
        command = ["delete", name]
        if force:
            command.append("--force")
        
        result = await self.execute_command(command)
        return result["returncode"] == 0
    
    async def activate_environment(self, name: str) -> bool:
        """Active un environnement."""
        result = await self.execute_command(["activate", name])
        return result["returncode"] == 0
    
    # ===== Méthodes pour les packages =====
    
    async def list_packages(
        self, 
        env_name: str, 
        group: Optional[str] = None
    ) -> List[Package]:
        """Liste les packages d'un environnement."""
        command = ["list-packages", "--env", env_name, "--format", "json"]
        
        if group:
            command.extend(["--group", group])
        
        result = await self.execute_command(command)
        
        if result["returncode"] != 0:
            logger.error(f"Failed to list packages: {result['stderr']}")
            return []
        
        try:
            data = json.loads(result["stdout"]) if result["stdout"] else []
            packages = []
            
            for pkg_data in data:
                pkg = Package(
                    name=pkg_data.get("name", ""),
                    version=pkg_data.get("version"),
                    installed_version=pkg_data.get("installed_version"),
                    latest_version=pkg_data.get("latest_version"),
                    status=PackageStatus(pkg_data.get("status", "installed")),
                    group=pkg_data.get("group", "main"),
                    size_mb=pkg_data.get("size_mb", 0.0),
                    description=pkg_data.get("description")
                )
                packages.append(pkg)
            
            return packages
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse packages JSON: {e}")
            return []
    
    async def install_package(
        self,
        env_name: str,
        package: str,
        group: Optional[str] = None,
        editable: bool = False,
        upgrade: bool = False
    ) -> bool:
        """Installe un package dans un environnement."""
        command = ["install", package, "--env", env_name]
        
        if group:
            command.extend(["--group", group])
        
        if editable:
            command.append("--editable")
        
        if upgrade:
            command.append("--upgrade")
        
        result = await self.execute_command(command)
        return result["returncode"] == 0
    
    async def uninstall_package(self, env_name: str, package: str) -> bool:
        """Désinstalle un package."""
        command = ["uninstall", package, "--env", env_name, "--yes"]
        result = await self.execute_command(command)
        return result["returncode"] == 0
    
    async def update_packages(
        self, 
        env_name: str, 
        packages: Optional[List[str]] = None
    ) -> bool:
        """Met à jour des packages."""
        command = ["update", "--env", env_name]
        
        if packages:
            command.extend(packages)
        else:
            command.append("--all")
        
        result = await self.execute_command(command)
        return result["returncode"] == 0
    
    # ===== Méthodes pour le cache =====
    
    async def get_cache_info(self) -> Optional[CacheInfo]:
        """Récupère les informations du cache."""
        result = await self.execute_command(["cache", "info"])
        
        if result["returncode"] != 0:
            return None
        
        # TODO: Parser les informations du cache
        return CacheInfo(
            total_size_mb=0.0,
            package_count=0,
            hit_rate=0.0,
            location="/tmp/cache"
        )
    
    async def clean_cache(
        self, 
        older_than: Optional[int] = None,
        size_limit: Optional[str] = None
    ) -> bool:
        """Nettoie le cache."""
        command = ["cache", "clean"]
        
        if older_than:
            command.extend(["--older-than", str(older_than)])
        
        if size_limit:
            command.extend(["--size-limit", size_limit])
        
        command.append("--force")
        
        result = await self.execute_command(command)
        return result["returncode"] == 0
    
    # ===== Méthodes pour le système =====
    
    async def get_system_info(self) -> Optional[SystemInfo]:
        """Récupère les informations système."""
        # Récupérer la version
        version_result = await self.execute_command(["--version"])
        if version_result["returncode"] != 0:
            return None
        
        # Récupérer la liste des backends
        backends_result = await self.execute_command(["backend", "list"])
        
        # TODO: Parser les informations système complètes
        return SystemInfo(
            os="Linux",  # TODO: Détecter l'OS
            python_version="3.11.0",  # TODO: Détecter la version Python
            gestvenv_version=version_result["stdout"],
            backends_available=[BackendType.PIP, BackendType.UV],
            disk_usage={"total": 100.0, "used": 50.0, "free": 50.0},
            memory_usage={"total": 8.0, "used": 4.0, "free": 4.0}
        )
    
    async def run_doctor(self, env_name: Optional[str] = None) -> Dict[str, Any]:
        """Exécute le diagnostic."""
        command = ["doctor"]
        if env_name:
            command.append(env_name)
        
        result = await self.execute_command(command)
        
        return {
            "success": result["returncode"] == 0,
            "output": result["stdout"],
            "errors": result["stderr"]
        }
    
    # ===== Méthodes pour les templates =====
    
    async def list_templates(self) -> List[TemplateInfo]:
        """Liste les templates disponibles."""
        result = await self.execute_command(["template", "list"])
        
        if result["returncode"] != 0:
            return []
        
        # TODO: Parser la liste des templates
        return [
            TemplateInfo(
                name="basic",
                description="Projet Python minimal",
                category="basic",
                dependencies=["pytest"],
                files=["src/", "tests/", "pyproject.toml"],
                variables=["name", "author", "email"]
            )
        ]
    
    async def create_from_template(
        self,
        template_name: str,
        project_name: str,
        author: Optional[str] = None,
        email: Optional[str] = None,
        version: str = "0.1.0",
        output_path: Optional[str] = None
    ) -> bool:
        """Crée un projet depuis un template."""
        command = ["create-from-template", template_name, project_name]
        
        if author:
            command.extend(["--author", author])
        
        if email:
            command.extend(["--email", email])
        
        if version:
            command.extend(["--version", version])
        
        if output_path:
            command.extend(["--output", output_path])
        
        result = await self.execute_command(command)
        return result["returncode"] == 0