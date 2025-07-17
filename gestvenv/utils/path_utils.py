"""
Utilitaires de gestion des chemins pour GestVenv v1.1
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import logging
logger = logging.getLogger(__name__)


class PathUtils:
    """Utilitaires de gestion des chemins et fichiers"""
    
    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """Assure qu'un répertoire existe"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"Impossible de créer {path}: {e}")
            return False
    
    @staticmethod
    def safe_remove_directory(path: Path) -> bool:
        """Supprime un répertoire en sécurité"""
        if not path.exists():
            return True
        
        if not path.is_dir():
            logger.error(f"{path} n'est pas un répertoire")
            return False
        
        try:
            # Vérification sécurité
            if not PathUtils._is_safe_to_remove(path):
                logger.error(f"Suppression refusée pour raisons de sécurité: {path}")
                return False
            
            shutil.rmtree(path)
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"Erreur suppression {path}: {e}")
            return False
    
    @staticmethod
    def get_environment_path(name: str, base_path: Path) -> Path:
        """Chemin d'environnement sécurisé"""
        # Nettoyage nom
        safe_name = PathUtils._sanitize_filename(name)
        return base_path / safe_name
    
    @staticmethod
    def find_pyproject_files(directory: Path) -> List[Path]:
        """Trouve tous les fichiers pyproject.toml"""
        pyproject_files = []
        
        if not directory.exists() or not directory.is_dir():
            return pyproject_files
        
        try:
            # Recherche récursive limitée (3 niveaux max)
            for root in [directory] + list(directory.iterdir())[:10]:
                if root.is_dir():
                    pyproject_path = root / "pyproject.toml"
                    if pyproject_path.exists():
                        pyproject_files.append(pyproject_path)
        except (OSError, PermissionError):
            pass
        
        return pyproject_files
    
    @staticmethod
    def backup_file(source: Path, backup_dir: Path) -> Optional[Path]:
        """Sauvegarde un fichier avec timestamp"""
        if not source.exists():
            return None
        
        try:
            PathUtils.ensure_directory(backup_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source.name}.{timestamp}.backup"
            backup_path = backup_dir / backup_name
            
            shutil.copy2(source, backup_path)
            return backup_path
        except (OSError, PermissionError) as e:
            logger.error(f"Erreur sauvegarde {source}: {e}")
            return None
    
    @staticmethod
    def find_project_root(start_path: Path) -> Optional[Path]:
        """Trouve la racine d'un projet Python"""
        current = start_path.resolve()
        
        project_markers = [
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            ".git",
            ".gitignore"
        ]
        
        # Remonte jusqu'à 5 niveaux
        for _ in range(5):
            for marker in project_markers:
                if (current / marker).exists():
                    return current
            
            parent = current.parent
            if parent == current:  # Racine système
                break
            current = parent
        
        return None
    
    @staticmethod
    def resolve_relative_path(base: Path, relative: str) -> Path:
        """Résout un chemin relatif de manière sécurisée"""
        try:
            resolved = (base / relative).resolve()
            
            # Vérification que le chemin reste dans base
            if not str(resolved).startswith(str(base.resolve())):
                raise ValueError("Path traversal détecté")
            
            return resolved
        except (OSError, ValueError) as e:
            logger.error(f"Erreur résolution chemin: {e}")
            raise
    
    @staticmethod
    def copy_directory_tree(source: Path, target: Path) -> bool:
        """Copie un arbre de répertoires"""
        if not source.exists() or not source.is_dir():
            return False
        
        try:
            # Vérifications sécurité
            if not PathUtils._is_safe_copy_operation(source, target):
                return False
            
            # Suppression cible si existe
            if target.exists():
                PathUtils.safe_remove_directory(target)
            
            shutil.copytree(source, target)
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"Erreur copie {source} → {target}: {e}")
            return False
    
    @staticmethod
    def get_size_mb(path: Path) -> float:
        """Taille d'un fichier/répertoire en MB"""
        if not path.exists():
            return 0.0
        
        try:
            if path.is_file():
                return path.stat().st_size / (1024 * 1024)
            elif path.is_dir():
                total_size = 0
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                return total_size / (1024 * 1024)
        except (OSError, PermissionError):
            pass
        
        return 0.0
    
    @staticmethod
    def is_empty_directory(path: Path) -> bool:
        """Vérifie si un répertoire est vide"""
        if not path.exists() or not path.is_dir():
            return False
        
        try:
            return not any(path.iterdir())
        except (OSError, PermissionError):
            return False
    
    @staticmethod
    def clean_empty_directories(root_path: Path) -> int:
        """Nettoie les répertoires vides récursivement"""
        if not root_path.exists() or not root_path.is_dir():
            return 0
        
        cleaned_count = 0
        
        try:
            # Parcours en profondeur d'abord
            for path in sorted(root_path.rglob('*'), key=lambda x: -len(x.parts)):
                if path.is_dir() and PathUtils.is_empty_directory(path):
                    try:
                        path.rmdir()
                        cleaned_count += 1
                    except OSError:
                        pass
        except (OSError, PermissionError):
            pass
        
        return cleaned_count
    
    @staticmethod
    def find_files_by_pattern(directory: Path, pattern: str, max_depth: int = 3) -> List[Path]:
        """Trouve fichiers par pattern avec limitation profondeur"""
        files = []
        
        if not directory.exists() or not directory.is_dir():
            return files
        
        try:
            current_depth = 0
            to_process = [(directory, 0)]
            
            while to_process and current_depth <= max_depth:
                current_dir, depth = to_process.pop(0)
                
                if depth > max_depth:
                    continue
                
                for item in current_dir.iterdir():
                    if item.is_file() and item.match(pattern):
                        files.append(item)
                    elif item.is_dir() and depth < max_depth:
                        to_process.append((item, depth + 1))
                        
                current_depth = max(current_depth, depth)
                
        except (OSError, PermissionError):
            pass
        
        return files
    
    # Méthodes privées
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Assainit un nom de fichier"""
        # Caractères interdits
        forbidden_chars = '<>:"/\\|?*'
        sanitized = ''.join('_' if c in forbidden_chars else c for c in filename)
        
        # Longueur maximum
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        
        # Pas de points à la fin
        sanitized = sanitized.rstrip('.')
        
        return sanitized or "default"
    
    @staticmethod
    def _is_safe_to_remove(path: Path) -> bool:
        """Vérifie si un chemin peut être supprimé en sécurité"""
        path_str = str(path.resolve())
        
        # Répertoires système protégés
        protected_paths = [
            '/etc', '/bin', '/usr', '/var', '/root', '/home',
            'C:\\Windows', 'C:\\Program Files', 'C:\\Users'
        ]
        
        for protected in protected_paths:
            if path_str.startswith(protected):
                return False
        
        # Vérification ownership (Unix)
        if hasattr(os, 'getuid'):
            try:
                stat = path.stat()
                if stat.st_uid != os.getuid():
                    return False
            except OSError:
                return False
        
        return True
    
    @staticmethod
    def _is_safe_copy_operation(source: Path, target: Path) -> bool:
        """Vérifie si une opération de copie est sécurisée"""
        try:
            source_resolved = source.resolve()
            target_resolved = target.resolve()
            
            # Éviter copie récursive
            if str(target_resolved).startswith(str(source_resolved)):
                return False
            
            # Vérifier permissions source
            if not os.access(source, os.R_OK):
                return False
            
            # Vérifier permissions cible
            target_parent = target_resolved.parent
            if not os.access(target_parent, os.W_OK):
                return False
            
            return True
        except (OSError, ValueError):
            return False