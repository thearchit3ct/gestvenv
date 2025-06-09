"""
Utilitaires de validation pour GestVenv v1.1.
Validation de packages, versions, configurations, etc.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from packaging import version as pkg_version
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.requirements import Requirement, InvalidRequirement

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Exception pour les erreurs de validation."""
    pass

class ValidationUtils:
    """Utilitaires de validation avancés."""
    
    # Expressions régulières pour validation
    PACKAGE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$')
    VERSION_PATTERN = re.compile(r'^\d+(\.\d+)*([a-zA-Z0-9]+(\.\d+)*)?$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// ou https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domaine
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # port optionnel
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    @staticmethod
    def validate_package_name(name: str, strict: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Valide un nom de package Python.
        
        Args:
            name: Nom du package à valider
            strict: Mode strict (PEP 508) ou permissif
            
        Returns:
            (valide, message_erreur)
        """
        if not name:
            return False, "Le nom du package ne peut pas être vide"
        
        if not isinstance(name, str):
            return False, "Le nom du package doit être une chaîne"
        
        # Vérifier la longueur
        if len(name) > 214:  # Limite PyPI
            return False, "Le nom du package ne peut pas dépasser 214 caractères"
        
        if strict:
            # Validation stricte selon PEP 508
            if not ValidationUtils.PACKAGE_NAME_PATTERN.match(name):
                return False, (
                    "Le nom du package doit commencer et finir par une lettre ou un chiffre, "
                    "et ne peut contenir que des lettres, chiffres, points, tirets et underscores"
                )
            
            # Vérifier les caractères interdits
            if name.startswith(('.', '-', '_')) or name.endswith(('.', '-', '_')):
                return False, "Le nom du package ne peut pas commencer ou finir par '.', '-' ou '_'"
            
            # Vérifier les séquences multiples
            if '..' in name or '--' in name or '__' in name:
                return False, "Le nom du package ne peut pas contenir de séquences multiples de séparateurs"
        
        # Vérifier que ce n'est pas un mot-clé Python
        import keyword
        if keyword.iskeyword(name):
            return False, f"'{name}' est un mot-clé Python réservé"
        
        return True, None
    
    @staticmethod
    def validate_version(version_str: str, allow_prereleases: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Valide une version de package.
        
        Args:
            version_str: Chaîne de version à valider
            allow_prereleases: Autoriser les pré-versions
            
        Returns:
            (valide, message_erreur)
        """
        if not version_str:
            return False, "La version ne peut pas être vide"
        
        if not isinstance(version_str, str):
            return False, "La version doit être une chaîne"
        
        try:
            parsed_version = pkg_version.parse(version_str)
            
            # Vérifier si c'est une pré-version
            if not allow_prereleases and parsed_version.is_prerelease:
                return False, "Les pré-versions ne sont pas autorisées"
            
            return True, None
            
        except pkg_version.InvalidVersion as e:
            return False, f"Version invalide: {e}"
    
    @staticmethod
    def validate_requirement(requirement_str: str) -> Tuple[bool, Optional[str], Optional[Requirement]]:
        """
        Valide une spécification de requirement (ex: "requests>=2.25.0").
        
        Args:
            requirement_str: Chaîne de requirement à valider
            
        Returns:
            (valide, message_erreur, objet_requirement)
        """
        if not requirement_str:
            return False, "Le requirement ne peut pas être vide", None
        
        if not isinstance(requirement_str, str):
            return False, "Le requirement doit être une chaîne", None
        
        try:
            req = Requirement(requirement_str.strip())
            
            # Valider le nom du package
            name_valid, name_error = ValidationUtils.validate_package_name(req.name)
            if not name_valid:
                return False, f"Nom de package invalide: {name_error}", None
            
            # Valider les spécificateurs de version
            if req.specifier:
                try:
                    # Vérifier que les spécificateurs sont valides
                    SpecifierSet(str(req.specifier))
                except InvalidSpecifier as e:
                    return False, f"Spécificateur de version invalide: {e}", None
            
            return True, None, req
            
        except InvalidRequirement as e:
            return False, f"Requirement invalide: {e}", None
    
    @staticmethod
    def validate_requirements_list(requirements: List[str]) -> Tuple[bool, List[str], List[Requirement]]:
        """
        Valide une liste de requirements.
        
        Args:
            requirements: Liste de chaînes de requirements
            
        Returns:
            (tout_valide, liste_erreurs, liste_requirements_valides)
        """
        errors = []
        valid_requirements = []
        
        for i, req_str in enumerate(requirements):
            valid, error, req_obj = ValidationUtils.validate_requirement(req_str)
            
            if valid and req_obj:
                valid_requirements.append(req_obj)
            else:
                errors.append(f"Ligne {i+1}: {error}")
        
        return len(errors) == 0, errors, valid_requirements
    
    @staticmethod
    def validate_python_version(version_str: str) -> Tuple[bool, Optional[str]]:
        """
        Valide une spécification de version Python.
        
        Args:
            version_str: Spécification de version Python (ex: ">=3.9")
            
        Returns:
            (valide, message_erreur)
        """
        if not version_str:
            return False, "La version Python ne peut pas être vide"
        
        try:
            specifier = SpecifierSet(version_str)
            
            # Vérifier que la version actuelle est compatible si possible
            current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            if not specifier.contains(current_version):
                logger.warning(f"Version Python actuelle {current_version} non compatible avec {version_str}")
            
            return True, None
            
        except InvalidSpecifier as e:
            return False, f"Spécification de version Python invalide: {e}"
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Valide une adresse email.
        
        Args:
            email: Adresse email à valider
            
        Returns:
            (valide, message_erreur)
        """
        if not email:
            return False, "L'email ne peut pas être vide"
        
        if not isinstance(email, str):
            return False, "L'email doit être une chaîne"
        
        if len(email) > 254:  # RFC 5321
            return False, "L'email ne peut pas dépasser 254 caractères"
        
        if not ValidationUtils.EMAIL_PATTERN.match(email):
            return False, "Format d'email invalide"
        
        return True, None
    
    @staticmethod
    def validate_url(url: str, schemes: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        """
        Valide une URL.
        
        Args:
            url: URL à valider
            schemes: Schémas autorisés (default: ['http', 'https'])
            
        Returns:
            (valide, message_erreur)
        """
        if not url:
            return False, "L'URL ne peut pas être vide"
        
        if not isinstance(url, str):
            return False, "L'URL doit être une chaîne"
        
        if schemes is None:
            schemes = ['http', 'https']
        
        # Vérifier le schéma
        url_lower = url.lower()
        if not any(url_lower.startswith(f"{scheme}://") for scheme in schemes):
            return False, f"L'URL doit commencer par un des schémas: {', '.join(schemes)}"
        
        if not ValidationUtils.URL_PATTERN.match(url):
            return False, "Format d'URL invalide"
        
        return True, None
    
    @staticmethod
    def validate_path(path: Union[str, Path], must_exist: bool = False, 
                     must_be_file: bool = False, must_be_dir: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Valide un chemin de fichier ou répertoire.
        
        Args:
            path: Chemin à valider
            must_exist: Le chemin doit exister
            must_be_file: Le chemin doit être un fichier
            must_be_dir: Le chemin doit être un répertoire
            
        Returns:
            (valide, message_erreur)
        """
        if not path:
            return False, "Le chemin ne peut pas être vide"
        
        try:
            path_obj = Path(path)
            
            if must_exist and not path_obj.exists():
                return False, f"Le chemin n'existe pas: {path}"
            
            if path_obj.exists():
                if must_be_file and not path_obj.is_file():
                    return False, f"Le chemin doit être un fichier: {path}"
                
                if must_be_dir and not path_obj.is_dir():
                    return False, f"Le chemin doit être un répertoire: {path}"
            
            return True, None
            
        except Exception as e:
            return False, f"Chemin invalide: {e}"
    
    @staticmethod
    def validate_environment_name(name: str) -> Tuple[bool, Optional[str]]:
        """
        Valide un nom d'environnement virtuel.
        
        Args:
            name: Nom de l'environnement à valider
            
        Returns:
            (valide, message_erreur)
        """
        if not name:
            return False, "Le nom de l'environnement ne peut pas être vide"
        
        if not isinstance(name, str):
            return False, "Le nom de l'environnement doit être une chaîne"
        
        # Vérifier la longueur
        if len(name) > 100:
            return False, "Le nom de l'environnement ne peut pas dépasser 100 caractères"
        
        # Vérifier les caractères autorisés (alphanumériques, tirets, underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return False, "Le nom de l'environnement ne peut contenir que des lettres, chiffres, tirets et underscores"
        
        # Vérifier qu'il ne commence pas par un tiret
        if name.startswith('-'):
            return False, "Le nom de l'environnement ne peut pas commencer par un tiret"
        
        # Vérifier les noms réservés
        reserved_names = ['python', 'pip', 'setuptools', 'wheel', 'conda', 'base', 'root']
        if name.lower() in reserved_names:
            return False, f"'{name}' est un nom réservé"
        
        return True, None
    
    @staticmethod
    def sanitize_filename(filename: str, replacement_char: str = '_') -> str:
        """
        Nettoie un nom de fichier en supprimant/remplaçant les caractères interdits.
        
        Args:
            filename: Nom de fichier à nettoyer
            replacement_char: Caractère de remplacement
            
        Returns:
            Nom de fichier nettoyé
        """
        # Caractères interdits sur la plupart des systèmes
        forbidden_chars = r'<>:"/\|?*'
        
        # Remplacer les caractères interdits
        cleaned = filename
        for char in forbidden_chars:
            cleaned = cleaned.replace(char, replacement_char)
        
        # Supprimer les espaces en début/fin
        cleaned = cleaned.strip()
        
        # Remplacer les espaces multiples par un seul
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Limiter la longueur (255 caractères pour la plupart des systèmes)
        if len(cleaned) > 255:
            name, ext = Path(cleaned).stem, Path(cleaned).suffix
            max_name_length = 255 - len(ext)
            cleaned = name[:max_name_length] + ext
        
        return cleaned

# Fonctions utilitaires pour compatibilité
def validate_package_name(name: str) -> Tuple[bool, Optional[str]]:
    """Fonction utilitaire pour valider un nom de package."""
    return ValidationUtils.validate_package_name(name)

def validate_version(version_str: str) -> Tuple[bool, Optional[str]]:
    """Fonction utilitaire pour valider une version."""
    return ValidationUtils.validate_version(version_str)

def validate_requirement(requirement_str: str) -> Tuple[bool, Optional[str], Optional[Requirement]]:
    """Fonction utilitaire pour valider un requirement."""
    return ValidationUtils.validate_requirement(requirement_str)
