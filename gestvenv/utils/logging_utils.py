"""
Utilitaires de logging pour GestVenv.

Ce module fournit des fonctions et classes pour gérer les logs de GestVenv,
incluant la configuration des loggers, la rotation des fichiers et le formatage.
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, TextIO
from enum import Enum

class LogLevel(Enum):
    """Niveaux de log personnalisés pour GestVenv."""
    TRACE = 5
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

class LogCategory(Enum):
    """Catégories de logs pour GestVenv."""
    GENERAL = "general"
    ENVIRONMENT = "environment"
    PACKAGE = "package"
    CACHE = "cache"
    DIAGNOSTIC = "diagnostic"
    SYSTEM = "system"
    CLI = "cli"

class ColoredFormatter(logging.Formatter):
    """Formateur de logs avec couleurs pour le terminal."""
    
    # Codes couleur ANSI
    COLORS = {
        'TRACE': '\033[36m',      # Cyan
        'DEBUG': '\033[34m',      # Bleu
        'INFO': '\033[32m',       # Vert
        'WARNING': '\033[33m',    # Jaune
        'ERROR': '\033[31m',      # Rouge
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, 
                 use_colors: bool = True):
        """
        Initialise le formateur coloré.
        
        Args:
            fmt: Format des messages.
            datefmt: Format des dates.
            use_colors: Si True, utilise les couleurs dans le terminal.
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and self._supports_color()
    
    def _supports_color(self) -> bool:
        """Vérifie si le terminal supporte les couleurs."""
        return (
            hasattr(sys.stderr, "isatty") and sys.stderr.isatty() and
            os.environ.get("TERM") != "dumb" and
            os.name != "nt"  # Désactivé sur Windows par défaut
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Formate un enregistrement de log avec couleurs."""
        if self.use_colors and record.levelname in self.COLORS:
            # Ajouter la couleur au nom du niveau
            colored_levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            )
            # Sauvegarder l'original
            original_levelname = record.levelname
            record.levelname = colored_levelname
            
            # Formater avec couleur
            formatted = super().format(record)
            
            # Restaurer l'original
            record.levelname = original_levelname
            
            return formatted
        
        return super().format(record)

class StructuredFormatter(logging.Formatter):
    """Formateur de logs structuré (JSON)."""
    
    def __init__(self, include_extra: bool = True):
        """
        Initialise le formateur structuré.
        
        Args:
            include_extra: Si True, inclut les champs supplémentaires.
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Formate un enregistrement en JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Ajouter les champs supplémentaires si disponibles
        if self.include_extra:
            extra_fields = [
                'environment', 'category', 'operation', 'duration',
                'package_name', 'cache_hit', 'error_type'
            ]
            
            for field in extra_fields:
                if hasattr(record, field):
                    log_data[field] = getattr(record, field)
        
        # Ajouter les informations d'exception si présentes
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)

class GestVenvLogManager:
    """Gestionnaire principal des logs pour GestVenv."""
    
    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialise le gestionnaire de logs.
        
        Args:
            logs_dir: Répertoire des logs. Si None, utilise le répertoire par défaut.
        """
        if logs_dir is None:
            from .path_utils import get_default_data_dir
            self.logs_dir = get_default_data_dir() / "logs"
        else:
            self.logs_dir = Path(logs_dir)
        
        # Créer le répertoire des logs
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration par défaut
        self.default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.date_format = "%Y-%m-%d %H:%M:%S"
        
        # Loggers configurés
        self._configured_loggers: Dict[str, logging.Logger] = {}
        
        # Ajouter le niveau TRACE personnalisé
        logging.addLevelName(LogLevel.TRACE.value, "TRACE")
    
    def get_logger(self, name: str, category: LogCategory = LogCategory.GENERAL,
                   level: LogLevel = LogLevel.INFO, 
                   console_output: bool = True,
                   file_output: bool = True,
                   structured_format: bool = False) -> logging.Logger:
        """
        Obtient ou crée un logger configuré.
        
        Args:
            name: Nom du logger.
            category: Catégorie du logger.
            level: Niveau de log minimum.
            console_output: Si True, active la sortie console.
            file_output: Si True, active la sortie fichier.
            structured_format: Si True, utilise le format JSON.
            
        Returns:
            Logger configuré.
        """
        logger_key = f"{name}_{category.value}"
        
        if logger_key in self._configured_loggers:
            return self._configured_loggers[logger_key]
        
        # Créer le logger
        logger = logging.getLogger(logger_key)
        logger.setLevel(level.value)
        
        # Nettoyer les handlers existants
        logger.handlers.clear()
        
        # Ajouter un handler console si demandé
        if console_output:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(level.value)
            
            if structured_format:
                console_formatter = StructuredFormatter()
            else:
                console_formatter = ColoredFormatter(
                    fmt=self.default_format,
                    datefmt=self.date_format
                )
            
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # Ajouter un handler fichier si demandé
        if file_output:
            log_file = self.logs_dir / f"{category.value}.log"
            
            # Utiliser un RotatingFileHandler pour la rotation automatique
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(level.value)
            
            if structured_format:
                file_formatter = StructuredFormatter()
            else:
                file_formatter = logging.Formatter(
                    fmt=self.default_format,
                    datefmt=self.date_format
                )
            
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        # Éviter la propagation vers le logger racine
        logger.propagate = False
        
        # Sauvegarder le logger configuré
        self._configured_loggers[logger_key] = logger
        
        return logger
    
    def setup_default_logging(self, debug: bool = False, 
                            structured: bool = False,
                            quiet: bool = False) -> None:
        """
        Configure le logging par défaut pour GestVenv.
        
        Args:
            debug: Si True, active le niveau DEBUG.
            structured: Si True, utilise le format JSON.
            quiet: Si True, réduit la verbosité console.
        """
        # Déterminer le niveau de log
        level = LogLevel.DEBUG if debug else LogLevel.INFO
        console_level = LogLevel.WARNING if quiet else level
        
        # Configurer les loggers par catégorie
        categories = [
            LogCategory.GENERAL,
            LogCategory.ENVIRONMENT,
            LogCategory.PACKAGE,
            LogCategory.CACHE,
            LogCategory.DIAGNOSTIC,
            LogCategory.SYSTEM,
            LogCategory.CLI
        ]
        
        for category in categories:
            logger = self.get_logger(
                name="gestvenv",
                category=category,
                level=level,
                console_output=not quiet,
                file_output=True,
                structured_format=structured
            )
            
            # Ajuster le niveau console si nécessaire
            if not quiet and console_level != level:
                for handler in logger.handlers:
                    if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                        handler.setLevel(console_level.value)
    
    def log_operation(self, logger: logging.Logger, operation: str, 
                     environment: Optional[str] = None,
                     duration: Optional[float] = None,
                     success: bool = True,
                     details: Optional[Dict[str, Any]] = None) -> None:
        """
        Enregistre une opération avec contexte.
        
        Args:
            logger: Logger à utiliser.
            operation: Nom de l'opération.
            environment: Nom de l'environnement (optionnel).
            duration: Durée de l'opération en secondes.
            success: Si True, opération réussie.
            details: Détails supplémentaires.
        """
        level = logging.INFO if success else logging.ERROR
        
        # Préparer le message
        message_parts = [f"Operation: {operation}"]
        
        if environment:
            message_parts.append(f"Environment: {environment}")
        
        if duration is not None:
            message_parts.append(f"Duration: {duration:.3f}s")
        
        if details:
            for key, value in details.items():
                message_parts.append(f"{key}: {value}")
        
        message = " | ".join(message_parts)
        
        # Créer l'enregistrement avec des champs supplémentaires
        extra = {
            'operation': operation,
            'environment': environment,
            'duration': duration,
            'success': success
        }
        
        if details:
            extra.update(details)
        
        logger.log(level, message, extra=extra)
    
    def log_package_operation(self, logger: logging.Logger, operation: str,
                            package_name: str, version: Optional[str] = None,
                            environment: Optional[str] = None,
                            success: bool = True,
                            cache_hit: bool = False) -> None:
        """
        Enregistre une opération sur un package.
        
        Args:
            logger: Logger à utiliser.
            operation: Type d'opération (install, uninstall, update).
            package_name: Nom du package.
            version: Version du package.
            environment: Nom de l'environnement.
            success: Si True, opération réussie.
            cache_hit: Si True, package trouvé dans le cache.
        """
        level = logging.INFO if success else logging.ERROR
        
        # Préparer le message
        message = f"Package {operation}: {package_name}"
        if version:
            message += f"=={version}"
        
        # Créer l'enregistrement avec des champs supplémentaires
        extra = {
            'operation': f"package_{operation}",
            'package_name': package_name,
            'package_version': version,
            'environment': environment,
            'success': success,
            'cache_hit': cache_hit
        }
        
        logger.log(level, message, extra=extra)
    
    def log_error(self, logger: logging.Logger, error: Exception,
                 operation: Optional[str] = None,
                 environment: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None) -> None:
        """
        Enregistre une erreur avec contexte complet.
        
        Args:
            logger: Logger à utiliser.
            error: Exception à enregistrer.
            operation: Opération en cours lors de l'erreur.
            environment: Environnement concerné.
            context: Contexte supplémentaire.
        """
        # Préparer le message
        message = f"Error: {str(error)}"
        if operation:
            message = f"Error in {operation}: {str(error)}"
        
        # Créer l'enregistrement avec des champs supplémentaires
        extra = {
            'error_type': type(error).__name__,
            'operation': operation,
            'environment': environment
        }
        
        if context:
            extra.update(context)
        
        logger.error(message, exc_info=True, extra=extra)
    
    def get_log_files(self, category: Optional[LogCategory] = None,
                     days: int = 30) -> List[Dict[str, Any]]:
        """
        Récupère la liste des fichiers de log.
        
        Args:
            category: Catégorie de logs (optionnel).
            days: Nombre de jours à inclure.
            
        Returns:
            Liste des fichiers de log avec leurs métadonnées.
        """
        files = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            pattern = f"{category.value}.log*" if category else "*.log*"
            
            for log_file in self.logs_dir.glob(pattern):
                if not log_file.is_file():
                    continue
                
                try:
                    stat = log_file.stat()
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    if modified_time < cutoff_date:
                        continue
                    
                    files.append({
                        "path": str(log_file),
                        "name": log_file.name,
                        "size": stat.st_size,
                        "modified": modified_time.isoformat(),
                        "category": self._extract_category_from_filename(log_file.name)
                    })
                    
                except (OSError, ValueError):
                    continue
            
            # Trier par date de modification (plus récent en premier)
            files.sort(key=lambda x: x["modified"], reverse=True)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de la récupération des fichiers de log: {str(e)}")
        
        return files
    
    def _extract_category_from_filename(self, filename: str) -> Optional[str]:
        """Extrait la catégorie depuis le nom de fichier."""
        for category in LogCategory:
            if filename.startswith(category.value):
                return category.value
        return None
    
    def read_log_entries(self, category: LogCategory, 
                        lines: int = 100,
                        filter_level: Optional[LogLevel] = None,
                        filter_environment: Optional[str] = None,
                        structured: bool = False) -> List[Dict[str, Any]]:
        """
        Lit les entrées de log d'un fichier.
        
        Args:
            category: Catégorie de logs à lire.
            lines: Nombre maximum de lignes à lire.
            filter_level: Niveau de log minimum (optionnel).
            filter_environment: Environnement à filtrer (optionnel).
            structured: Si True, parse les logs JSON.
            
        Returns:
            Liste des entrées de log.
        """
        log_file = self.logs_dir / f"{category.value}.log"
        entries = []
        
        if not log_file.exists():
            return entries
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # Lire les dernières lignes
                file_lines = f.readlines()
                recent_lines = file_lines[-lines:] if len(file_lines) > lines else file_lines
                
                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        if structured:
                            # Parser JSON
                            entry = json.loads(line)
                        else:
                            # Parser format texte
                            entry = self._parse_text_log_line(line)
                        
                        # Appliquer les filtres
                        if filter_level and self._get_level_value(entry.get("level", "INFO")) < filter_level.value:
                            continue
                        
                        if filter_environment and entry.get("environment") != filter_environment:
                            continue
                        
                        entries.append(entry)
                        
                    except Exception:
                        # Ignorer les lignes mal formatées
                        continue
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de la lecture du fichier de log: {str(e)}")
        
        return entries
    
    def _parse_text_log_line(self, line: str) -> Dict[str, Any]:
        """Parse une ligne de log au format texte."""
        parts = line.split(" - ", 3)
        
        if len(parts) >= 4:
            return {
                "timestamp": parts[0],
                "logger": parts[1],
                "level": parts[2],
                "message": parts[3]
            }
        else:
            return {
                "timestamp": datetime.now().isoformat(),
                "logger": "unknown",
                "level": "INFO",
                "message": line
            }
    
    def _get_level_value(self, level_name: str) -> int:
        """Convertit un nom de niveau en valeur numérique."""
        level_map = {
            "TRACE": LogLevel.TRACE.value,
            "DEBUG": LogLevel.DEBUG.value,
            "INFO": LogLevel.INFO.value,
            "WARNING": LogLevel.WARNING.value,
            "ERROR": LogLevel.ERROR.value,
            "CRITICAL": LogLevel.CRITICAL.value
        }
        return level_map.get(level_name.upper(), LogLevel.INFO.value)
    
    def export_logs(self, output_path: str, category: Optional[LogCategory] = None,
                   days: int = 7, format_type: str = "json") -> bool:
        """
        Exporte les logs vers un fichier.
        
        Args:
            output_path: Chemin du fichier de sortie.
            category: Catégorie à exporter (optionnel, toutes si None).
            days: Nombre de jours à inclure.
            format_type: Format d'export ('json' ou 'text').
            
        Returns:
            True si l'export réussit, False sinon.
        """
        try:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "days_included": days,
                "format": format_type,
                "categories": {}
            }
            
            # Déterminer les catégories à exporter
            categories = [category] if category else list(LogCategory)
            
            for cat in categories:
                entries = self.read_log_entries(cat, lines=10000, structured=False)
                
                # Filtrer par date
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_entries = []
                
                for entry in entries:
                    try:
                        entry_time = datetime.fromisoformat(entry["timestamp"])
                        if entry_time >= cutoff_date:
                            filtered_entries.append(entry)
                    except Exception:
                        # Inclure les entrées sans timestamp valide
                        filtered_entries.append(entry)
                
                export_data["categories"][cat.value] = {
                    "total_entries": len(filtered_entries),
                    "entries": filtered_entries
                }
            
            # Écrire le fichier d'export
            with open(output_path, 'w', encoding='utf-8') as f:
                if format_type == "json":
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    # Format texte
                    f.write(f"GestVenv Logs Export - {export_data['exported_at']}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for cat_name, cat_data in export_data["categories"].items():
                        f.write(f"Category: {cat_name.upper()}\n")
                        f.write("-" * 30 + "\n")
                        
                        for entry in cat_data["entries"]:
                            f.write(f"{entry['timestamp']} - {entry['level']} - {entry['message']}\n")
                        
                        f.write("\n")
            
            return True
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de l'export des logs: {str(e)}")
            return False
    
    def clean_old_logs(self, days: int = 30) -> Tuple[int, int]:
        """
        Nettoie les anciens fichiers de log.
        
        Args:
            days: Âge maximum des logs à conserver.
            
        Returns:
            Tuple contenant (nombre de fichiers supprimés, espace libéré en octets).
        """
        deleted_count = 0
        freed_space = 0
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Nettoyer les fichiers de log rotatés (.log.1, .log.2, etc.)
            for log_file in self.logs_dir.glob("*.log.*"):
                if not log_file.is_file():
                    continue
                
                try:
                    stat = log_file.stat()
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    if modified_time < cutoff_date:
                        freed_space += stat.st_size
                        log_file.unlink()
                        deleted_count += 1
                        
                except (OSError, ValueError):
                    continue
            
            # Nettoyer les lignes anciennes des fichiers de log actifs
            for category in LogCategory:
                log_file = self.logs_dir / f"{category.value}.log"
                if log_file.exists():
                    self._clean_log_file_content(log_file, cutoff_date)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors du nettoyage des logs: {str(e)}")
        
        return deleted_count, freed_space
    
    def _clean_log_file_content(self, log_file: Path, cutoff_date: datetime) -> None:
        """Nettoie le contenu d'un fichier de log en supprimant les anciennes entrées."""
        try:
            temp_file = log_file.with_suffix('.tmp')
            lines_kept = 0
            
            with open(log_file, 'r', encoding='utf-8') as infile, \
                 open(temp_file, 'w', encoding='utf-8') as outfile:
                
                for line in infile:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Essayer d'extraire la date de la ligne
                    try:
                        # Format standard: YYYY-MM-DD HH:MM:SS
                        if len(line) >= 19:
                            date_str = line[:19]
                            log_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            
                            if log_date >= cutoff_date:
                                outfile.write(line + '\n')
                                lines_kept += 1
                        else:
                            # Conserver les lignes sans date valide
                            outfile.write(line + '\n')
                            lines_kept += 1
                            
                    except ValueError:
                        # Conserver les lignes avec format de date non standard
                        outfile.write(line + '\n')
                        lines_kept += 1
            
            # Remplacer le fichier original si des lignes ont été conservées
            if lines_kept > 0:
                temp_file.replace(log_file)
            else:
                # Supprimer le fichier temporaire et vider le fichier original
                temp_file.unlink()
                log_file.write_text('', encoding='utf-8')
                
        except Exception as e:
            # Nettoyer le fichier temporaire en cas d'erreur
            if temp_file.exists():
                temp_file.unlink()
            raise e
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Récupère des statistiques sur les logs.
        
        Returns:
            Dictionnaire de statistiques.
        """
        stats = {
            "total_files": 0,
            "total_size": 0,
            "categories": {},
            "oldest_entry": None,
            "newest_entry": None,
            "error_count_today": 0,
            "warning_count_today": 0
        }
        
        try:
            today = datetime.now().date()
            
            for log_file in self.logs_dir.glob("*.log*"):
                if not log_file.is_file():
                    continue
                
                stats["total_files"] += 1
                file_size = log_file.stat().st_size
                stats["total_size"] += file_size
                
                # Extraire la catégorie
                category = self._extract_category_from_filename(log_file.name)
                if category:
                    if category not in stats["categories"]:
                        stats["categories"][category] = {
                            "files": 0,
                            "size": 0,
                            "entries_today": 0
                        }
                    
                    stats["categories"][category]["files"] += 1
                    stats["categories"][category]["size"] += file_size
                    
                    # Compter les entrées d'aujourd'hui
                    if log_file.name.endswith(".log"):  # Fichier principal
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    if line.strip():
                                        try:
                                            if line[:10] == today.strftime("%Y-%m-%d"):
                                                stats["categories"][category]["entries_today"] += 1
                                                
                                                # Compter les erreurs et avertissements
                                                if "ERROR" in line:
                                                    stats["error_count_today"] += 1
                                                elif "WARNING" in line:
                                                    stats["warning_count_today"] += 1
                                        except (ValueError, IndexError):
                                            pass
                        except Exception:
                            pass
            
            # Convertir la taille totale en format lisible
            stats["total_size_mb"] = stats["total_size"] / (1024 * 1024)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
        
        return stats

# Instance globale du gestionnaire de logs
_log_manager: Optional[GestVenvLogManager] = None

def get_log_manager() -> GestVenvLogManager:
    """Récupère l'instance globale du gestionnaire de logs."""
    global _log_manager
    if _log_manager is None:
        _log_manager = GestVenvLogManager()
    return _log_manager

def setup_logging(debug: bool = False, structured: bool = False, 
                 quiet: bool = False, logs_dir: Optional[Path] = None) -> None:
    """
    Configure le logging global pour GestVenv.
    
    Args:
        debug: Si True, active le niveau DEBUG.
        structured: Si True, utilise le format JSON.
        quiet: Si True, réduit la verbosité console.
        logs_dir: Répertoire des logs personnalisé.
    """
    global _log_manager
    _log_manager = GestVenvLogManager(logs_dir)
    _log_manager.setup_default_logging(debug, structured, quiet)

def get_logger(name: str, category: LogCategory = LogCategory.GENERAL) -> logging.Logger:
    """
    Raccourci pour obtenir un logger configuré.
    
    Args:
        name: Nom du logger.
        category: Catégorie du logger.
        
    Returns:
        Logger configuré.
    """
    return get_log_manager().get_logger(name, category)

def log_operation(operation: str, environment: Optional[str] = None,
                 duration: Optional[float] = None, success: bool = True,
                 category: LogCategory = LogCategory.GENERAL,
                 details: Optional[Dict[str, Any]] = None) -> None:
    """
    Raccourci pour enregistrer une opération.
    
    Args:
        operation: Nom de l'opération.
        environment: Nom de l'environnement.
        duration: Durée de l'opération.
        success: Si True, opération réussie.
        category: Catégorie de log.
        details: Détails supplémentaires.
    """
    logger = get_logger("gestvenv", category)
    get_log_manager().log_operation(logger, operation, environment, duration, success, details)

def log_package_operation(operation: str, package_name: str, 
                         version: Optional[str] = None,
                         environment: Optional[str] = None,
                         success: bool = True, cache_hit: bool = False) -> None:
    """
    Raccourci pour enregistrer une opération sur un package.
    
    Args:
        operation: Type d'opération.
        package_name: Nom du package.
        version: Version du package.
        environment: Nom de l'environnement.
        success: Si True, opération réussie.
        cache_hit: Si True, package trouvé dans le cache.
    """
    logger = get_logger("gestvenv", LogCategory.PACKAGE)
    get_log_manager().log_package_operation(
        logger, operation, package_name, version, environment, success, cache_hit
    )

def log_error(error: Exception, operation: Optional[str] = None,
             environment: Optional[str] = None,
             category: LogCategory = LogCategory.GENERAL,
             context: Optional[Dict[str, Any]] = None) -> None:
    """
    Raccourci pour enregistrer une erreur.
    
    Args:
        error: Exception à enregistrer.
        operation: Opération en cours.
        environment: Environnement concerné.
        category: Catégorie de log.
        context: Contexte supplémentaire.
    """
    logger = get_logger("gestvenv", category)
    get_log_manager().log_error(logger, error, operation, environment, context)

# Utilitaires de contexte pour le logging automatique
class LoggedOperation:
    """Gestionnaire de contexte pour le logging automatique d'opérations."""
    
    def __init__(self, operation: str, environment: Optional[str] = None,
                 category: LogCategory = LogCategory.GENERAL,
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialise l'opération loggée.
        
        Args:
            operation: Nom de l'opération.
            environment: Nom de l'environnement.
            category: Catégorie de log.
            details: Détails supplémentaires.
        """
        self.operation = operation
        self.environment = environment
        self.category = category
        self.details = details or {}
        self.start_time = None
        self.success = True
        self.logger = get_logger("gestvenv", category)
    
    def __enter__(self):
        """Démarre l'opération."""
        self.start_time = datetime.now()
        self.logger.info(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Termine l'opération et enregistre le résultat."""
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else None
        
        if exc_type is not None:
            self.success = False
            get_log_manager().log_error(self.logger, exc_val, self.operation, self.environment)
        
        get_log_manager().log_operation(
            self.logger, self.operation, self.environment, duration, self.success, self.details
        )
        
        return False  # Ne pas supprimer l'exception