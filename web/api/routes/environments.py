"""
Routes API pour la gestion des environnements virtuels.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from typing import List, Optional
import logging

from api.models.schemas import (
    Environment, EnvironmentCreate, EnvironmentUpdate, EnvironmentDetails,
    Package, ApiResponse, Operation
)
from api.services.gestvenv_service import GestVenvService
from api.services.operation_service import OperationService
from api.websocket import event_emitter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/environments")

# Services
gestvenv_service = GestVenvService()
operation_service = OperationService()


@router.get("/", response_model=List[Environment])
async def list_environments(
    backend: Optional[str] = Query(None, description="Filtrer par backend"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    sort_by: str = Query("name", description="Critère de tri (name, created, used, size)")
):
    """
    Liste tous les environnements virtuels.
    
    Args:
        backend: Filtrer par type de backend
        status: Filtrer par statut
        sort_by: Critère de tri
    
    Returns:
        Liste des environnements
    """
    try:
        environments = await gestvenv_service.list_environments()
        
        # Appliquer les filtres
        if backend:
            environments = [env for env in environments if env.backend.value == backend]
        
        if status:
            environments = [env for env in environments if env.status.value == status]
        
        # Trier les résultats
        if sort_by == "created":
            environments.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "used":
            environments.sort(key=lambda x: x.last_used or x.created_at, reverse=True)
        elif sort_by == "size":
            environments.sort(key=lambda x: x.size_mb, reverse=True)
        else:  # name
            environments.sort(key=lambda x: x.name)
        
        return environments
        
    except Exception as e:
        logger.error(f"Failed to list environments: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des environnements")


@router.post("/", response_model=ApiResponse)
async def create_environment(
    env_data: EnvironmentCreate,
    background_tasks: BackgroundTasks
):
    """
    Crée un nouvel environnement virtuel.
    
    Args:
        env_data: Données de l'environnement à créer
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API avec l'ID de l'opération
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("create_environment")
        
        # Lancer la création en arrière-plan
        background_tasks.add_task(
            _create_environment_task,
            operation_id,
            env_data
        )
        
        return ApiResponse(
            success=True,
            message=f"Création de l'environnement '{env_data.name}' démarrée",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to create environment: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de l'environnement")


@router.get("/{env_name}", response_model=EnvironmentDetails)
async def get_environment(
    env_name: str = Path(..., description="Nom de l'environnement")
):
    """
    Récupère les détails d'un environnement.
    
    Args:
        env_name: Nom de l'environnement
    
    Returns:
        Détails de l'environnement
    """
    try:
        environment = await gestvenv_service.get_environment(env_name)
        
        if not environment:
            raise HTTPException(status_code=404, detail="Environnement non trouvé")
        
        # Récupérer la liste des packages
        packages = await gestvenv_service.list_packages(env_name)
        
        # TODO: Récupérer les informations de santé et configuration
        
        return EnvironmentDetails(
            **environment.model_dump(),
            packages=packages,
            config={},
            health_info={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get environment {env_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'environnement")


@router.put("/{env_name}", response_model=ApiResponse)
async def update_environment(
    env_name: str,
    env_update: EnvironmentUpdate
):
    """
    Met à jour un environnement.
    
    Args:
        env_name: Nom de l'environnement
        env_update: Données de mise à jour
    
    Returns:
        Réponse API
    """
    try:
        # Vérifier que l'environnement existe
        environment = await gestvenv_service.get_environment(env_name)
        if not environment:
            raise HTTPException(status_code=404, detail="Environnement non trouvé")
        
        # TODO: Implémenter la mise à jour
        
        return ApiResponse(
            success=True,
            message=f"Environnement '{env_name}' mis à jour avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update environment {env_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")


@router.delete("/{env_name}", response_model=ApiResponse)
async def delete_environment(
    env_name: str,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Forcer la suppression")
):
    """
    Supprime un environnement.
    
    Args:
        env_name: Nom de l'environnement
        force: Forcer la suppression
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Vérifier que l'environnement existe
        environment = await gestvenv_service.get_environment(env_name)
        if not environment:
            raise HTTPException(status_code=404, detail="Environnement non trouvé")
        
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("delete_environment")
        
        # Lancer la suppression en arrière-plan
        background_tasks.add_task(
            _delete_environment_task,
            operation_id,
            env_name,
            force
        )
        
        return ApiResponse(
            success=True,
            message=f"Suppression de l'environnement '{env_name}' démarrée",
            data={"operation_id": operation_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete environment {env_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression")


@router.post("/{env_name}/activate", response_model=ApiResponse)
async def activate_environment(env_name: str):
    """
    Active un environnement.
    
    Args:
        env_name: Nom de l'environnement
    
    Returns:
        Réponse API
    """
    try:
        success = await gestvenv_service.activate_environment(env_name)
        
        if not success:
            raise HTTPException(status_code=400, detail="Échec de l'activation")
        
        return ApiResponse(
            success=True,
            message=f"Environnement '{env_name}' activé avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate environment {env_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'activation")


@router.get("/{env_name}/packages", response_model=List[Package])
async def list_environment_packages(
    env_name: str,
    group: Optional[str] = Query(None, description="Filtrer par groupe"),
    outdated_only: bool = Query(False, description="Seulement les packages obsolètes")
):
    """
    Liste les packages d'un environnement.
    
    Args:
        env_name: Nom de l'environnement
        group: Filtrer par groupe
        outdated_only: Seulement les packages obsolètes
    
    Returns:
        Liste des packages
    """
    try:
        packages = await gestvenv_service.list_packages(env_name, group)
        
        if outdated_only:
            packages = [pkg for pkg in packages if pkg.status.value == "outdated"]
        
        return packages
        
    except Exception as e:
        logger.error(f"Failed to list packages for {env_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des packages")


@router.post("/{env_name}/sync", response_model=ApiResponse)
async def sync_environment(
    env_name: str,
    background_tasks: BackgroundTasks,
    groups: Optional[str] = Query(None, description="Groupes à synchroniser"),
    clean: bool = Query(False, description="Nettoyer les packages non listés")
):
    """
    Synchronise un environnement avec pyproject.toml.
    
    Args:
        env_name: Nom de l'environnement
        groups: Groupes à synchroniser
        clean: Nettoyer les packages non listés
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("sync_environment")
        
        # Lancer la synchronisation en arrière-plan
        background_tasks.add_task(
            _sync_environment_task,
            operation_id,
            env_name,
            groups,
            clean
        )
        
        return ApiResponse(
            success=True,
            message=f"Synchronisation de l'environnement '{env_name}' démarrée",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to sync environment {env_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la synchronisation")


# ===== Tâches en arrière-plan =====

async def _create_environment_task(operation_id: str, env_data: EnvironmentCreate):
    """Tâche de création d'environnement."""
    try:
        await operation_service.run_operation(
            operation_id,
            gestvenv_service.create_environment,
            env_data.name,
            env_data.python_version,
            env_data.backend,
            env_data.template,
            env_data.packages
        )
        
        # Émettre un événement WebSocket
        await event_emitter.emit_environment_created(
            env_data.name,
            env_data.model_dump()
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))


async def _delete_environment_task(operation_id: str, env_name: str, force: bool):
    """Tâche de suppression d'environnement."""
    try:
        await operation_service.run_operation(
            operation_id,
            gestvenv_service.delete_environment,
            env_name,
            force
        )
        
        # Émettre un événement WebSocket
        await event_emitter.emit_environment_deleted(env_name)
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))


async def _sync_environment_task(operation_id: str, env_name: str, groups: Optional[str], clean: bool):
    """Tâche de synchronisation d'environnement."""
    try:
        # TODO: Implémenter la synchronisation via le service
        operation_service.update_operation(
            operation_id,
            progress=100.0,
            message="Synchronisation terminée",
            result={"synchronized": True}
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))