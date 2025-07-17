"""
Schémas Pydantic pour les modèles de données GestVenv Web API.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class EnvironmentStatus(str, Enum):
    """Statut d'un environnement."""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CREATING = "creating"
    DELETING = "deleting"


class BackendType(str, Enum):
    """Types de backends supportés."""
    PIP = "pip"
    UV = "uv"
    POETRY = "poetry"
    PDM = "pdm"
    AUTO = "auto"


class PackageStatus(str, Enum):
    """Statut d'un package."""
    INSTALLED = "installed"
    OUTDATED = "outdated"
    MISSING = "missing"


# ===== Schémas pour les environnements =====

class EnvironmentBase(BaseModel):
    """Base pour les environnements."""
    name: str = Field(..., min_length=1, max_length=100)
    python_version: Optional[str] = Field(None, pattern=r'^\d+\.\d+(\.\d+)?$')
    backend: BackendType = BackendType.AUTO


class EnvironmentCreate(EnvironmentBase):
    """Schéma pour créer un environnement."""
    template: Optional[str] = None
    packages: Optional[List[str]] = Field(default_factory=list)
    path: Optional[str] = None
    author: Optional[str] = None
    email: Optional[str] = None
    version: str = "0.1.0"
    output: Optional[str] = None


class EnvironmentUpdate(BaseModel):
    """Schéma pour mettre à jour un environnement."""
    python_version: Optional[str] = Field(None, pattern=r'^\d+\.\d+(\.\d+)?$')
    backend: Optional[BackendType] = None


class Environment(EnvironmentBase):
    """Schéma complet d'un environnement."""
    path: str
    status: EnvironmentStatus
    created_at: datetime
    last_used: Optional[datetime] = None
    package_count: int = 0
    size_mb: float = 0.0
    active: bool = False
    
    class Config:
        from_attributes = True


class EnvironmentDetails(Environment):
    """Détails complets d'un environnement."""
    packages: List["Package"] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    health_info: Dict[str, Any] = Field(default_factory=dict)


# ===== Schémas pour les packages =====

class PackageBase(BaseModel):
    """Base pour les packages."""
    name: str = Field(..., min_length=1)
    version: Optional[str] = None


class PackageInstall(PackageBase):
    """Schéma pour installer un package."""
    group: Optional[str] = "main"
    editable: bool = False
    upgrade: bool = False


class Package(PackageBase):
    """Schéma complet d'un package."""
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    status: PackageStatus
    group: str = "main"
    size_mb: float = 0.0
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


# ===== Schémas pour le cache =====

class CacheInfo(BaseModel):
    """Informations sur le cache."""
    total_size_mb: float
    package_count: int
    hit_rate: float
    location: str
    last_cleanup: Optional[datetime] = None


class CachePackage(BaseModel):
    """Package dans le cache."""
    name: str
    version: str
    size_mb: float
    platform: str
    cached_at: datetime


class CacheExport(BaseModel):
    """Configuration d'export du cache."""
    output_path: str
    compress: bool = True
    include_metadata: bool = True


class CacheImport(BaseModel):
    """Configuration d'import du cache."""
    source_path: str
    merge: bool = False
    verify: bool = True


# ===== Schémas pour le système =====

class SystemInfo(BaseModel):
    """Informations système."""
    os: str
    python_version: str
    gestvenv_version: str
    backends_available: List[BackendType]
    disk_usage: Dict[str, float]
    memory_usage: Dict[str, float]


class SystemHealth(BaseModel):
    """Santé du système."""
    status: str
    checks: List[Dict[str, Any]]
    recommendations: List[str]
    
    
# ===== Schémas pour les templates =====

class TemplateInfo(BaseModel):
    """Informations sur un template."""
    name: str
    description: str
    category: str
    dependencies: List[str]
    files: List[str]
    variables: List[str]


class TemplateCreate(BaseModel):
    """Création depuis un template."""
    template_name: str
    project_name: str
    author: Optional[str] = None
    email: Optional[str] = None
    version: str = "0.1.0"
    python_version: Optional[str] = None
    backend: BackendType = BackendType.AUTO
    output_path: Optional[str] = None
    variables: Dict[str, str] = Field(default_factory=dict)


# ===== Schémas pour les opérations =====

class OperationStatus(str, Enum):
    """Statut d'une opération."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Operation(BaseModel):
    """Opération en cours ou terminée."""
    id: str
    type: str
    status: OperationStatus
    progress: float = 0.0
    message: str = ""
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ===== Schémas de réponse =====

class ApiResponse(BaseModel):
    """Réponse API générique."""
    success: bool
    message: str
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    """Réponse paginée."""
    items: List[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


# ===== WebSocket Messages =====

class WSMessageType(str, Enum):
    """Types de messages WebSocket."""
    ENVIRONMENT_CREATED = "environment_created"
    ENVIRONMENT_DELETED = "environment_deleted"
    ENVIRONMENT_UPDATED = "environment_updated"
    PACKAGE_INSTALLED = "package_installed"
    PACKAGE_UNINSTALLED = "package_uninstalled"
    OPERATION_PROGRESS = "operation_progress"
    OPERATION_COMPLETED = "operation_completed"
    CACHE_UPDATED = "cache_updated"


class WSMessage(BaseModel):
    """Message WebSocket."""
    type: WSMessageType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


# Résoudre les références circulaires
EnvironmentDetails.model_rebuild()