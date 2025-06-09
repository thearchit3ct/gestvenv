"""
Gestionnaire TOML optimisé pour GestVenv v1.1

Utilise une approche hybride :
- tomllib (Python 3.11+) ou tomli pour la lecture
- tomlkit pour l'écriture avec préservation du formatage
- Fallback vers implémentation basique si nécessaire
"""

import sys
from pathlib import Path
from typing import Dict, Any, Union, TextIO
import logging

logger = logging.getLogger(__name__)

# Import conditionnel selon la version Python
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import tomlkit
    TOMLKIT_AVAILABLE = True
except ImportError:
    TOMLKIT_AVAILABLE = False
    tomlkit = None


class TomlHandler:
    """Gestionnaire TOML avec support optimisé lecture/écriture"""
    
    @staticmethod
    def load(path: Union[str, Path]) -> Dict[str, Any]:
        """Charge un fichier TOML"""
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Fichier TOML introuvable: {path}")
        
        try:
            return TomlHandler._load_with_tomllib(path)
        except Exception as e:
            logger.warning(f"Échec lecture avec tomllib: {e}")
            return TomlHandler._load_with_fallback(path)
    
    @staticmethod
    def loads(content: str) -> Dict[str, Any]:
        """Parse une chaîne TOML"""
        try:
            if tomllib:
                return tomllib.loads(content)
            else:
                return TomlHandler._parse_basic_toml(content)
        except Exception as e:
            logger.error(f"Erreur parsing TOML: {e}")
            raise ValueError(f"Contenu TOML invalide: {e}")
    
    @staticmethod
    def dump(data: Dict[str, Any], path: Union[str, Path]) -> None:
        """Sauvegarde données vers fichier TOML"""
        path = Path(path)
        
        try:
            if TOMLKIT_AVAILABLE:
                TomlHandler._dump_with_tomlkit(data, path)
            else:
                TomlHandler._dump_basic(data, path)
        except Exception as e:
            logger.error(f"Erreur sauvegarde TOML: {e}")
            raise
    
    @staticmethod
    def dumps(data: Dict[str, Any]) -> str:
        """Convertit données vers chaîne TOML"""
        try:
            if TOMLKIT_AVAILABLE:
                doc = tomlkit.document()
                TomlHandler._dict_to_tomlkit(data, doc)
                return doc.as_string()
            else:
                return TomlHandler._dump_basic_string(data)
        except Exception as e:
            logger.error(f"Erreur conversion TOML: {e}")
            raise ValueError(f"Impossible de convertir en TOML: {e}")
    
    # Méthodes privées
    
    @staticmethod
    def _load_with_tomllib(path: Path) -> Dict[str, Any]:
        """Lecture avec tomllib/tomli"""
        if not tomllib:
            raise ImportError("tomllib/tomli non disponible")
        
        with open(path, 'rb') as f:
            return tomllib.load(f)
    
    @staticmethod
    def _load_with_fallback(path: Path) -> Dict[str, Any]:
        """Lecture fallback basique"""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return TomlHandler._parse_basic_toml(content)
    
    @staticmethod
    def _dump_with_tomlkit(data: Dict[str, Any], path: Path) -> None:
        """Sauvegarde avec tomlkit (préserve formatage)"""
        doc = tomlkit.document()
        TomlHandler._dict_to_tomlkit(data, doc)
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(doc.as_string())
    
    @staticmethod
    def _dump_basic(data: Dict[str, Any], path: Path) -> None:
        """Sauvegarde basique sans tomlkit"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            TomlHandler._write_dict_as_toml(data, f, 0)
    
    @staticmethod
    def _dict_to_tomlkit(data: Dict[str, Any], container) -> None:
        """Convertit dict vers structure tomlkit"""
        for key, value in data.items():
            if isinstance(value, dict):
                table = tomlkit.table()
                TomlHandler._dict_to_tomlkit(value, table)
                container[key] = table
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # Array of tables
                    array = tomlkit.aot()
                    for item in value:
                        table = tomlkit.table()
                        TomlHandler._dict_to_tomlkit(item, table)
                        array.append(table)
                    container[key] = array
                else:
                    container[key] = value
            else:
                container[key] = value
    
    @staticmethod
    def _write_dict_as_toml(data: Dict[str, Any], f: TextIO, indent: int) -> None:
        """Écriture TOML basique"""
        indent_str = "  " * indent
        
        # Valeurs simples d'abord
        for key, value in data.items():
            if not isinstance(value, dict):
                if isinstance(value, str):
                    f.write(f'{indent_str}{key} = "{value}"\n')
                elif isinstance(value, bool):
                    f.write(f'{indent_str}{key} = {str(value).lower()}\n')
                elif isinstance(value, list):
                    if value and isinstance(value[0], str):
                        quoted_values = [f'"{v}"' for v in value]
                        f.write(f'{indent_str}{key} = [{", ".join(quoted_values)}]\n')
                    else:
                        f.write(f'{indent_str}{key} = {value}\n')
                else:
                    f.write(f'{indent_str}{key} = {value}\n')
        
        # Tables ensuite
        for key, value in data.items():
            if isinstance(value, dict):
                if indent == 0:
                    f.write(f'\n[{key}]\n')
                else:
                    f.write(f'\n[{".".join([""] * indent)}{key}]\n')
                TomlHandler._write_dict_as_toml(value, f, indent + 1)
    
    @staticmethod
    def _dump_basic_string(data: Dict[str, Any]) -> str:
        """Conversion basique vers string TOML"""
        lines = []
        
        # Valeurs simples
        for key, value in data.items():
            if not isinstance(value, dict):
                if isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                elif isinstance(value, bool):
                    lines.append(f'{key} = {str(value).lower()}')
                elif isinstance(value, list):
                    if value and isinstance(value[0], str):
                        quoted_values = [f'"{v}"' for v in value]
                        lines.append(f'{key} = [{", ".join(quoted_values)}]')
                    else:
                        lines.append(f'{key} = {value}')
                else:
                    lines.append(f'{key} = {value}')
        
        # Tables
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'\n[{key}]')
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, str):
                        lines.append(f'{subkey} = "{subvalue}"')
                    elif isinstance(subvalue, bool):
                        lines.append(f'{subkey} = {str(subvalue).lower()}')
                    else:
                        lines.append(f'{subkey} = {subvalue}')
        
        return '\n'.join(lines)
    
    @staticmethod
    def _parse_basic_toml(content: str) -> Dict[str, Any]:
        """Parser TOML basique (fallback)"""
        data = {}
        current_section = data
        section_path = []
        
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            
            # Ignorer commentaires et lignes vides
            if not line or line.startswith('#'):
                continue
            
            # Section [table]
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1].strip()
                section_path = section_name.split('.')
                
                # Créer la structure imbriquée
                current_section = data
                for part in section_path[:-1]:
                    if part not in current_section:
                        current_section[part] = {}
                    current_section = current_section[part]
                
                if section_path[-1] not in current_section:
                    current_section[section_path[-1]] = {}
                current_section = current_section[section_path[-1]]
                continue
            
            # Paires clé = valeur
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Parsing basique des valeurs
                if value.startswith('"') and value.endswith('"'):
                    # String
                    current_section[key] = value[1:-1]
                elif value.lower() in ('true', 'false'):
                    # Boolean
                    current_section[key] = value.lower() == 'true'
                elif value.startswith('[') and value.endswith(']'):
                    # Array
                    array_content = value[1:-1].strip()
                    if array_content:
                        items = [item.strip().strip('"') for item in array_content.split(',')]
                        current_section[key] = items
                    else:
                        current_section[key] = []
                elif value.isdigit():
                    # Integer
                    current_section[key] = int(value)
                elif '.' in value and value.replace('.', '').isdigit():
                    # Float
                    current_section[key] = float(value)
                else:
                    # String sans quotes
                    current_section[key] = value
        
        return data