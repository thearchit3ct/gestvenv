"""
Configuration du logging structuré pour GestVenv

Fournit un logging JSON structuré avec contexte automatique.
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from contextlib import contextmanager
from functools import wraps
import threading

# Stockage du contexte par thread
_context = threading.local()


def get_trace_id() -> str:
    """Récupère ou génère un trace ID"""
    if not hasattr(_context, 'trace_id') or _context.trace_id is None:
        _context.trace_id = str(uuid.uuid4())[:8]
    return _context.trace_id


def set_trace_id(trace_id: str):
    """Définit le trace ID"""
    _context.trace_id = trace_id


def clear_trace_id():
    """Efface le trace ID"""
    _context.trace_id = None


class StructuredFormatter(logging.Formatter):
    """Formatter JSON structuré"""

    def __init__(self, include_timestamp: bool = True, include_trace: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_trace = include_trace

    def format(self, record: logging.LogRecord) -> str:
        """Formate le record en JSON"""
        log_data = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        if self.include_trace:
            log_data["trace_id"] = get_trace_id()

        # Ajouter la localisation
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName
        }

        # Ajouter les extras s'il y en a
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Ajouter l'exception si présente
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None
            }

        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Formatter avec couleurs pour le terminal"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime('%H:%M:%S')
        trace_id = get_trace_id()

        # Format: [HH:MM:SS] [LEVEL] [trace_id] message
        prefix = f"{color}[{timestamp}] [{record.levelname:<8}]{self.RESET}"
        if trace_id:
            prefix += f" [{trace_id}]"

        message = record.getMessage()

        # Ajouter les extras s'il y en a
        if hasattr(record, 'extra_data') and record.extra_data:
            extras = " ".join(f"{k}={v}" for k, v in record.extra_data.items())
            message += f" | {extras}"

        return f"{prefix} {message}"


class StructuredLogger(logging.Logger):
    """Logger avec support pour données structurées"""

    def _log_with_extra(self, level: int, msg: str, extra_data: Optional[Dict] = None,
                        *args, **kwargs):
        """Log avec données supplémentaires"""
        if extra_data:
            # Créer un record avec extra_data
            extra = kwargs.get('extra', {})
            extra['extra_data'] = extra_data
            kwargs['extra'] = extra
        super().log(level, msg, *args, **kwargs)

    def debug(self, msg: str, extra_data: Optional[Dict] = None, *args, **kwargs):
        self._log_with_extra(logging.DEBUG, msg, extra_data, *args, **kwargs)

    def info(self, msg: str, extra_data: Optional[Dict] = None, *args, **kwargs):
        self._log_with_extra(logging.INFO, msg, extra_data, *args, **kwargs)

    def warning(self, msg: str, extra_data: Optional[Dict] = None, *args, **kwargs):
        self._log_with_extra(logging.WARNING, msg, extra_data, *args, **kwargs)

    def error(self, msg: str, extra_data: Optional[Dict] = None, *args, **kwargs):
        self._log_with_extra(logging.ERROR, msg, extra_data, *args, **kwargs)

    def critical(self, msg: str, extra_data: Optional[Dict] = None, *args, **kwargs):
        self._log_with_extra(logging.CRITICAL, msg, extra_data, *args, **kwargs)

    def event(self, event_name: str, **kwargs):
        """Log un événement structuré"""
        self.info(event_name, extra_data=kwargs)


# Enregistrer la classe de logger personnalisée
logging.setLoggerClass(StructuredLogger)


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
    colored: bool = True
) -> logging.Logger:
    """
    Configure le logging pour GestVenv.

    Args:
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Utiliser le format JSON structuré
        log_file: Fichier de log optionnel
        colored: Utiliser les couleurs (terminal uniquement)

    Returns:
        Logger configuré
    """
    # Niveau de log
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Logger racine pour gestvenv
    logger = logging.getLogger("gestvenv")
    logger.setLevel(log_level)

    # Supprimer les handlers existants
    logger.handlers.clear()

    # Handler console
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)

    if json_format:
        console_handler.setFormatter(StructuredFormatter())
    elif colored and sys.stderr.isatty():
        console_handler.setFormatter(ColoredFormatter())
    else:
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    logger.addHandler(console_handler)

    # Handler fichier si spécifié
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "gestvenv") -> StructuredLogger:
    """
    Récupère un logger structuré.

    Args:
        name: Nom du logger (sous-module de gestvenv)

    Returns:
        StructuredLogger configuré
    """
    if not name.startswith("gestvenv"):
        name = f"gestvenv.{name}"
    return logging.getLogger(name)


@contextmanager
def log_context(**kwargs):
    """
    Context manager pour ajouter du contexte aux logs.

    Usage:
        with log_context(environment="myenv", operation="install"):
            logger.info("Installing packages")
    """
    # Générer un nouveau trace_id si pas déjà défini
    old_trace_id = getattr(_context, 'trace_id', None)
    if old_trace_id is None:
        set_trace_id(str(uuid.uuid4())[:8])

    try:
        yield
    finally:
        if old_trace_id is None:
            clear_trace_id()


def log_operation(operation_name: str):
    """
    Décorateur pour logger les opérations.

    Usage:
        @log_operation("create_environment")
        def create_env(name):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            trace_id = str(uuid.uuid4())[:8]
            set_trace_id(trace_id)

            logger.info(f"Starting {operation_name}", extra_data={
                "operation": operation_name,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })

            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()

                logger.info(f"Completed {operation_name}", extra_data={
                    "operation": operation_name,
                    "duration_seconds": duration,
                    "status": "success"
                })
                return result

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"Failed {operation_name}", extra_data={
                    "operation": operation_name,
                    "duration_seconds": duration,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
                raise
            finally:
                clear_trace_id()

        return wrapper
    return decorator
