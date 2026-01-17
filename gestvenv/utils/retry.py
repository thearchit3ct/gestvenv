"""
Module de retry avec backoff exponentiel pour GestVenv v2.0

Fournit des décorateurs et utilitaires pour les opérations réseau
et les appels aux backends avec gestion automatique des erreurs.
"""

import asyncio
import functools
import logging
import random
import time
from typing import (
    Any,
    Callable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    Sequence,
)
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class RetryConfig:
    """Configuration pour les opérations de retry

    Attributes:
        max_attempts: Nombre maximum de tentatives (défaut: 3)
        base_delay: Délai de base en secondes (défaut: 1.0)
        max_delay: Délai maximum en secondes (défaut: 60.0)
        backoff_factor: Facteur multiplicateur pour backoff (défaut: 2.0)
        jitter: Ajouter du jitter aléatoire (défaut: True)
        jitter_factor: Facteur de jitter (0.0-1.0) (défaut: 0.1)
        exceptions: Tuple d'exceptions à retry (défaut: Exception)
        on_retry: Callback appelé à chaque retry
        on_failure: Callback appelé en cas d'échec final
    """
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
    on_failure: Optional[Callable[[Exception, int], None]] = None

    def calculate_delay(self, attempt: int) -> float:
        """Calcule le délai pour une tentative donnée

        Args:
            attempt: Numéro de la tentative (1-indexed)

        Returns:
            Délai en secondes
        """
        delay = min(
            self.base_delay * (self.backoff_factor ** (attempt - 1)),
            self.max_delay
        )

        if self.jitter:
            jitter_range = delay * self.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)

        return delay


# Configurations prédéfinies pour différents cas d'usage
RETRY_NETWORK = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0,
    jitter=True,
)

RETRY_BACKEND = RetryConfig(
    max_attempts=2,
    base_delay=0.5,
    backoff_factor=1.5,
    jitter=False,
)

RETRY_CACHE = RetryConfig(
    max_attempts=2,
    base_delay=0.1,
    backoff_factor=2.0,
    jitter=False,
)

RETRY_AGGRESSIVE = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    backoff_factor=2.0,
    max_delay=30.0,
    jitter=True,
)


def retry(
    config: Optional[RetryConfig] = None,
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Callable[[F], F]:
    """Décorateur pour ajouter retry avec backoff exponentiel

    Peut être utilisé avec une config prédéfinie ou des paramètres individuels.

    Args:
        config: Configuration RetryConfig complète
        max_attempts: Surcharge du nombre de tentatives
        base_delay: Surcharge du délai de base
        exceptions: Surcharge des exceptions à retry
        on_retry: Callback à chaque retry

    Returns:
        Décorateur de fonction

    Example:
        @retry(config=RETRY_NETWORK)
        def fetch_data():
            ...

        @retry(max_attempts=5, exceptions=(TimeoutError,))
        def slow_operation():
            ...
    """
    effective_config = config or RetryConfig()

    # Appliquer les surcharges
    if max_attempts is not None:
        effective_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=effective_config.base_delay,
            max_delay=effective_config.max_delay,
            backoff_factor=effective_config.backoff_factor,
            jitter=effective_config.jitter,
            jitter_factor=effective_config.jitter_factor,
            exceptions=effective_config.exceptions,
            on_retry=effective_config.on_retry,
            on_failure=effective_config.on_failure,
        )
    if base_delay is not None:
        effective_config.base_delay = base_delay
    if exceptions is not None:
        effective_config.exceptions = exceptions
    if on_retry is not None:
        effective_config.on_retry = on_retry

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(1, effective_config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except effective_config.exceptions as e:
                    last_exception = e

                    if attempt == effective_config.max_attempts:
                        logger.warning(
                            f"Retry exhausted for {func.__name__} after "
                            f"{attempt} attempts: {e}"
                        )
                        if effective_config.on_failure:
                            effective_config.on_failure(e, attempt)
                        raise

                    delay = effective_config.calculate_delay(attempt)
                    logger.info(
                        f"Retry {attempt}/{effective_config.max_attempts} "
                        f"for {func.__name__} in {delay:.2f}s: {e}"
                    )

                    if effective_config.on_retry:
                        effective_config.on_retry(e, attempt, delay)

                    time.sleep(delay)

            # Ne devrait jamais arriver
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry loop completed without result")

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(1, effective_config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except effective_config.exceptions as e:
                    last_exception = e

                    if attempt == effective_config.max_attempts:
                        logger.warning(
                            f"Retry exhausted for {func.__name__} after "
                            f"{attempt} attempts: {e}"
                        )
                        if effective_config.on_failure:
                            effective_config.on_failure(e, attempt)
                        raise

                    delay = effective_config.calculate_delay(attempt)
                    logger.info(
                        f"Retry {attempt}/{effective_config.max_attempts} "
                        f"for {func.__name__} in {delay:.2f}s: {e}"
                    )

                    if effective_config.on_retry:
                        effective_config.on_retry(e, attempt, delay)

                    await asyncio.sleep(delay)

            if last_exception:
                raise last_exception
            raise RuntimeError("Retry loop completed without result")

        # Choisir le bon wrapper selon le type de fonction
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any,
) -> Any:
    """Exécute une fonction async avec retry

    Version fonctionnelle du décorateur pour usage dynamique.

    Args:
        func: Fonction async à exécuter
        *args: Arguments positionnels
        config: Configuration retry
        **kwargs: Arguments nommés

    Returns:
        Résultat de la fonction

    Example:
        result = await retry_async(fetch_data, url, config=RETRY_NETWORK)
    """
    effective_config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(1, effective_config.max_attempts + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except effective_config.exceptions as e:
            last_exception = e

            if attempt == effective_config.max_attempts:
                if effective_config.on_failure:
                    effective_config.on_failure(e, attempt)
                raise

            delay = effective_config.calculate_delay(attempt)
            logger.info(
                f"Retry {attempt}/{effective_config.max_attempts} "
                f"for {func.__name__} in {delay:.2f}s: {e}"
            )

            if effective_config.on_retry:
                effective_config.on_retry(e, attempt, delay)

            await asyncio.sleep(delay)

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop completed without result")


def retry_sync(
    func: Callable[..., T],
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any,
) -> T:
    """Exécute une fonction sync avec retry

    Version fonctionnelle du décorateur pour usage dynamique.

    Args:
        func: Fonction à exécuter
        *args: Arguments positionnels
        config: Configuration retry
        **kwargs: Arguments nommés

    Returns:
        Résultat de la fonction
    """
    effective_config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(1, effective_config.max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except effective_config.exceptions as e:
            last_exception = e

            if attempt == effective_config.max_attempts:
                if effective_config.on_failure:
                    effective_config.on_failure(e, attempt)
                raise

            delay = effective_config.calculate_delay(attempt)
            logger.info(
                f"Retry {attempt}/{effective_config.max_attempts} "
                f"for {func.__name__} in {delay:.2f}s: {e}"
            )

            if effective_config.on_retry:
                effective_config.on_retry(e, attempt, delay)

            time.sleep(delay)

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop completed without result")


class RetryContext:
    """Context manager pour retry avec état

    Permet de tracker l'état des retries et d'implémenter
    des logiques de retry plus complexes.

    Example:
        async with RetryContext(config=RETRY_NETWORK) as ctx:
            while ctx.should_retry():
                try:
                    result = await fetch_data()
                    break
                except NetworkError as e:
                    ctx.record_failure(e)
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.attempt = 0
        self.failures: list[Exception] = []
        self.total_delay = 0.0
        self._success = False

    def should_retry(self) -> bool:
        """Vérifie si on doit continuer à réessayer"""
        return self.attempt < self.config.max_attempts and not self._success

    def record_failure(self, exception: Exception) -> None:
        """Enregistre un échec"""
        self.failures.append(exception)
        self.attempt += 1

        if self.config.on_retry and self.attempt < self.config.max_attempts:
            delay = self.config.calculate_delay(self.attempt)
            self.config.on_retry(exception, self.attempt, delay)

    def record_success(self) -> None:
        """Enregistre un succès"""
        self._success = True

    def get_delay(self) -> float:
        """Retourne le délai avant la prochaine tentative"""
        delay = self.config.calculate_delay(self.attempt)
        self.total_delay += delay
        return delay

    async def wait(self) -> None:
        """Attend avant la prochaine tentative (async)"""
        delay = self.get_delay()
        await asyncio.sleep(delay)

    def wait_sync(self) -> None:
        """Attend avant la prochaine tentative (sync)"""
        delay = self.get_delay()
        time.sleep(delay)

    def __enter__(self) -> 'RetryContext':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_val and isinstance(exc_val, self.config.exceptions):
            self.record_failure(exc_val)
            if self.should_retry():
                return True  # Supprime l'exception
        return False

    async def __aenter__(self) -> 'RetryContext':
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_val and isinstance(exc_val, self.config.exceptions):
            self.record_failure(exc_val)
            if self.should_retry():
                await self.wait()
                return True
        return False

    @property
    def stats(self) -> dict[str, Any]:
        """Statistiques des retries"""
        return {
            "attempts": self.attempt,
            "failures": len(self.failures),
            "total_delay": self.total_delay,
            "success": self._success,
            "last_error": str(self.failures[-1]) if self.failures else None,
        }
