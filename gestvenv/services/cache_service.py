"""
Service de cache intelligent pour GestVenv v1.1
"""

import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import tempfile
from ..core.models import (
    Config,
    EnvironmentInfo,
    InstallResult,
    ExportResult,
    CacheAddResult
)
from ..core.exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheService:
    """Service de cache intelligent avec support hors ligne"""
    
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
        
        # Index et stats en mémoire
        self._cache_index = self._load_cache_index()
        self._stats = self._load_cache_stats()
        
        self._ensure_cache_structure()
    
    def cache_package(
        self, 
        package: str, 
        version: str, 
        platform: str, 
        data: bytes,
        backend: str = "pip"
    ) -> bool:
        """Met en cache un package téléchargé"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_cache_key(package, version, platform)
            
            # Vérification taille avant ajout
            if self._would_exceed_cache_limit(len(data)):
                self._make_space_for(len(data))
            
            # Chemins
            backend_dir = self.packages_path / backend
            backend_dir.mkdir(parents=True, exist_ok=True)
            
            cache_file = backend_dir / f"{cache_key}.whl"
            metadata_file = self.metadata_path / f"{cache_key}.json"
            
            # Compression si activée
            if self.compression:
                data = self._compress_data(data)
            
            # Sauvegarde fichier
            cache_file.write_bytes(data)
            
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
            
            self.metadata_path.mkdir(parents=True, exist_ok=True)
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            # Mise à jour index
            self._update_cache_index(cache_key, metadata)
            
            # Statistiques
            self._update_stats("cache_add", package, len(data))
            
            logger.debug(f"Package {package}=={version} mis en cache")
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise en cache {package}: {e}")
            return False
    
    def get_cached_package(
        self, 
        package: str, 
        version: str = None, 
        platform: str = None
    ) -> Optional[bytes]:
        """Récupère un package du cache"""
        try:
            platform = platform or self._get_current_platform()
            
            # Recherche exacte si version spécifiée
            if version:
                cache_key = self._generate_cache_key(package, version, platform)
                if cache_key in self._cache_index:
                    return self._load_cached_package(cache_key)
            else:
                # Recherche dernière version disponible
                matching_keys = [
                    key for key in self._cache_index.keys()
                    if (self._cache_index[key]["package"] == package and
                        self._cache_index[key]["platform"] == platform)
                ]
                
                if matching_keys:
                    # Tri par version (dernière en premier)
                    from packaging import version as pkg_version
                    latest_key = max(
                        matching_keys,
                        key=lambda k: pkg_version.parse(self._cache_index[k]["version"])
                    )
                    return self._load_cached_package(latest_key)
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération cache {package}: {e}")
            return None
    
    def is_package_cached(
        self, 
        package: str, 
        version: str = None, 
        platform: str = None
    ) -> bool:
        """Vérifie si un package est en cache"""
        platform = platform or self._get_current_platform()
        
        if version:
            cache_key = self._generate_cache_key(package, version, platform)
            return cache_key in self._cache_index
        else:
            # Recherche toute version
            return any(
                self._cache_index[key]["package"] == package and
                self._cache_index[key]["platform"] == platform
                for key in self._cache_index.keys()
            )
    
    def install_from_cache(self, env: EnvironmentInfo, package: str) -> InstallResult:
        """Installe un package depuis le cache"""
        try:
            platform = self._get_current_platform()
            cached_data = self.get_cached_package(package, platform=platform)
            
            if not cached_data:
                return InstallResult(
                    success=False,
                    message=f"Package {package} non trouvé en cache"
                )
            
            # Installation directe du wheel
            temp_wheel = self._create_temp_wheel(package, cached_data)
            python_exe = self._get_python_executable(env.path)
            
            cmd = [str(python_exe), "-m", "pip", "install", str(temp_wheel)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Nettoyage
            if temp_wheel.exists():
                temp_wheel.unlink()
            
            if result.returncode == 0:
                self._update_stats("cache_install", package, 0)
                return InstallResult(
                    success=True,
                    message=f"Package {package} installé depuis le cache",
                    packages_installed=[package],
                    backend_used="cache"
                )
            else:
                return InstallResult(
                    success=False,
                    message=f"Erreur installation depuis cache: {result.stderr}"
                )
                
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Erreur installation cache: {e}"
            )
    
    def cache_installed_package(self, env: EnvironmentInfo, package: str) -> bool:
        """Met en cache un package après installation"""
        try:
            # Recherche du wheel dans site-packages
            site_packages = env.path / "lib" / f"python{env.python_version[:3]}" / "site-packages"
            
            # Recherche fichier wheel ou info du package
            package_files = list(site_packages.glob(f"{package}*"))
            
            if package_files:
                # Création wheel temporaire depuis installation
                wheel_data = self._create_wheel_from_installation(package, site_packages)
                if wheel_data:
                    version = self._extract_package_version(package, site_packages)
                    platform = self._get_current_platform()
                    return self.cache_package(package, version, platform, wheel_data)
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur mise en cache package installé {package}: {e}")
            return False

    def add_package_to_cache(
        self,
        package: str,
        platforms: Optional[List[str]] = None,
        python_version: Optional[str] = None
    ) -> CacheAddResult:
        """
        Télécharge un package et l'ajoute au cache.

        Args:
            package: Nom du package (avec version optionnelle, ex: 'requests==2.28.0')
            platforms: Liste des plateformes cibles (optionnel)
            python_version: Version Python cible (optionnel)

        Returns:
            CacheAddResult avec le statut de l'opération
        """
        if not self.enabled:
            return CacheAddResult(
                success=False,
                message="Cache désactivé",
                package=package
            )

        temp_dir = None
        try:
            # Créer un répertoire temporaire pour le téléchargement
            temp_dir = tempfile.mkdtemp(prefix="gestvenv_cache_")
            temp_path = Path(temp_dir)

            # Construire la commande pip download
            cmd = ["pip", "download", "--dest", str(temp_path), package]

            # Ajouter les options de plateforme si spécifiées
            if platforms:
                for platform in platforms:
                    cmd.extend(["--platform", platform])

            # Ajouter la version Python si spécifiée
            if python_version:
                cmd.extend(["--python-version", python_version])

            logger.info(f"Téléchargement de {package} vers le cache")

            # Exécuter pip download avec encodage UTF-8 explicite
            # pour éviter les erreurs Windows cp1252
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Remplacer les caractères non-décodables
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Erreur inconnue"
                logger.error(f"Échec pip download pour {package}: {error_msg}")
                return CacheAddResult(
                    success=False,
                    message=f"Échec téléchargement: {error_msg[:200]}",
                    package=package
                )

            # Trouver les fichiers téléchargés (.whl ou .tar.gz)
            downloaded_files = list(temp_path.glob("*.whl")) + list(temp_path.glob("*.tar.gz"))

            if not downloaded_files:
                return CacheAddResult(
                    success=False,
                    message="Aucun fichier téléchargé",
                    package=package
                )

            cached_files = []
            total_size = 0
            main_version = ""

            # Mettre en cache chaque fichier téléchargé
            for file_path in downloaded_files:
                try:
                    # Lire les données du fichier
                    file_data = file_path.read_bytes()
                    file_size = len(file_data)
                    total_size += file_size

                    # Parser le nom du fichier pour extraire package/version
                    file_name = file_path.name
                    parts = file_name.replace('.whl', '').replace('.tar.gz', '').split('-')

                    if len(parts) >= 2:
                        pkg_name = parts[0]
                        pkg_version = parts[1]

                        # Garder la version du package principal
                        if pkg_name.lower().replace('_', '-') == package.lower().split('==')[0].replace('_', '-'):
                            main_version = pkg_version

                        # Déterminer la plateforme
                        platform = self._get_current_platform()
                        if len(parts) >= 5 and file_name.endswith('.whl'):
                            # Format wheel: name-version-pyver-abi-platform.whl
                            platform = parts[-1]

                        # Mettre en cache
                        if self.cache_package(pkg_name, pkg_version, platform, file_data):
                            cached_files.append(f"{pkg_name}-{pkg_version}")
                            logger.debug(f"Package mis en cache: {pkg_name}-{pkg_version}")

                except Exception as e:
                    logger.warning(f"Erreur mise en cache de {file_path.name}: {e}")
                    continue

            if cached_files:
                return CacheAddResult(
                    success=True,
                    message=f"{len(cached_files)} fichier(s) mis en cache",
                    package=package,
                    version=main_version,
                    file_size=total_size,
                    cached_files=cached_files
                )
            else:
                return CacheAddResult(
                    success=False,
                    message="Aucun fichier n'a pu être mis en cache",
                    package=package
                )

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout lors du téléchargement de {package}")
            return CacheAddResult(
                success=False,
                message="Timeout lors du téléchargement (>5min)",
                package=package
            )
        except Exception as e:
            logger.error(f"Erreur ajout package au cache {package}: {e}")
            return CacheAddResult(
                success=False,
                message=str(e),
                package=package
            )
        finally:
            # Nettoyer le répertoire temporaire
            if temp_dir and Path(temp_dir).exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Impossible de supprimer {temp_dir}: {e}")

    def clear_cache(self, selective: bool = False) -> bool:
        """Nettoie le cache"""
        try:
            if selective:
                # Nettoyage sélectif (LRU)
                return self._cleanup_lru()
            else:
                # Nettoyage complet
                if self.cache_path.exists():
                    shutil.rmtree(self.cache_path)
                self._ensure_cache_structure()
                self._cache_index = {}
                self._stats = self._init_stats()
                return True
        except Exception as e:
            logger.error(f"Erreur nettoyage cache: {e}")
            return False
    
    def get_cache_size(self) -> int:
        """Taille du cache en bytes"""
        try:
            if not self.cache_path.exists():
                return 0
            
            total_size = 0
            for file_path in self.cache_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size
        except Exception:
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        stats = self._stats.copy()
        stats.update({
            "cache_size_mb": self.get_cache_size() / (1024 * 1024),
            "total_packages": len(self._cache_index),
            "cache_enabled": self.enabled,
            "offline_mode": self.offline_mode,
            "compression": self.compression
        })
        return stats
    
    def optimize_cache(self) -> bool:
        """Optimise le cache"""
        try:
            # Nettoyage LRU
            current_size = self.get_cache_size()
            max_size = self.max_size_mb * 1024 * 1024
            
            if current_size > max_size:
                self._cleanup_lru()
            
            # Déduplication
            self._deduplicate_packages()
            
            # Nettoyage métadonnées orphelines
            self._cleanup_orphaned_metadata()
            
            return True
        except Exception as e:
            logger.error(f"Erreur optimisation cache: {e}")
            return False
    
    def export_cache(self, output_path: Path) -> ExportResult:
        """Exporte le cache pour partage"""
        try:
            import tarfile
            
            with tarfile.open(output_path, 'w:gz') as tar:
                tar.add(self.packages_path, arcname="packages")
                tar.add(self.metadata_path, arcname="metadata")
                tar.add(self.index_path, arcname="index.json")
                tar.add(self.stats_path, arcname="stats.json")
            
            return ExportResult(
                success=True,
                message=f"Cache exporté vers {output_path}",
                output_path=output_path,
                format="tar.gz",
                items_exported=len(self._cache_index)
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Erreur export cache: {e}",
                output_path=Path(),
                format="tar.gz",
                items_exported=0
            )
    
    def import_cache(self, cache_archive: Path, merge: bool = True) -> bool:
        """Importe un cache depuis archive"""
        try:
            import tarfile
            
            # Sauvegarde cache actuel si merge
            if merge and self.cache_path.exists():
                backup_path = self.cache_path.with_suffix('.backup')
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(self.cache_path, backup_path)
            
            # Extraction avec filtre de sécurité (évite path traversal)
            with tarfile.open(cache_archive, 'r:gz') as tar:
                # Python 3.12+: filter='data' filtre les membres dangereux
                # Pour compatibilité, on utilise une approche manuelle
                for member in tar.getmembers():
                    # Vérifie que le chemin est sûr (pas de path traversal)
                    member_path = self.cache_path.parent / member.name
                    if not member_path.resolve().is_relative_to(self.cache_path.parent.resolve()):
                        logger.warning(f"Membre tar ignoré (path traversal): {member.name}")
                        continue
                    tar.extract(member, self.cache_path.parent)  # nosec B202
            
            # Rechargement
            self._cache_index = self._load_cache_index()
            self._stats = self._load_cache_stats()
            
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
    
    def _ensure_cache_structure(self) -> None:
        """Assure la structure du cache"""
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.packages_path.mkdir(exist_ok=True)
        self.metadata_path.mkdir(exist_ok=True)
        
        if not self.index_path.exists():
            self._save_cache_index()
        
        if not self.stats_path.exists():
            self._save_cache_stats()
    
    def _generate_cache_key(self, package: str, version: str, platform: str) -> str:
        """Génère clé de cache (MD5 utilisé pour hashing non-cryptographique)"""
        key_string = f"{package}-{version}-{platform}"
        # usedforsecurity=False indique que MD5 n'est pas utilisé pour la sécurité
        return hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()  # nosec B324
    
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
    
    def _load_cache_index(self) -> Dict[str, Any]:
        """Charge l'index du cache"""
        try:
            if self.index_path.exists():
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_cache_index(self) -> None:
        """Sauvegarde l'index du cache"""
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache_index, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde index cache: {e}")
    
    def _load_cache_stats(self) -> Dict[str, Any]:
        """Charge les statistiques du cache"""
        try:
            if self.stats_path.exists():
                with open(self.stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
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
    
    def _save_cache_stats(self) -> None:
        """Sauvegarde les statistiques"""
        try:
            with open(self.stats_path, 'w', encoding='utf-8') as f:
                json.dump(self._stats, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde stats cache: {e}")
    
    def _update_cache_index(self, cache_key: str, metadata: Dict[str, Any]) -> None:
        """Met à jour l'index du cache"""
        self._cache_index[cache_key] = metadata
        self._save_cache_index()
    
    def _update_stats(self, operation: str, package: str, size: int) -> None:
        """Met à jour les statistiques"""
        if operation == "cache_add":
            self._stats["packages_cached"] += 1
            self._stats["space_saved_mb"] += size / (1024 * 1024)
        elif operation == "cache_hit":
            self._stats["cache_hits"] += 1
        elif operation == "cache_miss":
            self._stats["cache_misses"] += 1
        elif operation == "cache_install":
            self._stats["cache_hits"] += 1
        
        self._save_cache_stats()
    
    def _would_exceed_cache_limit(self, additional_size: int) -> bool:
        """Vérifie si l'ajout dépasserait la limite"""
        current_size = self.get_cache_size()
        max_size = self.max_size_mb * 1024 * 1024
        return (current_size + additional_size) > max_size
    
    def _make_space_for(self, required_size: int) -> None:
        """Libère de l'espace pour un ajout"""
        self._cleanup_lru(required_size)
    
    def _cleanup_lru(self, required_space: int = None) -> bool:
        """Nettoyage LRU"""
        try:
            current_size = self.get_cache_size()
            max_size = self.max_size_mb * 1024 * 1024
            
            if required_space:
                target_size = current_size - required_space
            else:
                target_size = max_size * 0.8  # 80% de la limite
            
            if current_size <= target_size:
                return True
            
            # Tri par dernière utilisation
            items_by_usage = sorted(
                self._cache_index.items(),
                key=lambda x: x[1].get("last_used", x[1]["cached_at"])
            )
            
            space_freed = 0
            for cache_key, metadata in items_by_usage:
                if current_size - space_freed <= target_size:
                    break
                
                file_size = self._remove_cache_entry(cache_key)
                space_freed += file_size
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur nettoyage LRU: {e}")
            return False
    
    def _remove_cache_entry(self, cache_key: str) -> int:
        """Supprime une entrée du cache"""
        try:
            metadata = self._cache_index.get(cache_key)
            if not metadata:
                return 0
            
            # Suppression fichiers
            backend = metadata.get("backend", "pip")
            cache_file = self.packages_path / backend / f"{cache_key}.whl"
            metadata_file = self.metadata_path / f"{cache_key}.json"
            
            file_size = 0
            if cache_file.exists():
                file_size = cache_file.stat().st_size
                cache_file.unlink()
            
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Suppression de l'index
            del self._cache_index[cache_key]
            self._save_cache_index()
            
            return file_size
            
        except Exception as e:
            logger.error(f"Erreur suppression entrée cache {cache_key}: {e}")
            return 0
    
    def _load_cached_package(self, cache_key: str) -> Optional[bytes]:
        """Charge un package depuis le cache"""
        try:
            metadata = self._cache_index.get(cache_key)
            if not metadata:
                return None
            
            backend = metadata.get("backend", "pip")
            cache_file = self.packages_path / backend / f"{cache_key}.whl"
            
            if not cache_file.exists():
                return None
            
            data = cache_file.read_bytes()
            
            # Décompression si nécessaire
            if metadata.get("compressed", False):
                data = self._decompress_data(data)
            
            # Mise à jour dernière utilisation
            metadata["last_used"] = datetime.now().isoformat()
            self._update_cache_index(cache_key, metadata)
            
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
    
    def _create_wheel_from_installation(self, package: str, site_packages: Path) -> Optional[bytes]:
        """Crée un wheel depuis une installation"""
        # Implémentation simplifiée
        # Dans une vraie implémentation, utiliser wheel ou pip wheel
        return None
    
    def _extract_package_version(self, package: str, site_packages: Path) -> str:
        """Extrait la version d'un package installé"""
        try:
            # Recherche fichier METADATA ou PKG-INFO
            for dist_info in site_packages.glob(f"{package}*.dist-info"):
                metadata_file = dist_info / "METADATA"
                if metadata_file.exists():
                    content = metadata_file.read_text(encoding='utf-8')
                    for line in content.split('\n'):
                        if line.startswith('Version:'):
                            return line.split(':', 1)[1].strip()
            
            return "unknown"
        except Exception:
            return "unknown"
    
    def _deduplicate_packages(self) -> None:
        """Déduplication des packages"""
        # Implémentation simplifiée
        # Peut être améliorée avec vérification checksum
        pass
    
    def _cleanup_orphaned_metadata(self) -> None:
        """Nettoie les métadonnées orphelines"""
        try:
            for metadata_file in self.metadata_path.glob("*.json"):
                cache_key = metadata_file.stem
                if cache_key not in self._cache_index:
                    metadata_file.unlink()
        except Exception as e:
            logger.error(f"Erreur nettoyage métadonnées orphelines: {e}")