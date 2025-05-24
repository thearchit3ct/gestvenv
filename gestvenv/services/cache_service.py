"""
Service de gestion du cache pour GestVenv.

Ce module fournit les fonctionnalités pour gérer le cache local des packages,
permettant l'installation et la mise à jour des packages en mode hors ligne.
"""

import os
import json
import shutil
import hashlib
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set, cast

# Configuration du logger
logger = logging.getLogger(__name__)

class CacheService:
    """Service pour gérer le cache local de packages."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialise le service de cache.
        
        Args:
            cache_dir: Répertoire du cache. Si None, utilise le répertoire par défaut.
        """
        from ..utils.path_utils import get_default_data_dir
        
        self.cache_dir = cache_dir or (get_default_data_dir() / "cache")
        self.metadata_dir = self.cache_dir / "metadata"
        self.packages_dir = self.cache_dir / "packages"
        self.requirements_dir = self.cache_dir / "requirements"
        
        # Créer les répertoires s'ils n'existent pas
        self._ensure_cache_structure()
        
        # Charger l'index
        self.index = self._load_index()
    
    def _ensure_cache_structure(self) -> None:
        """Crée la structure de répertoires du cache si elle n'existe pas."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self.requirements_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Charge l'index des packages du cache.
        
        Returns:
            Dict: Index des packages cachés
        """
        index_path = self.metadata_dir / "index.json"
        
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    return cast(Dict[str, Dict[str, Any]], json.load(f))
            except Exception as e:
                logger.error(f"Erreur lors du chargement de l'index du cache: {e}")
                # Créer une sauvegarde de l'index corrompu
                if index_path.exists():
                    backup_path = index_path.with_suffix('.json.bak')
                    shutil.copy2(index_path, backup_path)
                    logger.warning(f"Sauvegarde de l'index corrompu créée: {backup_path}")
        
        # Si l'index n'existe pas ou est corrompu, créer un nouvel index vide
        return {}
    
    def _save_index(self) -> bool:
        """
        Sauvegarde l'index des packages du cache.
        
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        index_path = self.metadata_dir / "index.json"
        
        try:
            # Créer une sauvegarde de l'index existant si nécessaire
            if index_path.exists():
                backup_path = index_path.with_suffix('.json.bak')
                shutil.copy2(index_path, backup_path)
            
            # Sauvegarder le nouvel index
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'index du cache: {e}")
            return False
    
    def add_package(self, package_path: Path, package_name: str, 
                   version: str, dependencies: List[str]) -> bool:
        """
        Ajoute un package au cache.
        
        Args:
            package_path: Chemin vers le fichier wheel du package
            package_name: Nom du package
            version: Version du package
            dependencies: Liste des dépendances du package
            
        Returns:
            bool: True si l'ajout a réussi, False sinon
        """
        try:
            # Calculer le hash du fichier pour vérification d'intégrité
            file_hash = self._calculate_file_hash(package_path)
            
            # Créer le répertoire pour ce package s'il n'existe pas
            package_dir = self.packages_dir / package_name
            package_dir.mkdir(exist_ok=True)
            
            # Destination dans le cache
            dest_path = package_dir / f"{package_name}-{version}.whl"
            
            # Copier le fichier dans le cache
            shutil.copy2(package_path, dest_path)
            
            # Mettre à jour les métadonnées du package
            package_info = {
                "name": package_name,
                "version": version,
                "path": str(dest_path.relative_to(self.cache_dir)),
                "added_at": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "hash": file_hash,
                "dependencies": dependencies,
                "size": os.path.getsize(dest_path),
                "usage_count": 1
            }
            
            # Mettre à jour l'index
            if package_name not in self.index:
                self.index[package_name] = {"versions": {}}
            
            self.index[package_name]["versions"][version] = package_info
            
            # Sauvegarder l'index
            return self._save_index()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du package {package_name} au cache: {e}")
            return False
    
    def get_package(self, package_name: str, version: Optional[str] = None) -> Optional[Path]:
        """
        Récupère un package du cache.
        
        Args:
            package_name: Nom du package
            version: Version spécifique à récupérer (si None, utilise la dernière version)
            
        Returns:
            Path ou None: Chemin vers le fichier wheel ou None si non trouvé
        """
        # Vérifier si le package existe dans l'index
        if package_name not in self.index:
            return None
        
        # Si aucune version spécifiée, utiliser la dernière version
        if version is None:
            versions = self.index[package_name]["versions"]
            if not versions:
                return None
            
            # Trouver la dernière version (tri sémantique)
            version = sorted(versions.keys(), key=lambda v: [int(x) for x in v.split('.')])[-1]
        
        # Vérifier si la version spécifiée existe
        if version not in self.index[package_name]["versions"]:
            return None
        
        # Récupérer le chemin du package
        package_info = self.index[package_name]["versions"][version]
        package_path = self.cache_dir / package_info["path"]
        
        # Vérifier si le fichier existe réellement
        if not package_path.exists():
            logger.warning(f"Fichier manquant dans le cache: {package_path}")
            return None
        
        # Vérifier l'intégrité du fichier
        file_hash = self._calculate_file_hash(package_path)
        if file_hash != package_info["hash"]:
            logger.warning(f"Intégrité du package compromise: {package_name}-{version}")
            return None
        
        # Mettre à jour les statistiques d'utilisation
        package_info["last_used"] = datetime.now().isoformat()
        package_info["usage_count"] += 1
        self._save_index()
        
        return Path(package_path)
    
    def has_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """
        Vérifie si un package est disponible dans le cache.
        
        Args:
            package_name: Nom du package
            version: Version spécifique à vérifier (si None, vérifie si n'importe quelle version est disponible)
            
        Returns:
            bool: True si le package est disponible, False sinon
        """
        if package_name not in self.index:
            return False
        
        if version is None:
            # Vérifier si au moins une version est disponible
            return len(self.index[package_name]["versions"]) > 0
        
        # Vérifier si la version spécifiée est disponible
        return version in self.index[package_name]["versions"]
    
    def get_available_packages(self) -> Dict[str, List[str]]:
        """
        Retourne la liste des packages disponibles dans le cache.
        
        Returns:
            Dict: Dictionnaire des packages avec leurs versions disponibles
        """
        available = {}
        for package_name, package_data in self.index.items():
            available[package_name] = list(package_data["versions"].keys())
        
        return available
    
    def clean_cache(self, max_age_days: int = 90, 
                   max_size_mb: int = 5000, 
                   keep_min_versions: int = 1) -> Tuple[int, int]:
        """
        Nettoie le cache en supprimant les packages obsolètes ou rarement utilisés.
        
        Args:
            max_age_days: Âge maximum en jours pour les packages rarement utilisés
            max_size_mb: Taille maximale du cache en Mo
            keep_min_versions: Nombre minimum de versions à conserver par package
            
        Returns:
            Tuple[int, int]: (nombre de packages supprimés, espace libéré en octets)
        """
        removed_count = 0
        freed_space = 0
        
        try:
            # Calculer la taille actuelle du cache
            current_size = sum(
                package_info["size"]
                for package_data in self.index.values()
                for package_info in package_data["versions"].values()
            )
            
            # Convertir max_size_mb en octets
            max_size = max_size_mb * 1024 * 1024
            
            # Si le cache est déjà sous la limite, pas besoin de nettoyage
            if current_size <= max_size:
                return 0, 0
            
            # Date actuelle pour calcul de l'âge
            now = datetime.now()
            
            # Collecter les packages candidats pour suppression
            candidates = []
            for package_name, package_data in self.index.items():
                versions = package_data["versions"]
                
                # Ne pas supprimer si on n'a que le minimum de versions
                if len(versions) <= keep_min_versions:
                    continue
                
                for version, info in versions.items():
                    # Calculer l'âge du package en jours
                    last_used = datetime.fromisoformat(info["last_used"])
                    age_days = (now - last_used).days
                    
                    # Ajouter à la liste des candidats si obsolète
                    if age_days > max_age_days:
                        candidates.append({
                            "package_name": package_name,
                            "version": version,
                            "size": info["size"],
                            "age_days": age_days,
                            "usage_count": info["usage_count"],
                            "score": age_days / info["usage_count"]  # Score pour priorisation
                        })
            
            # Trier les candidats par score décroissant (priorité de suppression)
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            # Supprimer les packages jusqu'à atteindre la taille cible
            for candidate in candidates:
                if current_size <= max_size:
                    break
                
                package_name = candidate["package_name"]
                version = candidate["version"]
                
                # Vérifier qu'on ne va pas sous le minimum de versions
                remaining_versions = len(self.index[package_name]["versions"])
                if remaining_versions <= keep_min_versions:
                    continue
                
                # Récupérer le chemin du package
                package_info = self.index[package_name]["versions"][version]
                package_path = self.cache_dir / package_info["path"]
                
                # Supprimer le fichier
                if package_path.exists():
                    package_path.unlink()
                
                # Mettre à jour le compteur d'espace libéré
                freed_space += package_info["size"]
                current_size -= package_info["size"]
                
                # Supprimer les métadonnées
                del self.index[package_name]["versions"][version]
                
                # Si c'était la dernière version, supprimer complètement le package
                if not self.index[package_name]["versions"]:
                    del self.index[package_name]
                
                removed_count += 1
            
            # Sauvegarder l'index mis à jour
            self._save_index()
            
            return removed_count, freed_space
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du cache: {e}")
            return 0, 0
    
    def cache_requirements(self, requirements_content: str) -> str:
        """
        Met en cache un fichier requirements.txt et retourne son identifiant.
        
        Args:
            requirements_content: Contenu du fichier requirements.txt
            
        Returns:
            str: Identifiant unique du fichier requirements
        """
        # Générer un hash du contenu comme identifiant
        content_hash = hashlib.sha256(requirements_content.encode()).hexdigest()
        
        # Chemin du fichier dans le cache
        requirements_path = self.requirements_dir / f"{content_hash}.txt"
        
        # Sauvegarder le contenu si le fichier n'existe pas déjà
        if not requirements_path.exists():
            with open(requirements_path, 'w', encoding='utf-8') as f:
                f.write(requirements_content)
        
        return content_hash
    
    def get_cached_requirements(self, requirements_id: str) -> Optional[str]:
        """
        Récupère un fichier requirements.txt du cache.
        
        Args:
            requirements_id: Identifiant du fichier requirements
            
        Returns:
            str ou None: Contenu du fichier requirements ou None si non trouvé
        """
        requirements_path = self.requirements_dir / f"{requirements_id}.txt"
        
        if not requirements_path.exists():
            return None
        
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier requirements: {e}")
            return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur le cache.
        
        Returns:
            Dict: Statistiques sur le cache
        """
        package_count = len(self.index)
        version_count = sum(len(pkg_data["versions"]) for pkg_data in self.index.values())
        
        # Calculer la taille totale
        total_size = sum(
            pkg_info["size"]
            for pkg_data in self.index.values()
            for pkg_info in pkg_data["versions"].values()
        )
        
        # Trouver le package le plus récent
        latest_package = {"name": None, "added_at": "1970-01-01T00:00:00"}
        for pkg_name, pkg_data in self.index.items():
            for version, info in pkg_data["versions"].items():
                if info["added_at"] > latest_package["added_at"]:
                    latest_package = {"name": f"{pkg_name}-{version}", "added_at": info["added_at"]}
        
        return {
            "package_count": package_count,
            "version_count": version_count,
            "total_size_bytes": total_size,
            "latest_package": latest_package["name"],
            "latest_added_at": latest_package["added_at"],
            "cache_dir": str(self.cache_dir)
        }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calcule le hash SHA-256 d'un fichier.
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            str: Hash SHA-256 du fichier
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    