"""
Utilitaires TOML avec gestion conditionnelle Python 3.11+.
Conformité PEP 518, 621 pour pyproject.toml.
"""

import sys
from typing import Dict, Any, Union, Optional, List
from pathlib import Path
import logging

# Import conditionnel selon version Python
if sys.version_info >= (3, 11):
    import tomllib
    HAS_TOMLLIB = True
else:
    try:
        import tomli as tomllib
        HAS_TOMLLIB = True
    except ImportError:
        HAS_TOMLLIB = False
        tomllib = None

# Pour l'écriture, on utilise tomlkit ou tomli_w
try:
    import tomlkit
    HAS_TOMLKIT = True
except ImportError:
    try:
        import tomli_w
        HAS_TOMLKIT = False
        HAS_TOMLI_W = True
    except ImportError:
        HAS_TOMLKIT = False
        HAS_TOMLI_W = False

logger = logging.getLogger(__name__)

class TomlError(Exception):
    """Exception pour les erreurs TOML."""
    pass

class TomlUtils:
    """Utilitaires pour la gestion des fichiers TOML."""
    
    @staticmethod
    def _check_toml_support() -> None:
        """Vérifie que le support TOML est disponible."""
        if not HAS_TOMLLIB:
            raise TomlError(
                "Support TOML non disponible. "
                "Installez 'tomli' pour Python < 3.11 : pip install tomli"
            )
    
    @staticmethod
    def _check_toml_write_support() -> None:
        """Vérifie que l'écriture TOML est disponible."""
        if not (HAS_TOMLKIT or HAS_TOMLI_W):
            raise TomlError(
                "Écriture TOML non disponible. "
                "Installez 'tomlkit' ou 'tomli-w' : pip install tomlkit"
            )
    
    @staticmethod
    def load_toml(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Charge un fichier TOML.
        
        Args:
            file_path: Chemin vers le fichier TOML
            
        Returns:
            Contenu du fichier TOML parsé
            
        Raises:
            TomlError: Si erreur de lecture ou parsing
        """
        TomlUtils._check_toml_support()
        
        try:
            path_obj = Path(file_path)
            
            if not path_obj.exists():
                raise TomlError(f"Fichier TOML inexistant: {file_path}")
            
            if not path_obj.is_file():
                raise TomlError(f"Le chemin n'est pas un fichier: {file_path}")
            
            with open(path_obj, 'rb') as f:
                data = tomllib.load(f)
            
            logger.debug(f"Fichier TOML chargé: {file_path}")
            return data
            
        except tomllib.TOMLDecodeError as e:
            raise TomlError(f"Erreur parsing TOML dans {file_path}: {e}")
        except Exception as e:
            raise TomlError(f"Erreur lecture fichier TOML {file_path}: {e}")
    
    @staticmethod
    def load_toml_string(toml_string: str) -> Dict[str, Any]:
        """
        Parse une chaîne TOML.
        
        Args:
            toml_string: Chaîne TOML à parser
            
        Returns:
            Contenu TOML parsé
            
        Raises:
            TomlError: Si erreur de parsing
        """
        TomlUtils._check_toml_support()
        
        try:
            data = tomllib.loads(toml_string)
            logger.debug("Chaîne TOML parsée avec succès")
            return data
        except tomllib.TOMLDecodeError as e:
            raise TomlError(f"Erreur parsing chaîne TOML: {e}")
    
    @staticmethod
    def save_toml(data: Dict[str, Any], file_path: Union[str, Path], 
                  preserve_formatting: bool = True) -> None:
        """
        Sauvegarde des données en fichier TOML.
        
        Args:
            data: Données à sauvegarder
            file_path: Chemin de destination
            preserve_formatting: Préserver le formatage avec tomlkit
            
        Raises:
            TomlError: Si erreur d'écriture
        """
        TomlUtils._check_toml_write_support()
        
        try:
            path_obj = Path(file_path)
            
            # Créer le répertoire parent si nécessaire
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            if HAS_TOMLKIT and preserve_formatting:
                # Utiliser tomlkit pour préserver le formatage
                import tomlkit
                
                # Si le fichier existe, le charger pour préserver la structure
                if path_obj.exists():
                    with open(path_obj, 'r', encoding='utf-8') as f:
                        doc = tomlkit.load(f)
                    # Mettre à jour avec les nouvelles données
                    doc.update(data)
                else:
                    doc = tomlkit.document()
                    doc.update(data)
                
                with open(path_obj, 'w', encoding='utf-8') as f:
                    tomlkit.dump(doc, f)
            
            elif HAS_TOMLI_W:
                # Utiliser tomli_w pour écriture simple
                import tomli_w
                with open(path_obj, 'wb') as f:
                    tomli_w.dump(data, f)
            
            else:
                raise TomlError("Aucune bibliothèque d'écriture TOML disponible")
            
            logger.debug(f"Fichier TOML sauvegardé: {file_path}")
            
        except Exception as e:
            raise TomlError(f"Erreur sauvegarde fichier TOML {file_path}: {e}")
    
    @staticmethod
    def validate_toml_structure(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        Valide la structure d'un fichier TOML selon un schéma.
        
        Args:
            data: Données TOML à valider
            schema: Schéma de validation
            
        Returns:
            Liste des erreurs de validation (vide si valide)
        """
        errors = []
        
        def validate_recursive(current_data, current_schema, path=""):
            if not isinstance(current_schema, dict):
                return
            
            for key, expected_type in current_schema.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(expected_type, dict):
                    # Validation récursive pour les sous-sections
                    if key in current_data:
                        if isinstance(current_data[key], dict):
                            validate_recursive(current_data[key], expected_type, current_path)
                        else:
                            errors.append(f"{current_path}: doit être un dictionnaire")
                    else:
                        errors.append(f"{current_path}: section manquante")
                
                elif isinstance(expected_type, type):
                    # Validation de type simple
                    if key in current_data:
                        if not isinstance(current_data[key], expected_type):
                            errors.append(f"{current_path}: doit être de type {expected_type.__name__}")
                    else:
                        errors.append(f"{current_path}: champ manquant")
                
                elif isinstance(expected_type, list) and expected_type:
                    # Validation de liste avec type d'éléments
                    if key in current_data:
                        if isinstance(current_data[key], list):
                            element_type = expected_type[0]
                            for i, item in enumerate(current_data[key]):
                                if not isinstance(item, element_type):
                                    errors.append(f"{current_path}[{i}]: doit être de type {element_type.__name__}")
                        else:
                            errors.append(f"{current_path}: doit être une liste")
                    else:
                        errors.append(f"{current_path}: champ manquant")
        
        validate_recursive(data, schema)
        return errors
    
    @staticmethod
    def merge_toml_data(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fusionne deux dictionnaires TOML de manière récursive.
        
        Args:
            base: Données de base
            override: Données à fusionner
            
        Returns:
            Dictionnaire fusionné
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Fusion récursive pour les dictionnaires
                result[key] = TomlUtils.merge_toml_data(result[key], value)
            else:
                # Remplacement pour les autres types
                result[key] = value
        
        return result
    
    @staticmethod
    def extract_section(data: Dict[str, Any], section_path: str) -> Optional[Dict[str, Any]]:
        """
        Extrait une section d'un fichier TOML selon un chemin.
        
        Args:
            data: Données TOML
            section_path: Chemin de la section (ex: "tool.gestvenv")
            
        Returns:
            Section extraite ou None si introuvable
        """
        current = data
        
        for part in section_path.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current if isinstance(current, dict) else None
    
    @staticmethod
    def set_section(data: Dict[str, Any], section_path: str, value: Any) -> Dict[str, Any]:
        """
        Définit une section dans un fichier TOML selon un chemin.
        
        Args:
            data: Données TOML
            section_path: Chemin de la section (ex: "tool.gestvenv")
            value: Valeur à définir
            
        Returns:
            Données modifiées
        """
        result = data.copy()
        current = result
        parts = section_path.split('.')
        
        # Créer les sections intermédiaires si nécessaire
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        
        # Définir la valeur finale
        current[parts[-1]] = value
        
        return result

# Fonctions utilitaires pour compatibilité
def load_toml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Fonction utilitaire pour charger un fichier TOML."""
    return TomlUtils.load_toml(file_path)

def save_toml(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """Fonction utilitaire pour sauvegarder un fichier TOML."""
    return TomlUtils.save_toml(data, file_path)

def validate_toml_structure(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Fonction utilitaire pour valider une structure TOML."""
    return TomlUtils.validate_toml_structure(data, schema)
