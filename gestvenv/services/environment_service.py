"""
EnvironmentService - Service de gestion des environnements virtuels.

Ce service est responsable de toutes les opérations liées aux environnements virtuels Python :
- Création et suppression d'environnements
- Validation des noms et chemins
- Vérification de la santé des environnements
- Scripts d'activation
- Sécurité et nettoyage

Il utilise le SystemService pour les opérations système et peut fonctionner avec
différents backends d'environnements virtuels.
"""

import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EnvironmentStatus(Enum):
    """Statut d'un environnement virtuel."""
    HEALTHY = "healthy"
    BROKEN = "broken"
    MISSING = "missing"
    CORRUPTED = "corrupted"
    PARTIAL = "partial"


@dataclass
class EnvironmentHealth:
    """Informations sur la santé d'un environnement."""
    status: EnvironmentStatus
    python_executable: Optional[Path] = None
    python_version: Optional[str] = None
    pip_available: bool = False
    site_packages: Optional[Path] = None
    issues: List[str] = None
    
    def __post_init__(self) -> None:
        if self.issues is None:
            self.issues = []
    
    @property
    def is_healthy(self) -> bool:
        """True si l'environnement est en bonne santé."""
        return self.status == EnvironmentStatus.HEALTHY
    
    @property
    def can_be_used(self) -> bool:
        """True si l'environnement peut être utilisé malgré des problèmes mineurs."""
        return self.status in (EnvironmentStatus.HEALTHY, EnvironmentStatus.PARTIAL)


@dataclass
class EnvironmentInfo:
    """Informations complètes sur un environnement."""
    name: str
    path: Path
    python_version: str
    health: EnvironmentHealth
    size_mb: Optional[float] = None
    created_at: Optional[str] = None
    last_used: Optional[str] = None
    packages_count: Optional[int] = None


class EnvironmentService:
    """
    Service pour la gestion des environnements virtuels Python.
    
    Responsabilités:
    - Création/suppression sécurisée d'environnements
    - Validation et diagnostic de santé
    - Scripts d'activation multi-plateforme
    - Gestion des métadonnées d'environnements
    """
    
    # Noms réservés non autorisés pour les environnements
    RESERVED_NAMES = {
        'system', 'global', 'base', 'root', 'admin', 'administrator',
        'python', 'python3', 'pip', 'venv', 'virtualenv', 'conda',
        'site', 'site-packages', 'scripts', 'bin', 'lib', 'include',
        'pyvenv.cfg', '__pycache__', '.git', '.svn', '.hg',
        'con', 'prn', 'aux', 'nul'  # Windows reserved
    }
    
    # Pattern pour validation des noms d'environnements
    NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$')
    
    def __init__(self, system_service=None, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialise le service d'environnements.
        
        Args:
            system_service: Service système pour les opérations shell
            config: Configuration optionnelle du service
        """
        self.system_service = system_service
        self.config = config or {}
        
        # Configuration par défaut
        self.max_name_length = self.config.get('max_name_length', 50)
        self.min_name_length = self.config.get('min_name_length', 1)
        self.auto_cleanup = self.config.get('auto_cleanup', True)
        self.safe_mode = self.config.get('safe_mode', True)
        
        logger.debug(f"EnvironmentService initialisé avec config: {self.config}")
    
    def create_environment(self, name: str, python_cmd: str, path: Path,
                         force: bool = False, system_site_packages: bool = False) -> Tuple[bool, str]:
        """
        Crée un nouvel environnement virtuel.
        
        Args:
            name: Nom de l'environnement
            python_cmd: Commande Python à utiliser (ex: 'python3.11')
            path: Chemin où créer l'environnement
            force: Forcer la création même si l'environnement existe
            system_site_packages: Accès aux packages système
            
        Returns:
            Tuple[bool, str]: (succès, message)
        """
        try:
            # Validation du nom
            valid, error_msg = self.validate_environment_name(name)
            if not valid:
                return False, f"Nom invalide: {error_msg}"
            
            # Vérification de la version Python
            if self.system_service:
                python_version = self.system_service.check_python_version(python_cmd)
                if not python_version:
                    return False, f"Version Python invalide ou non trouvée: {python_cmd}"
                logger.info(f"Utilisation de Python {python_version}")
            
            # Vérification si l'environnement existe déjà
            env_path = path / name
            if env_path.exists():
                if not force:
                    return False, f"L'environnement '{name}' existe déjà. Utilisez --force pour l'écraser."
                
                # Suppression sécurisée de l'environnement existant
                safe_to_delete, delete_msg = self.is_safe_to_delete(name, env_path)
                if not safe_to_delete:
                    return False, f"Impossible d'écraser l'environnement: {delete_msg}"
                
                shutil.rmtree(env_path)
                logger.info(f"Environnement existant '{name}' supprimé")
            
            # Création de l'environnement
            success = self._create_venv(python_cmd, env_path, system_site_packages)
            if not success:
                return False, f"Échec de la création de l'environnement avec {python_cmd}"
            
            # Vérification post-création
            health = self.check_environment_health(name, env_path)
            if not health.is_healthy:
                return False, f"Environnement créé mais défaillant: {', '.join(health.issues)}"
            
            logger.info(f"Environnement '{name}' créé avec succès à {env_path}")
            return True, f"Environnement '{name}' créé avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'environnement '{name}': {e}")
            return False, f"Erreur interne: {str(e)}"
    
    def _create_venv(self, python_cmd: str, env_path: Path, system_site_packages: bool) -> bool:
        """
        Crée l'environnement virtuel en utilisant le module venv.
        
        Args:
            python_cmd: Commande Python
            env_path: Chemin de l'environnement
            system_site_packages: Accès aux packages système
            
        Returns:
            bool: True si la création a réussi
        """
        try:
            import venv
            
            # Configuration du builder
            builder = venv.EnvBuilder(
                system_site_packages=system_site_packages,
                clear=True,  # Nettoyer si existe déjà
                symlinks=not sys.platform.startswith('win'),  # Symlinks sur Unix
                upgrade=False,
                with_pip=True,
                prompt=env_path.name
            )
            
            # Création de l'environnement
            builder.create(str(env_path))
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création venv: {e}")
            
            # Fallback: utilisation de la commande système
            if self.system_service:
                cmd = [python_cmd, '-m', 'venv', str(env_path)]
                if system_site_packages:
                    cmd.append('--system-site-packages')
                
                result = self.system_service.run_command(cmd)
                return result.get('returncode', 1) == 0
            
            return False
    
    def delete_environment(self, name: str, path: Path, force: bool = False) -> Tuple[bool, str]:
        """
        Supprime un environnement virtuel.
        
        Args:
            name: Nom de l'environnement
            path: Chemin de l'environnement
            force: Forcer la suppression sans vérifications
            
        Returns:
            Tuple[bool, str]: (succès, message)
        """
        try:
            env_path = path / name
            
            if not env_path.exists():
                return False, f"L'environnement '{name}' n'existe pas"
            
            # Vérifications de sécurité
            if not force:
                safe_to_delete, safety_msg = self.is_safe_to_delete(name, env_path)
                if not safe_to_delete:
                    return False, f"Suppression refusée: {safety_msg}"
            
            # Suppression effective
            shutil.rmtree(env_path)
            logger.info(f"Environnement '{name}' supprimé de {env_path}")
            return True, f"Environnement '{name}' supprimé avec succès"
            
        except PermissionError:
            return False, f"Permission refusée pour supprimer '{name}'"
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de '{name}': {e}")
            return False, f"Erreur lors de la suppression: {str(e)}"
    
    def check_environment_health(self, name: str, path: Path) -> EnvironmentHealth:
        """
        Vérifie la santé d'un environnement virtuel.
        
        Args:
            name: Nom de l'environnement
            path: Chemin de l'environnement
            
        Returns:
            EnvironmentHealth: Rapport de santé complet
        """
        env_path = path / name
        issues = []
        
        # Vérification de base : le répertoire existe-t-il ?
        if not env_path.exists():
            return EnvironmentHealth(
                status=EnvironmentStatus.MISSING,
                issues=["Le répertoire de l'environnement n'existe pas"]
            )
        
        # Vérification du fichier pyvenv.cfg
        pyvenv_cfg = env_path / 'pyvenv.cfg'
        if not pyvenv_cfg.exists():
            issues.append("Fichier pyvenv.cfg manquant")
        
        # Détection de l'exécutable Python
        python_exe = self._find_python_executable(env_path)
        if not python_exe or not python_exe.exists():
            issues.append("Exécutable Python non trouvé")
            return EnvironmentHealth(
                status=EnvironmentStatus.BROKEN,
                issues=issues
            )
        
        # Test de l'exécutable Python
        python_version = None
        if self.system_service:
            python_version = self.system_service.check_python_version(str(python_exe))
            if not python_version:
                issues.append("L'exécutable Python ne fonctionne pas")
        
        # Vérification de pip
        pip_available = self._check_pip_availability(python_exe)
        if not pip_available:
            issues.append("pip non disponible")
        
        # Vérification du répertoire site-packages
        site_packages = self._find_site_packages(env_path)
        if not site_packages or not site_packages.exists():
            issues.append("Répertoire site-packages non trouvé")
        
        # Détermination du statut final
        if not issues:
            status = EnvironmentStatus.HEALTHY
        elif len(issues) <= 1 and python_exe and python_exe.exists():
            status = EnvironmentStatus.PARTIAL
        elif python_exe and python_exe.exists():
            status = EnvironmentStatus.CORRUPTED
        else:
            status = EnvironmentStatus.BROKEN
        
        return EnvironmentHealth(
            status=status,
            python_executable=python_exe,
            python_version=python_version,
            pip_available=pip_available,
            site_packages=site_packages,
            issues=issues
        )
    
    def _find_python_executable(self, env_path: Path) -> Optional[Path]:
        """Trouve l'exécutable Python dans l'environnement."""
        # Windows
        if sys.platform.startswith('win'):
            candidates = [
                env_path / 'Scripts' / 'python.exe',
                env_path / 'Scripts' / 'python3.exe'
            ]
        # Unix/Linux/macOS
        else:
            candidates = [
                env_path / 'bin' / 'python',
                env_path / 'bin' / 'python3'
            ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        return None
    
    def _find_site_packages(self, env_path: Path) -> Optional[Path]:
        """Trouve le répertoire site-packages."""
        # Schéma Windows
        if sys.platform.startswith('win'):
            lib_dir = env_path / 'Lib' / 'site-packages'
        # Schéma Unix
        else:
            # Chercher dans lib/python*/site-packages
            lib_base = env_path / 'lib'
            if lib_base.exists():
                for python_dir in lib_base.glob('python*'):
                    site_packages = python_dir / 'site-packages'
                    if site_packages.exists():
                        return site_packages
            lib_dir = None
        
        return lib_dir if lib_dir and lib_dir.exists() else None
    
    def _check_pip_availability(self, python_exe: Path) -> bool:
        """Vérifie si pip est disponible dans l'environnement."""
        if not self.system_service:
            return False
        
        try:
            result = self.system_service.run_command([
                str(python_exe), '-m', 'pip', '--version'
            ], timeout=10)
            return result.get('returncode', 1) == 0
        except Exception:
            return False
    
    def validate_environment_name(self, name: str) -> Tuple[bool, str]:
        """
        Valide un nom d'environnement.
        
        Args:
            name: Nom à valider
            
        Returns:
            Tuple[bool, str]: (valide, message d'erreur si invalide)
        """
        # Vérification de base
        if not name:
            return False, "Le nom ne peut pas être vide"
        
        if len(name) < self.min_name_length:
            return False, f"Le nom doit contenir au moins {self.min_name_length} caractère(s)"
        
        if len(name) > self.max_name_length:
            return False, f"Le nom ne peut pas dépasser {self.max_name_length} caractères"
        
        # Vérification du pattern
        if not self.NAME_PATTERN.match(name):
            return False, ("Le nom doit commencer par une lettre ou un chiffre, "
                          "contenir uniquement des lettres, chiffres, tirets et underscores, "
                          "et ne pas finir par un tiret ou underscore")
        
        # Vérification des noms réservés
        if name.lower() in self.RESERVED_NAMES:
            return False, f"'{name}' est un nom réservé"
        
        # Vérifications spécifiques Windows
        if sys.platform.startswith('win'):
            if any(char in name for char in '<>:"|?*'):
                return False, "Le nom contient des caractères interdits sur Windows"
            
            if name.lower().endswith('.'):
                return False, "Le nom ne peut pas finir par un point sur Windows"
        
        return True, ""
    
    def get_activation_script_path(self, name: str, path: Path) -> Optional[Path]:
        """
        Retourne le chemin du script d'activation.
        
        Args:
            name: Nom de l'environnement
            path: Chemin de base des environnements
            
        Returns:
            Optional[Path]: Chemin du script d'activation ou None
        """
        env_path = path / name
        
        # Windows
        if sys.platform.startswith('win'):
            scripts = [
                env_path / 'Scripts' / 'activate.bat',
                env_path / 'Scripts' / 'Activate.ps1'
            ]
        # Unix/Linux/macOS
        else:
            scripts = [
                env_path / 'bin' / 'activate'
            ]
        
        for script in scripts:
            if script.exists():
                return script
        
        return None
    
    def is_safe_to_delete(self, name: str, path: Path) -> Tuple[bool, str]:
        """
        Vérifie s'il est sécurisé de supprimer un environnement.
        
        Args:
            name: Nom de l'environnement
            path: Chemin de l'environnement
            
        Returns:
            Tuple[bool, str]: (sécurisé, raison si non sécurisé)
        """
        if not self.safe_mode:
            return True, "Mode sécurisé désactivé"
        
        # Vérifications de base
        if not path.exists():
            return True, "Le répertoire n'existe pas"
        
        # Vérifier qu'il s'agit bien d'un environnement virtuel
        pyvenv_cfg = path / 'pyvenv.cfg'
        if not pyvenv_cfg.exists():
            return False, "Ce ne semble pas être un environnement virtuel (pyvenv.cfg manquant)"
        
        # Vérifier qu'on n'est pas dans un répertoire système
        system_paths = {
            Path('/'),
            Path('/usr'),
            Path('/bin'),
            Path('/etc'),
            Path('/var'),
            Path('/opt'),
            Path.home(),
            Path('/System'),  # macOS
            Path('C:\\'),     # Windows
            Path('C:\\Windows'),
            Path('C:\\Program Files'),
            Path('C:\\Program Files (x86)')
        }
        
        try:
            resolved_path = path.resolve()
            for sys_path in system_paths:
                try:
                    resolved_sys = sys_path.resolve()
                    if resolved_path == resolved_sys or resolved_path in resolved_sys.parents:
                        return False, f"Répertoire système détecté: {resolved_path}"
                except (OSError, RuntimeError):
                    continue
        except (OSError, RuntimeError):
            return False, "Impossible de résoudre le chemin"
        
        # Vérifier la taille (protection contre suppression accidentelle)
        try:
            total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            
            # Seuil de 1GB pour demander confirmation supplémentaire
            if size_mb > 1024:
                return False, f"Environnement très volumineux ({size_mb:.1f} MB). Utilisez --force si nécessaire."
        
        except (OSError, PermissionError):
            # Si on ne peut pas calculer la taille, on continue
            pass
        
        return True, "Suppression sécurisée"
    
    def get_environment_info(self, name: str, path: Path) -> Optional[EnvironmentInfo]:
        """
        Retourne les informations complètes sur un environnement.
        
        Args:
            name: Nom de l'environnement
            path: Chemin de base des environnements
            
        Returns:
            Optional[EnvironmentInfo]: Informations sur l'environnement ou None
        """
        env_path = path / name
        
        if not env_path.exists():
            return None
        
        # Vérification de santé
        health = self.check_environment_health(name, env_path)
        
        # Calcul de la taille
        size_mb = None
        try:
            total_size = sum(f.stat().st_size for f in env_path.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
        except (OSError, PermissionError):
            pass
        
        # Date de création (approximative via pyvenv.cfg)
        created_at = None
        try:
            pyvenv_cfg = env_path / 'pyvenv.cfg'
            if pyvenv_cfg.exists():
                created_at = pyvenv_cfg.stat().st_ctime
        except (OSError, PermissionError):
            pass
        
        # Comptage des packages
        packages_count = None
        if health.site_packages and health.site_packages.exists():
            try:
                # Compter les répertoires dans site-packages (approximation)
                packages_count = len([d for d in health.site_packages.iterdir() 
                                    if d.is_dir() and not d.name.startswith('_')])
            except (OSError, PermissionError):
                pass
        
        return EnvironmentInfo(
            name=name,
            path=env_path,
            python_version=health.python_version or "unknown",
            health=health,
            size_mb=size_mb,
            created_at=str(created_at) if created_at else None,
            packages_count=packages_count
        )