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
import subprocess
import re
import zipfile
from datetime import datetime, timedelta
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
        self.temp_dir = self.cache_dir / "temp"
        
        # Créer les répertoires s'ils n'existent pas
        self._ensure_cache_structure()
        
        # Charger l'index
        self.index = self._load_index()
    
    def _ensure_cache_structure(self) -> None:
        """Crée la structure de répertoires du cache si elle n'existe pas."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self.requirements_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
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
            except json.JSONDecodeError as e:
                logger.error(f"Erreur lors du chargement de l'index du cache: {e}")
                # Créer une sauvegarde du fichier corrompu
                if index_path.exists():
                    backup_path = index_path.with_suffix('.json.bak')
                    shutil.copy2(index_path, backup_path)
                    logger.warning(f"Sauvegarde de l'index corrompu créée: {backup_path}")
            except Exception as e:
                logger.error(f"Erreur inattendue lors du chargement de l'index: {e}")
        
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
            
            # Sauvegarder le nouvel index avec métadonnées
            index_with_metadata = {
                "_metadata": {
                    "version": "1.0",
                    "updated_at": datetime.now().isoformat(),
                    "total_packages": len(self.index),
                    "total_versions": sum(len(pkg_data.get("versions", {})) for pkg_data in self.index.values())
                },
                **self.index
            }
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_with_metadata, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'index du cache: {e}")
            return False
    
    def download_and_cache_packages_from_string(self, packages_str: str) -> Tuple[int, List[str]]:
        """
        Télécharge et met en cache des packages depuis une chaîne.
        
        Args:
            packages_str: Chaîne de packages séparés par des virgules
            
        Returns:
            Tuple[int, List[str]]: (nombre de packages ajoutés, liste des erreurs)
        """
        # Parser la chaîne de packages
        packages = [pkg.strip() for pkg in packages_str.split(',') if pkg.strip()]
        return self.download_and_cache_packages(packages)
    
    def download_and_cache_packages(self, packages: List[str]) -> Tuple[int, List[str]]:
        """
        Télécharge et met en cache une liste de packages.
        
        Args:
            packages: Liste des packages à télécharger
            
        Returns:
            Tuple[int, List[str]]: (nombre de packages ajoutés, liste des erreurs)
        """
        added_count = 0
        errors = []
        
        if not packages:
            return 0, ["Aucun package spécifié"]
        
        # Créer un répertoire temporaire pour le téléchargement
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Commande pip download avec gestion d'encodage
                cmd = ["pip", "download", "--dest", temp_dir] + packages
                logger.info(f"Exécution: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    shell=False,
                    check=False,
                    encoding='utf-8',
                    errors='replace',
                    timeout=300
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr or "Erreur de téléchargement inconnue"
                    logger.error(f"Échec téléchargement: {error_msg}")
                    return 0, [f"Échec téléchargement: {error_msg}"]
                
                # Traiter les fichiers téléchargés
                try:
                    for file_name in os.listdir(temp_dir):
                        file_path = Path(temp_dir) / file_name
                        
                        if self._is_package_file(file_path):
                            try:
                                package_info = self._extract_package_info_safe(file_name)
                                
                                if package_info:
                                    dependencies = self._get_dependencies_safe(package_info['name'])
                                    
                                    success = self.add_package(
                                        file_path,
                                        package_info['name'],
                                        package_info['version'],
                                        dependencies
                                    )
                                    
                                    if success:
                                        logger.info(f"Package mis en cache: {package_info['name']}-{package_info['version']}")
                                        added_count += 1
                                    else:
                                        error_msg = f"Échec mise en cache: {package_info['name']}"
                                        errors.append(error_msg)
                                else:
                                    errors.append(f"Impossible d'extraire les infos de: {file_name}")
                                    
                            except Exception as e:
                                error_msg = f"Erreur traitement {file_name}: {str(e)}"
                                logger.error(error_msg)
                                errors.append(error_msg)
                                
                except Exception as e:
                    error_msg = f"Erreur listage fichiers: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
            except subprocess.TimeoutExpired:
                error_msg = "Timeout: téléchargement trop long"
                logger.error(error_msg)
                errors.append(error_msg)
                
            except Exception as e:
                error_msg = f"Erreur générale téléchargement: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return added_count, errors
    
    def _is_package_file(self, file_path: Path) -> bool:
        """Vérifie si un fichier est un package Python."""
        return file_path.suffix.lower() in ['.whl', '.tar.gz', '.zip']
    
    def _extract_package_info_safe(self, filename: str) -> Optional[Dict[str, str]]:
        """
        Extraction sécurisée des informations de package.
        """
        try:
            # Supprimer TOUTES les extensions possibles
            name_without_ext = filename

            # Gérer .tar.gz en premier
            if filename.endswith('.tar.gz'):
                name_without_ext = filename[:-7]
            else:
                # Supprimer les autres extensions
                for ext in ['.whl', '.zip', '.gz', '.tar', '.txt']:
                    if filename.endswith(ext):
                        name_without_ext = filename[:-len(ext)]
                        break
                    
            # Si aucune extension connue, prendre jusqu'au premier point
            if name_without_ext == filename and '.' in filename:
                name_without_ext = filename.split('.')[0]

            # Parser le nom avec méthode robuste
            parts = name_without_ext.split('-')

            if len(parts) >= 2:
                package_name = parts[0]
                version = "unknown"

                # Chercher le premier élément qui ressemble à une version
                for i, part in enumerate(parts[1:], 1):
                    if self._looks_like_version(part):
                        package_name = '-'.join(parts[:i])
                        version = part
                        break
                    
                # Si pas de version trouvée, prendre le deuxième élément
                if version == "unknown" and len(parts) >= 2:
                    package_name = parts[0]
                    version = parts[1]

                return {
                    'name': package_name,
                    'version': version,
                    'filename': filename
                }

            # Fallback si moins de 2 parties
            base_name = name_without_ext
            return {
                'name': base_name,
                'version': 'unknown',
                'filename': filename
            }

        except Exception as e:
            logger.warning(f"Erreur extraction info {filename}: {e}")
            # Extraire le nom de base plus intelligemment
            base_name = filename
            for ext in ['.tar.gz', '.whl', '.zip', '.gz', '.tar', '.txt']:
                if filename.endswith(ext):
                    base_name = filename[:-len(ext)]
                    break
            if base_name == filename and '.' in filename:
                base_name = filename.split('.')[0]

            return {
                'name': base_name,
                'version': 'unknown',
                'filename': filename
            }
    
    def _looks_like_version(self, text: str) -> bool:
        """
        Vérifie si une chaîne ressemble à un numéro de version.
        
        Args:
            text: Texte à vérifier
            
        Returns:
            bool: True si ressemble à une version
        """
        if not text:
            return False
            
        version_pattern = r'^\d+(\.\d+)*([a-zA-Z]\d*)?(\.\w+)*$'
        return bool(re.match(version_pattern, text))
    
    def _get_dependencies_safe(self, package_name: str) -> List[str]:
        """
        Récupère les dépendances d'un package de manière sécurisée.
        
        Args:
            package_name: Nom du package
            
        Returns:
            List[str]: Liste des dépendances (vide si erreur)
        """
        try:
            cmd = ["pip", "show", package_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=False,
                check=False,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith('Requires:'):
                        deps_str = line.split(':', 1)[1].strip()
                        if deps_str and deps_str.lower() != 'none':
                            return [dep.strip() for dep in deps_str.split(',') if dep.strip()]
                        break
            
        except Exception as e:
            logger.debug(f"Impossible de récupérer les dépendances de {package_name}: {e}")
        
        return []
    
    def add_package(self, package_path: Path, package_name: str, 
                   version: str, dependencies: List[str]) -> bool:
        """
        Ajoute un package au cache.
        
        Args:
            package_path: Chemin vers le fichier du package
            package_name: Nom du package
            version: Version du package
            dependencies: Liste des dépendances du package
            
        Returns:
            bool: True si l'ajout a réussi, False sinon
        """
        try:
            if not package_path.exists():
                logger.error(f"Fichier package inexistant: {package_path}")
                return False
            
            # Calculer le hash du fichier pour vérification d'intégrité
            file_hash = self._calculate_file_hash(package_path)
            
            # Créer le répertoire pour ce package s'il n'existe pas
            package_dir = self.packages_dir / package_name
            package_dir.mkdir(exist_ok=True)
            
            # Destination dans le cache - conserver l'extension originale complète
            if package_path.suffix == '.gz' and package_path.stem.endswith('.tar'):
                # Cas spécial pour .tar.gz
                original_ext = '.tar.gz'
            else:
                # Pour les autres cas (.whl, .zip)
                original_ext = ''.join(package_path.suffixes)
            dest_path = package_dir / f"{package_name}-{version}{original_ext}"
            
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
                "usage_count": 1,
                "original_filename": package_path.name
            }
            
            # Mettre à jour l'index
            if package_name not in self.index:
                self.index[package_name] = {"versions": {}}
            
            self.index[package_name]["versions"][version] = package_info
            
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
            Path ou None: Chemin vers le fichier ou None si non trouvé
        """
        if package_name not in self.index:
            return None
        
        versions = self.index[package_name].get("versions", {})
        if not versions:
            return None

        if version is None:
            # Trouver la dernière version avec tri sémantique sécurisé
            try:
                # Trier les versions correctement
                sorted_versions = sorted(
                    versions.keys(), 
                    key=lambda v: tuple(int(x) if x.isdigit() else 0 for x in v.split('.')),
                    reverse=True
                )
                version = sorted_versions[0]
            except (ValueError, IndexError):
                # Fallback : prendre la première version disponible
                version = list(versions.keys())[0]

            if version not in self.index[package_name]["versions"]:
                return None
        
        package_info = self.index[package_name]["versions"][version]
        package_path = self.cache_dir / package_info["path"]
        
        if not package_path.exists():
            logger.warning(f"Fichier manquant dans le cache: {package_path}")
            return None
        
        # Vérifier l'intégrité du fichier
        try:
            file_hash = self._calculate_file_hash(package_path)
            if file_hash != package_info.get("hash", file_hash):  # Si pas de hash stocké, accepter
                logger.warning(f"Intégrité du package compromise: {package_name}-{version}")
                return None
        except Exception as e:
            logger.warning(f"Impossible de vérifier l'intégrité de {package_name}-{version}: {e}")
        
        # Mettre à jour les statistiques d'utilisation
        try:
            package_info["last_used"] = datetime.now().isoformat()
            package_info["usage_count"] = package_info.get("usage_count", 0) + 1
            self._save_index()
        except Exception as e:
            logger.debug(f"Erreur mise à jour stats d'usage: {e}")
        
        return Path(package_path)
    
    def has_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """
        Vérifie si un package est disponible dans le cache.
        
        Args:
            package_name: Nom du package
            version: Version spécifique à vérifier
            
        Returns:
            bool: True si le package est disponible
        """
        if package_name not in self.index:
            return False
        
        if version is None:
            return len(self.index[package_name]["versions"]) > 0
        
        return version in self.index[package_name]["versions"]
    
    def get_available_packages(self) -> Dict[str, List[str]]:
        """
        Retourne la liste des packages disponibles dans le cache.

        Returns:
            Dict: Dictionnaire des packages avec leurs versions disponibles
        """
        available = {}
        for package_name, package_data in self.index.items():
            # Ignorer les métadonnées et autres clés spéciales
            if package_name.startswith('_'):
                continue
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
                package_info.get("size", 0)
                for package_data in self.index.values()
                for package_info in package_data["versions"].values()
            )
            
            max_size = max_size_mb * 1024 * 1024
            
            if current_size <= max_size:
                return 0, 0
            
            now = datetime.now()
            candidates = []
            
            for package_name, package_data in self.index.items():
                versions = package_data["versions"]
                
                if len(versions) <= keep_min_versions:
                    continue
                
                for version, info in versions.items():
                    try:
                        last_used = datetime.fromisoformat(info.get("last_used", info.get("added_at", "")))
                        age_days = (now - last_used).days
                        
                        if age_days > max_age_days:
                            usage_count = info.get("usage_count", 1)
                            candidates.append({
                                "package_name": package_name,
                                "version": version,
                                "size": info.get("size", 0),
                                "age_days": age_days,
                                "usage_count": usage_count,
                                "score": age_days / max(usage_count, 1)
                            })
                    except Exception as e:
                        logger.debug(f"Erreur calcul âge package {package_name}-{version}: {e}")
            
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            for candidate in candidates:
                if current_size <= max_size:
                    break
                
                package_name = candidate["package_name"]
                version = candidate["version"]
                
                remaining_versions = len(self.index[package_name]["versions"])
                if remaining_versions <= keep_min_versions:
                    continue
                
                try:
                    package_info = self.index[package_name]["versions"][version]
                    package_path = self.cache_dir / package_info["path"]
                    
                    if package_path.exists():
                        package_path.unlink()
                    
                    freed_space += package_info.get("size", 0)
                    current_size -= package_info.get("size", 0)
                    
                    del self.index[package_name]["versions"][version]
                    
                    if not self.index[package_name]["versions"]:
                        del self.index[package_name]
                    
                    removed_count += 1
                    
                except Exception as e:
                    logger.error(f"Erreur suppression {package_name}-{version}: {e}")
            
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
        try:
            content_hash = hashlib.sha256(requirements_content.encode('utf-8')).hexdigest()
            requirements_path = self.requirements_dir / f"{content_hash}.txt"
            
            if not requirements_path.exists():
                with open(requirements_path, 'w', encoding='utf-8') as f:
                    f.write(requirements_content)
            
            return content_hash
        except Exception as e:
            logger.error(f"Erreur mise en cache requirements: {e}")
            return ""
    
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
        try:
            package_count = len(self.index)
            version_count = sum(len(pkg_data["versions"]) for pkg_data in self.index.values())
            
            total_size = sum(
                pkg_info.get("size", 0)
                for pkg_data in self.index.values()
                for pkg_info in pkg_data["versions"].values()
            )
            
            latest_package = {"name": None, "added_at": "1970-01-01T00:00:00"}
            for pkg_name, pkg_data in self.index.items():
                for version, info in pkg_data["versions"].items():
                    added_at = info.get("added_at", "1970-01-01T00:00:00")
                    if added_at > latest_package["added_at"]:
                        latest_package = {"name": f"{pkg_name}-{version}", "added_at": added_at}
            
            return {
                "package_count": package_count,
                "version_count": version_count,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "latest_package": latest_package["name"],
                "latest_added_at": latest_package["added_at"],
                "cache_dir": str(self.cache_dir),
                "disk_usage": self._get_disk_usage()
            }
        except Exception as e:
            logger.error(f"Erreur calcul statistiques cache: {e}")
            return {
                "package_count": 0,
                "version_count": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "latest_package": None,
                "latest_added_at": None,
                "cache_dir": str(self.cache_dir)
            }
    
    def remove_package(self, package_name: str, version: Optional[str] = None) -> Tuple[bool, str]:
        """
        Supprime un package ou une version spécifique du cache.
        
        Args:
            package_name: Nom du package à supprimer
            version: Version spécifique (si None, supprime toutes les versions)
            
        Returns:
            Tuple[bool, str]: (succès, message)
        """
        try:
            if package_name not in self.index:
                return False, f"Package '{package_name}' non trouvé dans le cache"
            
            removed_count = 0
            freed_space = 0
            
            if version:
                if version not in self.index[package_name]["versions"]:
                    return False, f"Version '{version}' du package '{package_name}' non trouvée"
                
                package_info = self.index[package_name]["versions"][version]
                package_path = self.cache_dir / package_info["path"]
                
                if package_path.exists():
                    try:
                        package_path.unlink()
                        freed_space += package_info.get("size", 0)
                    except Exception as e:
                        logger.error(f"Erreur suppression fichier {package_path}: {e}")
                        return False, f"Erreur lors de la suppression du fichier: {str(e)}"
                
                del self.index[package_name]["versions"][version]
                removed_count = 1
                
                if not self.index[package_name]["versions"]:
                    del self.index[package_name]
                    
            else:
                versions = list(self.index[package_name]["versions"].keys())
                
                for ver in versions:
                    package_info = self.index[package_name]["versions"][ver]
                    package_path = self.cache_dir / package_info["path"]
                    
                    if package_path.exists():
                        try:
                            package_path.unlink()
                            freed_space += package_info.get("size", 0)
                        except Exception as e:
                            logger.warning(f"Erreur suppression {package_path}: {e}")
                    
                    removed_count += 1
                
                del self.index[package_name]
            
            if self._save_index():
                freed_mb = freed_space / (1024 * 1024)
                if version:
                    return True, f"Version {version} du package {package_name} supprimée avec succès ({freed_mb:.1f} MB libérés)"
                else:
                    return True, f"Package {package_name} supprimé avec succès ({removed_count} version(s), {freed_mb:.1f} MB libérés)"
            else:
                return False, "Erreur lors de la sauvegarde de l'index"
                
        except Exception as e:
            logger.error(f"Erreur suppression package {package_name}: {e}")
            return False, f"Erreur lors de la suppression: {str(e)}"
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calcule le hash SHA-256 d'un fichier.
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            str: Hash SHA-256 du fichier
        """
        try:
            sha256_hash = hashlib.sha256()
            
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Erreur calcul hash {file_path}: {e}")
            return "unknown"
    
    def _get_disk_usage(self) -> Dict[str, int]:
        """
        Retourne l'utilisation du disque pour le répertoire du cache.
        
        Returns:
            Dict: Utilisation du disque (total, used, free)
        """
        try:
            usage = shutil.disk_usage(self.cache_dir)
            return {
                "total": usage.total,
                "used": usage.total - usage.free,
                "free": usage.free
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisation du disque: {e}")
            return {"total": 0, "used": 0, "free": 0}
    
    # NOUVELLES FONCTIONNALITÉS ÉTENDUES
    
    def verify_integrity(self) -> Dict[str, Any]:
        """
        Vérifie l'intégrité complète du cache.
        
        Returns:
            Dict: Rapport de vérification de l'intégrité
        """
        try:
            report = {
                "verified_at": datetime.now().isoformat(),
                "status": "healthy",
                "total_packages": 0,
                "verified_packages": 0,
                "corrupted_packages": [],
                "missing_files": [],
                "orphaned_metadata": [],
                "orphaned_files": [],
                "issues": [],
                "warnings": [],
                "recommendations": []
            }
            
            # Vérifier chaque package dans l'index
            for package_name, package_data in self.index.items():
                for version, package_info in package_data["versions"].items():
                    report["total_packages"] += 1
                    
                    package_path = self.cache_dir / package_info["path"]
                    
                    # Vérifier l'existence du fichier
                    if not package_path.exists():
                        report["missing_files"].append({
                            "package": f"{package_name}-{version}",
                            "expected_path": str(package_path)
                        })
                        continue
                    
                    # Vérifier l'intégrité du fichier
                    expected_hash = package_info.get("hash")
                    if expected_hash:
                        actual_hash = self._calculate_file_hash(package_path)
                        if actual_hash != expected_hash:
                            report["corrupted_packages"].append({
                                "package": f"{package_name}-{version}",
                                "path": str(package_path),
                                "expected_hash": expected_hash,
                                "actual_hash": actual_hash
                            })
                            continue
                    
                    report["verified_packages"] += 1
            
            # Vérifier les fichiers orphelins (fichiers présents mais pas dans l'index)
            if self.packages_dir.exists():
                for package_dir in self.packages_dir.iterdir():
                    if package_dir.is_dir():
                        package_name = package_dir.name
                        for file_path in package_dir.iterdir():
                            if file_path.is_file() and self._is_package_file(file_path):
                                # Vérifier si ce fichier est référencé dans l'index
                                file_referenced = False
                                if package_name in self.index:
                                    for version_info in self.index[package_name]["versions"].values():
                                        if self.cache_dir / version_info["path"] == file_path:
                                            file_referenced = True
                                            break
                                
                                if not file_referenced:
                                    report["orphaned_files"].append(str(file_path))
            
            # Déterminer le statut global
            if report["corrupted_packages"] or report["missing_files"]:
                report["status"] = "corrupted"
            elif report["orphaned_files"] or report["orphaned_metadata"]:
                report["status"] = "degraded"
            
            # Générer des recommandations
            if report["corrupted_packages"]:
                report["recommendations"].append("Supprimer et re-télécharger les packages corrompus")
            if report["missing_files"]:
                report["recommendations"].append("Nettoyer les métadonnées des fichiers manquants")
            if report["orphaned_files"]:
                report["recommendations"].append("Supprimer les fichiers orphelins ou les réintégrer")
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'intégrité: {e}")
            return {
                "verified_at": datetime.now().isoformat(),
                "status": "error",
                "error": f"Erreur lors de la vérification: {str(e)}"
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Effectue un contrôle de santé du cache.
        
        Returns:
            Dict: Rapport de santé du cache
        """
        try:
            health_report = {
                "checked_at": datetime.now().isoformat(),
                "overall_health": "healthy",
                "checks": {},
                "issues": [],
                "warnings": [],
                "recommendations": [],
                "metrics": {}
            }
            
            # Vérifier l'existence des répertoires
            dirs_to_check = {
                "cache_dir": self.cache_dir,
                "metadata_dir": self.metadata_dir,
                "packages_dir": self.packages_dir,
                "requirements_dir": self.requirements_dir
            }
            
            for dir_name, dir_path in dirs_to_check.items():
                health_report["checks"][f"{dir_name}_exists"] = dir_path.exists()
                if not dir_path.exists():
                    health_report["issues"].append(f"Répertoire manquant: {dir_path}")
            
            # Vérifier les permissions
            for dir_name, dir_path in dirs_to_check.items():
                if dir_path.exists():
                    readable = os.access(dir_path, os.R_OK)
                    writable = os.access(dir_path, os.W_OK)
                    health_report["checks"][f"{dir_name}_readable"] = readable
                    health_report["checks"][f"{dir_name}_writable"] = writable
                    
                    if not readable:
                        health_report["issues"].append(f"Pas de permission de lecture: {dir_path}")
                    if not writable:
                        health_report["issues"].append(f"Pas de permission d'écriture: {dir_path}")
            
            # Vérifier l'espace disque
            disk_usage = self._get_disk_usage()
            free_space_mb = disk_usage["free"] / (1024 * 1024)
            health_report["metrics"]["free_space_mb"] = free_space_mb
            
            if free_space_mb < 100:  # Moins de 100 MB
                health_report["issues"].append(f"Espace disque critique: {free_space_mb:.1f} MB disponible")
            elif free_space_mb < 500:  # Moins de 500 MB
                health_report["warnings"].append(f"Espace disque faible: {free_space_mb:.1f} MB disponible")
            
            # Vérifier la cohérence de l'index
            index_path = self.metadata_dir / "index.json"
            health_report["checks"]["index_exists"] = index_path.exists()
            
            if index_path.exists():
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    health_report["checks"]["index_valid"] = True
                except json.JSONDecodeError:
                    health_report["checks"]["index_valid"] = False
                    health_report["issues"].append("Index corrompu (JSON invalide)")
            
            # Métriques du cache
            stats = self.get_cache_stats()
            health_report["metrics"].update({
                "package_count": stats["package_count"],
                "version_count": stats["version_count"],
                "total_size_mb": stats["total_size_mb"]
            })
            
            # Déterminer la santé globale
            if health_report["issues"]:
                health_report["overall_health"] = "unhealthy"
            elif health_report["warnings"]:
                health_report["overall_health"] = "degraded"
            
            # Recommandations
            if health_report["issues"]:
                health_report["recommendations"].append("Résoudre les problèmes critiques identifiés")
            if free_space_mb < 500:
                health_report["recommendations"].append("Nettoyer le cache pour libérer de l'espace")
            
            return health_report
            
        except Exception as e:
            logger.error(f"Erreur lors du contrôle de santé: {e}")
            return {
                "checked_at": datetime.now().isoformat(),
                "overall_health": "error",
                "error": f"Erreur lors du contrôle: {str(e)}"
            }
    
    def optimize_cache(self) -> Dict[str, Any]:
        """
        Optimise le cache en réorganisant les fichiers et nettoyant les données.
        
        Returns:
            Dict: Rapport d'optimisation
        """
        try:
            optimization_report = {
                "started_at": datetime.now().isoformat(),
                "actions_performed": [],
                "space_saved": 0,
                "files_processed": 0,
                "errors": []
            }
            
            # 1. Nettoyer les fichiers temporaires
            temp_files_removed = 0
            if self.temp_dir.exists():
                for temp_file in self.temp_dir.iterdir():
                    try:
                        if temp_file.is_file():
                            temp_file.unlink()
                            temp_files_removed += 1
                    except Exception as e:
                        optimization_report["errors"].append(f"Erreur suppression {temp_file}: {e}")
            
            if temp_files_removed > 0:
                optimization_report["actions_performed"].append(f"Supprimé {temp_files_removed} fichier(s) temporaire(s)")
            
            # 2. Supprimer les fichiers orphelins
            integrity_report = self.verify_integrity()
            orphaned_files = integrity_report.get("orphaned_files", [])
            
            for orphaned_file in orphaned_files:
                try:
                    file_path = Path(orphaned_file)
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        optimization_report["space_saved"] += file_size
                        optimization_report["files_processed"] += 1
                except Exception as e:
                    optimization_report["errors"].append(f"Erreur suppression fichier orphelin {orphaned_file}: {e}")
            
            if orphaned_files:
                optimization_report["actions_performed"].append(f"Supprimé {len(orphaned_files)} fichier(s) orphelin(s)")
            
            # 3. Nettoyer les métadonnées des packages manquants
            missing_files = integrity_report.get("missing_files", [])
            removed_metadata = 0
            
            for missing in missing_files:
                try:
                    package_name, version = missing["package"].split("-", 1)
                    if package_name in self.index and version in self.index[package_name]["versions"]:
                        del self.index[package_name]["versions"][version]
                        if not self.index[package_name]["versions"]:
                            del self.index[package_name]
                        removed_metadata += 1
                except Exception as e:
                    optimization_report["errors"].append(f"Erreur nettoyage métadonnées {missing['package']}: {e}")
            
            if removed_metadata > 0:
                optimization_report["actions_performed"].append(f"Nettoyé {removed_metadata} métadonnée(s) obsolète(s)")
                self._save_index()
            
            # 4. Défragmenter l'index (réécrire proprement)
            if self._save_index():
                optimization_report["actions_performed"].append("Index défragmenté et optimisé")
            
            # 5. Statistiques finales
            optimization_report["completed_at"] = datetime.now().isoformat()
            optimization_report["space_saved_mb"] = optimization_report["space_saved"] / (1024 * 1024)
            
            return optimization_report
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation du cache: {e}")
            return {
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "error": f"Erreur lors de l'optimisation: {str(e)}",
                "actions_performed": [],
                "space_saved": 0
            }
    
    def export_cache(self, output_path: str, include_packages: bool = True) -> Dict[str, Any]:
        """
        Exporte le cache vers un fichier archive.
        
        Args:
            output_path: Chemin du fichier d'export
            include_packages: Si True, inclut les fichiers de packages
            
        Returns:
            Dict: Rapport d'export
        """
        try:
            export_report = {
                "started_at": datetime.now().isoformat(),
                "output_path": output_path,
                "included_packages": include_packages,
                "exported_items": 0,
                "total_size": 0,
                "errors": []
            }
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Exporter l'index
                index_data = {
                    "_export_metadata": {
                        "version": "1.0",
                        "exported_at": datetime.now().isoformat(),
                        "source_cache_dir": str(self.cache_dir),
                        "include_packages": include_packages
                    },
                    **self.index
                }
                
                zipf.writestr("index.json", json.dumps(index_data, indent=2, ensure_ascii=False))
                export_report["exported_items"] += 1
                
                # Exporter les fichiers de packages si demandé
                if include_packages:
                    for package_name, package_data in self.index.items():
                        for version, package_info in package_data["versions"].items():
                            try:
                                package_path = self.cache_dir / package_info["path"]
                                if package_path.exists():
                                    # Utiliser un nom de fichier relatif dans l'archive
                                    arcname = package_info["path"]
                                    zipf.write(package_path, arcname)
                                    export_report["exported_items"] += 1
                                    export_report["total_size"] += package_path.stat().st_size
                            except Exception as e:
                                export_report["errors"].append(f"Erreur export {package_name}-{version}: {e}")
                
                # Exporter les requirements cachés
                if self.requirements_dir.exists():
                    for req_file in self.requirements_dir.glob("*.txt"):
                        try:
                            arcname = f"requirements/{req_file.name}"
                            zipf.write(req_file, arcname)
                            export_report["exported_items"] += 1
                        except Exception as e:
                            export_report["errors"].append(f"Erreur export requirements {req_file.name}: {e}")
            
            export_report["completed_at"] = datetime.now().isoformat()
            export_report["total_size_mb"] = export_report["total_size"] / (1024 * 1024)
            export_report["success"] = True
            
            return export_report
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export du cache: {e}")
            return {
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "success": False,
                "error": f"Erreur lors de l'export: {str(e)}"
            }
    
    def import_cache(self, import_path: str, merge: bool = True) -> Dict[str, Any]:
        """
        Importe un cache depuis un fichier archive.
        
        Args:
            import_path: Chemin du fichier d'import
            merge: Si True, fusionne avec le cache existant
            
        Returns:
            Dict: Rapport d'import
        """
        try:
            import_report = {
                "started_at": datetime.now().isoformat(),
                "import_path": import_path,
                "merge_mode": merge,
                "imported_items": 0,
                "skipped_items": 0,
                "errors": []
            }
            
            import_file = Path(import_path)
            if not import_file.exists():
                raise FileNotFoundError(f"Fichier d'import non trouvé: {import_path}")
            
            # Créer une sauvegarde du cache actuel si fusion
            if merge and self.index:
                backup_path = self.cache_dir / f"backup_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(self.index, f, indent=2, ensure_ascii=False)
            
            with zipfile.ZipFile(import_file, 'r') as zipf:
                # Lire l'index
                try:
                    index_content = zipf.read("index.json").decode('utf-8')
                    imported_index = json.loads(index_content)
                    
                    # Supprimer les métadonnées d'export
                    if "_export_metadata" in imported_index:
                        del imported_index["_export_metadata"]
                    
                except Exception as e:
                    raise ValueError(f"Index invalide dans l'archive: {e}")
                
                # Traiter chaque package
                for package_name, package_data in imported_index.items():
                    if package_name.startswith("_"):  # Ignorer les métadonnées
                        continue
                        
                    for version, package_info in package_data["versions"].items():
                        try:
                            # Vérifier si le package existe déjà
                            if (not merge and 
                                package_name in self.index and 
                                version in self.index[package_name]["versions"]):
                                import_report["skipped_items"] += 1
                                continue
                            
                            # Extraire le fichier du package s'il existe dans l'archive
                            package_path_in_archive = package_info["path"]
                            if package_path_in_archive in zipf.namelist():
                                # Créer le répertoire de destination
                                dest_dir = self.packages_dir / package_name
                                dest_dir.mkdir(exist_ok=True)
                                
                                # Extraire le fichier
                                with zipf.open(package_path_in_archive) as source:
                                    dest_file = dest_dir / Path(package_path_in_archive).name
                                    with open(dest_file, 'wb') as target:
                                        shutil.copyfileobj(source, target)
                                
                                # Mettre à jour les métadonnées
                                package_info["path"] = str(dest_file.relative_to(self.cache_dir))
                                package_info["imported_at"] = datetime.now().isoformat()
                                
                                # Ajouter à l'index
                                if package_name not in self.index:
                                    self.index[package_name] = {"versions": {}}
                                
                                self.index[package_name]["versions"][version] = package_info
                                import_report["imported_items"] += 1
                            
                        except Exception as e:
                            import_report["errors"].append(f"Erreur import {package_name}-{version}: {e}")
                
                # Importer les requirements
                for item in zipf.namelist():
                    if item.startswith("requirements/") and item.endswith(".txt"):
                        try:
                            with zipf.open(item) as source:
                                dest_file = self.requirements_dir / Path(item).name
                                with open(dest_file, 'wb') as target:
                                    shutil.copyfileobj(source, target)
                        except Exception as e:
                            import_report["errors"].append(f"Erreur import requirements {item}: {e}")
            
            # Sauvegarder l'index mis à jour
            if self._save_index():
                import_report["completed_at"] = datetime.now().isoformat()
                import_report["success"] = True
            else:
                raise Exception("Échec de la sauvegarde de l'index après import")
            
            return import_report
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import du cache: {e}")
            return {
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "success": False,
                "error": f"Erreur lors de l'import: {str(e)}"
            }
    
    def get_package_info(self, package_name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère des informations détaillées sur un package.
        
        Args:
            package_name: Nom du package
            version: Version spécifique (optionnel)
            
        Returns:
            Dict: Informations détaillées sur le package
        """
        if package_name not in self.index:
            return None
        
        package_data = self.index[package_name]
        
        if version:
            if version not in package_data["versions"]:
                return None
            return package_data["versions"][version]
        else:
            # Retourner les infos de toutes les versions
            return {
                "name": package_name,
                "versions_available": list(package_data["versions"].keys()),
                "versions_info": package_data["versions"],
                "total_versions": len(package_data["versions"])
            }
    
    def search_packages(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Recherche des packages dans le cache.
        
        Args:
            query: Terme de recherche
            case_sensitive: Si True, recherche sensible à la casse
            
        Returns:
            List: Liste des packages correspondants
        """
        results = []
        
        if not case_sensitive:
            query = query.lower()
        
        for package_name, package_data in self.index.items():
            search_name = package_name if case_sensitive else package_name.lower()
            
            if query in search_name:
                results.append({
                    "name": package_name,
                    "versions": list(package_data["versions"].keys()),
                    "total_versions": len(package_data["versions"]),
                    "latest_version": max(package_data["versions"].keys()) if package_data["versions"] else None,
                    "total_size": sum(v.get("size", 0) for v in package_data["versions"].values())
                })
        
        # Trier par pertinence (correspondance exacte en premier)
        results.sort(key=lambda x: (
            0 if x["name"].lower() == query else 1,
            x["name"].lower()
        ))
        
        return results
    
    def rebuild_index(self) -> Dict[str, Any]:
        """
        Reconstruit l'index en scannant les fichiers présents dans le cache.
        
        Returns:
            Dict: Rapport de reconstruction
        """
        try:
            rebuild_report = {
                "started_at": datetime.now().isoformat(),
                "old_index_packages": len(self.index),
                "scanned_files": 0,
                "added_packages": 0,
                "errors": []
            }
            
            # Sauvegarder l'ancien index
            old_index = self.index.copy()
            
            # Réinitialiser l'index
            self.index = {}
            
            # Scanner le répertoire des packages
            if self.packages_dir.exists():
                for package_dir in self.packages_dir.iterdir():
                    if package_dir.is_dir():
                        package_name = package_dir.name
                        
                        for file_path in package_dir.iterdir():
                            if file_path.is_file() and self._is_package_file(file_path):
                                try:
                                    rebuild_report["scanned_files"] += 1
                                    
                                    # Extraire les informations du package
                                    package_info = self._extract_package_info_safe(file_path.name)
                                    
                                    if package_info:
                                        # Calculer le hash
                                        file_hash = self._calculate_file_hash(file_path)
                                        
                                        # Récupérer les anciennes métadonnées si disponibles
                                        old_info = None
                                        if (package_name in old_index and 
                                            package_info["version"] in old_index[package_name].get("versions", {})):
                                            old_info = old_index[package_name]["versions"][package_info["version"]]
                                        
                                        # Créer les nouvelles métadonnées
                                        new_package_info = {
                                            "name": package_name,
                                            "version": package_info["version"],
                                            "path": str(file_path.relative_to(self.cache_dir)),
                                            "hash": file_hash,
                                            "size": file_path.stat().st_size,
                                            "added_at": old_info.get("added_at", datetime.now().isoformat()),
                                            "last_used": old_info.get("last_used", datetime.now().isoformat()),
                                            "usage_count": old_info.get("usage_count", 0),
                                            "dependencies": old_info.get("dependencies", []),
                                            "original_filename": file_path.name,
                                            "rebuilt": True
                                        }
                                        
                                        # Ajouter à l'index
                                        if package_name not in self.index:
                                            self.index[package_name] = {"versions": {}}
                                        
                                        self.index[package_name]["versions"][package_info["version"]] = new_package_info
                                        rebuild_report["added_packages"] += 1
                                    
                                except Exception as e:
                                    rebuild_report["errors"].append(f"Erreur traitement {file_path}: {e}")
            
            # Sauvegarder le nouvel index
            if self._save_index():
                rebuild_report["completed_at"] = datetime.now().isoformat()
                rebuild_report["new_index_packages"] = len(self.index)
                rebuild_report["success"] = True
            else:
                raise Exception("Échec de la sauvegarde du nouvel index")
            
            return rebuild_report
            
        except Exception as e:
            logger.error(f"Erreur lors de la reconstruction de l'index: {e}")
            # Restaurer l'ancien index en cas d'erreur
            if 'old_index' in locals():
                self.index = old_index
            
            return {
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "success": False,
                "error": f"Erreur lors de la reconstruction: {str(e)}"
            }