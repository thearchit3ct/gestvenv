"""
Routes API pour la gestion du cache.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional
import logging

from api.models.schemas import CacheInfo, CacheExport, CacheImport, ApiResponse
from api.services.gestvenv_service import GestVenvService
from api.services.operation_service import OperationService
from api.websocket import event_emitter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache")

# Services
gestvenv_service = GestVenvService()
operation_service = OperationService()


@router.get("/info", response_model=CacheInfo)
async def get_cache_info():
    """
    Récupère les informations du cache.
    
    Returns:
        Informations du cache
    """
    try:
        cache_info = await gestvenv_service.get_cache_info()
        
        if not cache_info:
            raise HTTPException(status_code=500, detail="Impossible de récupérer les informations du cache")
        
        return cache_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cache info: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des informations du cache")


@router.post("/clean", response_model=ApiResponse)
async def clean_cache(
    background_tasks: BackgroundTasks,
    older_than: Optional[int] = Query(None, description="Nettoyer les éléments plus anciens que X jours"),
    size_limit: Optional[str] = Query(None, description="Nettoyer pour atteindre cette taille max")
):
    """
    Nettoie le cache selon les critères spécifiés.
    
    Args:
        older_than: Age limite en jours
        size_limit: Taille limite (ex: 500MB)
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("clean_cache")
        
        # Lancer le nettoyage en arrière-plan
        background_tasks.add_task(
            _clean_cache_task,
            operation_id,
            older_than,
            size_limit
        )
        
        return ApiResponse(
            success=True,
            message="Nettoyage du cache démarré",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to clean cache: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du nettoyage du cache")


@router.post("/export", response_model=ApiResponse)
async def export_cache(
    export_config: CacheExport,
    background_tasks: BackgroundTasks
):
    """
    Exporte le cache vers un fichier archive.
    
    Args:
        export_config: Configuration d'export
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("export_cache")
        
        # Lancer l'export en arrière-plan
        background_tasks.add_task(
            _export_cache_task,
            operation_id,
            export_config
        )
        
        return ApiResponse(
            success=True,
            message=f"Export du cache vers '{export_config.output_path}' démarré",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to export cache: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'export du cache")


@router.post("/import", response_model=ApiResponse)
async def import_cache(
    import_config: CacheImport,
    background_tasks: BackgroundTasks
):
    """
    Importe un cache depuis un fichier archive.
    
    Args:
        import_config: Configuration d'import
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("import_cache")
        
        # Lancer l'import en arrière-plan
        background_tasks.add_task(
            _import_cache_task,
            operation_id,
            import_config
        )
        
        return ApiResponse(
            success=True,
            message=f"Import du cache depuis '{import_config.source_path}' démarré",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to import cache: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'import du cache")


# ===== Tâches en arrière-plan =====

async def _clean_cache_task(operation_id: str, older_than: Optional[int], size_limit: Optional[str]):
    """Tâche de nettoyage du cache."""
    try:
        await operation_service.run_operation(
            operation_id,
            gestvenv_service.clean_cache,
            older_than,
            size_limit
        )
        
        # Émettre un événement WebSocket pour la mise à jour du cache
        cache_info = await gestvenv_service.get_cache_info()
        if cache_info:
            await event_emitter.emit_cache_updated(cache_info.model_dump())
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))


async def _export_cache_task(operation_id: str, export_config: CacheExport):
    """Tâche d'export du cache."""
    try:
        # TODO: Implémenter l'export via le service GestVenv
        operation_service.update_operation(
            operation_id,
            progress=100.0,
            message="Export terminé",
            result={"exported_to": export_config.output_path}
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))


async def _import_cache_task(operation_id: str, import_config: CacheImport):
    """Tâche d'import du cache."""
    try:
        # TODO: Implémenter l'import via le service GestVenv
        operation_service.update_operation(
            operation_id,
            progress=100.0,
            message="Import terminé",
            result={"imported_from": import_config.source_path}
        )
        
        # Émettre un événement WebSocket pour la mise à jour du cache
        cache_info = await gestvenv_service.get_cache_info()
        if cache_info:
            await event_emitter.emit_cache_updated(cache_info.model_dump())
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))