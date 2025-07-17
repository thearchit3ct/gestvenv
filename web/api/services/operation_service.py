"""
Service pour gérer les opérations longues et le suivi de progression.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
import logging

from api.models.schemas import Operation, OperationStatus

logger = logging.getLogger(__name__)


@dataclass
class OperationContext:
    """Contexte d'une opération."""
    id: str
    type: str
    status: OperationStatus = OperationStatus.PENDING
    progress: float = 0.0
    message: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None


class OperationService:
    """Service pour gérer les opérations asynchrones."""
    
    def __init__(self):
        self._operations: Dict[str, OperationContext] = {}
        self._callbacks: Dict[str, list] = {}
    
    def create_operation(self, operation_type: str) -> str:
        """
        Crée une nouvelle opération.
        
        Args:
            operation_type: Type d'opération
            
        Returns:
            ID de l'opération
        """
        operation_id = str(uuid.uuid4())
        
        operation = OperationContext(
            id=operation_id,
            type=operation_type
        )
        
        self._operations[operation_id] = operation
        self._callbacks[operation_id] = []
        
        logger.info(f"Created operation {operation_id} of type {operation_type}")
        return operation_id
    
    def get_operation(self, operation_id: str) -> Optional[Operation]:
        """
        Récupère une opération par son ID.
        
        Args:
            operation_id: ID de l'opération
            
        Returns:
            Opération ou None si non trouvée
        """
        if operation_id not in self._operations:
            return None
        
        ctx = self._operations[operation_id]
        return Operation(
            id=ctx.id,
            type=ctx.type,
            status=ctx.status,
            progress=ctx.progress,
            message=ctx.message,
            started_at=ctx.started_at,
            completed_at=ctx.completed_at,
            result=ctx.result,
            error=ctx.error
        )
    
    def list_operations(self, operation_type: Optional[str] = None) -> list[Operation]:
        """
        Liste les opérations.
        
        Args:
            operation_type: Filtrer par type d'opération
            
        Returns:
            Liste des opérations
        """
        operations = []
        
        for ctx in self._operations.values():
            if operation_type and ctx.type != operation_type:
                continue
            
            operation = Operation(
                id=ctx.id,
                type=ctx.type,
                status=ctx.status,
                progress=ctx.progress,
                message=ctx.message,
                started_at=ctx.started_at,
                completed_at=ctx.completed_at,
                result=ctx.result,
                error=ctx.error
            )
            operations.append(operation)
        
        return sorted(operations, key=lambda x: x.started_at, reverse=True)
    
    def add_callback(self, operation_id: str, callback: Callable):
        """
        Ajoute un callback pour une opération.
        
        Args:
            operation_id: ID de l'opération
            callback: Fonction à appeler lors des mises à jour
        """
        if operation_id in self._callbacks:
            self._callbacks[operation_id].append(callback)
    
    def update_operation(
        self,
        operation_id: str,
        status: Optional[OperationStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Met à jour une opération.
        
        Args:
            operation_id: ID de l'opération
            status: Nouveau statut
            progress: Nouveau pourcentage de progression
            message: Nouveau message
            result: Résultat de l'opération
            error: Message d'erreur
        """
        if operation_id not in self._operations:
            return
        
        ctx = self._operations[operation_id]
        
        if status:
            ctx.status = status
            if status in [OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED]:
                ctx.completed_at = datetime.now()
        
        if progress is not None:
            ctx.progress = max(0.0, min(100.0, progress))
        
        if message:
            ctx.message = message
        
        if result:
            ctx.result = result
        
        if error:
            ctx.error = error
            ctx.status = OperationStatus.FAILED
        
        # Notifier les callbacks
        for callback in self._callbacks.get(operation_id, []):
            try:
                callback(self.get_operation(operation_id))
            except Exception as e:
                logger.error(f"Callback error for operation {operation_id}: {e}")
    
    async def run_operation(
        self,
        operation_id: str,
        coro_func: Callable,
        *args,
        **kwargs
    ):
        """
        Exécute une opération asynchrone.
        
        Args:
            operation_id: ID de l'opération
            coro_func: Fonction coroutine à exécuter
            *args: Arguments pour la fonction
            **kwargs: Arguments nommés pour la fonction
        """
        if operation_id not in self._operations:
            return
        
        ctx = self._operations[operation_id]
        
        try:
            self.update_operation(operation_id, status=OperationStatus.RUNNING)
            
            # Créer la tâche
            task = asyncio.create_task(coro_func(*args, **kwargs))
            ctx.task = task
            
            # Attendre le résultat
            result = await task
            
            self.update_operation(
                operation_id,
                status=OperationStatus.COMPLETED,
                progress=100.0,
                result=result
            )
            
        except asyncio.CancelledError:
            self.update_operation(
                operation_id,
                status=OperationStatus.CANCELLED,
                message="Opération annulée"
            )
            
        except Exception as e:
            logger.error(f"Operation {operation_id} failed: {e}")
            self.update_operation(
                operation_id,
                status=OperationStatus.FAILED,
                error=str(e)
            )
    
    def cancel_operation(self, operation_id: str) -> bool:
        """
        Annule une opération.
        
        Args:
            operation_id: ID de l'opération
            
        Returns:
            True si l'opération a été annulée
        """
        if operation_id not in self._operations:
            return False
        
        ctx = self._operations[operation_id]
        
        if ctx.task and not ctx.task.done():
            ctx.task.cancel()
            self.update_operation(
                operation_id,
                status=OperationStatus.CANCELLED,
                message="Opération annulée par l'utilisateur"
            )
            return True
        
        return False
    
    def cleanup_completed_operations(self, max_age_hours: int = 24):
        """
        Nettoie les opérations terminées anciennes.
        
        Args:
            max_age_hours: Age maximum en heures
        """
        now = datetime.now()
        to_remove = []
        
        for operation_id, ctx in self._operations.items():
            if ctx.completed_at:
                age_hours = (now - ctx.completed_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(operation_id)
        
        for operation_id in to_remove:
            del self._operations[operation_id]
            if operation_id in self._callbacks:
                del self._callbacks[operation_id]
            
            logger.info(f"Cleaned up old operation {operation_id}")
    
    async def stream_operation_progress(
        self,
        operation_id: str
    ) -> AsyncGenerator[Operation, None]:
        """
        Stream les mises à jour d'une opération.
        
        Args:
            operation_id: ID de l'opération
            
        Yields:
            Mises à jour de l'opération
        """
        if operation_id not in self._operations:
            return
        
        # État initial
        operation = self.get_operation(operation_id)
        if operation:
            yield operation
        
        # Attendre les mises à jour
        last_status = operation.status if operation else OperationStatus.PENDING
        
        while operation_id in self._operations:
            await asyncio.sleep(0.5)  # Polling toutes les 500ms
            
            operation = self.get_operation(operation_id)
            if not operation:
                break
            
            # Envoyer si le statut a changé
            if operation.status != last_status:
                yield operation
                last_status = operation.status
            
            # Arrêter si l'opération est terminée
            if operation.status in [
                OperationStatus.COMPLETED,
                OperationStatus.FAILED,
                OperationStatus.CANCELLED
            ]:
                break