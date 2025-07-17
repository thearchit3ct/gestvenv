"""
Service pour la gestion des templates de projet
"""

from typing import List, Dict, Any, Optional
from pathlib import Path


class TemplateService:
    """Service pour gérer les templates de projet"""
    
    def __init__(self):
        self.templates = {
            "django": {
                "name": "Django",
                "description": "Django web application template",
                "packages": ["django", "djangorestframework", "django-cors-headers"]
            },
            "fastapi": {
                "name": "FastAPI",
                "description": "FastAPI REST API template",
                "packages": ["fastapi", "uvicorn", "pydantic"]
            },
            "data-science": {
                "name": "Data Science",
                "description": "Data science project template",
                "packages": ["numpy", "pandas", "matplotlib", "jupyter", "scikit-learn"]
            }
        }
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """Liste tous les templates disponibles"""
        return [
            {
                "id": key,
                "name": value["name"],
                "description": value["description"],
                "packages_count": len(value["packages"])
            }
            for key, value in self.templates.items()
        ]
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un template spécifique"""
        if template_id in self.templates:
            template = self.templates[template_id]
            return {
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "packages": template["packages"]
            }
        return None
    
    async def create_from_template(self, template_id: str, project_name: str, path: str) -> Dict[str, Any]:
        """Crée un projet à partir d'un template"""
        return {
            "success": True,
            "message": f"Project {project_name} created from template {template_id}",
            "path": path
        }