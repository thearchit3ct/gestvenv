"""
Routes API pour la gestion des packages.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from typing import List, Optional
import logging

from api.models.schemas import Package, PackageInstall, ApiResponse
from api.services.gestvenv_service import GestVenvService
from api.services.operation_service import OperationService
from api.websocket import event_emitter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/packages")

# Services
gestvenv_service = GestVenvService()
operation_service = OperationService()


@router.post("/install", response_model=ApiResponse)
async def install_package(
    package_data: PackageInstall,
    background_tasks: BackgroundTasks,
    env_name: str = Query(..., description="Nom de l'environnement")
):
    """
    Installe un package dans un environnement.
    
    Args:
        package_data: Données du package à installer
        env_name: Nom de l'environnement
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API avec l'ID de l'opération
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("install_package")
        
        # Lancer l'installation en arrière-plan
        background_tasks.add_task(
            _install_package_task,
            operation_id,
            env_name,
            package_data
        )
        
        return ApiResponse(
            success=True,
            message=f"Installation du package '{package_data.name}' démarrée",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to install package {package_data.name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'installation du package")


@router.delete("/{package_name}", response_model=ApiResponse)
async def uninstall_package(
    background_tasks: BackgroundTasks,
    package_name: str = Path(..., description="Nom du package"),
    env_name: str = Query(..., description="Nom de l'environnement")
):
    """
    Désinstalle un package d'un environnement.
    
    Args:
        package_name: Nom du package
        env_name: Nom de l'environnement
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("uninstall_package")
        
        # Lancer la désinstallation en arrière-plan
        background_tasks.add_task(
            _uninstall_package_task,
            operation_id,
            env_name,
            package_name
        )
        
        return ApiResponse(
            success=True,
            message=f"Désinstallation du package '{package_name}' démarrée",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to uninstall package {package_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la désinstallation")


@router.post("/update", response_model=ApiResponse)
async def update_packages(
    background_tasks: BackgroundTasks,
    env_name: str = Query(..., description="Nom de l'environnement"),
    packages: Optional[List[str]] = Query(None, description="Packages à mettre à jour")
):
    """
    Met à jour des packages dans un environnement.
    
    Args:
        env_name: Nom de l'environnement
        packages: Liste des packages (tous si None)
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("update_packages")
        
        # Lancer la mise à jour en arrière-plan
        background_tasks.add_task(
            _update_packages_task,
            operation_id,
            env_name,
            packages
        )
        
        message = "Mise à jour de tous les packages démarrée" if not packages else f"Mise à jour de {len(packages)} packages démarrée"
        
        return ApiResponse(
            success=True,
            message=message,
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to update packages in {env_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")


# ===== Tâches en arrière-plan =====

async def _install_package_task(operation_id: str, env_name: str, package_data: PackageInstall):
    """Tâche d'installation de package."""
    try:
        await operation_service.run_operation(
            operation_id,
            gestvenv_service.install_package,
            env_name,
            package_data.name,
            package_data.group,
            package_data.editable,
            package_data.upgrade
        )
        
        # Émettre un événement WebSocket
        await event_emitter.emit_package_installed(
            env_name,
            package_data.name,
            package_data.model_dump()
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))


async def _uninstall_package_task(operation_id: str, env_name: str, package_name: str):
    """Tâche de désinstallation de package."""
    try:
        await operation_service.run_operation(
            operation_id,
            gestvenv_service.uninstall_package,
            env_name,
            package_name
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))


async def _update_packages_task(operation_id: str, env_name: str, packages: Optional[List[str]]):
    """Tâche de mise à jour de packages."""
    try:
        await operation_service.run_operation(
            operation_id,
            gestvenv_service.update_packages,
            env_name,
            packages
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))