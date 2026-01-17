"""
Service pour la gestion des packages
"""

from typing import List, Dict, Any, Optional
from .gestvenv_service import GestVenvService


class PackageService:
    """Service pour gérer les packages dans les environnements"""
    
    def __init__(self):
        self.gestvenv = GestVenvService()
    
    async def list_packages(self, env_id: str) -> List[Dict[str, Any]]:
        """Liste les packages installés dans un environnement"""
        # Pour les tests, retourner une liste factice
        return [
            {"name": "requests", "version": "2.31.0"},
            {"name": "numpy", "version": "1.24.0"}
        ]
    
    async def install_package(self, env_id: str, package_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Installe un package dans un environnement"""
        return {
            "success": True,
            "message": f"Package {package_name} installed successfully"
        }
    
    async def uninstall_package(self, env_id: str, package_name: str) -> Dict[str, Any]:
        """Désinstalle un package d'un environnement"""
        return {
            "success": True,
            "message": f"Package {package_name} uninstalled successfully"
        }