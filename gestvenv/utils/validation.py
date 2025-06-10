"""
Utilitaires de validation pour GestVenv v1.1
"""

import re
import string
from pathlib import Path
from typing import List, Dict, Any

from ..core.exceptions import ValidationError

import logging
logger = logging.getLogger(__name__)


class ValidationUtils:
    """Utilitaires de validation des données"""
    
    # Patterns de validation
    ENVIRONMENT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,98}[a-zA-Z0-9]$')
    PYTHON_VERSION_PATTERN = re.compile(r'^\d+\.\d+(\.\d+)?$')
    PACKAGE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')
    
    # Noms réservés système
    RESERVED_NAMES = {
        'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5',
        'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4',
        'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
    }
    
    @staticmethod
    def validate_environment_name(name: str) -> bool:
        """Valide un nom d'environnement"""
        if not name or len(name) > 100:
            return False
        
        # Noms réservés système
        if name.lower() in ValidationUtils.RESERVED_NAMES:
            return False
        
        # Pattern validation
        if not ValidationUtils.ENVIRONMENT_NAME_PATTERN.match(name):
            return False
        
        # Caractères dangereux
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
        if any(char in name for char in dangerous_chars):
            return False
        
        # Path traversal
        if '..' in name or name.startswith('.'):
            return False
        
        return True
    
    @staticmethod
    def sanitize_environment_name(name: str) -> str:
        """Assainit un nom d'environnement"""
        if not name:
            return "default_env"
        
        # Suppression caractères dangereux
        safe_chars = string.ascii_letters + string.digits + '._-'
        sanitized = ''.join(c for c in name if c in safe_chars)
        
        # Assurer début/fin valides
        sanitized = re.sub(r'^[._-]+', '', sanitized)
        sanitized = re.sub(r'[._-]+$', '', sanitized)
        
        # Longueur
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        # Fallback si vide
        if not sanitized:
            sanitized = "sanitized_env"
        
        return sanitized
    
    @staticmethod
    def validate_python_version(version_str: str) -> bool:
        """Valide une version Python"""
        if not version_str:
            return False
        
        if not ValidationUtils.PYTHON_VERSION_PATTERN.match(version_str):
            return False
        
        try:
            parts = version_str.split('.')
            major = int(parts[0])
            minor = int(parts[1])
            
            # Support Python 3.9+
            if major < 3 or (major == 3 and minor < 9):
                return False
            
            # Version raisonnable (pas plus de 3.20)
            if major > 3 or (major == 3 and minor > 20):
                return False
            
            return True
        except (ValueError, IndexError):
            return False
    
    @staticmethod
    def validate_package_specification(spec: str) -> bool:
        """Valide une spécification de package"""
        if not spec or not spec.strip():
            return False
        
        spec = spec.strip()
        
        # Caractères dangereux pour injection commandes
        dangerous_chars = [';', '|', '&', '`', '$', '(', ')', '\n', '\r']
        if any(char in spec for char in dangerous_chars):
            return False
        
        # URLs suspectes
        suspicious_urls = ['file://', 'ftp://', 'data:', 'javascript:']
        if any(url in spec.lower() for url in suspicious_urls):
            return False
        
        # Flags pip dangereux
        dangerous_flags = ['--trusted-host', '--index-url', '--extra-index-url', '--find-links']
        if any(flag in spec for flag in dangerous_flags):
            return False
        
        # Validation format basique
        # Nom[extras]version_spec ou URL git+https
        if spec.startswith(('git+', 'hg+', 'svn+', 'bzr+')):
            return ValidationUtils._validate_vcs_url(spec)
        elif spec.startswith(('http://', 'https://')):
            return ValidationUtils._validate_http_url(spec)
        elif spec.startswith('-e '):
            return ValidationUtils._validate_editable_spec(spec[3:])
        else:
            return ValidationUtils._validate_package_name_spec(spec)
    
    @staticmethod
    def validate_pyproject_structure(data: dict) -> List[str]:
        """Valide la structure d'un pyproject.toml"""
        errors = []
        
        if not isinstance(data, dict):
            errors.append("Structure racine doit être un dictionnaire")
            return errors
        
        # Section project
        if 'project' not in data:
            errors.append("Section [project] requise")
        else:
            project_errors = ValidationUtils._validate_project_section(data['project'])
            errors.extend(project_errors)
        
        # Build system
        if 'build-system' in data:
            build_errors = ValidationUtils._validate_build_system(data['build-system'])
            errors.extend(build_errors)
        
        return errors
    
    @staticmethod
    def validate_path_safety(path: Path) -> bool:
        """Valide la sécurité d'un chemin"""
        try:
            path_str = str(path)
            
            # Path traversal
            if '..' in path_str:
                return False
            
            # Chemins absolus vers système
            dangerous_paths = ['/etc', '/bin', '/usr', '/var', '/root', 'C:\\Windows', 'C:\\Program Files']
            if any(path_str.startswith(dp) for dp in dangerous_paths):
                return False
            
            # Caractères dangereux
            if any(char in path_str for char in ['<', '>', '|', '"', '?', '*']):
                return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_requirements_syntax(req_path: Path) -> List[ValidationError]:
        """Valide la syntaxe d'un requirements.txt"""
        errors = []
        
        if not req_path.exists():
            errors.append(ValidationError(f"Fichier introuvable: {req_path}"))
            return errors
        
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('-'):
                        # Options pip - validation basique
                        if not ValidationUtils._validate_pip_option(line):
                            errors.append(ValidationError(
                                f"Option pip invalide ligne {line_num}: {line}"
                            ))
                    else:
                        # Spécification package
                        if not ValidationUtils.validate_package_specification(line):
                            errors.append(ValidationError(
                                f"Spécification package invalide ligne {line_num}: {line}"
                            ))
        except Exception as e:
            errors.append(ValidationError(f"Erreur lecture fichier: {e}"))
        
        return errors
    
    # Méthodes privées
    
    @staticmethod
    def _validate_vcs_url(spec: str) -> bool:
        """Valide une URL VCS"""
        # git+https://github.com/user/repo.git
        if not spec.startswith(('git+https://', 'git+ssh://')):
            return False
        
        # Vérification domaine connu
        known_domains = ['github.com', 'gitlab.com', 'bitbucket.org']
        if not any(domain in spec for domain in known_domains):
            logger.warning(f"Domaine VCS non reconnu: {spec}")
        
        return True
    
    @staticmethod
    def _validate_http_url(spec: str) -> bool:
        """Valide une URL HTTP"""
        if not spec.startswith('https://'):
            return False  # Seulement HTTPS autorisé
        
        # Validation basique
        return '/' in spec[8:] and '.' in spec
    
    @staticmethod
    def _validate_editable_spec(spec: str) -> bool:
        """Valide une spécification editable"""
        if spec.startswith('/'):
            # Chemin absolu - vérifier sécurité
            return ValidationUtils.validate_path_safety(Path(spec))
        elif spec.startswith('./') or spec.startswith('../'):
            # Chemin relatif
            return True
        else:
            # URL ou autre
            return ValidationUtils._validate_http_url(spec) or ValidationUtils._validate_vcs_url(spec)
    
    @staticmethod
    def _validate_package_name_spec(spec: str) -> bool:
        """Valide spécification nom[extras]version"""
        # Extraction nom
        name_match = re.match(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*)', spec)
        if not name_match:
            return False
        
        name = name_match.group(1)
        if not ValidationUtils.PACKAGE_NAME_PATTERN.match(name):
            return False
        
        remainder = spec[len(name):]
        
        # Extras optionnels [extra1,extra2]
        if remainder.startswith('['):
            extras_match = re.match(r'^\[([a-zA-Z0-9,._-]+)\]', remainder)
            if not extras_match:
                return False
            remainder = remainder[len(extras_match.group(0)):]
        
        # Version optionnelle
        if remainder:
            version_pattern = r'^(==|>=|<=|>|<|~=|!=)[a-zA-Z0-9._-]+(\*)?$'
            if not re.match(version_pattern, remainder):
                return False
        
        return True
    
    @staticmethod
    def _validate_project_section(project: dict) -> List[str]:
        """Valide la section [project]"""
        errors = []
        
        if not isinstance(project, dict):
            errors.append("Section [project] doit être un dictionnaire")
            return errors
        
        # Nom requis
        if 'name' not in project:
            errors.append("Champ 'name' requis dans [project]")
        elif not ValidationUtils.PACKAGE_NAME_PATTERN.match(project['name']):
            errors.append(f"Nom projet invalide: {project['name']}")
        
        # Version si présente
        if 'version' in project:
            if not ValidationUtils._validate_version_pep440(project['version']):
                errors.append(f"Version invalide: {project['version']}")
        
        # Dependencies si présentes
        if 'dependencies' in project:
            if not isinstance(project['dependencies'], list):
                errors.append("'dependencies' doit être une liste")
            else:
                for i, dep in enumerate(project['dependencies']):
                    if not ValidationUtils.validate_package_specification(dep):
                        errors.append(f"Dépendance invalide #{i}: {dep}")
        
        return errors
    
    @staticmethod
    def _validate_build_system(build_system: dict) -> List[str]:
        """Valide la section [build-system]"""
        errors = []
        
        if not isinstance(build_system, dict):
            errors.append("Section [build-system] doit être un dictionnaire")
            return errors
        
        # Requires requis
        if 'requires' not in build_system:
            errors.append("Champ 'requires' requis dans [build-system]")
        elif not isinstance(build_system['requires'], list):
            errors.append("'requires' doit être une liste")
        
        return errors
    
    @staticmethod
    def _validate_version_pep440(version: str) -> bool:
        """Valide version selon PEP 440"""
        if not version:
            return False
        
        # Pattern PEP 440 simplifié
        pattern = r'^\d+(\.\d+)*((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?$'
        return bool(re.match(pattern, version))
    
    @staticmethod
    def _validate_pip_option(option: str) -> bool:
        """Valide une option pip"""
        safe_options = [
            '-r', '--requirement',
            '-e', '--editable',
            '--no-deps',
            '--upgrade',
            '--force-reinstall'
        ]
        
        return any(option.startswith(opt) for opt in safe_options)