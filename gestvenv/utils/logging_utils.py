"""
Système de logging centralisé pour GestVenv v1.1.
Configuration avancée avec support multi-niveaux, rotation, couleurs.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Optional, Union, Any, List
from datetime import datetime
from dataclasses import dataclass
import threading
from contextlib import contextmanager

# Import des couleurs depuis format_utils
from .format_utils import Colors

@dataclass
class LogConfig:
    """Configuration du système de logging."""
    level: str = "INFO"
    format_console: str = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    format_file: str = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(filename)s:%(lineno)d | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_dir: Optional[Path] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_colors: bool = True
    enable_file_logging: bool = True
    enable_console_logging: bool = True
    modules_config: Dict[str, str] = None

class ColoredFormatter(logging.Formatter):
    """Formateur avec support des couleurs pour le terminal."""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BRIGHT_BLACK,
        logging.INFO: Colors.BRIGHT_BLUE,
        logging.WARNING: Colors.BRIGHT_YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.BRIGHT_MAGENTA + Colors.BOLD,
    }
    
    def __init__(self, fmt: str, datefmt: str = None, enable_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.enable_colors = enable_colors and self._supports_color()
    
    def _supports_color(self) -> bool:
        """Vérifie si le terminal supporte les couleurs."""
        if not hasattr(sys.stderr, "isatty"):
            return False
        if not sys.stderr.isatty():
            return False
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("TERM") == "dumb":
            return False
        return True
    
    def format(self, record: logging.LogRecord) -> str:
        """Formate un enregistrement de log avec couleurs."""
        if not self.enable_colors:
            return super().format(record)
        
        # Sauvegarder le message original
        original_msg = record.getMessage()
        
        # Obtenir la couleur pour le niveau
        level_color = self.LEVEL_COLORS.get(record.levelno, "")
        
        # Coloriser le niveau
        if level_color:
            record.levelname = f"{level_color}{record.levelname}{Colors.RESET}"
        
        # Coloriser le nom du module
        if record.name:
            record.name = f"{Colors.CYAN}{record.name}{Colors.RESET}"
        
        # Coloriser le message selon le niveau
        if record.levelno >= logging.ERROR:
            record.msg = f"{Colors.BRIGHT_RED}{record.msg}{Colors.RESET}"
        elif record.levelno >= logging.WARNING:
            record.msg = f"{Colors.BRIGHT_YELLOW}{record.msg}{Colors.RESET}"
        
        # Formater
        formatted = super().format(record)
        
        # Restaurer le message original
        record.msg = original_msg
        
        return formatted

class ThreadSafeLogger:
    """Logger thread-safe avec cache des instances."""
    
    _loggers: Dict[str, logging.Logger] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Récupère un logger thread-safe."""
        if name not in cls._loggers:
            with cls._lock:
                if name not in cls._loggers:
                    cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]

class LoggingUtils:
    """Utilitaires de logging centralisés pour GestVenv."""
    
    _initialized = False
    _config: Optional[LogConfig] = None
    _log_dir: Optional[Path] = None
    
    @staticmethod
    def setup_logging(config: Optional[LogConfig] = None, 
                     log_dir: Optional[Union[str, Path]] = None,
                     verbosity: int = 0) -> None:
        """
        Configure le système de logging global.
        
        Args:
            config: Configuration personnalisée
            log_dir: Répertoire des logs
            verbosity: Niveau de verbosité (0=INFO, 1=DEBUG, 2=TRACE)
        """
        if LoggingUtils._initialized:
            return
        
        # Configuration par défaut ou personnalisée
        if config is None:
            config = LogConfig()
        
        # Déterminer le niveau selon la verbosité
        level_map = {0: "INFO", 1: "DEBUG", 2: "DEBUG"}
        if verbosity in level_map:
            config.level = level_map[verbosity]
        
        # Configurer le répertoire de logs
        if log_dir:
            config.log_dir = Path(log_dir)
        elif config.log_dir is None:
            config.log_dir = LoggingUtils._get_default_log_dir()
        
        # Créer le répertoire de logs
        if config.enable_file_logging and config.log_dir:
            config.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder la configuration
        LoggingUtils._config = config
        LoggingUtils._log_dir = config.log_dir
        
        # Configuration du logger racine
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.level.upper()))
        
        # Nettoyer les handlers existants
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Handler console
        if config.enable_console_logging:
            console_handler = logging.StreamHandler(sys.stderr)
            console_formatter = ColoredFormatter(
                config.format_console,
                config.date_format,
                config.enable_colors
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(getattr(logging, config.level.upper()))
            root_logger.addHandler(console_handler)
        
        # Handler fichier avec rotation
        if config.enable_file_logging and config.log_dir:
            log_file = config.log_dir / "gestvenv.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=config.max_file_size,
                backupCount=config.backup_count,
                encoding='utf-8'
            )
            file_formatter = logging.Formatter(
                config.format_file,
                config.date_format
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)  # Fichier = toujours DEBUG
            root_logger.addHandler(file_handler)
        
        # Configuration des modules spécifiques
        LoggingUtils._configure_module_loggers(config)
        
        # Log d'initialisation
        logger = LoggingUtils.get_logger("gestvenv.logging")
        logger.info(f"Système de logging initialisé - Niveau: {config.level}")
        if config.log_dir:
            logger.debug(f"Répertoire de logs: {config.log_dir}")
        
        LoggingUtils._initialized = True
    
    @staticmethod
    def _get_default_log_dir() -> Path:
        """Détermine le répertoire de logs par défaut."""
        if os.name == 'nt':  # Windows
            base = Path(os.environ.get('APPDATA', '')) / 'GestVenv' / 'logs'
        elif sys.platform == 'darwin':  # macOS
            base = Path.home() / 'Library' / 'Logs' / 'GestVenv'
        else:  # Linux et autres Unix
            xdg_state = os.environ.get('XDG_STATE_HOME')
            if xdg_state:
                base = Path(xdg_state) / 'gestvenv' / 'logs'
            else:
                base = Path.home() / '.local' / 'state' / 'gestvenv' / 'logs'
        
        return base
    
    @staticmethod
    def _configure_module_loggers(config: LogConfig) -> None:
        """Configure les loggers spécifiques aux modules."""
        # Configuration par défaut des modules
        default_modules = {
            'gestvenv.core': 'INFO',
            'gestvenv.services': 'INFO', 
            'gestvenv.backends': 'INFO',
            'gestvenv.utils': 'INFO',
            'gestvenv.cli': 'INFO',
            'urllib3': 'WARNING',  # Réduire le bruit des requêtes HTTP
            'requests': 'WARNING',
            'pip': 'WARNING'
        }
        
        # Fusionner avec la configuration personnalisée
        modules_config = default_modules.copy()
        if config.modules_config:
            modules_config.update(config.modules_config)
        
        # Appliquer la configuration
        for module_name, level_str in modules_config.items():
            logger = logging.getLogger(module_name)
            logger.setLevel(getattr(logging, level_str.upper()))
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Récupère un logger configuré pour un module.
        
        Args:
            name: Nom du module/logger
            
        Returns:
            Logger configuré
        """
        return ThreadSafeLogger.get_logger(name)
    
    @staticmethod
    def set_level(level: Union[str, int], module: Optional[str] = None) -> None:
        """
        Modifie le niveau de logging.
        
        Args:
            level: Nouveau niveau (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            module: Module spécifique ou None pour le logger racine
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        
        if module:
            logger = logging.getLogger(module)
            logger.setLevel(level)
        else:
            # Logger racine et tous ses handlers
            root_logger = logging.getLogger()
            root_logger.setLevel(level)
            for handler in root_logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
                    handler.setLevel(level)
    
    @staticmethod
    def add_file_handler(log_file: Union[str, Path], 
                        level: str = "DEBUG",
                        format_str: Optional[str] = None) -> None:
        """
        Ajoute un handler de fichier supplémentaire.
        
        Args:
            log_file: Chemin du fichier de log
            level: Niveau du handler
            format_str: Format personnalisé
        """
        if not LoggingUtils._config:
            raise RuntimeError("Le système de logging n'est pas initialisé")
        
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Créer le handler
        handler = logging.FileHandler(log_path, encoding='utf-8')
        handler.setLevel(getattr(logging, level.upper()))
        
        # Format
        if format_str is None:
            format_str = LoggingUtils._config.format_file
        
        formatter = logging.Formatter(format_str, LoggingUtils._config.date_format)
        handler.setFormatter(formatter)
        
        # Ajouter au logger racine
        logging.getLogger().addHandler(handler)
    
    @staticmethod
    def get_log_files() -> List[Path]:
        """
        Retourne la liste des fichiers de logs.
        
        Returns:
            Liste des chemins des fichiers de logs
        """
        if not LoggingUtils._log_dir or not LoggingUtils._log_dir.exists():
            return []
        
        log_files = []
        for file_path in LoggingUtils._log_dir.iterdir():
            if file_path.is_file() and file_path.suffix == '.log':
                log_files.append(file_path)
        
        return sorted(log_files, key=lambda p: p.stat().st_mtime, reverse=True)
    
    @staticmethod
    def cleanup_old_logs(days: int = 30) -> int:
        """
        Supprime les anciens fichiers de logs.
        
        Args:
            days: Âge maximum des logs en jours
            
        Returns:
            Nombre de fichiers supprimés
        """
        if not LoggingUtils._log_dir or not LoggingUtils._log_dir.exists():
            return 0
        
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        deleted_count = 0
        
        for log_file in LoggingUtils.get_log_files():
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
            except OSError:
                continue
        
        if deleted_count > 0:
            logger = LoggingUtils.get_logger("gestvenv.logging")
            logger.info(f"Suppression de {deleted_count} anciens fichiers de logs")
        
        return deleted_count
    
    @staticmethod
    @contextmanager
    def temporary_level(level: Union[str, int], module: Optional[str] = None):
        """
        Gestionnaire de contexte pour modifier temporairement le niveau de logging.
        
        Args:
            level: Niveau temporaire
            module: Module spécifique ou None pour le logger racine
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        
        # Sauvegarder le niveau actuel
        if module:
            logger = logging.getLogger(module)
            old_level = logger.level
        else:
            logger = logging.getLogger()
            old_level = logger.level
        
        try:
            # Appliquer le nouveau niveau
            logger.setLevel(level)
            yield
        finally:
            # Restaurer l'ancien niveau
            logger.setLevel(old_level)
    
    @staticmethod
    def log_performance(operation: str, duration: float, 
                       threshold: float = 1.0, logger_name: str = "gestvenv.performance") -> None:
        """
        Log les performances d'une opération.
        
        Args:
            operation: Nom de l'opération
            duration: Durée en secondes
            threshold: Seuil pour warning
            logger_name: Nom du logger
        """
        logger = LoggingUtils.get_logger(logger_name)
        
        if duration > threshold:
            logger.warning(f"Opération lente: {operation} - {duration:.2f}s")
        else:
            logger.debug(f"Performance: {operation} - {duration:.2f}s")
    
    @staticmethod
    def log_memory_usage(operation: str, logger_name: str = "gestvenv.memory") -> None:
        """
        Log l'utilisation mémoire actuelle.
        
        Args:
            operation: Opération en cours
            logger_name: Nom du logger
        """
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            logger = LoggingUtils.get_logger(logger_name)
            logger.debug(f"Mémoire: {operation} - {memory_mb:.1f} MB")
        except ImportError:
            pass  # psutil non disponible
    
    @staticmethod
    def configure_development_logging() -> None:
        """Configure le logging pour le développement."""
        config = LogConfig(
            level="DEBUG",
            enable_colors=True,
            enable_file_logging=True,
            modules_config={
                'gestvenv': 'DEBUG',
                'urllib3': 'INFO',
                'requests': 'INFO'
            }
        )
        LoggingUtils.setup_logging(config, verbosity=1)
    
    @staticmethod
    def configure_production_logging(log_dir: Optional[Path] = None) -> None:
        """Configure le logging pour la production."""
        config = LogConfig(
            level="INFO",
            enable_colors=False,
            enable_file_logging=True,
            enable_console_logging=False,
            log_dir=log_dir
        )
        LoggingUtils.setup_logging(config, verbosity=0)
    
    @staticmethod
    def get_config() -> Optional[LogConfig]:
        """Retourne la configuration actuelle."""
        return LoggingUtils._config

# Fonctions utilitaires pour compatibilité
def setup_logging(verbosity: int = 0, log_dir: Optional[Union[str, Path]] = None) -> None:
    """Fonction utilitaire pour configurer le logging."""
    LoggingUtils.setup_logging(verbosity=verbosity, log_dir=log_dir)

def get_logger(name: str) -> logging.Logger:
    """Fonction utilitaire pour obtenir un logger."""
    return LoggingUtils.get_logger(name)

# Décorateur pour logging automatique
def log_calls(logger_name: Optional[str] = None, level: str = "DEBUG"):
    """
    Décorateur pour logger automatiquement les appels de fonction.
    
    Args:
        logger_name: Nom du logger (auto-détecté si None)
        level: Niveau de logging
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Déterminer le nom du logger
            if logger_name:
                logger = get_logger(logger_name)
            else:
                module_name = func.__module__
                logger = get_logger(module_name)
            
            # Logger l'entrée
            log_level = getattr(logging, level.upper())
            logger.log(log_level, f"Entrée: {func.__name__}(args={len(args)}, kwargs={list(kwargs.keys())})")
            
            try:
                # Exécuter la fonction
                start_time = datetime.now()
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                # Logger la sortie
                logger.log(log_level, f"Sortie: {func.__name__} - {duration:.3f}s")
                return result
                
            except Exception as e:
                # Logger l'erreur
                logger.error(f"Erreur dans {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator