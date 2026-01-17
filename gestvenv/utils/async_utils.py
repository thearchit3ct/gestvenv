"""
Utilitaires async pour GestVenv v2.0

Fournit des helpers pour la conversion sync/async,
l'exécution concurrente et la gestion du contexte async.
"""

import asyncio
import functools
import logging
import concurrent.futures
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    List,
    Optional,
    TypeVar,
    Union,
    Sequence,
    Dict,
)
from contextlib import asynccontextmanager
import threading

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# Thread pool pour exécuter du code sync dans async
_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def get_executor(max_workers: int = 4) -> concurrent.futures.ThreadPoolExecutor:
    """Obtient le thread pool executor global

    Args:
        max_workers: Nombre max de workers

    Returns:
        ThreadPoolExecutor partagé
    """
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="gestvenv_async_"
            )
    return _executor


def shutdown_executor() -> None:
    """Arrête le thread pool executor"""
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=True)
            _executor = None


async def run_in_executor(
    func: Callable[..., T],
    *args: Any,
    executor: Optional[concurrent.futures.Executor] = None,
    **kwargs: Any,
) -> T:
    """Exécute une fonction sync dans un executor

    Permet d'appeler du code bloquant depuis du code async
    sans bloquer la boucle événements.

    Args:
        func: Fonction synchrone à exécuter
        *args: Arguments positionnels
        executor: Executor personnalisé (défaut: pool global)
        **kwargs: Arguments nommés

    Returns:
        Résultat de la fonction

    Example:
        result = await run_in_executor(blocking_io_function, arg1, arg2)
    """
    loop = asyncio.get_running_loop()
    executor = executor or get_executor()

    if kwargs:
        func = functools.partial(func, **kwargs)

    return await loop.run_in_executor(executor, func, *args)


def sync_to_async(func: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    """Décorateur pour convertir une fonction sync en async

    La fonction sera exécutée dans un thread pool.

    Args:
        func: Fonction synchrone

    Returns:
        Version async de la fonction

    Example:
        @sync_to_async
        def blocking_operation():
            time.sleep(1)
            return "done"

        result = await blocking_operation()
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await run_in_executor(func, *args, **kwargs)
    return wrapper


def async_to_sync(func: Callable[..., Awaitable[T]]) -> Callable[..., T]:
    """Décorateur pour convertir une fonction async en sync

    Crée une nouvelle boucle événements si nécessaire.

    Args:
        func: Fonction async

    Returns:
        Version sync de la fonction

    Example:
        @async_to_sync
        async def async_operation():
            await asyncio.sleep(1)
            return "done"

        result = async_operation()  # Appelable de manière synchrone
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # On est dans une boucle async, utiliser un thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, func(*args, **kwargs))
                return future.result()
        else:
            # Pas de boucle, on peut en créer une
            return asyncio.run(func(*args, **kwargs))
    return wrapper


async def gather_with_concurrency(
    limit: int,
    *coros: Coroutine[Any, Any, T],
    return_exceptions: bool = False,
) -> List[Union[T, BaseException]]:
    """Exécute des coroutines avec limite de concurrence

    Args:
        limit: Nombre max de tâches concurrentes
        *coros: Coroutines à exécuter
        return_exceptions: Retourner les exceptions au lieu de les lever

    Returns:
        Liste des résultats dans l'ordre des coroutines

    Example:
        results = await gather_with_concurrency(
            5,
            fetch_url(url1),
            fetch_url(url2),
            fetch_url(url3),
        )
    """
    semaphore = asyncio.Semaphore(limit)

    async def limited_coro(coro: Coroutine[Any, Any, T]) -> T:
        async with semaphore:
            return await coro

    return await asyncio.gather(
        *[limited_coro(c) for c in coros],
        return_exceptions=return_exceptions,
    )


async def first_completed(
    *coros: Coroutine[Any, Any, T],
    timeout: Optional[float] = None,
) -> T:
    """Retourne le résultat de la première coroutine terminée

    Les autres coroutines sont annulées.

    Args:
        *coros: Coroutines à exécuter
        timeout: Timeout optionnel

    Returns:
        Résultat de la première coroutine terminée

    Raises:
        TimeoutError: Si timeout atteint
        Exception: Si toutes les coroutines échouent
    """
    tasks = [asyncio.create_task(c) for c in coros]

    try:
        done, pending = await asyncio.wait(
            tasks,
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Annuler les tâches restantes
        for task in pending:
            task.cancel()

        if not done:
            raise TimeoutError("Timeout waiting for first completed task")

        # Retourner le premier résultat
        task = done.pop()
        return task.result()

    except Exception:
        # Annuler toutes les tâches en cas d'erreur
        for task in tasks:
            task.cancel()
        raise


async def retry_first_success(
    *coros_factories: Callable[[], Coroutine[Any, Any, T]],
    delay_between: float = 0.0,
) -> T:
    """Essaie les coroutines jusqu'au premier succès

    Args:
        *coros_factories: Factories de coroutines (callables qui créent des coros)
        delay_between: Délai entre les tentatives

    Returns:
        Résultat de la première coroutine réussie

    Raises:
        Exception: La dernière exception si toutes échouent

    Example:
        result = await retry_first_success(
            lambda: fetch_from_primary(),
            lambda: fetch_from_secondary(),
            lambda: fetch_from_fallback(),
        )
    """
    last_exception: Optional[Exception] = None

    for factory in coros_factories:
        try:
            return await factory()
        except Exception as e:
            last_exception = e
            logger.debug(f"Attempt failed: {e}")
            if delay_between > 0:
                await asyncio.sleep(delay_between)

    if last_exception:
        raise last_exception
    raise RuntimeError("No coroutine factories provided")


class AsyncLock:
    """Lock async réentrant avec timeout

    Wrapper autour de asyncio.Lock avec fonctionnalités supplémentaires.
    """

    def __init__(self, timeout: Optional[float] = None):
        self._lock = asyncio.Lock()
        self._timeout = timeout

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquiert le lock avec timeout optionnel"""
        effective_timeout = timeout or self._timeout

        if effective_timeout is None:
            await self._lock.acquire()
            return True

        try:
            await asyncio.wait_for(
                self._lock.acquire(),
                timeout=effective_timeout
            )
            return True
        except asyncio.TimeoutError:
            return False

    def release(self) -> None:
        """Libère le lock"""
        self._lock.release()

    async def __aenter__(self) -> 'AsyncLock':
        acquired = await self.acquire()
        if not acquired:
            raise TimeoutError("Failed to acquire lock")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()


class AsyncCache:
    """Cache async simple avec TTL

    Utile pour mettre en cache des résultats de coroutines.
    """

    def __init__(self, ttl_seconds: float = 60.0):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self._ttl = ttl_seconds

    async def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if asyncio.get_event_loop().time() - timestamp < self._ttl:
                    return value
                del self._cache[key]
        return None

    async def set(self, key: str, value: Any) -> None:
        """Stocke une valeur dans le cache"""
        async with self._lock:
            self._cache[key] = (value, asyncio.get_event_loop().time())

    async def get_or_compute(
        self,
        key: str,
        compute: Callable[[], Awaitable[T]],
    ) -> T:
        """Récupère du cache ou calcule et cache"""
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await compute()
        await self.set(key, value)
        return value

    async def clear(self) -> None:
        """Vide le cache"""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """Supprime les entrées expirées"""
        async with self._lock:
            current_time = asyncio.get_event_loop().time()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp >= self._ttl
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


@asynccontextmanager
async def timeout_context(seconds: float):
    """Context manager avec timeout

    Example:
        async with timeout_context(5.0):
            await slow_operation()
    """
    try:
        yield
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {seconds}s")


async def run_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    default: Optional[T] = None,
) -> Optional[T]:
    """Exécute une coroutine avec timeout

    Args:
        coro: Coroutine à exécuter
        timeout: Timeout en secondes
        default: Valeur par défaut si timeout

    Returns:
        Résultat ou default si timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return default


def ensure_async(func: Union[Callable[..., T], Callable[..., Awaitable[T]]]) -> Callable[..., Awaitable[T]]:
    """S'assure qu'une fonction est async

    Si la fonction est sync, elle est wrappée pour être async.

    Args:
        func: Fonction sync ou async

    Returns:
        Version async de la fonction
    """
    if asyncio.iscoroutinefunction(func):
        return func
    return sync_to_async(func)


class TaskGroup:
    """Groupe de tâches avec gestion automatique

    Similaire à asyncio.TaskGroup de Python 3.11+ mais compatible 3.9+.

    Example:
        async with TaskGroup() as group:
            group.create_task(task1())
            group.create_task(task2())
        # Toutes les tâches sont terminées ici
    """

    def __init__(self):
        self._tasks: List[asyncio.Task] = []
        self._errors: List[BaseException] = []

    def create_task(self, coro: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
        """Crée et enregistre une tâche"""
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        return task

    async def __aenter__(self) -> 'TaskGroup':
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        # Attendre toutes les tâches
        if self._tasks:
            results = await asyncio.gather(
                *self._tasks,
                return_exceptions=True
            )

            # Collecter les erreurs
            for result in results:
                if isinstance(result, BaseException):
                    self._errors.append(result)

        # Lever les erreurs s'il y en a
        if self._errors:
            if len(self._errors) == 1:
                raise self._errors[0]
            raise ExceptionGroup("TaskGroup errors", self._errors)

        return False

    @property
    def tasks(self) -> List[asyncio.Task]:
        """Liste des tâches"""
        return self._tasks.copy()

    @property
    def errors(self) -> List[BaseException]:
        """Liste des erreurs"""
        return self._errors.copy()


# Compatibilité Python 3.9-3.10 pour ExceptionGroup
try:
    ExceptionGroup  # Python 3.11+
except NameError:
    class ExceptionGroup(Exception):
        """Polyfill pour ExceptionGroup (Python < 3.11)"""

        def __init__(self, message: str, exceptions: Sequence[BaseException]):
            super().__init__(message)
            self.exceptions = list(exceptions)

        def __str__(self) -> str:
            return f"{self.args[0]} ({len(self.exceptions)} sub-exceptions)"
