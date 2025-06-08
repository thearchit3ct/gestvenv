"""
Utilitaires avancés pour la gestion des chemins et fichiers.
Support multi-plateforme avec sécurité renforcée.
"""

import os
import shutil
import tempfile
from pathlib import Path, PurePath
from typing import Optional, Union, List, Generator, Tuple
import logging
import hashlib
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PathUtils:
    """Utilitaires avancés pour la gestion des chemins."""
    
    @staticmethod
    def normalize_path(path: Union[str, Path]) -> Path:
        """
        Normalise un chemin de manière sécurisée.
        
        Args:
            path: Chemin à normaliser
            
        Returns:
            Path normalisé et résolu
            
        Example:
            >>> PathUtils.normalize_path("~/project/../config.toml")
            Path('/home/user/config.toml')
        """
        try:
            path_obj = Path(path).expanduser().resolve()
            return path_obj
        except (OSError, RuntimeError) as e:
            logger.error(f"Erreur normalisation chemin {path}: {e}")
            raise ValueError(f"Chemin invalide: {path}")
    
    @staticmethod
    def safe_path_join(base: Union[str, Path], *parts: str) -> Path:
        """
        Joint des chemins de manière sécurisée (évite path traversal).
        
        Args:
            base: Chemin de base
            *parts: Parties à joindre
            
        Returns:
            Chemin joint sécurisé
            
        Raises:
            ValueError: Si tentative de sortir du répertoire de base
        """
        base_path = PathUtils.normalize_path(base)
        result_path = base_path
        
        for part in parts:
            # Nettoyer la partie du chemin
            clean_part = str(part).replace('..', '').replace('~', '')
            result_path = result_path / clean_part
        
        # Vérifier que le résultat est bien dans le répertoire de base
        try:
            result_path.resolve().relative_to(base_path.resolve())
        except ValueError:
            raise ValueError(f"Tentative d'accès hors du répertoire de base: {result_path}")
            
        return result_path
    
    @staticmethod
    def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> Path:
        """
        Assure qu'un répertoire existe avec les permissions appropriées.
        
        Args:
            path: Chemin du répertoire
            mode: Permissions du répertoire
            
        Returns:
            Chemin du répertoire créé
        """
        dir_path = PathUtils.normalize_path(path)
        dir_path.mkdir(parents=True, exist_ok=True, mode=mode)
        return dir_path
    
    @staticmethod
    def safe_copy(src: Union[str, Path], dst: Union[str, Path], 
                  preserve_metadata: bool = True) -> bool:
        """
        Copie un fichier de manière sécurisée avec gestion d'erreurs.
        
        Args:
            src: Fichier source
            dst: Fichier destination
            preserve_metadata: Préserver les métadonnées
            
        Returns:
            True si succès, False sinon
        """
        try:
            src_path = PathUtils.normalize_path(src)
            dst_path = PathUtils.normalize_path(dst)
            
            if not src_path.exists():
                logger.error(f"Fichier source inexistant: {src_path}")
                return False
            
            # Créer le répertoire de destination si nécessaire
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            if preserve_metadata:
                shutil.copy2(src_path, dst_path)
            else:
                shutil.copy(src_path, dst_path)
                
            logger.debug(f"Fichier copié: {src_path} → {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur copie {src} → {dst}: {e}")
            return False
    
    @staticmethod
    def safe_delete(path: Union[str, Path], recursive: bool = False) -> bool:
        """
        Supprime un fichier ou répertoire de manière sécurisée.
        
        Args:
            path: Chemin à supprimer
            recursive: Suppression récursive pour les répertoires
            
        Returns:
            True si succès, False sinon
        """
        try:
            target_path = PathUtils.normalize_path(path)
            
            if not target_path.exists():
                logger.warning(f"Chemin inexistant: {target_path}")
                return True
            
            if target_path.is_file():
                target_path.unlink()
                logger.debug(f"Fichier supprimé: {target_path}")
            elif target_path.is_dir():
                if recursive:
                    shutil.rmtree(target_path)
                    logger.debug(f"Répertoire supprimé: {target_path}")
                else:
                    target_path.rmdir()  # Seulement si vide
                    logger.debug(f"Répertoire vide supprimé: {target_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression {path}: {e}")
            return False
    
    @staticmethod
    def get_file_hash(path: Union[str, Path], algorithm: str = "sha256") -> Optional[str]:
        """
        Calcule le hash d'un fichier.
        
        Args:
            path: Chemin du fichier
            algorithm: Algorithme de hash (md5, sha1, sha256)
            
        Returns:
            Hash du fichier ou None si erreur
        """
        try:
            file_path = PathUtils.normalize_path(path)
            
            if not file_path.is_file():
                return None
            
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Erreur calcul hash {path}: {e}")
            return None
    
    @staticmethod
    @contextmanager
    def temporary_directory(prefix: str = "gestvenv_", cleanup: bool = True):
        """
        Gestionnaire de contexte pour répertoire temporaire.
        
        Args:
            prefix: Préfixe du répertoire temporaire
            cleanup: Nettoyer à la sortie
            
        Yields:
            Path du répertoire temporaire
        """
        temp_dir = None
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
            logger.debug(f"Répertoire temporaire créé: {temp_dir}")
            yield temp_dir
        finally:
            if cleanup and temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.debug(f"Répertoire temporaire supprimé: {temp_dir}")
    
    @staticmethod
    def find_files(directory: Union[str, Path], pattern: str = "*", 
                   recursive: bool = True) -> Generator[Path, None, None]:
        """
        Trouve des fichiers selon un motif.
        
        Args:
            directory: Répertoire de recherche
            pattern: Motif de recherche (glob)
            recursive: Recherche récursive
            
        Yields:
            Chemins des fichiers trouvés
        """
        try:
            search_path = PathUtils.normalize_path(directory)
            
            if not search_path.is_dir():
                logger.warning(f"Répertoire inexistant: {search_path}")
                return
            
            if recursive:
                for file_path in search_path.rglob(pattern):
                    if file_path.is_file():
                        yield file_path
            else:
                for file_path in search_path.glob(pattern):
                    if file_path.is_file():
                        yield file_path
                        
        except Exception as e:
            logger.error(f"Erreur recherche fichiers dans {directory}: {e}")

# Fonctions utilitaires pour compatibilité
def normalize_path(path: Union[str, Path]) -> Path:
    """Fonction utilitaire pour normaliser un chemin."""
    return PathUtils.normalize_path(path)

def safe_path_join(base: Union[str, Path], *parts: str) -> Path:
    """Fonction utilitaire pour joindre des chemins sécurisément."""
    return PathUtils.safe_path_join(base, *parts)
