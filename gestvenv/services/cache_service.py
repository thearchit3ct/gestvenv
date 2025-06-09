"""
CacheService - Service de gestion du cache de packages.

Ce service gère le cache intelligent des packages Python pour :
- Mode hors ligne complet
- Accélération des installations répétées
- Stockage optimisé avec compression
- Stratégies d'expiration configurables
- Nettoyage automatique et sélectif

Il supporte plusieurs backends de cache et stratégies de stockage
pour optimiser l'espace disque et la performance.
"""

import hashlib
import json
import logging
import os
import shutil
import time
import gzip
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Stratégies de mise en cache."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE = "size"  # Based on size limits


class CompressionType(Enum):
    """Types de compression supportés."""
    NONE = "none"
    GZIP = "gzip"
    AUTO = "auto"  # Choix automatique selon la taille


@dataclass
class CacheEntry:
    """Entrée dans le cache."""
    package_name: str
    version: str
    file_path: Path
    size: int
    created_at: float
    last_accessed: float
    access_count: int
    compressed: bool = False
    compression_type: str = "none"
    original_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def age_seconds(self) -> float:
        """Âge de l'entrée en secondes."""
        return time.time() - self.created_at
    
    @property
    def age_days(self) -> float:
        """Âge de l'entrée en jours."""
        return self.age_seconds / 86400
    
    @property
    def compression_ratio(self) -> float:
        """Ratio de compression (si applicable)."""
        if self.compressed and self.original_size:
            return self.size / self.original_size
        return 1.0
    
    def update_access(self) -> None:
        """Met à jour les statistiques d'accès."""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Statistiques du cache."""
    total_entries: int
    total_size_mb: float
    compressed_entries: int
    compression_ratio: float
    hit_rate: float
    miss_rate: float
    oldest_entry_days: float
    newest_entry_days: float
    most_accessed_package: Optional[str] = None
    cache_efficiency: float = 0.0


class CacheService:
    """
    Service de gestion du cache de packages Python.
    
    Responsabilités:
    - Cache intelligent avec stratégies multiples
    - Compression automatique
    - Nettoyage et optimisation
    - Mode hors ligne
    - Statistiques et monitoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le service de cache.
        
        Args:
            config: Configuration optionnelle du service
        """
        self.config = config or {}
        
        # Configuration par défaut
        self.cache_dir = Path(self.config.get('cache_dir', Path.home() / '.gestvenv' / 'cache'))
        self.max_size_mb = self.config.get('max_size_mb', 1024)  # 1GB par défaut
        self.max_entries = self.config.get('max_entries', 1000)
        self.default_ttl_days = self.config.get('default_ttl_days', 30)
        self.compression_threshold_kb = self.config.get('compression_threshold_kb', 100)
        self.cleanup_frequency_hours = self.config.get('cleanup_frequency_hours', 24)
        self.strategy = CacheStrategy(self.config.get('strategy', 'lru'))
        self.compression = CompressionType(self.config.get('compression', 'auto'))
        
        # Répertoires de cache
        self.packages_dir = self.cache_dir / 'packages'
        self.metadata_dir = self.cache_dir / 'metadata'
        self.temp_dir = self.cache_dir / 'temp'
        
        # Index du cache
        self.index_file = self.metadata_dir / 'index.json'
        self._index: Dict[str, CacheEntry] = {}
        
        # Statistiques
        self._stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0,
            'last_cleanup': 0
        }
        
        # Mode hors ligne
        self.offline_mode = self.config.get('offline_mode', False)
        
        # Initialisation
        self._initialize_cache()
        
        logger.debug(f"CacheService initialisé avec config: {self.config}")
    
    def _initialize_cache(self) -> None:
        """Initialise la structure du cache."""
        try:
            # Création des répertoires
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.packages_dir.mkdir(exist_ok=True)
            self.metadata_dir.mkdir(exist_ok=True)
            self.temp_dir.mkdir(exist_ok=True)
            
            # Chargement de l'index existant
            self._load_index()
            
            # Vérification de l'intégrité
            self._verify_cache_integrity()
            
            # Nettoyage automatique si nécessaire
            if self._should_cleanup():
                self._cleanup_cache()
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du cache: {e}")
            # Recréation du cache en cas d'erreur critique
            self._reset_cache()
    
    def _load_index(self) -> None:
        """Charge l'index du cache depuis le disque."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Reconstruction des objets CacheEntry
                for key, entry_data in data.get('entries', {}).items():
                    try:
                        entry_data['file_path'] = Path(entry_data['file_path'])
                        self._index[key] = CacheEntry(**entry_data)
                    except Exception as e:
                        logger.warning(f"Entrée de cache corrompue ignorée {key}: {e}")
                
                # Chargement des statistiques
                if 'stats' in data:
                    self._stats.update(data['stats'])
                
                logger.debug(f"Index chargé: {len(self._index)} entrées")
            else:
                logger.debug("Aucun index existant, création d'un nouveau cache")
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'index: {e}")
            self._index = {}
    
    def _save_index(self) -> None:
        """Sauvegarde l'index du cache sur disque."""
        try:
            # Préparation des données
            entries_data = {}
            for key, entry in self._index.items():
                entry_dict = asdict(entry)
                entry_dict['file_path'] = str(entry.file_path)
                entries_data[key] = entry_dict
            
            data = {
                'entries': entries_data,
                'stats': self._stats,
                'version': '1.1.0',
                'updated_at': time.time()
            }
            
            # Sauvegarde atomique
            temp_file = self.index_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.index_file)
            logger.debug("Index sauvegardé")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'index: {e}")
    
    def _verify_cache_integrity(self) -> None:
        """Vérifie l'intégrité du cache et nettoie les entrées orphelines."""
        orphaned_entries = []
        
        for key, entry in self._index.items():
            if not entry.file_path.exists():
                orphaned_entries.append(key)
                logger.debug(f"Fichier de cache manquant: {entry.file_path}")
        
        # Suppression des entrées orphelines
        for key in orphaned_entries:
            del self._index[key]
        
        if orphaned_entries:
            logger.info(f"Nettoyage: {len(orphaned_entries)} entrées orphelines supprimées")
            self._save_index()
    
    def cache_package(self, package_name: str, version: str, data: bytes,
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Met en cache un package.
        
        Args:
            package_name: Nom du package
            version: Version du package
            data: Données binaires du package
            metadata: Métadonnées optionnelles
            
        Returns:
            bool: True si la mise en cache a réussi
        """
        try:
            # Génération de la clé de cache
            cache_key = self._generate_cache_key(package_name, version)
            
            # Vérification de l'espace disponible
            if not self._ensure_space_available(len(data)):
                logger.warning(f"Espace insuffisant pour mettre en cache {package_name}=={version}")
                return False
            
            # Compression si nécessaire
            compressed_data, compression_type, original_size = self._compress_data(data)
            
            # Génération du chemin de fichier
            file_path = self._generate_file_path(package_name, version, compression_type)
            
            # Écriture du fichier
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(compressed_data)
            
            # Création de l'entrée de cache
            entry = CacheEntry(
                package_name=package_name,
                version=version,
                file_path=file_path,
                size=len(compressed_data),
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                compressed=compression_type != CompressionType.NONE.value,
                compression_type=compression_type,
                original_size=original_size,
                metadata=metadata or {}
            )
            
            # Ajout à l'index
            self._index[cache_key] = entry
            self._save_index()
            
            logger.info(f"Package mis en cache: {package_name}=={version} "
                       f"({len(data)} bytes -> {len(compressed_data)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache de {package_name}=={version}: {e}")
            return False
    
    def get_cached_package(self, package_name: str, version: str) -> Optional[bytes]:
        """
        Récupère un package depuis le cache.
        
        Args:
            package_name: Nom du package
            version: Version du package
            
        Returns:
            Optional[bytes]: Données du package ou None si non trouvé
        """
        try:
            cache_key = self._generate_cache_key(package_name, version)
            
            # Mise à jour des statistiques
            self._stats['total_requests'] += 1
            
            if cache_key not in self._index:
                self._stats['misses'] += 1
                logger.debug(f"Cache miss: {package_name}=={version}")
                return None
            
            entry = self._index[cache_key]
            
            # Vérification de l'existence du fichier
            if not entry.file_path.exists():
                logger.warning(f"Fichier de cache manquant: {entry.file_path}")
                del self._index[cache_key]
                self._save_index()
                self._stats['misses'] += 1
                return None
            
            # Lecture du fichier
            with open(entry.file_path, 'rb') as f:
                data = f.read()
            
            # Décompression si nécessaire
            if entry.compressed:
                data = self._decompress_data(data, entry.compression_type)
            
            # Mise à jour des statistiques d'accès
            entry.update_access()
            self._stats['hits'] += 1
            
            logger.debug(f"Cache hit: {package_name}=={version}")
            return data
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache pour {package_name}=={version}: {e}")
            self._stats['misses'] += 1
            return None
    
    def is_package_cached(self, package_name: str, version: str) -> bool:
        """
        Vérifie si un package est en cache.
        
        Args:
            package_name: Nom du package
            version: Version du package
            
        Returns:
            bool: True si le package est en cache
        """
        cache_key = self._generate_cache_key(package_name, version)
        return (cache_key in self._index and 
                self._index[cache_key].file_path.exists())
    
    def remove_package(self, package_name: str, version: str) -> bool:
        """
        Supprime un package du cache.
        
        Args:
            package_name: Nom du package
            version: Version du package
            
        Returns:
            bool: True si la suppression a réussi
        """
        try:
            cache_key = self._generate_cache_key(package_name, version)
            
            if cache_key not in self._index:
                return False
            
            entry = self._index[cache_key]
            
            # Suppression du fichier
            if entry.file_path.exists():
                entry.file_path.unlink()
            
            # Suppression de l'index
            del self._index[cache_key]
            self._save_index()
            
            logger.info(f"Package supprimé du cache: {package_name}=={version}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du cache: {e}")
            return False
    
    def clear_cache(self, selective: bool = False, 
                   older_than_days: Optional[int] = None,
                   package_pattern: Optional[str] = None) -> int:
        """
        Vide le cache selon les critères spécifiés.
        
        Args:
            selective: Si True, utilise les critères de filtrage
            older_than_days: Supprimer les entrées plus anciennes que N jours
            package_pattern: Pattern pour filtrer les packages
            
        Returns:
            int: Nombre d'entrées supprimées
        """
        try:
            if not selective:
                # Nettoyage complet
                shutil.rmtree(self.packages_dir, ignore_errors=True)
                self.packages_dir.mkdir(exist_ok=True)
                
                count = len(self._index)
                self._index.clear()
                self._save_index()
                
                logger.info(f"Cache vidé complètement: {count} entrées supprimées")
                return count
            
            # Nettoyage sélectif
            to_remove = []
            current_time = time.time()
            
            for key, entry in self._index.items():
                should_remove = False
                
                # Critère d'âge
                if older_than_days is not None:
                    age_days = (current_time - entry.created_at) / 86400
                    if age_days > older_than_days:
                        should_remove = True
                
                # Critère de pattern
                if package_pattern is not None:
                    import re
                    if re.search(package_pattern, entry.package_name, re.IGNORECASE):
                        should_remove = True
                
                if should_remove:
                    to_remove.append(key)
            
            # Suppression effective
            for key in to_remove:
                entry = self._index[key]
                if entry.file_path.exists():
                    entry.file_path.unlink()
                del self._index[key]
            
            if to_remove:
                self._save_index()
            
            logger.info(f"Nettoyage sélectif: {len(to_remove)} entrées supprimées")
            return len(to_remove)
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du cache: {e}")
            return 0
    
    def get_cache_stats(self) -> CacheStats:
        """
        Retourne les statistiques du cache.
        
        Returns:
            CacheStats: Statistiques complètes
        """
        try:
            total_size = sum(entry.size for entry in self._index.values())
            compressed_count = sum(1 for entry in self._index.values() if entry.compressed)
            
            # Calcul du ratio de compression moyen
            if compressed_count > 0:
                compression_ratios = [
                    entry.compression_ratio for entry in self._index.values() 
                    if entry.compressed and entry.original_size
                ]
                avg_compression = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 1.0
            else:
                avg_compression = 1.0
            
            # Calcul des taux de hit/miss
            total_requests = self._stats['total_requests']
            hit_rate = (self._stats['hits'] / total_requests) if total_requests > 0 else 0.0
            miss_rate = (self._stats['misses'] / total_requests) if total_requests > 0 else 0.0
            
            # Entrées les plus anciennes et récentes
            if self._index:
                ages = [(time.time() - entry.created_at) / 86400 for entry in self._index.values()]
                oldest_days = max(ages)
                newest_days = min(ages)
                
                # Package le plus accédé
                most_accessed = max(self._index.values(), key=lambda e: e.access_count)
                most_accessed_package = f"{most_accessed.package_name}=={most_accessed.version}"
            else:
                oldest_days = newest_days = 0.0
                most_accessed_package = None
            
            # Efficacité du cache (basée sur la compression et les hits)
            cache_efficiency = (hit_rate * 0.7) + (avg_compression * 0.3)
            
            return CacheStats(
                total_entries=len(self._index),
                total_size_mb=total_size / (1024 * 1024),
                compressed_entries=compressed_count,
                compression_ratio=avg_compression,
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                oldest_entry_days=oldest_days,
                newest_entry_days=newest_days,
                most_accessed_package=most_accessed_package,
                cache_efficiency=cache_efficiency
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques: {e}")
            return CacheStats(0, 0.0, 0, 1.0, 0.0, 0.0, 0.0, 0.0)
    
    def optimize_cache(self) -> Dict[str, Any]:
        """
        Optimise le cache selon la stratégie configurée.
        
        Returns:
            Dict[str, Any]: Résultats de l'optimisation
        """
        try:
            logger.info("Début de l'optimisation du cache...")
            
            initial_stats = self.get_cache_stats()
            removed_count = 0
            freed_space_mb = 0.0
            
            # Application de la stratégie d'optimisation
            if self.strategy == CacheStrategy.LRU:
                removed_count, freed_space_mb = self._optimize_lru()
            elif self.strategy == CacheStrategy.LFU:
                removed_count, freed_space_mb = self._optimize_lfu()
            elif self.strategy == CacheStrategy.TTL:
                removed_count, freed_space_mb = self._optimize_ttl()
            elif self.strategy == CacheStrategy.SIZE:
                removed_count, freed_space_mb = self._optimize_size()
            
            # Nettoyage des métadonnées
            self._save_index()
            
            final_stats = self.get_cache_stats()
            
            result = {
                'strategy': self.strategy.value,
                'initial_entries': initial_stats.total_entries,
                'final_entries': final_stats.total_entries,
                'removed_entries': removed_count,
                'initial_size_mb': initial_stats.total_size_mb,
                'final_size_mb': final_stats.total_size_mb,
                'freed_space_mb': freed_space_mb,
                'efficiency_improvement': final_stats.cache_efficiency - initial_stats.cache_efficiency
            }
            
            logger.info(f"Optimisation terminée: {removed_count} entrées supprimées, "
                       f"{freed_space_mb:.2f} MB libérés")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {e}")
            return {'error': str(e)}
    
    def _optimize_lru(self) -> Tuple[int, float]:
        """Optimisation LRU (Least Recently Used)."""
        if len(self._index) <= self.max_entries:
            return 0, 0.0
        
        # Tri par dernière utilisation
        entries = list(self._index.items())
        entries.sort(key=lambda x: x[1].last_accessed)
        
        # Suppression des entrées les moins récentes
        to_remove = entries[:len(entries) - self.max_entries]
        return self._remove_entries([key for key, _ in to_remove])
    
    def _optimize_lfu(self) -> Tuple[int, float]:
        """Optimisation LFU (Least Frequently Used)."""
        if len(self._index) <= self.max_entries:
            return 0, 0.0
        
        # Tri par fréquence d'accès
        entries = list(self._index.items())
        entries.sort(key=lambda x: x[1].access_count)
        
        # Suppression des entrées les moins utilisées
        to_remove = entries[:len(entries) - self.max_entries]
        return self._remove_entries([key for key, _ in to_remove])
    
    def _optimize_ttl(self) -> Tuple[int, float]:
        """Optimisation TTL (Time To Live)."""
        current_time = time.time()
        ttl_seconds = self.default_ttl_days * 86400
        
        expired_keys = [
            key for key, entry in self._index.items()
            if (current_time - entry.created_at) > ttl_seconds
        ]
        
        return self._remove_entries(expired_keys)
    
    def _optimize_size(self) -> Tuple[int, float]:
        """Optimisation basée sur la taille."""
        total_size = sum(entry.size for entry in self._index.values())
        max_size_bytes = self.max_size_mb * 1024 * 1024
        
        if total_size <= max_size_bytes:
            return 0, 0.0
        
        # Tri par taille décroissante
        entries = list(self._index.items())
        entries.sort(key=lambda x: x[1].size, reverse=True)
        
        # Suppression jusqu'à atteindre la limite
        current_size = total_size
        to_remove = []
        
        for key, entry in entries:
            if current_size <= max_size_bytes:
                break
            to_remove.append(key)
            current_size -= entry.size
        
        return self._remove_entries(to_remove)
    
    def _remove_entries(self, keys: List[str]) -> Tuple[int, float]:
        """Supprime une liste d'entrées du cache."""
        if not keys:
            return 0, 0.0
        
        freed_space = 0.0
        successful_removals = 0
        
        for key in keys:
            if key in self._index:
                entry = self._index[key]
                freed_space += entry.size / (1024 * 1024)  # Conversion en MB
                
                # Suppression du fichier
                try:
                    if entry.file_path.exists():
                        entry.file_path.unlink()
                    del self._index[key]
                    successful_removals += 1
                except Exception as e:
                    logger.warning(f"Erreur lors de la suppression de {key}: {e}")
        
        return successful_removals, freed_space
    
    def _compress_data(self, data: bytes) -> Tuple[bytes, str, int]:
        """
        Compresse les données selon la stratégie configurée.
        
        Returns:
            Tuple[bytes, str, int]: (données compressées, type de compression, taille originale)
        """
        original_size = len(data)
        
        # Pas de compression pour les petits fichiers
        if self.compression == CompressionType.NONE or original_size < self.compression_threshold_kb * 1024:
            return data, CompressionType.NONE.value, original_size
        
        # Compression gzip
        try:
            compressed_data = gzip.compress(data, compresslevel=6)
            
            # Vérification du gain de compression
            if len(compressed_data) < original_size * 0.9:  # Au moins 10% de gain
                return compressed_data, CompressionType.GZIP.value, original_size
            else:
                # Pas de gain significatif
                return data, CompressionType.NONE.value, original_size
                
        except Exception as e:
            logger.warning(f"Erreur de compression: {e}")
            return data, CompressionType.NONE.value, original_size
    
    def _decompress_data(self, data: bytes, compression_type: str) -> bytes:
        """Décompresse les données."""
        if compression_type == CompressionType.GZIP.value:
            return gzip.decompress(data)
        else:
            return data
    
    def _generate_cache_key(self, package_name: str, version: str) -> str:
        """Génère une clé de cache unique."""
        return f"{package_name.lower()}=={version}"
    
    def _generate_file_path(self, package_name: str, version: str, compression_type: str) -> Path:
        """Génère le chemin de fichier pour un package."""
        # Utilisation d'un hash pour éviter les problèmes de noms de fichiers
        key = self._generate_cache_key(package_name, version)
        hash_digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        
        # Extension selon la compression
        extension = '.gz' if compression_type == CompressionType.GZIP.value else '.pkg'
        
        # Structure: packages/first_char/package_name/hash.ext
        first_char = package_name[0].lower() if package_name else 'unknown'
        return self.packages_dir / first_char / package_name.lower() / f"{hash_digest}{extension}"
    
    def _ensure_space_available(self, required_bytes: int) -> bool:
        """Vérifie et libère l'espace nécessaire."""
        current_size = sum(entry.size for entry in self._index.values())
        max_size_bytes = self.max_size_mb * 1024 * 1024
        
        if current_size + required_bytes <= max_size_bytes:
            return True
        
        # Libération d'espace automatique
        logger.info("Libération d'espace automatique...")
        self._optimize_cache()
        
        # Nouvelle vérification
        current_size = sum(entry.size for entry in self._index.values())
        return current_size + required_bytes <= max_size_bytes
    
    def _should_cleanup(self) -> bool:
        """Détermine si un nettoyage automatique est nécessaire."""
        last_cleanup = self._stats.get('last_cleanup', 0)
        cleanup_interval = self.cleanup_frequency_hours * 3600
        
        return (time.time() - last_cleanup) > cleanup_interval
    
    def _cleanup_cache(self) -> None:
        """Effectue un nettoyage automatique du cache."""
        logger.info("Nettoyage automatique du cache...")
        
        # Mise à jour du timestamp
        self._stats['last_cleanup'] = time.time()
        
        # Optimisation selon la stratégie
        self.optimize_cache()
        
        # Vérification de l'intégrité
        self._verify_cache_integrity()
    
    def _reset_cache(self) -> None:
        """Recrée complètement le cache."""
        logger.warning("Recréation complète du cache...")
        
        try:
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            self._initialize_cache()
        except Exception as e:
            logger.error(f"Erreur lors de la recréation du cache: {e}")
    
    def set_offline_mode(self, enabled: bool) -> bool:
        """
        Active ou désactive le mode hors ligne.
        
        Args:
            enabled: True pour activer le mode hors ligne
            
        Returns:
            bool: True si le changement a été appliqué
        """
        try:
            self.offline_mode = enabled
            logger.info(f"Mode hors ligne {'activé' if enabled else 'désactivé'}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du changement de mode: {e}")
            return False
    
    def is_offline_mode(self) -> bool:
        """Retourne True si le mode hors ligne est activé."""
        return self.offline_mode