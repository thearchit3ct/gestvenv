"""
Service pour la gestion des environnements virtuels - GestVenv v1.1.

Ce module fournit les fonctionnalités pour créer, supprimer et gérer
les environnements virtuels Python et leurs configurations avec support étendu pour:
- pyproject.toml (PEP 517/518/621)
- Backends multiples (pip, uv, poetry, pdm)
- Lock files et synchronisation
- Détection automatique de type de projet
- Métriques de performance et santé avancée

Version 1.1 - Nouvelles fonctionnalités:
- Support pyproject.toml natif
- Détection intelligente du backend optimal
- Gestion des groupes de dépendances
- Validation étendue avec contexte
- Export/import multi-formats
"""

import os
import re
import json
import platform
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set

from ..core.models import (
    EnvironmentHealth, EnvironmentInfo, PyProjectInfo, 
    LockFileInfo, ValidationError, BackendType, SourceFileType,
    validate_environment_name, validate_python_version
)

# Configuration du logger
logger = logging.getLogger(__name__)


class EnvironmentService:
    """Service pour les opérations sur les environnements virtuels v1.1."""
    
    def __init__(self) -> None:
        """Initialise le service d'environnement."""
        self.system = platform.system().lower()  # 'windows', 'linux', 'darwin' (macOS)
        self._init_paths()
    
    def _init_paths(self) -> None:
        """Initialise les chemins système."""
        # Déterminer les chemins selon le système
        if self.system == "windows":
            self.scripts_dir = "Scripts"
            self.python_exe = "python.exe"
            self.pip_exe = "pip.exe"
            self.activate_script = "activate.bat"
        else:
            self.scripts_dir = "bin"
            self.python_exe = "python"
            self.pip_exe = "pip"
            self.activate_script = "activate"
    
    def validate_environment_name(self, name: str) -> Tuple[bool, str]:
        """
        Valide un nom d'environnement virtuel.
        
        Args:
            name: Nom d'environnement à valider.
            
        Returns:
            Tuple contenant (validité, message d'erreur si invalide).
        """
        validation_errors = validate_environment_name(name)
        
        if validation_errors:
            error_messages = "; ".join([err.message for err in validation_errors])
            return False, error_messages
        
        return True, ""
    
    def validate_python_version(self, version: str) -> Tuple[bool, str]:
        """
        Valide une spécification de version Python.
        
        Args:
            version: Version Python à valider.
            
        Returns:
            Tuple contenant (validité, message d'erreur si invalide).
        """
        validation_errors = validate_python_version(version)
        
        if validation_errors:
            error_messages = "; ".join([err.message for err in validation_errors])
            return False, error_messages
        
        return True, ""
    
    def validate_packages_list(self, packages: str) -> Tuple[bool, List[str], str]:
        """
        Valide une liste de packages séparés par des virgules.
        
        Args:
            packages: Chaîne de packages séparés par des virgules.
            
        Returns:
            Tuple contenant (validité, liste de packages, message d'erreur si invalide).
        """
        if not packages:
            return False, [], "La liste de packages ne peut pas être vide"
        
        # Séparer la chaîne en liste de packages
        package_list = [pkg.strip() for pkg in packages.split(",")]
        
        # Valider chaque package individuellement
        invalid_packages = []
        for pkg in package_list:
            valid, message = self._validate_package_name(pkg)
            if not valid:
                invalid_packages.append((pkg, message))
        
        if invalid_packages:
            error_message = "Packages invalides: " + ", ".join([f"{pkg} ({msg})" for pkg, msg in invalid_packages])
            return False, [], error_message
        
        return True, package_list, ""
    
    def _validate_package_name(self, package: str) -> Tuple[bool, str]:
        """
        Valide un nom de package Python avec support étendu v1.1.
        
        Args:
            package: Nom du package à valider.
            
        Returns:
            Tuple contenant (validité, message d'erreur si invalide).
        """
        if not package:
            return False, "Le nom du package ne peut pas être vide"
        
        # Patterns étendus pour v1.1
        patterns = [
            # Format standard : package==version, package>=version, etc.
            r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])(\[[a-zA-Z0-9._,-]+\])?((==|>=|<=|>|<|!=|~=)[0-9]+(\.[0-9]+)*([a-zA-Z0-9]+)?)?$',
            # URLs Git
            r'^git\+https?://.*$',
            # Chemins locaux
            r'^(\.|\/|~|[a-zA-Z]:).*$',
            # URLs directes
            r'^https?://.*\.(whl|tar\.gz|zip)$',
            # Editable installs
            r'^-e\s+.*$'
        ]
        
        for pattern in patterns:
            if re.match(pattern, package):
                return True, ""
        
        return False, f"Format de package invalide: {package}"
    
    def validate_output_format(self, format_str: str) -> Tuple[bool, str]:
        """
        Valide un format de sortie spécifié.
        
        Args:
            format_str: Format de sortie à valider.
            
        Returns:
            Tuple contenant (validité, message d'erreur si invalide).
        """
        valid_formats = ["json", "requirements", "pyproject", "toml", "yaml"]
        
        if not format_str:
            return False, "Le format de sortie ne peut pas être vide"
        
        if format_str.lower() not in valid_formats:
            return False, f"Format de sortie invalide. Formats valides: {', '.join(valid_formats)}"
        
        return True, ""
    
    def validate_metadata(self, metadata_str: str) -> Tuple[bool, Dict[str, str], str]:
        """
        Valide une chaîne de métadonnées au format "clé1:valeur1,clé2:valeur2".
        
        Args:
            metadata_str: Chaîne de métadonnées à valider.
            
        Returns:
            Tuple contenant (validité, dictionnaire de métadonnées, message d'erreur si invalide).
        """
        if not metadata_str:
            return True, {}, ""
        
        metadata = {}
        
        try:
            pairs = metadata_str.split(",")
            
            for pair in pairs:
                if ":" not in pair:
                    return False, {}, f"Format de métadonnées invalide (manque ':') : {pair}"
                
                key, value = pair.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                if not key:
                    return False, {}, "Les clés de métadonnées ne peuvent pas être vides"
                
                metadata[key] = value
            
            return True, metadata, ""
        except Exception as e:
            return False, {}, f"Erreur lors de la validation des métadonnées: {str(e)}"
    
    def detect_project_type(self, project_path: Path) -> SourceFileType:
        """
        Détecte le type de projet basé sur les fichiers présents.
        
        Args:
            project_path: Chemin du projet
            
        Returns:
            SourceFileType: Type de source détecté
        """
        try:
            # Ordre de priorité pour la détection
            if (project_path / "poetry.lock").exists():
                return SourceFileType.POETRY_LOCK
            elif (project_path / "pdm.lock").exists():
                return SourceFileType.PDM_LOCK
            elif (project_path / "uv.lock").exists() or (project_path / "pyproject.toml").exists():
                return SourceFileType.PYPROJECT
            elif (project_path / "requirements.txt").exists():
                return SourceFileType.REQUIREMENTS
            elif (project_path / "environment.yml").exists() or (project_path / "environment.yaml").exists():
                return SourceFileType.CONDA_ENV
            else:
                return SourceFileType.REQUIREMENTS  # Default
                
        except Exception as e:
            logger.debug(f"Erreur détection type projet: {e}")
            return SourceFileType.REQUIREMENTS
    
    def detect_optimal_backend(self, project_path: Path) -> BackendType:
        """
        Détecte le backend optimal pour un projet.
        
        Args:
            project_path: Chemin du projet
            
        Returns:
            BackendType: Backend recommandé
        """
        try:
            source_type = self.detect_project_type(project_path)
            
            # Mapping source type -> backend
            backend_mapping = {
                SourceFileType.POETRY_LOCK: BackendType.POETRY,
                SourceFileType.PDM_LOCK: BackendType.PDM,
                SourceFileType.CONDA_ENV: BackendType.CONDA,
                SourceFileType.PYPROJECT: BackendType.UV,  # uv est optimal pour pyproject.toml
                SourceFileType.REQUIREMENTS: BackendType.PIP
            }
            
            return backend_mapping.get(source_type, BackendType.PIP)
            
        except Exception as e:
            logger.debug(f"Erreur détection backend optimal: {e}")
            return BackendType.PIP
    
    def resolve_path(self, path_str: str) -> Path:
        """
        Résout un chemin relatif ou absolu.
        
        Args:
            path_str: Chaîne de caractères représentant un chemin.
            
        Returns:
            Path: Chemin absolu résolu.
        """
        path = Path(path_str)
        
        # Résoudre les chemins relatifs aux utilisateurs (~)
        if path_str.startswith("~"):
            path = Path(os.path.expanduser(path_str))
        
        # Rendre absolu si relatif
        if not path.is_absolute():
            path = Path.cwd() / path
        
        return path.resolve()
    
    def get_app_data_dir(self) -> Path:
        """
        Obtient le répertoire d'application approprié selon le système d'exploitation.
        
        Returns:
            Path: Chemin vers le répertoire d'application.
        """
        if self.system == "windows":
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            return Path(app_data) / "GestVenv"
        elif self.system == "darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "GestVenv"
        else:  # Linux et autres systèmes Unix-like
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config_home:
                return Path(xdg_config_home) / "gestvenv"
            else:
                return Path.home() / ".config" / "gestvenv"
    
    def get_default_venv_dir(self) -> Path:
        """
        Obtient le répertoire par défaut pour les environnements virtuels.
        
        Returns:
            Path: Chemin vers le répertoire des environnements virtuels.
        """
        venv_dir = self.get_app_data_dir() / "environments"
        venv_dir.mkdir(parents=True, exist_ok=True)
        return venv_dir
    
    def get_environment_path(self, name: str, custom_path: Optional[str] = None) -> Path:
        """
        Détermine le chemin pour un environnement virtuel.
        
        Args:
            name: Nom de l'environnement.
            custom_path: Chemin personnalisé optionnel.
            
        Returns:
            Path: Chemin vers l'environnement virtuel.
        """
        if custom_path:
            return self.resolve_path(custom_path)
        
        return self.get_default_venv_dir() / name
    
    def get_python_executable(self, name: str, env_path: Path) -> Optional[Path]:
        """
        Obtient le chemin vers l'exécutable Python d'un environnement virtuel.
        
        Args:
            name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Optional[Path]: Chemin vers l'exécutable Python s'il existe, None sinon.
        """
        if not env_path.exists():
            logger.warning(f"L'environnement '{name}' n'existe pas à {env_path}")
            return None
        
        python_path = env_path / self.scripts_dir / self.python_exe
        
        if python_path.exists():
            return python_path
        
        logger.warning(f"Exécutable Python non trouvé pour l'environnement '{name}'")
        return None
    
    def get_pip_executable(self, name: str, env_path: Path) -> Optional[Path]:
        """
        Obtient le chemin vers l'exécutable pip d'un environnement virtuel.
        
        Args:
            name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Optional[Path]: Chemin vers l'exécutable pip s'il existe, None sinon.
        """
        if not env_path.exists():
            logger.warning(f"L'environnement '{name}' n'existe pas à {env_path}")
            return None
        
        pip_path = env_path / self.scripts_dir / self.pip_exe
        
        if pip_path.exists():
            return pip_path
        
        logger.warning(f"Exécutable pip non trouvé pour l'environnement '{name}'")
        return None
    
    def get_activation_script_path(self, name: str, env_path: Path) -> Optional[Path]:
        """
        Obtient le chemin vers le script d'activation d'un environnement virtuel.
        
        Args:
            name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Optional[Path]: Chemin vers le script d'activation s'il existe, None sinon.
        """
        if not env_path.exists():
            logger.warning(f"L'environnement '{name}' n'existe pas à {env_path}")
            return None
        
        activate_path = env_path / self.scripts_dir / self.activate_script
        
        if activate_path.exists():
            return activate_path
        
        logger.warning(f"Script d'activation non trouvé pour l'environnement '{name}'")
        return None
    
    def create_environment(self, name: str, python_cmd: str, env_path: Path,
                          backend_type: BackendType = BackendType.PIP) -> Tuple[bool, str]:
        """
        Crée un nouvel environnement virtuel (délégué au backend).
        
        Args:
            name: Nom de l'environnement.
            python_cmd: Commande Python à utiliser.
            env_path: Chemin où créer l'environnement.
            backend_type: Type de backend à utiliser.
            
        Returns:
            Tuple contenant (succès, message).
        """
        # Note: Cette méthode est maintenant principalement déléguée aux backends
        # Elle reste ici pour la compatibilité et les cas de fallback
        
        if env_path.exists():
            logger.error(f"L'environnement '{name}' existe déjà à {env_path}")
            return False, f"L'environnement '{name}' existe déjà à {env_path}"
        
        # Créer le répertoire parent si nécessaire
        env_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Utilisation de venv par défaut (fallback)
            cmd = [python_cmd, "-m", "venv", str(env_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)
            
            if result.returncode != 0:
                logger.error(f"Échec de la création: {result.stderr}")
                return False, f"Échec de la création de l'environnement: {result.stderr}"
            
            logger.info(f"Environnement virtuel '{name}' créé avec succès à {env_path}")
            return True, f"Environnement virtuel '{name}' créé avec succès"
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'environnement: {str(e)}")
            
            # Nettoyer si nécessaire
            if env_path.exists():
                try:
                    shutil.rmtree(env_path)
                except Exception as cleanup_error:
                    logger.error(f"Erreur lors du nettoyage: {str(cleanup_error)}")
            
            return False, f"Erreur lors de la création de l'environnement: {str(e)}"
    
    def delete_environment(self, env_path: Path) -> Tuple[bool, str]:
        """
        Supprime un environnement virtuel.
        
        Args:
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Tuple contenant (succès, message).
        """
        if not env_path.exists():
            logger.warning(f"L'environnement à {env_path} n'existe pas")
            return True, "L'environnement n'existe pas (déjà supprimé)"
        
        try:
            # Suppression récursive du répertoire
            shutil.rmtree(env_path)
            logger.info(f"Environnement supprimé avec succès: {env_path}")
            return True, "Environnement supprimé avec succès"
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'environnement: {str(e)}")
            return False, f"Erreur lors de la suppression de l'environnement: {str(e)}"
    
    def check_environment_exists(self, env_path: Path) -> bool:
        """
        Vérifie si un environnement virtuel existe à l'emplacement spécifié.
        
        Args:
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            bool: True si l'environnement existe, False sinon.
        """
        if not env_path.exists():
            return False
        
        # Vérifier la présence du fichier de configuration de l'environnement
        pyvenv_cfg = env_path / "pyvenv.cfg"
        if pyvenv_cfg.exists():
            return True
        
        # Vérifier la présence d'indicateurs alternatifs
        python_exe = env_path / self.scripts_dir / self.python_exe
        return python_exe.exists()
    
    def check_environment_health(self, name: str, env_path: Path) -> EnvironmentHealth:
        """
        Vérifie l'état de santé d'un environnement virtuel avec métriques étendues v1.1.
        
        Args:
            name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            EnvironmentHealth: État de santé de l'environnement.
        """
        health = EnvironmentHealth()
        health.last_health_check = datetime.now()
        
        # Vérifier si l'environnement existe
        health.exists = env_path.exists()
        if not health.exists:
            return health
        
        # Vérifier si Python est disponible
        python_exe = self.get_python_executable(name, env_path)
        health.python_available = python_exe is not None and python_exe.exists()
        
        # Vérifier si pip est disponible
        pip_exe = self.get_pip_executable(name, env_path)
        health.pip_available = pip_exe is not None and pip_exe.exists()
        
        # Vérifier si le script d'activation existe
        activation_script = self.get_activation_script_path(name, env_path)
        health.activation_script_exists = activation_script is not None and activation_script.exists()
        
        # Vérifications étendues v1.1
        
        # Vérifier la disponibilité du backend
        health.backend_available = self._check_backend_availability(env_path)
        
        # Vérifier la validité du lock file
        health.lock_file_valid = self._check_lock_file_validity(env_path)
        
        # Vérifier la synchronisation des dépendances
        health.dependencies_synchronized = self._check_dependencies_sync(env_path)
        
        # Vérifier les problèmes de sécurité
        health.security_issues = self._scan_security_issues(env_path)
        
        # Calculer le score de performance
        health.performance_score = self._calculate_performance_score(env_path)
        
        return health
    
    def _check_backend_availability(self, env_path: Path) -> bool:
        """Vérifie si le backend est disponible pour l'environnement."""
        # Simplification : on considère que le backend est disponible si pip existe
        # Les backends spécifiques peuvent surcharger cette logique
        pip_exe = env_path / self.scripts_dir / self.pip_exe
        return pip_exe.exists()
    
    def _check_lock_file_validity(self, env_path: Path) -> bool:
        """Vérifie la validité du fichier de lock."""
        # Chercher les fichiers de lock connus
        project_path = env_path.parent
        lock_files = [
            project_path / "uv.lock",
            project_path / "poetry.lock",
            project_path / "pdm.lock",
            project_path / "Pipfile.lock"
        ]
        
        for lock_file in lock_files:
            if lock_file.exists():
                # Vérifier si le lock file est plus récent que les sources
                source_files = [
                    project_path / "pyproject.toml",
                    project_path / "requirements.txt",
                    project_path / "setup.py"
                ]
                
                lock_mtime = lock_file.stat().st_mtime
                for source in source_files:
                    if source.exists() and source.stat().st_mtime > lock_mtime:
                        return False  # Source modifiée après le lock
                
                return True
        
        return True  # Pas de lock file = pas de problème
    
    def _check_dependencies_sync(self, env_path: Path) -> bool:
        """Vérifie si les dépendances sont synchronisées."""
        # Simplification : on considère synchronisé par défaut
        # Les backends spécifiques peuvent implémenter une vérification plus poussée
        return True
    
    def _scan_security_issues(self, env_path: Path) -> List[str]:
        """Scanne les problèmes de sécurité potentiels."""
        issues = []
        
        try:
            # Vérifier les permissions trop permissives
            if self.system != "windows":
                stat_info = env_path.stat()
                if stat_info.st_mode & 0o022:  # Writable by group/others
                    issues.append("Permissions trop permissives sur l'environnement")
            
            # Vérifier la présence de packages connus comme vulnérables
            # (Simplification : liste statique, devrait être dynamique)
            vulnerable_packages = {
                "requests": "< 2.20.0",
                "django": "< 3.2",
                "flask": "< 2.0.0"
            }
            
            # Note: Vérification réelle nécessiterait l'accès aux packages installés
            
        except Exception as e:
            logger.debug(f"Erreur scan sécurité: {e}")
        
        return issues
    
    def _calculate_performance_score(self, env_path: Path) -> float:
        """Calcule un score de performance pour l'environnement."""
        try:
            score = 1.0
            
            # Pénalité pour taille excessive
            env_size = sum(f.stat().st_size for f in env_path.rglob('*') if f.is_file())
            if env_size > 1e9:  # > 1GB
                score *= 0.8
            elif env_size > 500e6:  # > 500MB
                score *= 0.9
            
            # Bonus pour présence de cache compilé
            pyc_files = list(env_path.rglob('*.pyc'))
            if pyc_files:
                score = min(1.0, score * 1.1)
            
            return round(score, 2)
            
        except Exception as e:
            logger.debug(f"Erreur calcul performance: {e}")
            return 0.5
    
    def is_safe_to_delete(self, name: str, env_path: Path) -> Tuple[bool, str]:
        """
        Vérifie s'il est sécuritaire de supprimer un environnement.
        
        Args:
            name: Nom de l'environnement.
            env_path: Chemin vers l'environnement.
            
        Returns:
            Tuple contenant (sécurité, message d'avertissement si non sécuritaire).
        """
        # Vérifier si l'environnement existe
        if not env_path.exists():
            return False, f"L'environnement '{name}' n'existe pas à {env_path}"
        
        # Vérifier si le chemin est sécuritaire
        system_directories = [
            Path("/"),
            Path("/usr"),
            Path("/bin"),
            Path("/etc"),
            Path("/var"),
            Path("/home"),
            Path("/tmp"),
            Path("C:\\"),
            Path("C:\\Windows"),
            Path("C:\\Program Files"),
            Path("C:\\Users"),
            Path.home()
        ]
        
        try:
            resolved_path = env_path.resolve()
            
            for sys_dir in system_directories:
                try:
                    sys_dir_resolved = sys_dir.resolve()
                    if resolved_path == sys_dir_resolved:
                        return False, f"Suppression refusée: '{env_path}' est un répertoire système critique"
                    
                    # Vérifier si c'est un sous-répertoire direct d'un répertoire système
                    if resolved_path.parent == sys_dir_resolved:
                        # Exception pour les répertoires virtuels standards
                        if resolved_path.name not in ["venv", "env", ".venv", ".env"] and "gestvenv" not in str(resolved_path).lower():
                            return False, f"Suppression refusée: '{env_path}' est dans un répertoire système"
                except Exception:
                    continue
        except Exception:
            pass
        
        # Vérifier si le chemin ressemble à un environnement virtuel
        venv_indicators = [
            "pyvenv.cfg",
            os.path.join(self.scripts_dir, self.python_exe),
            os.path.join(self.scripts_dir, self.activate_script)
        ]
        
        any_indicator_found = False
        for indicator in venv_indicators:
            indicator_path = env_path / indicator
            if indicator_path.exists():
                any_indicator_found = True
                break
        
        if not any_indicator_found:
            return False, f"Suppression refusée: '{env_path}' ne semble pas être un environnement virtuel"
        
        return True, ""
    
    def get_export_directory(self) -> Path:
        """
        Obtient le répertoire par défaut pour l'exportation des configurations.
        
        Returns:
            Path: Chemin vers le répertoire d'exportation.
        """
        export_dir = self.get_app_data_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir
    
    def get_json_output_path(self, env_name: str) -> Path:
        """
        Obtient le chemin par défaut pour l'exportation JSON d'un environnement.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            
        Returns:
            Path: Chemin par défaut pour l'exportation JSON.
        """
        export_dir = self.get_export_directory()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{env_name}_{timestamp}.json"
        return export_dir / filename
    
    def get_requirements_output_path(self, env_name: str, custom_path: Optional[str] = None) -> Path:
        """
        Obtient le chemin pour l'exportation requirements.txt d'un environnement.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            custom_path: Chemin personnalisé optionnel.
            
        Returns:
            Path: Chemin pour l'exportation requirements.txt.
        """
        if custom_path:
            return self.resolve_path(custom_path)
        
        export_dir = self.get_export_directory()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{env_name}_requirements_{timestamp}.txt"
        return export_dir / filename
    
    def get_pyproject_output_path(self, env_name: str, custom_path: Optional[str] = None) -> Path:
        """
        Obtient le chemin pour l'exportation pyproject.toml d'un environnement.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            custom_path: Chemin personnalisé optionnel.
            
        Returns:
            Path: Chemin pour l'exportation pyproject.toml.
        """
        if custom_path:
            return self.resolve_path(custom_path)
        
        export_dir = self.get_export_directory()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{env_name}_pyproject_{timestamp}.toml"
        return export_dir / filename
    
    def analyze_pyproject_toml(self, pyproject_path: Path) -> Optional[PyProjectInfo]:
        """
        Analyse un fichier pyproject.toml et extrait les informations.
        
        Args:
            pyproject_path: Chemin vers le fichier pyproject.toml
            
        Returns:
            PyProjectInfo ou None si erreur
        """
        try:
            from ..utils.pyproject_parser import PyProjectParser
            parser = PyProjectParser(pyproject_path)
            return parser.extract_info()
        except Exception as e:
            logger.error(f"Erreur analyse pyproject.toml: {e}")
            return None
    
    def detect_lock_file(self, project_path: Path) -> Optional[LockFileInfo]:
        """
        Détecte et analyse le fichier de lock du projet.
        
        Args:
            project_path: Chemin du projet
            
        Returns:
            LockFileInfo ou None si pas de lock file
        """
        try:
            # Rechercher les fichiers de lock connus
            lock_patterns = [
                ("uv.lock", "uv"),
                ("poetry.lock", "poetry"),
                ("pdm.lock", "pdm"),
                ("Pipfile.lock", "pipenv"),
                ("pip-tools.lock", "pip-tools")
            ]
            
            for filename, lock_type in lock_patterns:
                lock_path = project_path / filename
                if lock_path.exists():
                    stat = lock_path.stat()
                    return LockFileInfo(
                        file_path=lock_path,
                        lock_type=lock_type,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        created_at=datetime.fromtimestamp(stat.st_ctime)
                    )
            
            return None
            
        except Exception as e:
            logger.debug(f"Erreur détection lock file: {e}")
            return None
    
    def create_from_pyproject(self, pyproject_path: Path, env_name: str, 
                             env_path: Path, groups: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Crée un environnement depuis un fichier pyproject.toml.
        
        Args:
            pyproject_path: Chemin vers pyproject.toml
            env_name: Nom de l'environnement
            env_path: Chemin de l'environnement
            groups: Groupes de dépendances à installer
            
        Returns:
            Tuple contenant (succès, message)
        """
        try:
            # Analyser le pyproject.toml
            pyproject_info = self.analyze_pyproject_toml(pyproject_path)
            if not pyproject_info:
                return False, "Impossible d'analyser le fichier pyproject.toml"
            
            # Déterminer la version Python
            python_version = pyproject_info.requires_python or "python3"
            
            # Créer l'environnement de base
            success, message = self.create_environment(env_name, python_version, env_path)
            if not success:
                return False, f"Échec création environnement: {message}"
            
            # Note: L'installation des dépendances est déléguée au backend
            # via le PackageService dans env_manager
            
            return True, f"Environnement '{env_name}' créé depuis pyproject.toml"
            
        except Exception as e:
            logger.error(f"Erreur création depuis pyproject.toml: {e}")
            return False, f"Erreur création depuis pyproject.toml: {str(e)}"
    
    def get_backend_info(self, backend_type: BackendType) -> Dict[str, Any]:
        """
        Retourne les informations sur un backend spécifique.
        
        Args:
            backend_type: Type de backend
            
        Returns:
            Dict avec les informations du backend
        """
        backend_info = {
            BackendType.PIP: {
                "name": "pip",
                "description": "Gestionnaire de packages Python standard",
                "features": ["installation", "désinstallation", "mise à jour", "requirements.txt"],
                "performance": "standard",
                "recommended_for": ["projets simples", "compatibilité maximale"]
            },
            BackendType.UV: {
                "name": "uv",
                "description": "Gestionnaire de packages ultra-rapide par Astral",
                "features": ["installation rapide", "résolution moderne", "lock files", "pyproject.toml"],
                "performance": "10-100x plus rapide que pip",
                "recommended_for": ["projets modernes", "développement rapide", "CI/CD"]
            },
            BackendType.POETRY: {
                "name": "poetry",
                "description": "Gestionnaire de dépendances et packaging Python",
                "features": ["gestion complète du projet", "publication PyPI", "lock files stricts"],
                "performance": "modérée",
                "recommended_for": ["packages Python", "projets avec publication"]
            },
            BackendType.PDM: {
                "name": "pdm",
                "description": "Gestionnaire de packages moderne compatible PEP",
                "features": ["support PEP 582", "sans environnement virtuel", "pyproject.toml"],
                "performance": "rapide",
                "recommended_for": ["projets PEP-compliant", "développement moderne"]
            }
        }
        
        return backend_info.get(backend_type, {
            "name": backend_type.value,
            "description": "Backend non documenté",
            "features": [],
            "performance": "inconnue",
            "recommended_for": []
        })
    
    def get_environment_size(self, env_path: Path) -> int:
        """
        Calcule la taille totale d'un environnement en octets.
        
        Args:
            env_path: Chemin de l'environnement
            
        Returns:
            int: Taille en octets
        """
        try:
            total_size = 0
            for item in env_path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
            return total_size
        except Exception as e:
            logger.debug(f"Erreur calcul taille environnement: {e}")
            return 0
    
    def clean_pyc_files(self, env_path: Path) -> Tuple[int, int]:
        """
        Nettoie les fichiers .pyc et __pycache__ d'un environnement.
        
        Args:
            env_path: Chemin de l'environnement
            
        Returns:
            Tuple (nombre de fichiers supprimés, espace libéré en octets)
        """
        try:
            count = 0
            freed_space = 0
            
            # Supprimer les fichiers .pyc
            for pyc_file in env_path.rglob('*.pyc'):
                try:
                    size = pyc_file.stat().st_size
                    pyc_file.unlink()
                    count += 1
                    freed_space += size
                except Exception:
                    pass
            
            # Supprimer les répertoires __pycache__
            for pycache_dir in env_path.rglob('__pycache__'):
                try:
                    shutil.rmtree(pycache_dir)
                    count += 1
                except Exception:
                    pass
            
            return count, freed_space
            
        except Exception as e:
            logger.debug(f"Erreur nettoyage pyc: {e}")
            return 0, 0
    
    def optimize_environment(self, env_path: Path) -> Dict[str, Any]:
        """
        Optimise un environnement (nettoyage, compression, etc.).
        
        Args:
            env_path: Chemin de l'environnement
            
        Returns:
            Dict avec les résultats de l'optimisation
        """
        results = {
            "pyc_cleaned": 0,
            "space_freed": 0,
            "errors": []
        }
        
        try:
            # Nettoyer les fichiers pyc
            count, freed = self.clean_pyc_files(env_path)
            results["pyc_cleaned"] = count
            results["space_freed"] = freed
            
            # Autres optimisations possibles :
            # - Suppression des fichiers de test dans site-packages
            # - Compression des archives wheel non utilisées
            # - Suppression des doublons
            
        except Exception as e:
            results["errors"].append(str(e))
        
        return results