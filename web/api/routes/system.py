"""
Routes API pour les informations système et diagnostic.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Dict, Any, Optional
import logging

from api.models.schemas import SystemInfo, SystemHealth, ApiResponse, Operation
from api.services.gestvenv_service import GestVenvService
from api.services.operation_service import OperationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system")

# Services
gestvenv_service = GestVenvService()
operation_service = OperationService()


@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """
    Récupère les informations système.
    
    Returns:
        Informations système
    """
    try:
        system_info = await gestvenv_service.get_system_info()
        
        if not system_info:
            raise HTTPException(status_code=500, detail="Impossible de récupérer les informations système")
        
        return system_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des informations système")


@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    """
    Vérifie la santé du système.
    
    Returns:
        État de santé du système
    """
    try:
        # Exécuter le diagnostic
        doctor_result = await gestvenv_service.run_doctor()
        
        # Parser les résultats du diagnostic
        checks = []
        recommendations = []
        
        if doctor_result["success"]:
            status = "healthy"
            # TODO: Parser la sortie du doctor pour extraire les vérifications
        else:
            status = "unhealthy"
            recommendations.append("Exécuter 'gestvenv doctor --auto-fix' pour réparer les problèmes")
        
        return SystemHealth(
            status=status,
            checks=checks,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification de santé")


@router.post("/doctor", response_model=ApiResponse)
async def run_doctor(
    background_tasks: BackgroundTasks,
    env_name: Optional[str] = Query(None, description="Environnement à diagnostiquer"),
    auto_fix: bool = Query(False, description="Réparation automatique")
):
    """
    Exécute le diagnostic du système.
    
    Args:
        env_name: Environnement spécifique à diagnostiquer
        auto_fix: Activer la réparation automatique
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("run_doctor")
        
        # Lancer le diagnostic en arrière-plan
        background_tasks.add_task(
            _run_doctor_task,
            operation_id,
            env_name,
            auto_fix
        )
        
        message = "Diagnostic système démarré"
        if env_name:
            message = f"Diagnostic de l'environnement '{env_name}' démarré"
        
        return ApiResponse(
            success=True,
            message=message,
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to run doctor: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du diagnostic")


@router.get("/operations", response_model=list[Operation])
async def list_operations(
    operation_type: Optional[str] = Query(None, description="Filtrer par type d'opération")
):
    """
    Liste les opérations en cours et terminées.
    
    Args:
        operation_type: Filtrer par type d'opération
    
    Returns:
        Liste des opérations
    """
    try:
        operations = operation_service.list_operations(operation_type)
        return operations
        
    except Exception as e:
        logger.error(f"Failed to list operations: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des opérations")


@router.get("/operations/{operation_id}", response_model=Operation)
async def get_operation(operation_id: str):
    """
    Récupère les détails d'une opération.
    
    Args:
        operation_id: ID de l'opération
    
    Returns:
        Détails de l'opération
    """
    try:
        operation = operation_service.get_operation(operation_id)
        
        if not operation:
            raise HTTPException(status_code=404, detail="Opération non trouvée")
        
        return operation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get operation {operation_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'opération")


@router.post("/operations/{operation_id}/cancel", response_model=ApiResponse)
async def cancel_operation(operation_id: str):
    """
    Annule une opération en cours.
    
    Args:
        operation_id: ID de l'opération
    
    Returns:
        Réponse API
    """
    try:
        success = operation_service.cancel_operation(operation_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Impossible d'annuler l'opération")
        
        return ApiResponse(
            success=True,
            message=f"Opération '{operation_id}' annulée"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel operation {operation_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'annulation")


@router.post("/cleanup", response_model=ApiResponse)
async def cleanup_system(
    background_tasks: BackgroundTasks,
    orphaned_only: bool = Query(False, description="Nettoyer seulement les environnements orphelins"),
    clean_cache: bool = Query(False, description="Nettoyer aussi le cache")
):
    """
    Nettoie le système (environnements orphelins, cache, etc.).
    
    Args:
        orphaned_only: Nettoyer seulement les orphelins
        clean_cache: Nettoyer aussi le cache
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("cleanup_system")
        
        # Lancer le nettoyage en arrière-plan
        background_tasks.add_task(
            _cleanup_system_task,
            operation_id,
            orphaned_only,
            clean_cache
        )
        
        return ApiResponse(
            success=True,
            message="Nettoyage du système démarré",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup system: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du nettoyage")


# ===== Tâches en arrière-plan =====

async def _run_doctor_task(operation_id: str, env_name: Optional[str], auto_fix: bool):
    """Tâche de diagnostic."""
    try:
        # TODO: Implémenter le diagnostic via le service GestVenv
        result = await gestvenv_service.run_doctor(env_name)
        
        operation_service.update_operation(
            operation_id,
            progress=100.0,
            message="Diagnostic terminé",
            result=result
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))


async def _cleanup_system_task(operation_id: str, orphaned_only: bool, clean_cache: bool):
    """Tâche de nettoyage système."""
    try:
        # TODO: Implémenter le nettoyage via le service GestVenv
        operation_service.update_operation(
            operation_id,
            progress=100.0,
            message="Nettoyage terminé",
            result={"orphaned_only": orphaned_only, "clean_cache": clean_cache}
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))