"""
Service de cache asynchrone pour GestVenv v2.0

Version async du CacheService avec support complet
pour les opérations concurrentes et non-bloquantes.
"""

import asyncio
import aiofiles
import gzip
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.models import (
    Config,
    EnvironmentInfo,
    InstallResult,
    ExportResult
)
from ..core.exceptions import CacheError
from ..utils.async_utils import (
    run_in_executor,
    AsyncLock,
    AsyncCache,
    gather_with_concurrency,
)
from ..utils.retry import retry, RETRY_CACHE
from ..utils.error_handling import (
    ErrorCode,
    enrich_error,
    with_error_handling,
)

logger = logging.getLogger(__name__)


class AsyncCacheService:
    """Service de cache asynchrone avec support hors ligne"""

    def __init__(self, config: Config):
        self.config = config
        self.cache_path = Path.home() / ".gestvenv" / "cache"
        self.enabled = config.cache_settings.get("enabled", True)
        self.max_size_mb = config.cache_settings.get("max_size_mb", 1000)
        self.compression = config.cache_settings.get("compression", True)
        self.offline_mode = config.cache_settings.get("offline_mode", False)

        # Structure du cache
        self.packages_path = self.cache_path / "packages"
        self.metadata_path = self.cache_path / "metadata"
        self.index_path = self.cache_path / "index.json"
        self.stats_path = self.cache_path / "stats.json"

        # Locks pour accès concurrents
        self._index_lock = AsyncLock()
        self._stats_lock = AsyncLock()
        self._file_locks: Dict[str, AsyncLock] = {}

        # Index et stats en mémoire (chargés de manière lazy)
        self._cache_index: Optional[Dict[str, Any]] = None
        self._stats: Optional[Dict[str, Any]] = None

        # Cache en mémoire pour accès fréquents
        self._memory_cache = AsyncCache(ttl_seconds=300)  # 5 minutes

        self._initialized = False

    async def initialize(self) -> None:
        """Initialise le service de cache de manière asynchrone"""
        if self._initialized:
            return

        await self._ensure_cache_structure()
        self._cache_index = await self._load_cache_index()
        self._stats = await self._load_cache_stats()
        self._initialized = True
        logger.debug("AsyncCacheService initialisé")

    async def _ensure_initialized(self) -> None:
        """S'assure que le service est initialisé"""
        if not self._initialized:
            await self.initialize()

    @retry(config=RETRY_CACHE)
    async def cache_package(
        self,
        package: str,
        version: str,
        platform: str,
        data: bytes,
        backend: str = "pip"
    ) -> bool:
        """Met en cache un package téléchargé de manière asynchrone"""
        if not self.enabled:
            return False

        await self._ensure_initialized()

        try:
            cache_key = self._generate_cache_key(package, version, platform)

            # Vérification taille avant ajout
            if await self._would_exceed_cache_limit(len(data)):
                await self._make_space_for(len(data))

            # Lock pour ce fichier spécifique
            file_lock = self._get_file_lock(cache_key)
            async with file_lock:
                # Chemins
                backend_dir = self.packages_path / backend
                await run_in_executor(backend_dir.mkdir, parents=True, exist_ok=True)

                cache_file = backend_dir / f"{cache_key}.whl"
                metadata_file = self.metadata_path / f"{cache_key}.json"

                # Compression si activée
                if self.compression:
                    data = await run_in_executor(self._compress_data, data)

                # Sauvegarde fichier de manière async
                async with aiofiles.open(cache_file, 'wb') as f:
                    await f.write(data)

                # Métadonnées
                metadata = {
                    "package": package,
                    "version": version,
                    "platform": platform,
                    "backend": backend,
                    "cached_at": datetime.now().isoformat(),
                    "file_size": len(data),
                    "compressed": self.compression,
                    "checksum": self._calculate_checksum(data),
                    "last_used": datetime.now().isoformat()
                }

                await run_in_executor(self.metadata_path.mkdir, parents=True, exist_ok=True)
                async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(metadata, indent=2))

                # Mise à jour index
                await self._update_cache_index(cache_key, metadata)

                # Statistiques
                await self._update_stats("cache_add", package, len(data))

            logger.debug(f"Package {package}=={version} mis en cache")
            return True

        except Exception as e:
            logger.error(f"Erreur mise en cache {package}: {e}")
            return False

    async def get_cached_package(
        self,
        package: str,
        version: str = None,
        platform: str = None
    ) -> Optional[bytes]:
        """Récupère un package du cache de manière asynchrone"""
        await self._ensure_initialized()

        try:
            platform = platform or self._get_current_platform()

            # Vérifier le cache mémoire d'abord
            memory_key = f"{package}:{version}:{platform}"
            cached = await self._memory_cache.get(memory_key)
            if cached is not None:
                await self._update_stats("cache_hit", package, 0)
                return cached

            # Recherche exacte si version spécifiée
            if version:
                cache_key = self._generate_cache_key(package, version, platform)
                if cache_key in self._cache_index:
                    data = await self._load_cached_package(cache_key)
                    if data:
                        await self._memory_cache.set(memory_key, data)
                    return data
            else:
                # Recherche dernière version disponible
                matching_keys = [
                    key for key in self._cache_index.keys()
                    if (self._cache_index[key]["package"] == package and
                        self._cache_index[key]["platform"] == platform)
                ]

                if matching_keys:
                    from packaging import version as pkg_version
                    latest_key = max(
                        matching_keys,
                        key=lambda k: pkg_version.parse(self._cache_index[k]["version"])
                    )
                    data = await self._load_cached_package(latest_key)
                    if data:
                        await self._memory_cache.set(memory_key, data)
                    return data

            await self._update_stats("cache_miss", package, 0)
            return None

        except Exception as e:
            logger.error(f"Erreur récupération cache {package}: {e}")
            return None

    async def is_package_cached(
        self,
        package: str,
        version: str = None,
        platform: str = None
    ) -> bool:
        """Vérifie si un package est en cache"""
        await self._ensure_initialized()

        platform = platform or self._get_current_platform()

        if version:
            cache_key = self._generate_cache_key(package, version, platform)
            return cache_key in self._cache_index
        else:
            return any(
                self._cache_index[key]["package"] == package and
                self._cache_index[key]["platform"] == platform
                for key in self._cache_index.keys()
            )

    async def get_multiple_cached_packages(
        self,
        packages: List[tuple],  # List of (package, version, platform)
        concurrency: int = 5
    ) -> Dict[str, Optional[bytes]]:
        """Récupère plusieurs packages en parallèle

        Args:
            packages: Liste de tuples (package, version, platform)
            concurrency: Nombre max de requêtes parallèles

        Returns:
            Dict avec package comme clé et données comme valeur
        """
        await self._ensure_initialized()

        async def get_one(pkg_info: tuple) -> tuple:
            package, version, platform = pkg_info
            data = await self.get_cached_package(package, version, platform)
            return (package, data)

        results = await gather_with_concurrency(
            concurrency,
            *[get_one(pkg) for pkg in packages],
            return_exceptions=True
        )

        return {
            pkg: data for pkg, data in results
            if not isinstance(data, Exception)
        }

    async def cache_multiple_packages(
        self,
        packages: List[Dict[str, Any]],
        concurrency: int = 3
    ) -> Dict[str, bool]:
        """Met en cache plusieurs packages en parallèle

        Args:
            packages: Liste de dicts avec package, version, platform, data, backend
            concurrency: Nombre max d'écritures parallèles

        Returns:
            Dict avec package comme clé et succès comme valeur
        """
        await self._ensure_initialized()

        async def cache_one(pkg_info: Dict[str, Any]) -> tuple:
            success = await self.cache_package(
                pkg_info["package"],
                pkg_info["version"],
                pkg_info.get("platform", self._get_current_platform()),
                pkg_info["data"],
                pkg_info.get("backend", "pip")
            )
            return (pkg_info["package"], success)

        results = await gather_with_concurrency(
            concurrency,
            *[cache_one(pkg) for pkg in packages],
            return_exceptions=True
        )

        return {
            pkg: success for pkg, success in results
            if not isinstance(success, Exception)
        }

    async def install_from_cache(
        self,
        env: EnvironmentInfo,
        package: str
    ) -> InstallResult:
        """Installe un package depuis le cache"""
        await self._ensure_initialized()

        try:
            platform = self._get_current_platform()
            cached_data = await self.get_cached_package(package, platform=platform)

            if not cached_data:
                return InstallResult(
                    success=False,
                    message=f"Package {package} non trouvé en cache"
                )

            # Installation directe du wheel (exécution dans executor)
            temp_wheel = await run_in_executor(
                self._create_temp_wheel, package, cached_data
            )
            python_exe = self._get_python_executable(env.path)

            # Exécution subprocess dans executor
            cmd = [str(python_exe), "-m", "pip", "install", str(temp_wheel)]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300
            )

            # Nettoyage
            if temp_wheel.exists():
                await run_in_executor(temp_wheel.unlink)

            if process.returncode == 0:
                await self._update_stats("cache_install", package, 0)
                return InstallResult(
                    success=True,
                    message=f"Package {package} installé depuis le cache",
                    packages_installed=[package],
                    backend_used="cache"
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Erreur installation depuis cache: {stderr.decode()}"
                )

        except asyncio.TimeoutError:
            return InstallResult(
                success=False,
                message=f"Timeout installation cache: {package}"
            )
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Erreur installation cache: {e}"
            )

    async def clear_cache(self, selective: bool = False) -> bool:
        """Nettoie le cache"""
        await self._ensure_initialized()

        try:
            if selective:
                return await self._cleanup_lru()
            else:
                # Nettoyage complet
                if self.cache_path.exists():
                    await run_in_executor(shutil.rmtree, self.cache_path)
                await self._ensure_cache_structure()

                async with self._index_lock:
                    self._cache_index = {}
                async with self._stats_lock:
                    self._stats = self._init_stats()

                await self._memory_cache.clear()
                return True

        except Exception as e:
            logger.error(f"Erreur nettoyage cache: {e}")
            return False

    async def get_cache_size(self) -> int:
        """Taille du cache en bytes"""
        try:
            if not self.cache_path.exists():
                return 0

            def calculate_size():
                total = 0
                for file_path in self.cache_path.rglob('*'):
                    if file_path.is_file():
                        total += file_path.stat().st_size
                return total

            return await run_in_executor(calculate_size)

        except Exception:
            return 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        await self._ensure_initialized()

        async with self._stats_lock:
            stats = self._stats.copy()

        cache_size = await self.get_cache_size()

        async with self._index_lock:
            total_packages = len(self._cache_index)

        stats.update({
            "cache_size_mb": cache_size / (1024 * 1024),
            "total_packages": total_packages,
            "cache_enabled": self.enabled,
            "offline_mode": self.offline_mode,
            "compression": self.compression,
            "memory_cache_ttl": self._memory_cache._ttl
        })
        return stats

    async def optimize_cache(self) -> bool:
        """Optimise le cache"""
        await self._ensure_initialized()

        try:
            # Nettoyage LRU
            current_size = await self.get_cache_size()
            max_size = self.max_size_mb * 1024 * 1024

            if current_size > max_size:
                await self._cleanup_lru()

            # Déduplication
            await self._deduplicate_packages()

            # Nettoyage métadonnées orphelines
            await self._cleanup_orphaned_metadata()

            # Nettoyage cache mémoire
            await self._memory_cache.cleanup_expired()

            return True

        except Exception as e:
            logger.error(f"Erreur optimisation cache: {e}")
            return False

    async def export_cache(self, output_path: Path) -> ExportResult:
        """Exporte le cache pour partage"""
        await self._ensure_initialized()

        try:
            import tarfile

            def do_export():
                with tarfile.open(output_path, 'w:gz') as tar:
                    if self.packages_path.exists():
                        tar.add(self.packages_path, arcname="packages")
                    if self.metadata_path.exists():
                        tar.add(self.metadata_path, arcname="metadata")
                    if self.index_path.exists():
                        tar.add(self.index_path, arcname="index.json")
                    if self.stats_path.exists():
                        tar.add(self.stats_path, arcname="stats.json")

            await run_in_executor(do_export)

            async with self._index_lock:
                items_count = len(self._cache_index)

            return ExportResult(
                success=True,
                message=f"Cache exporté vers {output_path}",
                output_path=output_path,
                format="tar.gz",
                items_exported=items_count
            )

        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Erreur export cache: {e}",
                output_path=Path(),
                format="tar.gz",
                items_exported=0
            )

    async def import_cache(self, cache_archive: Path, merge: bool = True) -> bool:
        """Importe un cache depuis archive"""
        await self._ensure_initialized()

        try:
            import tarfile

            def do_import():
                # Sauvegarde cache actuel si merge
                if merge and self.cache_path.exists():
                    backup_path = self.cache_path.with_suffix('.backup')
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                    shutil.copytree(self.cache_path, backup_path)

                # Extraction avec filtre de sécurité
                with tarfile.open(cache_archive, 'r:gz') as tar:
                    for member in tar.getmembers():
                        member_path = self.cache_path.parent / member.name
                        if not member_path.resolve().is_relative_to(
                            self.cache_path.parent.resolve()
                        ):
                            logger.warning(
                                f"Membre tar ignoré (path traversal): {member.name}"
                            )
                            continue
                        tar.extract(member, self.cache_path.parent)

            await run_in_executor(do_import)

            # Rechargement
            async with self._index_lock:
                self._cache_index = await self._load_cache_index()
            async with self._stats_lock:
                self._stats = await self._load_cache_stats()

            await self._memory_cache.clear()

            return True

        except Exception as e:
            logger.error(f"Erreur import cache: {e}")
            return False

    def set_offline_mode(self, enabled: bool) -> None:
        """Active/désactive le mode hors ligne"""
        self.offline_mode = enabled
        self.config.cache_settings["offline_mode"] = enabled

    def is_offline_mode_enabled(self) -> bool:
        """Vérifie si le mode hors ligne est activé"""
        return self.offline_mode

    # Méthodes privées

    def _get_file_lock(self, cache_key: str) -> AsyncLock:
        """Obtient ou crée un lock pour un fichier"""
        if cache_key not in self._file_locks:
            self._file_locks[cache_key] = AsyncLock(timeout=30)
        return self._file_locks[cache_key]

    async def _ensure_cache_structure(self) -> None:
        """Assure la structure du cache"""
        await run_in_executor(self.cache_path.mkdir, parents=True, exist_ok=True)
        await run_in_executor(self.packages_path.mkdir, exist_ok=True)
        await run_in_executor(self.metadata_path.mkdir, exist_ok=True)

        if not self.index_path.exists():
            await self._save_cache_index({})

        if not self.stats_path.exists():
            await self._save_cache_stats(self._init_stats())

    def _generate_cache_key(self, package: str, version: str, platform: str) -> str:
        """Génère clé de cache"""
        key_string = f"{package}-{version}-{platform}"
        return hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()

    def _get_current_platform(self) -> str:
        """Plateforme actuelle"""
        import platform
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "windows":
            return f"win_{machine}"
        elif system == "darwin":
            return f"macosx_{machine}"
        else:
            return f"linux_{machine}"

    def _compress_data(self, data: bytes) -> bytes:
        """Compresse les données"""
        return gzip.compress(data)

    def _decompress_data(self, data: bytes) -> bytes:
        """Décompresse les données"""
        return gzip.decompress(data)

    def _calculate_checksum(self, data: bytes) -> str:
        """Calcule le checksum"""
        return hashlib.sha256(data).hexdigest()

    async def _load_cache_index(self) -> Dict[str, Any]:
        """Charge l'index du cache"""
        try:
            if self.index_path.exists():
                async with aiofiles.open(self.index_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
        except Exception as e:
            logger.warning(f"Erreur chargement index: {e}")
        return {}

    async def _save_cache_index(self, index: Dict[str, Any] = None) -> None:
        """Sauvegarde l'index du cache"""
        try:
            if index is None:
                async with self._index_lock:
                    index = self._cache_index or {}

            async with aiofiles.open(self.index_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(index, indent=2))
        except Exception as e:
            logger.error(f"Erreur sauvegarde index cache: {e}")

    async def _load_cache_stats(self) -> Dict[str, Any]:
        """Charge les statistiques du cache"""
        try:
            if self.stats_path.exists():
                async with aiofiles.open(self.stats_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
        except Exception as e:
            logger.warning(f"Erreur chargement stats: {e}")
        return self._init_stats()

    def _init_stats(self) -> Dict[str, Any]:
        """Initialise les statistiques"""
        return {
            "cache_hits": 0,
            "cache_misses": 0,
            "packages_cached": 0,
            "total_downloads": 0,
            "space_saved_mb": 0.0,
            "created_at": datetime.now().isoformat()
        }

    async def _save_cache_stats(self, stats: Dict[str, Any] = None) -> None:
        """Sauvegarde les statistiques"""
        try:
            if stats is None:
                async with self._stats_lock:
                    stats = self._stats or self._init_stats()

            async with aiofiles.open(self.stats_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(stats, indent=2))
        except Exception as e:
            logger.error(f"Erreur sauvegarde stats cache: {e}")

    async def _update_cache_index(self, cache_key: str, metadata: Dict[str, Any]) -> None:
        """Met à jour l'index du cache"""
        async with self._index_lock:
            self._cache_index[cache_key] = metadata
            await self._save_cache_index(self._cache_index)

    async def _update_stats(self, operation: str, package: str, size: int) -> None:
        """Met à jour les statistiques"""
        async with self._stats_lock:
            if operation == "cache_add":
                self._stats["packages_cached"] += 1
                self._stats["space_saved_mb"] += size / (1024 * 1024)
            elif operation == "cache_hit":
                self._stats["cache_hits"] += 1
            elif operation == "cache_miss":
                self._stats["cache_misses"] += 1
            elif operation == "cache_install":
                self._stats["cache_hits"] += 1

            await self._save_cache_stats(self._stats)

    async def _would_exceed_cache_limit(self, additional_size: int) -> bool:
        """Vérifie si l'ajout dépasserait la limite"""
        current_size = await self.get_cache_size()
        max_size = self.max_size_mb * 1024 * 1024
        return (current_size + additional_size) > max_size

    async def _make_space_for(self, required_size: int) -> None:
        """Libère de l'espace pour un ajout"""
        await self._cleanup_lru(required_size)

    async def _cleanup_lru(self, required_space: int = None) -> bool:
        """Nettoyage LRU"""
        try:
            current_size = await self.get_cache_size()
            max_size = self.max_size_mb * 1024 * 1024

            if required_space:
                target_size = current_size - required_space
            else:
                target_size = max_size * 0.8

            if current_size <= target_size:
                return True

            async with self._index_lock:
                items_by_usage = sorted(
                    self._cache_index.items(),
                    key=lambda x: x[1].get("last_used", x[1]["cached_at"])
                )

            space_freed = 0
            for cache_key, metadata in items_by_usage:
                if current_size - space_freed <= target_size:
                    break

                file_size = await self._remove_cache_entry(cache_key)
                space_freed += file_size

            return True

        except Exception as e:
            logger.error(f"Erreur nettoyage LRU: {e}")
            return False

    async def _remove_cache_entry(self, cache_key: str) -> int:
        """Supprime une entrée du cache"""
        try:
            async with self._index_lock:
                metadata = self._cache_index.get(cache_key)
                if not metadata:
                    return 0

            backend = metadata.get("backend", "pip")
            cache_file = self.packages_path / backend / f"{cache_key}.whl"
            metadata_file = self.metadata_path / f"{cache_key}.json"

            file_size = 0
            if cache_file.exists():
                file_size = cache_file.stat().st_size
                await run_in_executor(cache_file.unlink)

            if metadata_file.exists():
                await run_in_executor(metadata_file.unlink)

            async with self._index_lock:
                if cache_key in self._cache_index:
                    del self._cache_index[cache_key]
                await self._save_cache_index(self._cache_index)

            return file_size

        except Exception as e:
            logger.error(f"Erreur suppression entrée cache {cache_key}: {e}")
            return 0

    async def _load_cached_package(self, cache_key: str) -> Optional[bytes]:
        """Charge un package depuis le cache"""
        try:
            async with self._index_lock:
                metadata = self._cache_index.get(cache_key)

            if not metadata:
                return None

            backend = metadata.get("backend", "pip")
            cache_file = self.packages_path / backend / f"{cache_key}.whl"

            if not cache_file.exists():
                return None

            async with aiofiles.open(cache_file, 'rb') as f:
                data = await f.read()

            if metadata.get("compressed", False):
                data = await run_in_executor(self._decompress_data, data)

            # Mise à jour dernière utilisation
            metadata["last_used"] = datetime.now().isoformat()
            await self._update_cache_index(cache_key, metadata)

            return data

        except Exception as e:
            logger.error(f"Erreur chargement package cache {cache_key}: {e}")
            return None

    def _create_temp_wheel(self, package: str, data: bytes) -> Path:
        """Crée un wheel temporaire"""
        import tempfile

        temp_dir = Path(tempfile.gettempdir())
        temp_wheel = temp_dir / f"{package}_temp.whl"
        temp_wheel.write_bytes(data)
        return temp_wheel

    def _get_python_executable(self, env_path: Path) -> Path:
        """Exécutable Python de l'environnement"""
        if os.name == 'nt':
            return env_path / "Scripts" / "python.exe"
        else:
            return env_path / "bin" / "python"

    async def _deduplicate_packages(self) -> None:
        """Déduplication des packages"""
        # Implémentation future avec vérification checksum
        pass

    async def _cleanup_orphaned_metadata(self) -> None:
        """Nettoie les métadonnées orphelines"""
        try:
            def find_orphans():
                orphans = []
                for metadata_file in self.metadata_path.glob("*.json"):
                    cache_key = metadata_file.stem
                    if cache_key not in self._cache_index:
                        orphans.append(metadata_file)
                return orphans

            orphans = await run_in_executor(find_orphans)

            for metadata_file in orphans:
                await run_in_executor(metadata_file.unlink)

        except Exception as e:
            logger.error(f"Erreur nettoyage métadonnées orphelines: {e}")


# Context manager pour utilisation simplifiée
class async_cache_context:
    """Context manager pour le service de cache async"""

    def __init__(self, config: Config):
        self.service = AsyncCacheService(config)

    async def __aenter__(self) -> AsyncCacheService:
        await self.service.initialize()
        return self.service

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # Sauvegarde finale des stats
        await self.service._save_cache_stats()
        await self.service._save_cache_index()
