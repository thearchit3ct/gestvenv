"""
Module de gestion d'erreurs améliorée pour GestVenv v2.0

Fournit des utilitaires pour enrichir les messages d'erreur,
ajouter du contexte et suggérer des résolutions.
"""

import logging
import sys
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Codes d'erreur standardisés pour GestVenv"""
    # Erreurs générales (1xxx)
    UNKNOWN = 1000
    INTERNAL = 1001
    CONFIGURATION = 1002
    VALIDATION = 1003

    # Erreurs d'environnement (2xxx)
    ENV_NOT_FOUND = 2001
    ENV_ALREADY_EXISTS = 2002
    ENV_CREATION_FAILED = 2003
    ENV_DELETION_FAILED = 2004
    ENV_ACTIVATION_FAILED = 2005
    ENV_CORRUPTED = 2006

    # Erreurs de backend (3xxx)
    BACKEND_NOT_AVAILABLE = 3001
    BACKEND_EXECUTION_FAILED = 3002
    BACKEND_TIMEOUT = 3003
    BACKEND_NOT_SUPPORTED = 3004

    # Erreurs réseau (4xxx)
    NETWORK_UNAVAILABLE = 4001
    NETWORK_TIMEOUT = 4002
    DOWNLOAD_FAILED = 4003
    UPLOAD_FAILED = 4004

    # Erreurs de packages (5xxx)
    PACKAGE_NOT_FOUND = 5001
    PACKAGE_INSTALL_FAILED = 5002
    PACKAGE_CONFLICT = 5003
    DEPENDENCY_RESOLUTION_FAILED = 5004

    # Erreurs de cache (6xxx)
    CACHE_CORRUPTED = 6001
    CACHE_FULL = 6002
    CACHE_READ_FAILED = 6003
    CACHE_WRITE_FAILED = 6004

    # Erreurs de fichiers (7xxx)
    FILE_NOT_FOUND = 7001
    FILE_READ_FAILED = 7002
    FILE_WRITE_FAILED = 7003
    PERMISSION_DENIED = 7004
    DISK_FULL = 7005

    # Erreurs éphémères (8xxx)
    EPHEMERAL_CREATION_FAILED = 8001
    EPHEMERAL_CLEANUP_FAILED = 8002
    RESOURCE_LIMIT_EXCEEDED = 8003
    CGROUPS_NOT_AVAILABLE = 8004


@dataclass
class ErrorSuggestion:
    """Suggestion de résolution pour une erreur"""
    description: str
    command: Optional[str] = None
    documentation_link: Optional[str] = None
    auto_fixable: bool = False
    fix_function: Optional[Callable[[], bool]] = None


@dataclass
class EnrichedError:
    """Erreur enrichie avec contexte et suggestions"""
    code: ErrorCode
    message: str
    original_exception: Optional[Exception] = None
    context: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[ErrorSuggestion] = field(default_factory=list)
    traceback_str: Optional[str] = None

    def __post_init__(self):
        if self.original_exception and not self.traceback_str:
            self.traceback_str = ''.join(
                traceback.format_exception(
                    type(self.original_exception),
                    self.original_exception,
                    self.original_exception.__traceback__
                )
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sérialisation"""
        return {
            "code": self.code.value,
            "code_name": self.code.name,
            "message": self.message,
            "context": self.context,
            "suggestions": [
                {
                    "description": s.description,
                    "command": s.command,
                    "documentation_link": s.documentation_link,
                    "auto_fixable": s.auto_fixable,
                }
                for s in self.suggestions
            ],
            "traceback": self.traceback_str,
        }

    def format_user_message(self, verbose: bool = False) -> str:
        """Formate le message pour l'utilisateur"""
        lines = [f"[{self.code.name}] {self.message}"]

        if self.context and verbose:
            lines.append("\nContexte:")
            for key, value in self.context.items():
                lines.append(f"  {key}: {value}")

        if self.suggestions:
            lines.append("\nSuggestions:")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"  {i}. {suggestion.description}")
                if suggestion.command:
                    lines.append(f"     Commande: {suggestion.command}")
                if suggestion.documentation_link:
                    lines.append(f"     Doc: {suggestion.documentation_link}")

        if verbose and self.traceback_str:
            lines.append(f"\nTraceback:\n{self.traceback_str}")

        return "\n".join(lines)

    def try_auto_fix(self) -> bool:
        """Tente de corriger automatiquement l'erreur"""
        for suggestion in self.suggestions:
            if suggestion.auto_fixable and suggestion.fix_function:
                try:
                    if suggestion.fix_function():
                        logger.info(f"Auto-fix successful: {suggestion.description}")
                        return True
                except Exception as e:
                    logger.warning(f"Auto-fix failed: {e}")
        return False


# Mappings des exceptions vers codes d'erreur
EXCEPTION_TO_CODE: Dict[Type[Exception], ErrorCode] = {
    FileNotFoundError: ErrorCode.FILE_NOT_FOUND,
    PermissionError: ErrorCode.PERMISSION_DENIED,
    TimeoutError: ErrorCode.NETWORK_TIMEOUT,
    ConnectionError: ErrorCode.NETWORK_UNAVAILABLE,
    OSError: ErrorCode.INTERNAL,
}


# Suggestions par code d'erreur
ERROR_SUGGESTIONS: Dict[ErrorCode, List[ErrorSuggestion]] = {
    ErrorCode.ENV_NOT_FOUND: [
        ErrorSuggestion(
            description="Vérifiez le nom de l'environnement avec 'gv list'",
            command="gv list",
        ),
        ErrorSuggestion(
            description="Créez l'environnement s'il n'existe pas",
            command="gv create <nom>",
        ),
    ],
    ErrorCode.BACKEND_NOT_AVAILABLE: [
        ErrorSuggestion(
            description="Vérifiez que le backend est installé",
            command="gv doctor",
        ),
        ErrorSuggestion(
            description="Installez uv pour de meilleures performances",
            command="pip install uv",
        ),
        ErrorSuggestion(
            description="Utilisez pip comme fallback",
            command="gv config set preferred_backend pip",
        ),
    ],
    ErrorCode.NETWORK_UNAVAILABLE: [
        ErrorSuggestion(
            description="Vérifiez votre connexion internet",
        ),
        ErrorSuggestion(
            description="Utilisez le mode offline si possible",
            command="gv --offline <commande>",
        ),
        ErrorSuggestion(
            description="Vérifiez la configuration du proxy",
        ),
    ],
    ErrorCode.PACKAGE_NOT_FOUND: [
        ErrorSuggestion(
            description="Vérifiez l'orthographe du nom du package",
        ),
        ErrorSuggestion(
            description="Recherchez le package sur PyPI",
            documentation_link="https://pypi.org/search/",
        ),
    ],
    ErrorCode.CACHE_CORRUPTED: [
        ErrorSuggestion(
            description="Nettoyez le cache",
            command="gv cache clear",
            auto_fixable=True,
        ),
    ],
    ErrorCode.PERMISSION_DENIED: [
        ErrorSuggestion(
            description="Vérifiez les permissions du répertoire",
        ),
        ErrorSuggestion(
            description="Exécutez la commande avec les bonnes permissions",
        ),
    ],
    ErrorCode.DISK_FULL: [
        ErrorSuggestion(
            description="Libérez de l'espace disque",
        ),
        ErrorSuggestion(
            description="Nettoyez les anciens environnements",
            command="gv cleanup --unused",
        ),
        ErrorSuggestion(
            description="Nettoyez le cache",
            command="gv cache clear",
        ),
    ],
    ErrorCode.CGROUPS_NOT_AVAILABLE: [
        ErrorSuggestion(
            description="Les cgroups v2 ne sont pas disponibles sur ce système",
        ),
        ErrorSuggestion(
            description="Utilisez les environnements éphémères sans limitation de ressources",
            command="gv ephemeral create --no-resource-limits",
        ),
    ],
}


def enrich_error(
    exception: Exception,
    code: Optional[ErrorCode] = None,
    context: Optional[Dict[str, Any]] = None,
    additional_suggestions: Optional[List[ErrorSuggestion]] = None,
) -> EnrichedError:
    """Enrichit une exception avec contexte et suggestions

    Args:
        exception: Exception originale
        code: Code d'erreur (auto-détecté si non fourni)
        context: Contexte additionnel
        additional_suggestions: Suggestions supplémentaires

    Returns:
        EnrichedError avec toutes les informations
    """
    # Auto-détection du code d'erreur
    if code is None:
        code = EXCEPTION_TO_CODE.get(type(exception), ErrorCode.UNKNOWN)

    # Récupération des suggestions par défaut
    suggestions = list(ERROR_SUGGESTIONS.get(code, []))

    # Ajout des suggestions supplémentaires
    if additional_suggestions:
        suggestions.extend(additional_suggestions)

    return EnrichedError(
        code=code,
        message=str(exception),
        original_exception=exception,
        context=context or {},
        suggestions=suggestions,
    )


def handle_error(
    exception: Exception,
    code: Optional[ErrorCode] = None,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = True,
    log_level: int = logging.ERROR,
) -> Optional[EnrichedError]:
    """Gère une erreur avec logging et enrichissement

    Args:
        exception: Exception à gérer
        code: Code d'erreur
        context: Contexte additionnel
        reraise: Re-lever l'exception après traitement
        log_level: Niveau de log

    Returns:
        EnrichedError si reraise=False, sinon lève l'exception
    """
    enriched = enrich_error(exception, code, context)

    logger.log(
        log_level,
        f"[{enriched.code.name}] {enriched.message}",
        extra={"error_context": enriched.context},
    )

    if reraise:
        raise exception

    return enriched


class ErrorHandler:
    """Gestionnaire d'erreurs centralisé

    Permet de configurer la gestion des erreurs globalement
    et de collecter des statistiques.
    """

    def __init__(self):
        self.error_counts: Dict[ErrorCode, int] = {}
        self.recent_errors: List[EnrichedError] = []
        self.max_recent_errors = 100
        self.auto_fix_enabled = True
        self.verbose = False

    def handle(
        self,
        exception: Exception,
        code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        try_fix: bool = True,
    ) -> EnrichedError:
        """Gère une erreur"""
        enriched = enrich_error(exception, code, context)

        # Stats
        self.error_counts[enriched.code] = (
            self.error_counts.get(enriched.code, 0) + 1
        )

        # Historique
        self.recent_errors.append(enriched)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)

        # Log
        logger.error(enriched.format_user_message(verbose=self.verbose))

        # Auto-fix
        if try_fix and self.auto_fix_enabled:
            enriched.try_auto_fix()

        return enriched

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'erreurs"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "by_code": {
                code.name: count
                for code, count in self.error_counts.items()
            },
            "recent_count": len(self.recent_errors),
        }

    def clear_stats(self) -> None:
        """Efface les statistiques"""
        self.error_counts.clear()
        self.recent_errors.clear()


# Instance globale
error_handler = ErrorHandler()


def with_error_handling(
    code: Optional[ErrorCode] = None,
    context_func: Optional[Callable[..., Dict[str, Any]]] = None,
):
    """Décorateur pour ajouter la gestion d'erreurs à une fonction

    Args:
        code: Code d'erreur par défaut
        context_func: Fonction pour générer le contexte depuis les args

    Example:
        @with_error_handling(code=ErrorCode.PACKAGE_INSTALL_FAILED)
        def install_package(name: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {}
                if context_func:
                    try:
                        context = context_func(*args, **kwargs)
                    except Exception:
                        pass
                enriched = error_handler.handle(e, code=code, context=context)
                raise

        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {}
                if context_func:
                    try:
                        context = context_func(*args, **kwargs)
                    except Exception:
                        pass
                enriched = error_handler.handle(e, code=code, context=context)
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator
