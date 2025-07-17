"""
Modèles de données pour les environnements éphémères
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List, Any

from ..models import BackendType as Backend


class EphemeralStatus(Enum):
    """État d'un environnement éphémère"""
    PENDING = "pending"
    CREATING = "creating"
    READY = "ready"
    RUNNING = "running"
    CLEANING_UP = "cleaning_up"
    DESTROYED = "destroyed"
    FAILED = "failed"


class IsolationLevel(Enum):
    """Niveau d'isolation de sécurité"""
    PROCESS = "process"        # Isolation par processus (défaut)
    NAMESPACE = "namespace"    # Isolation par namespaces Linux
    CONTAINER = "container"    # Isolation par container Docker/Podman
    CHROOT = "chroot"         # Isolation par chroot jail


class StorageBackend(Enum):
    """Backend de stockage pour environnements éphémères"""
    DISK = "disk"         # Stockage disque standard
    TMPFS = "tmpfs"       # Stockage en tmpfs (RAM)
    MEMORY = "memory"     # Stockage en mémoire pure


class SecurityMode(Enum):
    """Mode de sécurité"""
    PERMISSIVE = "permissive"  # Accès réseau et système autorisé
    RESTRICTED = "restricted"   # Accès limité (défaut)
    SANDBOXED = "sandboxed"    # Isolation maximale


@dataclass
class ResourceLimits:
    """Limites de ressources pour un environnement"""
    max_memory: Optional[int] = None  # MB
    max_disk: Optional[int] = None    # MB
    max_processes: int = 10
    max_cpu_percent: Optional[float] = None
    network_access: bool = True


@dataclass
class EphemeralEnvironment:
    """Modèle d'environnement éphémère"""
    # Identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    
    # Configuration de base
    backend: Backend = Backend.UV
    python_version: str = "3.11"
    
    # Configuration de cycle de vie
    ttl: Optional[int] = None        # Time To Live en secondes
    max_idle_time: int = 300         # 5 minutes par défaut
    auto_cleanup: bool = True
    
    # Ressources et sécurité
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    isolation_level: IsolationLevel = IsolationLevel.PROCESS
    security_mode: SecurityMode = SecurityMode.RESTRICTED
    
    # État runtime
    status: EphemeralStatus = EphemeralStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    cleanup_scheduled: bool = False
    
    # Chemins et processus
    storage_path: Optional[Path] = None
    venv_path: Optional[Path] = None
    pid: Optional[int] = None
    container_id: Optional[str] = None
    
    # Isolation (nouveaux attributs)
    isolation_script: Optional[str] = None
    chroot_path: Optional[Path] = None
    
    # Métadonnées
    tags: Dict[str, str] = field(default_factory=dict)
    parent_session: Optional[str] = None
    packages: List[str] = field(default_factory=list)
    
    # Statistiques
    creation_time: Optional[float] = None
    cleanup_time: Optional[float] = None
    peak_memory_mb: Optional[float] = None
    peak_disk_mb: Optional[float] = None

    def __post_init__(self):
        """Post-initialisation"""
        if self.name is None:
            self.name = f"ephemeral-{int(self.created_at.timestamp())}"
    
    @property
    def is_active(self) -> bool:
        """Vérifie si l'environnement est actif"""
        return self.status in [
            EphemeralStatus.READY,
            EphemeralStatus.RUNNING
        ]
    
    @property
    def age_seconds(self) -> int:
        """Âge de l'environnement en secondes"""
        return int((datetime.now() - self.created_at).total_seconds())
    
    @property
    def idle_seconds(self) -> int:
        """Temps d'inactivité en secondes"""
        return int((datetime.now() - self.last_activity).total_seconds())
    
    def update_activity(self):
        """Met à jour le timestamp de dernière activité"""
        self.last_activity = datetime.now()
    
    def is_expired(self) -> bool:
        """Vérifie si l'environnement a expiré"""
        if self.ttl is None:
            return False
        return self.age_seconds > self.ttl
    
    def is_idle_expired(self) -> bool:
        """Vérifie si l'environnement est inactif trop longtemps"""
        return self.idle_seconds > self.max_idle_time


@dataclass 
class EphemeralConfig:
    """Configuration globale pour environnements éphémères"""
    # Limites globales
    default_ttl: int = 3600              # 1 heure par défaut
    max_concurrent: int = 50             # Maximum d'environnements simultanés
    max_total_memory_mb: int = 8192      # 8GB maximum total
    max_total_disk_mb: int = 20480       # 20GB maximum total
    
    # Nettoyage
    cleanup_interval: int = 60           # Nettoyage toutes les minutes
    force_cleanup_after: int = 7200      # Nettoyage forcé après 2h
    
    # Stockage
    storage_backend: StorageBackend = StorageBackend.TMPFS
    base_storage_path: Optional[Path] = None
    
    # Sécurité par défaut
    default_security_mode: SecurityMode = SecurityMode.RESTRICTED
    default_isolation_level: IsolationLevel = IsolationLevel.PROCESS
    
    # Monitoring
    enable_monitoring: bool = True
    monitoring_interval: int = 5         # Surveillance toutes les 5 secondes
    
    # Performance
    enable_preallocation: bool = True    # Pré-allocation d'environnements
    pool_size: int = 3                   # Taille du pool de pré-allocation
    enable_template_cache: bool = True   # Cache des templates
    
    def __post_init__(self):
        """Post-initialisation de la configuration"""
        if self.base_storage_path is None:
            if self.storage_backend == StorageBackend.TMPFS:
                self.base_storage_path = Path("/tmp/gestvenv-ephemeral")
            elif self.storage_backend == StorageBackend.MEMORY:
                self.base_storage_path = Path("/dev/shm/gestvenv-ephemeral")
            else:
                self.base_storage_path = Path.home() / ".cache/gestvenv/ephemeral"


@dataclass
class OperationResult:
    """Résultat d'une opération dans un environnement éphémère"""
    returncode: int
    stdout: str
    stderr: str
    duration: float
    command: str
    success: bool = field(init=False)
    
    def __post_init__(self):
        self.success = self.returncode == 0


@dataclass
class ResourceUsage:
    """Usage des ressources d'un environnement"""
    memory_mb: float
    disk_mb: float
    cpu_percent: float
    active_processes: int
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CleanupReason:
    """Raison du nettoyage d'un environnement"""
    reason: str
    triggered_by: str
    forced: bool = False
    error: Optional[Exception] = None
    timestamp: datetime = field(default_factory=datetime.now)