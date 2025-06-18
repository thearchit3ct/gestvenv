"""
Template de projet web générique
"""

from typing import Dict, List, Any
from ..base_template import ProjectTemplate, TemplateFile


class WebTemplate(ProjectTemplate):
    """Template pour applications web modernes"""
    
    def __init__(self):
        super().__init__(
            name="web",
            description="Application web moderne", 
            category="web",
            dependencies=[
                "fastapi>=0.100.0",
                "uvicorn[standard]>=0.20.0",
                "pydantic>=2.0.0"
            ],
            dev_dependencies=[
                "pytest>=7.0.0",
                "pytest-asyncio>=0.21.0", 
                "httpx>=0.24.0",
                "black>=23.0.0",
                "isort>=5.12.0"
            ]
        )
        
    def get_files(self) -> List[TemplateFile]:
        return [
            TemplateFile(
                path="{{package_name}}/__init__.py",
                content='"""{{project_name}} - Application web moderne"""\n\n__version__ = "{{version}}"\n'
            ),
            TemplateFile(
                path="{{package_name}}/main.py",
                content='''"""Application principale FastAPI"""

from fastapi import FastAPI

app = FastAPI(
    title="{{project_name}}",
    description="{{description}}",
    version="{{version}}"
)


@app.get("/")
async def root():
    """Endpoint racine"""
    return {"message": "Hello from {{project_name}}!"}


@app.get("/health")
async def health():
    """Check de santé"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
            ),
            TemplateFile(
                path="tests/test_api.py",
                content='''"""Tests de l'API"""

import pytest
from fastapi.testclient import TestClient
from {{package_name}}.main import app

client = TestClient(app)


def test_root():
    """Test endpoint racine"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Hello from {{project_name}}!" in response.json()["message"]


def test_health():
    """Test endpoint santé"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
'''
            ),
            TemplateFile(
                path="requirements.txt",
                content="# Fichier legacy - utiliser pyproject.toml\n",
                is_template=False
            )
        ]
        
    def get_pyproject_config(self) -> Dict[str, Any]:
        return {
            "project": {
                "name": "{{project_name}}",
                "version": "{{version}}",
                "description": "{{description}}",
                "authors": [{"name": "{{author}}", "email": "{{email}}"}],
                "license": {"text": "{{license}}"},
                "readme": "README.md",
                "requires-python": ">=3.8",
                "dependencies": self.dependencies,
                "optional-dependencies": {
                    "dev": self.dev_dependencies
                },
                "scripts": {
                    "{{package_name}}": "{{package_name}}.main:app"
                }
            },
            "build-system": {
                "requires": ["setuptools>=61.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            }
        }