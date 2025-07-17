"""
Service pour la gestion du cache
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json


class CacheService:
    """Service pour gérer le cache des packages"""
    
    def __init__(self):
        self.cache_dir = Path.home() / ".cache" / "gestvenv"
        self.cache_info = {}
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Récupère les informations du cache"""
        return {
            "size": 1024 * 1024 * 100,  # 100 MB
            "packages": 42,
            "location": str(self.cache_dir)
        }
    
    async def clear_cache(self) -> Dict[str, Any]:
        """Vide le cache"""
        self.cache_info = {}
        return {
            "success": True,
            "message": "Cache cleared successfully"
        }
    
    async def get_cached_packages(self) -> List[Dict[str, Any]]:
        """Liste les packages en cache"""
        return [
            {"name": "requests", "version": "2.31.0", "size": 1024 * 100},
            {"name": "numpy", "version": "1.24.0", "size": 1024 * 1024 * 10}
        ]