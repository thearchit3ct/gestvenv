"""
Template FastAPI spécialisé
"""

from typing import Dict, List, Any
from ..base_template import ProjectTemplate, TemplateFile


class FastAPITemplate(ProjectTemplate):
    """Template pour applications FastAPI complètes"""
    
    def __init__(self):
        super().__init__(
            name="fastapi",
            description="Application FastAPI avec base de données",
            category="web",
            dependencies=[
                "fastapi>=0.100.0",
                "uvicorn[standard]>=0.20.0",
                "pydantic>=2.0.0",
                "sqlalchemy>=2.0.0",
                "alembic>=1.10.0",
                "python-multipart>=0.0.6"
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
                content='"""{{project_name}} - Application FastAPI"""\n\n__version__ = "{{version}}"\n'
            ),
            TemplateFile(
                path="{{package_name}}/main.py",
                content='''"""Application FastAPI principale"""

from fastapi import FastAPI
from .routers import api
from .database import engine
from .models import Base

# Création tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="{{project_name}}",
    description="{{description}}",
    version="{{version}}"
)

app.include_router(api.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Endpoint racine"""
    return {"message": "{{project_name}} API", "version": "{{version}}"}
'''
            ),
            TemplateFile(
                path="{{package_name}}/models.py",
                content='''"""Modèles SQLAlchemy"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .database import Base


class Item(Base):
    """Modèle d'exemple"""
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    created_at = Column(DateTime, default=func.now())
'''
            ),
            TemplateFile(
                path="{{package_name}}/database.py",
                content='''"""Configuration base de données"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./{{package_name}}.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dépendance base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''
            ),
            TemplateFile(
                path="{{package_name}}/routers/__init__.py",
                content="",
                is_template=False
            ),
            TemplateFile(
                path="{{package_name}}/routers/api.py",
                content='''"""Routeurs API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Item

router = APIRouter()


@router.get("/items/")
async def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Liste des items"""
    items = db.query(Item).offset(skip).limit(limit).all()
    return items


@router.get("/items/{item_id}")
async def read_item(item_id: int, db: Session = Depends(get_db)):
    """Récupère un item"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
'''
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
                    "dev": self.dev_dependencies,
                    "postgres": ["psycopg2-binary>=2.9.0"],
                    "redis": ["redis>=4.0.0"]
                }
            },
            "build-system": {
                "requires": ["setuptools>=61.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            }
        }