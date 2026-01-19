"""
Monitoring et suivi des ressources pour environnements éphémères

Fournit le suivi en temps réel des ressources, l'intégration
avec les cgroups v2, et un système d'alertes.
"""

import asyncio
import logging
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List, Callable, Any

from .models import (
    EphemeralEnvironment,
    ResourceUsage,
    EphemeralStatus
)
from .exceptions import EphemeralException
from .cgroups import cgroup_manager, CgroupInfo

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Niveaux d'alerte pour le monitoring"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types d'alertes"""
    MEMORY_HIGH = "memory_high"
    MEMORY_EXCEEDED = "memory_exceeded"
    CPU_HIGH = "cpu_high"
    DISK_HIGH = "disk_high"
    DISK_EXCEEDED = "disk_exceeded"
    PROCESSES_EXCEEDED = "processes_exceeded"
    ENVIRONMENT_STALE = "environment_stale"
    ENVIRONMENT_FAILED = "environment_failed"


@dataclass
class Alert:
    """Alerte de monitoring"""
    level: AlertLevel
    alert_type: AlertType
    env_id: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringMetrics:
    """Métriques agrégées pour un environnement"""
    env_id: str
    timestamp: datetime

    # Métriques mémoire
    memory_current_mb: float = 0.0
    memory_peak_mb: float = 0.0
    memory_limit_mb: Optional[float] = None
    memory_usage_percent: float = 0.0

    # Métriques CPU
    cpu_usage_percent: float = 0.0
    cpu_usage_seconds: float = 0.0

    # Métriques disque
    disk_usage_mb: float = 0.0
    disk_limit_mb: Optional[float] = None

    # Métriques processus
    active_processes: int = 0
    max_processes: Optional[int] = None

    # Métriques I/O (depuis cgroups)
    io_read_bytes: int = 0
    io_write_bytes: int = 0

    # État
    is_healthy: bool = True
    alerts: List[Alert] = field(default_factory=list)

    def to_prometheus_format(self) -> str:
        """Exporte les métriques au format Prometheus"""
        lines = []
        prefix = "gestvenv_ephemeral"
        labels = f'env_id="{self.env_id}"'

        lines.append(f'{prefix}_memory_current_bytes{{{labels}}} {int(self.memory_current_mb * 1024 * 1024)}')
        lines.append(f'{prefix}_memory_peak_bytes{{{labels}}} {int(self.memory_peak_mb * 1024 * 1024)}')
        if self.memory_limit_mb:
            lines.append(f'{prefix}_memory_limit_bytes{{{labels}}} {int(self.memory_limit_mb * 1024 * 1024)}')
        lines.append(f'{prefix}_cpu_usage_percent{{{labels}}} {self.cpu_usage_percent}')
        lines.append(f'{prefix}_disk_usage_bytes{{{labels}}} {int(self.disk_usage_mb * 1024 * 1024)}')
        lines.append(f'{prefix}_active_processes{{{labels}}} {self.active_processes}')
        lines.append(f'{prefix}_io_read_bytes{{{labels}}} {self.io_read_bytes}')
        lines.append(f'{prefix}_io_write_bytes{{{labels}}} {self.io_write_bytes}')
        lines.append(f'{prefix}_healthy{{{labels}}} {1 if self.is_healthy else 0}')

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "env_id": self.env_id,
            "timestamp": self.timestamp.isoformat(),
            "memory": {
                "current_mb": self.memory_current_mb,
                "peak_mb": self.memory_peak_mb,
                "limit_mb": self.memory_limit_mb,
                "usage_percent": self.memory_usage_percent,
            },
            "cpu": {
                "usage_percent": self.cpu_usage_percent,
                "usage_seconds": self.cpu_usage_seconds,
            },
            "disk": {
                "usage_mb": self.disk_usage_mb,
                "limit_mb": self.disk_limit_mb,
            },
            "processes": {
                "active": self.active_processes,
                "max": self.max_processes,
            },
            "io": {
                "read_bytes": self.io_read_bytes,
                "write_bytes": self.io_write_bytes,
            },
            "is_healthy": self.is_healthy,
            "alerts_count": len(self.alerts),
        }


# Type pour les callbacks d'alerte
AlertCallback = Callable[[Alert], None]


class ResourceTracker:
    """Suivi des ressources en temps réel avec intégration cgroups"""

    def __init__(self, manager):
        self.manager = manager
        self.monitoring_task: Optional[asyncio.Task] = None
        self.resource_history: Dict[str, List[ResourceUsage]] = {}
        self.metrics_history: Dict[str, List[MonitoringMetrics]] = {}
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[AlertCallback] = []
        self._shutdown = False

        # Seuils d'alerte (pourcentages)
        self.memory_warning_threshold = 80  # % de la limite
        self.memory_critical_threshold = 95
        self.cpu_warning_threshold = 80
        self.disk_warning_threshold = 80
        self.disk_critical_threshold = 95

        # Durée maximale d'inactivité avant alerte (secondes)
        self.stale_threshold_seconds = 300  # 5 minutes

    def register_alert_callback(self, callback: AlertCallback) -> None:
        """Enregistre un callback pour les alertes"""
        self.alert_callbacks.append(callback)

    def unregister_alert_callback(self, callback: AlertCallback) -> None:
        """Supprime un callback"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)

    async def _emit_alert(self, alert: Alert) -> None:
        """Émet une alerte vers tous les callbacks enregistrés"""
        self.alerts.append(alert)

        # Limiter l'historique des alertes
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-500:]

        # Notifier les callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        # Log selon le niveau
        if alert.level == AlertLevel.CRITICAL:
            logger.error(f"[CRITICAL] {alert.message}")
        elif alert.level == AlertLevel.WARNING:
            logger.warning(f"[WARNING] {alert.message}")
        else:
            logger.info(f"[INFO] {alert.message}")
    
    async def start(self):
        """Démarrage du monitoring"""
        if self.monitoring_task is None:
            logger.info("Starting resource monitoring")
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Arrêt du monitoring"""
        self._shutdown = True
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        logger.info("Resource monitoring stopped")
    
    async def start_monitoring(self, env: EphemeralEnvironment):
        """Démarrage du monitoring pour un environnement spécifique"""
        if env.id not in self.resource_history:
            self.resource_history[env.id] = []
        logger.debug(f"Started monitoring for environment {env.id}")
    
    async def stop_monitoring(self, env_id: str):
        """Arrêt du monitoring pour un environnement"""
        if env_id in self.resource_history:
            # Conservation de l'historique pendant un court moment
            history = self.resource_history[env_id]
            if history:
                logger.debug(f"Stopped monitoring for {env_id}, peak memory: {max(r.memory_mb for r in history):.1f}MB")
            del self.resource_history[env_id]
    
    async def get_current_usage(self, env: EphemeralEnvironment) -> Optional[ResourceUsage]:
        """Récupération de l'usage actuel d'un environnement"""
        try:
            return await self._measure_environment_resources(env)
        except Exception as e:
            logger.warning(f"Failed to get usage for {env.id}: {e}")
            return None
    
    async def get_resource_history(self, env_id: str) -> List[ResourceUsage]:
        """Récupération de l'historique des ressources"""
        return self.resource_history.get(env_id, [])

    async def get_metrics(self, env: EphemeralEnvironment) -> MonitoringMetrics:
        """Récupère les métriques complètes d'un environnement

        Combine les métriques psutil et cgroups pour une vue complète.
        """
        metrics = MonitoringMetrics(
            env_id=env.id,
            timestamp=datetime.now()
        )

        # Métriques de base via psutil
        usage = await self._measure_environment_resources(env)
        if usage:
            metrics.memory_current_mb = usage.memory_mb
            metrics.cpu_usage_percent = usage.cpu_percent
            metrics.disk_usage_mb = usage.disk_mb
            metrics.active_processes = usage.active_processes

        # Métriques enrichies via cgroups
        if hasattr(env, 'cgroup_path') and env.cgroup_path:
            cgroup_stats = await cgroup_manager.get_statistics(env.id)
            if cgroup_stats:
                # Mémoire depuis cgroups (plus précis)
                if "memory" in cgroup_stats:
                    mem_stats = cgroup_stats["memory"]
                    if "current_bytes" in mem_stats:
                        metrics.memory_current_mb = mem_stats["current_bytes"] / (1024 * 1024)
                    if "peak_bytes" in mem_stats:
                        metrics.memory_peak_mb = mem_stats["peak_bytes"] / (1024 * 1024)
                    if "max_bytes" in mem_stats and mem_stats["max_bytes"]:
                        metrics.memory_limit_mb = mem_stats["max_bytes"] / (1024 * 1024)

                # CPU depuis cgroups
                if "cpu" in cgroup_stats:
                    cpu_stats = cgroup_stats["cpu"]
                    if "usage_usec" in cpu_stats:
                        metrics.cpu_usage_seconds = cpu_stats["usage_usec"] / 1_000_000

                # I/O depuis cgroups
                if "io" in cgroup_stats:
                    io_stats = cgroup_stats["io"]
                    # Agréger les stats de tous les devices
                    for key, value in io_stats.items():
                        if key.startswith("device_") and isinstance(value, dict):
                            metrics.io_read_bytes += value.get("rbytes", 0)
                            metrics.io_write_bytes += value.get("wbytes", 0)

                # PIDs depuis cgroups
                if "pids" in cgroup_stats:
                    pids_stats = cgroup_stats["pids"]
                    if "current" in pids_stats:
                        metrics.active_processes = pids_stats["current"]
                    if "max" in pids_stats and pids_stats["max"]:
                        metrics.max_processes = pids_stats["max"]

        # Limites depuis l'environnement
        if env.resource_limits:
            if env.resource_limits.max_memory and not metrics.memory_limit_mb:
                metrics.memory_limit_mb = env.resource_limits.max_memory
            if env.resource_limits.max_disk:
                metrics.disk_limit_mb = env.resource_limits.max_disk
            if env.resource_limits.max_processes and not metrics.max_processes:
                metrics.max_processes = env.resource_limits.max_processes

        # Calculer le pourcentage d'utilisation mémoire
        if metrics.memory_limit_mb and metrics.memory_limit_mb > 0:
            metrics.memory_usage_percent = (
                metrics.memory_current_mb / metrics.memory_limit_mb * 100
            )

        # Vérifier la santé et générer les alertes
        await self._evaluate_health(env, metrics)

        return metrics

    async def _evaluate_health(self, env: EphemeralEnvironment, metrics: MonitoringMetrics) -> None:
        """Évalue la santé et génère les alertes si nécessaire"""
        metrics.is_healthy = True

        # Vérification mémoire
        if metrics.memory_limit_mb and metrics.memory_limit_mb > 0:
            usage_percent = metrics.memory_usage_percent

            if usage_percent >= self.memory_critical_threshold:
                metrics.is_healthy = False
                alert = Alert(
                    level=AlertLevel.CRITICAL,
                    alert_type=AlertType.MEMORY_EXCEEDED,
                    env_id=env.id,
                    message=f"Environment {env.id} memory critical: {usage_percent:.1f}% of limit",
                    details={
                        "current_mb": metrics.memory_current_mb,
                        "limit_mb": metrics.memory_limit_mb,
                        "usage_percent": usage_percent
                    }
                )
                metrics.alerts.append(alert)
                await self._emit_alert(alert)

            elif usage_percent >= self.memory_warning_threshold:
                alert = Alert(
                    level=AlertLevel.WARNING,
                    alert_type=AlertType.MEMORY_HIGH,
                    env_id=env.id,
                    message=f"Environment {env.id} memory high: {usage_percent:.1f}% of limit",
                    details={
                        "current_mb": metrics.memory_current_mb,
                        "limit_mb": metrics.memory_limit_mb,
                        "usage_percent": usage_percent
                    }
                )
                metrics.alerts.append(alert)
                await self._emit_alert(alert)

        # Vérification CPU
        if metrics.cpu_usage_percent >= self.cpu_warning_threshold:
            alert = Alert(
                level=AlertLevel.WARNING,
                alert_type=AlertType.CPU_HIGH,
                env_id=env.id,
                message=f"Environment {env.id} CPU high: {metrics.cpu_usage_percent:.1f}%",
                details={"cpu_percent": metrics.cpu_usage_percent}
            )
            metrics.alerts.append(alert)
            await self._emit_alert(alert)

        # Vérification disque
        if metrics.disk_limit_mb and metrics.disk_limit_mb > 0:
            disk_percent = metrics.disk_usage_mb / metrics.disk_limit_mb * 100

            if disk_percent >= self.disk_critical_threshold:
                metrics.is_healthy = False
                alert = Alert(
                    level=AlertLevel.CRITICAL,
                    alert_type=AlertType.DISK_EXCEEDED,
                    env_id=env.id,
                    message=f"Environment {env.id} disk critical: {disk_percent:.1f}% of limit",
                    details={
                        "current_mb": metrics.disk_usage_mb,
                        "limit_mb": metrics.disk_limit_mb
                    }
                )
                metrics.alerts.append(alert)
                await self._emit_alert(alert)

            elif disk_percent >= self.disk_warning_threshold:
                alert = Alert(
                    level=AlertLevel.WARNING,
                    alert_type=AlertType.DISK_HIGH,
                    env_id=env.id,
                    message=f"Environment {env.id} disk high: {disk_percent:.1f}% of limit",
                    details={
                        "current_mb": metrics.disk_usage_mb,
                        "limit_mb": metrics.disk_limit_mb
                    }
                )
                metrics.alerts.append(alert)
                await self._emit_alert(alert)

        # Vérification processus
        if metrics.max_processes and metrics.active_processes >= metrics.max_processes:
            metrics.is_healthy = False
            alert = Alert(
                level=AlertLevel.CRITICAL,
                alert_type=AlertType.PROCESSES_EXCEEDED,
                env_id=env.id,
                message=f"Environment {env.id} process limit reached: {metrics.active_processes}/{metrics.max_processes}",
                details={
                    "active": metrics.active_processes,
                    "max": metrics.max_processes
                }
            )
            metrics.alerts.append(alert)
            await self._emit_alert(alert)

        # Vérification inactivité
        if hasattr(env, 'last_activity') and env.last_activity:
            inactive_seconds = (datetime.now() - env.last_activity).total_seconds()
            if inactive_seconds > self.stale_threshold_seconds:
                alert = Alert(
                    level=AlertLevel.WARNING,
                    alert_type=AlertType.ENVIRONMENT_STALE,
                    env_id=env.id,
                    message=f"Environment {env.id} inactive for {inactive_seconds:.0f}s",
                    details={"inactive_seconds": inactive_seconds}
                )
                metrics.alerts.append(alert)
                await self._emit_alert(alert)

    async def get_all_metrics(self) -> List[MonitoringMetrics]:
        """Récupère les métriques de tous les environnements actifs"""
        metrics_list = []

        try:
            environments = await self.manager.list_environments()

            for env in environments:
                if env.is_active:
                    metrics = await self.get_metrics(env)
                    metrics_list.append(metrics)

        except Exception as e:
            logger.error(f"Failed to get all metrics: {e}")

        return metrics_list

    async def export_prometheus_metrics(self) -> str:
        """Exporte toutes les métriques au format Prometheus"""
        lines = []
        metrics_list = await self.get_all_metrics()

        for metrics in metrics_list:
            lines.append(metrics.to_prometheus_format())

        # Métriques globales
        lines.append(f"gestvenv_ephemeral_environments_total {len(metrics_list)}")
        lines.append(f"gestvenv_ephemeral_alerts_total {len(self.alerts)}")

        return "\n".join(lines)

    def get_recent_alerts(
        self,
        env_id: Optional[str] = None,
        level: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Récupère les alertes récentes

        Args:
            env_id: Filtrer par environnement
            level: Filtrer par niveau
            limit: Nombre max d'alertes

        Returns:
            Liste d'alertes filtrées
        """
        alerts = self.alerts

        if env_id:
            alerts = [a for a in alerts if a.env_id == env_id]

        if level:
            alerts = [a for a in alerts if a.level == level]

        return alerts[-limit:]
    
    async def _monitoring_loop(self):
        """Boucle principale de monitoring"""
        while not self._shutdown:
            try:
                # Monitoring de tous les environnements actifs
                environments = await self.manager.list_environments()
                
                for env in environments:
                    if env.is_active and env.id in self.resource_history:
                        usage = await self._measure_environment_resources(env)
                        if usage:
                            await self._record_usage(env, usage)
                
                # Nettoyage de l'historique ancien
                await self._cleanup_old_history()
                
                # Attente avant la prochaine mesure
                await asyncio.sleep(self.manager.config.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)  # Attente plus longue en cas d'erreur
    
    async def _measure_environment_resources(self, env: EphemeralEnvironment) -> Optional[ResourceUsage]:
        """Mesure des ressources d'un environnement"""
        try:
            # Mesure de l'usage disque
            disk_usage_mb = 0.0
            if env.storage_path and env.storage_path.exists():
                disk_usage_mb = await self._get_directory_size(env.storage_path)
            
            # Mesure de l'usage mémoire et CPU
            memory_mb = 0.0
            cpu_percent = 0.0
            active_processes = 0
            
            if env.pid:
                try:
                    # Processus principal
                    main_process = psutil.Process(env.pid)
                    if main_process.is_running():
                        memory_mb += main_process.memory_info().rss / (1024 * 1024)
                        cpu_percent += main_process.cpu_percent()
                        active_processes += 1
                        
                        # Processus enfants
                        for child in main_process.children(recursive=True):
                            try:
                                if child.is_running():
                                    memory_mb += child.memory_info().rss / (1024 * 1024)
                                    cpu_percent += child.cpu_percent()
                                    active_processes += 1
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Processus terminé ou accès refusé
                    pass
            
            return ResourceUsage(
                memory_mb=memory_mb,
                disk_mb=disk_usage_mb,
                cpu_percent=cpu_percent,
                active_processes=active_processes
            )
            
        except Exception as e:
            logger.warning(f"Failed to measure resources for {env.id}: {e}")
            return None
    
    async def _get_directory_size(self, path: Path) -> float:
        """Calcul de la taille d'un répertoire en MB"""
        try:
            def get_size():
                total_size = 0
                for dirpath, dirnames, filenames in path.walk():
                    for filename in filenames:
                        try:
                            file_path = dirpath / filename
                            total_size += file_path.stat().st_size
                        except (OSError, FileNotFoundError):
                            continue
                return total_size / (1024 * 1024)  # Conversion en MB
            
            # Exécution dans un thread pour éviter le blocage
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, get_size)
            
        except Exception:
            return 0.0
    
    async def _record_usage(self, env: EphemeralEnvironment, usage: ResourceUsage):
        """Enregistrement d'une mesure d'usage"""
        # Ajout à l'historique
        if env.id in self.resource_history:
            self.resource_history[env.id].append(usage)
            
            # Limitation de la taille de l'historique (30 dernières mesures)
            if len(self.resource_history[env.id]) > 30:
                self.resource_history[env.id] = self.resource_history[env.id][-30:]
        
        # Mise à jour des pics dans l'environnement
        if env.peak_memory_mb is None or usage.memory_mb > env.peak_memory_mb:
            env.peak_memory_mb = usage.memory_mb
        
        if env.peak_disk_mb is None or usage.disk_mb > env.peak_disk_mb:
            env.peak_disk_mb = usage.disk_mb
        
        # Vérification des limites
        await self._check_resource_limits(env, usage)
    
    async def _check_resource_limits(self, env: EphemeralEnvironment, usage: ResourceUsage):
        """Vérification des limites de ressources"""
        limits = env.resource_limits
        
        # Vérification mémoire
        if limits.max_memory and usage.memory_mb > limits.max_memory:
            logger.warning(
                f"Environment {env.id} exceeded memory limit: "
                f"{usage.memory_mb:.1f}MB > {limits.max_memory}MB"
            )
            # TODO: Déclencher action de limite (warning, throttling, cleanup)
        
        # Vérification disque
        if limits.max_disk and usage.disk_mb > limits.max_disk:
            logger.warning(
                f"Environment {env.id} exceeded disk limit: "
                f"{usage.disk_mb:.1f}MB > {limits.max_disk}MB"
            )
        
        # Vérification nombre de processus
        if usage.active_processes > limits.max_processes:
            logger.warning(
                f"Environment {env.id} exceeded process limit: "
                f"{usage.active_processes} > {limits.max_processes}"
            )
    
    async def _cleanup_old_history(self):
        """Nettoyage de l'historique ancien"""
        current_time = time.time()
        
        for env_id, history in list(self.resource_history.items()):
            # Suppression des mesures de plus de 5 minutes
            cutoff_time = current_time - 300
            
            filtered_history = [
                usage for usage in history
                if usage.timestamp.timestamp() > cutoff_time
            ]
            
            if filtered_history:
                self.resource_history[env_id] = filtered_history
            else:
                # Environnement probablement terminé
                del self.resource_history[env_id]


class PerformanceMonitor:
    """Monitoring des performances système globales"""
    
    def __init__(self):
        self.system_metrics: Dict[str, float] = {}
    
    async def get_system_load(self) -> Dict[str, float]:
        """Récupération de la charge système"""
        try:
            # Charge CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Utilisation mémoire
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Utilisation disque
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_available_gb = disk.free / (1024**3)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": memory_available_gb,
                "disk_percent": disk_percent,
                "disk_available_gb": disk_available_gb,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    async def check_system_health(self) -> bool:
        """Vérification de la santé du système"""
        try:
            metrics = await self.get_system_load()
            
            # Critères de santé
            if metrics.get("cpu_percent", 0) > 90:
                logger.warning("High CPU usage detected")
                return False
            
            if metrics.get("memory_percent", 0) > 95:
                logger.warning("High memory usage detected")
                return False
            
            if metrics.get("disk_percent", 0) > 95:
                logger.warning("High disk usage detected")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return False