"""
Environment models for API
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class BackendType(str, Enum):
    """Backend types"""
    PIP = "pip"
    UV = "uv"
    POETRY = "poetry"
    PDM = "pdm"


class Environment(BaseModel):
    """Environment model for API"""
    id: str
    name: str
    path: str
    python_version: str
    backend: BackendType
    is_active: bool = False
    created_at: datetime
    package_count: int = 0
    metadata: Dict[str, Any] = {}


class CreateEnvironmentRequest(BaseModel):
    """Request model for creating environment"""
    name: str
    python_version: Optional[str] = None
    backend: Optional[BackendType] = BackendType.UV
    packages: Optional[List[str]] = None
    template: Optional[str] = None


class EnvironmentResponse(BaseModel):
    """Response model for environment"""
    id: str
    name: str
    path: str
    python_version: str
    backend: str
    is_active: bool
    created_at: str
    package_count: int
    metadata: Dict[str, Any] = {}