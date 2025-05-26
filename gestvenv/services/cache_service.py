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
        MÉTHODE CORRIGÉE pour gérer l'encodage et les erreurs.
        
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
                
                # CORRECTION PRINCIPALE : Gestion encodage UTF-8
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    shell=False,
                    check=False,
                    encoding='utf-8',
                    errors='replace',  # Remplace caractères non-décodables
                    timeout=300  # Timeout 5 minutes
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
                                # Extraction sécurisée des informations
                                package_info = self._extract_package_info_safe(file_name)
                                
                                if package_info:
                                    # Obtenir dépendances de manière sécurisée
                                    dependencies = self._get_dependencies_safe(package_info['name'])
                                    
                                    # Ajouter au cache
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
        CORRECTION pour éviter les erreurs d'index.
        
        Args:
            filename: Nom du fichier package
            
        Returns:
            Dict avec name, version, filename ou None si échec
        """
        try:
            # Supprimer l'extension
            name_without_ext = filename
            for ext in ['.whl', '.tar.gz', '.zip']:
                if filename.endswith(ext):
                    name_without_ext = filename[:-len(ext)]
                    break
            
            # Cas spécial pour .tar.gz
            if filename.endswith('.tar.gz'):
                name_without_ext = filename[:-7]
            
            # Parser le nom avec méthode robuste
            parts = name_without_ext.split('-')
            
            if len(parts) >= 2:
                # Méthode robuste pour séparer nom et version
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
            base_name = parts[0] if parts else filename.split('.')[0]
            return {
                'name': base_name,
                'version': 'unknown',
                'filename': filename
            }
            
        except Exception as e:
            logger.warning(f"Erreur extraction info {filename}: {e}")
            # Fallback ultra-sécurisé
            base_name = filename.split('.')[0] if '.' in filename else filename
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
            
        # Pattern pour détecter une version (ex: 1.2.3, 2.0.1a1, 1.0.0rc1)
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
                # Parser la sortie pour extraire les dépendances
                for line in result.stdout.splitlines():
                    if line.startswith('Requires:'):
                        deps_str = line.split(':', 1)[1].strip()
                        if deps_str and deps_str.lower() != 'none':
                            return [dep.strip() for dep in deps_str.split(',') if dep.strip()]
                        break
            
        except Exception as e:
            logger.debug(f"Impossible de récupérer les dépendances de {package_name}: {e}")
        
        return []  # Retourne liste vide en cas d'erreur
    
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
            # Vérifier que le fichier existe
            if not package_path.exists():
                logger.error(f"Fichier package inexistant: {package_path}")
                return False
            
            # Calculer le hash du fichier pour vérification d'intégrité
            file_hash = self._calculate_file_hash(package_path)
            
            # Créer le répertoire pour ce package s'il n'existe pas
            package_dir = self.packages_dir / package_name
            package_dir.mkdir(exist_ok=True)
            
            # Destination dans le cache - conserver l'extension originale
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
            
            # Trouver la dernière version avec tri sémantique sécurisé
            try:
                version = sorted(
                    versions.keys(), 
                    key=lambda v: [int(x) for x in v.split('.') if x.isdigit()],
                    reverse=True
                )[0]
            except (ValueError, IndexError):
                # Fallback: prendre la première version disponible
                version = list(versions.keys())[0]
        
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
        try:
            file_hash = self._calculate_file_hash(package_path)
            if file_hash != package_info["hash"]:
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
                package_info.get("size", 0)
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
                    try:
                        # Calculer l'âge du package en jours
                        last_used = datetime.fromisoformat(info.get("last_used", info.get("added_at", "")))
                        age_days = (now - last_used).days
                        
                        # Ajouter à la liste des candidats si obsolète
                        if age_days > max_age_days:
                            usage_count = info.get("usage_count", 1)
                            candidates.append({
                                "package_name": package_name,
                                "version": version,
                                "size": info.get("size", 0),
                                "age_days": age_days,
                                "usage_count": usage_count,
                                "score": age_days / max(usage_count, 1)  # Score pour priorisation
                            })
                    except Exception as e:
                        logger.debug(f"Erreur calcul âge package {package_name}-{version}: {e}")
            
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
                
                try:
                    # Récupérer le chemin du package
                    package_info = self.index[package_name]["versions"][version]
                    package_path = self.cache_dir / package_info["path"]
                    
                    # Supprimer le fichier
                    if package_path.exists():
                        package_path.unlink()
                    
                    # Mettre à jour le compteur d'espace libéré
                    freed_space += package_info.get("size", 0)
                    current_size -= package_info.get("size", 0)
                    
                    # Supprimer les métadonnées
                    del self.index[package_name]["versions"][version]
                    
                    # Si c'était la dernière version, supprimer complètement le package
                    if not self.index[package_name]["versions"]:
                        del self.index[package_name]
                    
                    removed_count += 1
                    
                except Exception as e:
                    logger.error(f"Erreur suppression {package_name}-{version}: {e}")
            
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
        try:
            # Générer un hash du contenu comme identifiant
            content_hash = hashlib.sha256(requirements_content.encode('utf-8')).hexdigest()
            
            # Chemin du fichier dans le cache
            requirements_path = self.requirements_dir / f"{content_hash}.txt"
            
            # Sauvegarder le contenu si le fichier n'existe pas déjà
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
            
            # Calculer la taille totale
            total_size = sum(
                pkg_info.get("size", 0)
                for pkg_data in self.index.values()
                for pkg_info in pkg_data["versions"].values()
            )
            
            # Trouver le package le plus récent
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
                "latest_package": latest_package["name"],
                "latest_added_at": latest_package["added_at"],
                "cache_dir": str(self.cache_dir)
            }
        except Exception as e:
            logger.error(f"Erreur calcul statistiques cache: {e}")
            return {
                "package_count": 0,
                "version_count": 0,
                "total_size_bytes": 0,
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
                # Supprimer une version spécifique
                if version not in self.index[package_name]["versions"]:
                    return False, f"Version '{version}' du package '{package_name}' non trouvée"
                
                # Récupérer les informations du package
                package_info = self.index[package_name]["versions"][version]
                package_path = self.cache_dir / package_info["path"]
                
                # Supprimer le fichier physique
                if package_path.exists():
                    try:
                        package_path.unlink()
                        freed_space += package_info.get("size", 0)
                    except Exception as e:
                        logger.error(f"Erreur suppression fichier {package_path}: {e}")
                        return False, f"Erreur lors de la suppression du fichier: {str(e)}"
                
                # Supprimer de l'index
                del self.index[package_name]["versions"][version]
                removed_count = 1
                
                # Si c'était la dernière version, supprimer complètement le package
                if not self.index[package_name]["versions"]:
                    del self.index[package_name]
                    
            else:
                # Supprimer toutes les versions du package
                versions = list(self.index[package_name]["versions"].keys())
                
                for ver in versions:
                    package_info = self.index[package_name]["versions"][ver]
                    package_path = self.cache_dir / package_info["path"]
                    
                    # Supprimer le fichier physique
                    if package_path.exists():
                        try:
                            package_path.unlink()
                            freed_space += package_info.get("size", 0)
                        except Exception as e:
                            logger.warning(f"Erreur suppression {package_path}: {e}")
                    
                    removed_count += 1
                
                # Supprimer complètement le package de l'index
                del self.index[package_name]
            
            # Sauvegarder l'index modifié
            if self._save_index():
                freed_mb = freed_space / (1024 * 1024)
                if version:
                    return True, f"Version {version} du package {package_name} supprimée ({freed_mb:.1f} MB libérés)"
                else:
                    return True, f"Package {package_name} supprimé ({removed_count} version(s), {freed_mb:.1f} MB libérés)"
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