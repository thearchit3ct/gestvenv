"""
Routes API pour la gestion des templates.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
import logging

from api.models.schemas import TemplateInfo, TemplateCreate, ApiResponse
from api.services.gestvenv_service import GestVenvService
from api.services.operation_service import OperationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates")

# Services
gestvenv_service = GestVenvService()
operation_service = OperationService()


@router.get("/", response_model=List[TemplateInfo])
async def list_templates():
    """
    Liste tous les templates disponibles.
    
    Returns:
        Liste des templates
    """
    try:
        templates = await gestvenv_service.list_templates()
        return templates
        
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des templates")


@router.post("/create", response_model=ApiResponse)
async def create_from_template(
    template_data: TemplateCreate,
    background_tasks: BackgroundTasks
):
    """
    Crée un projet depuis un template.
    
    Args:
        template_data: Données de création depuis template
        background_tasks: Tâches en arrière-plan
    
    Returns:
        Réponse API
    """
    try:
        # Créer une opération pour suivre le progrès
        operation_id = operation_service.create_operation("create_from_template")
        
        # Lancer la création en arrière-plan
        background_tasks.add_task(
            _create_from_template_task,
            operation_id,
            template_data
        )
        
        return ApiResponse(
            success=True,
            message=f"Création du projet '{template_data.project_name}' depuis le template '{template_data.template_name}' démarrée",
            data={"operation_id": operation_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to create from template: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création depuis template")


# ===== Tâches en arrière-plan =====

async def _create_from_template_task(operation_id: str, template_data: TemplateCreate):
    """Tâche de création depuis template."""
    try:
        await operation_service.run_operation(
            operation_id,
            gestvenv_service.create_from_template,
            template_data.template_name,
            template_data.project_name,
            template_data.author,
            template_data.email,
            template_data.version,
            template_data.output_path
        )
        
    except Exception as e:
        operation_service.update_operation(operation_id, error=str(e))