"""
Module de gestion des cgroups v2 pour les environnements éphémères

Fournit des utilitaires pour limiter les ressources (CPU, mémoire, I/O)
des environnements éphémères en utilisant cgroups v2.
"""

import asyncio
import logging
import os
import pwd
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# Chemin racine des cgroups v2
CGROUP_ROOT = Path("/sys/fs/cgroup")


@dataclass
class ResourceLimits:
    """Configuration des limites de ressources"""
    # Mémoire
    max_memory_mb: Optional[int] = None  # Limite mémoire en MB
    memory_high_mb: Optional[int] = None  # Seuil d'avertissement
    swap_max_mb: Optional[int] = 0  # Limite swap (0 = désactivé)

    # CPU
    max_cpu_percent: Optional[int] = None  # % CPU max (100 = 1 core)
    cpu_weight: int = 100  # Poids relatif (1-10000, défaut 100)

    # I/O
    io_max_read_bps: Optional[int] = None  # Bytes/sec lecture
    io_max_write_bps: Optional[int] = None  # Bytes/sec écriture
    io_max_read_iops: Optional[int] = None  # IOPS lecture
    io_max_write_iops: Optional[int] = None  # IOPS écriture
    io_weight: int = 100  # Poids I/O (1-10000)

    # PIDs
    max_pids: Optional[int] = 100  # Nombre max de processus

    # Réseau (nécessite un namespace réseau)
    network_access: bool = True


@dataclass
class CgroupInfo:
    """Informations sur un cgroup"""
    name: str
    path: Path
    controllers: List[str] = field(default_factory=list)
    limits: Optional[ResourceLimits] = None

    # Statistiques
    memory_current: int = 0
    memory_peak: int = 0
    cpu_usage_usec: int = 0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    pids_current: int = 0


class CgroupsNotAvailableError(Exception):
    """cgroups v2 non disponible sur ce système"""
    pass


class CgroupOperationError(Exception):
    """Erreur lors d'une opération cgroup"""
    pass


class CgroupManager:
    """Gestionnaire des cgroups v2 pour les environnements éphémères"""

    GESTVENV_CGROUP_PREFIX = "gestvenv"

    def __init__(self):
        self._cgroups: Dict[str, CgroupInfo] = {}
        self._available: Optional[bool] = None
        self._controllers: List[str] = []

    @property
    def is_available(self) -> bool:
        """Vérifie si cgroups v2 est disponible"""
        if self._available is None:
            self._available = self._check_cgroups_v2()
        return self._available

    def _check_cgroups_v2(self) -> bool:
        """Vérification de la disponibilité de cgroups v2"""
        try:
            # Vérifier que le système de fichiers cgroup2 est monté
            if not CGROUP_ROOT.exists():
                logger.debug("cgroup root not found")
                return False

            # Vérifier que c'est bien cgroups v2 (unified hierarchy)
            cgroup_type_path = CGROUP_ROOT / "cgroup.type"
            controllers_path = CGROUP_ROOT / "cgroup.controllers"
            subtree_path = CGROUP_ROOT / "cgroup.subtree_control"

            # cgroups v2 a cgroup.controllers à la racine
            if not controllers_path.exists():
                # Vérifier via /proc/filesystems
                try:
                    with open("/proc/filesystems", "r") as f:
                        filesystems = f.read()
                        if "cgroup2" not in filesystems:
                            logger.debug("cgroup2 not in /proc/filesystems")
                            return False
                except Exception:
                    pass

                # Vérifier via /proc/mounts
                try:
                    with open("/proc/mounts", "r") as f:
                        mounts = f.read()
                        if "cgroup2" not in mounts:
                            logger.debug("cgroup2 not mounted")
                            return False
                except Exception:
                    return False

            # Charger les contrôleurs disponibles
            self._controllers = self._get_available_controllers()

            if not self._controllers:
                logger.debug("No cgroup controllers available")
                return False

            logger.info(f"cgroups v2 available with controllers: {self._controllers}")
            return True

        except Exception as e:
            logger.debug(f"cgroups v2 check failed: {e}")
            return False

    def _get_available_controllers(self) -> List[str]:
        """Récupère les contrôleurs cgroup disponibles"""
        controllers = []
        controllers_path = CGROUP_ROOT / "cgroup.controllers"

        try:
            if controllers_path.exists():
                content = controllers_path.read_text().strip()
                controllers = content.split()
        except Exception as e:
            logger.debug(f"Failed to read controllers: {e}")

        return controllers

    def _get_gestvenv_cgroup_root(self) -> Path:
        """Obtient le chemin racine des cgroups GestVenv"""
        # Utiliser user slice si disponible, sinon system slice
        user_id = os.getuid()

        # Essayer le user slice d'abord
        user_slice = CGROUP_ROOT / f"user.slice/user-{user_id}.slice"
        if user_slice.exists():
            return user_slice / self.GESTVENV_CGROUP_PREFIX

        # Fallback sur le cgroup racine (nécessite privilèges)
        return CGROUP_ROOT / self.GESTVENV_CGROUP_PREFIX

    async def create_cgroup(
        self,
        env_id: str,
        limits: ResourceLimits
    ) -> CgroupInfo:
        """Crée un cgroup pour un environnement éphémère

        Args:
            env_id: Identifiant de l'environnement
            limits: Limites de ressources à appliquer

        Returns:
            CgroupInfo avec les informations du cgroup créé
        """
        if not self.is_available:
            raise CgroupsNotAvailableError(
                "cgroups v2 not available on this system"
            )

        try:
            # Construire le chemin du cgroup
            cgroup_name = f"{self.GESTVENV_CGROUP_PREFIX}-{env_id[:8]}"
            gestvenv_root = self._get_gestvenv_cgroup_root()
            cgroup_path = gestvenv_root / cgroup_name

            # Créer le répertoire parent si nécessaire
            if not gestvenv_root.exists():
                await self._create_cgroup_directory(gestvenv_root)
                # Activer les contrôleurs sur le parent
                await self._enable_controllers(gestvenv_root.parent)

            # Créer le cgroup
            await self._create_cgroup_directory(cgroup_path)

            # Activer les contrôleurs nécessaires
            await self._enable_controllers(gestvenv_root)

            # Appliquer les limites
            await self._apply_limits(cgroup_path, limits)

            # Créer l'objet CgroupInfo
            cgroup_info = CgroupInfo(
                name=cgroup_name,
                path=cgroup_path,
                controllers=self._controllers.copy(),
                limits=limits
            )

            self._cgroups[env_id] = cgroup_info
            logger.info(f"Created cgroup: {cgroup_path}")

            return cgroup_info

        except PermissionError as e:
            raise CgroupOperationError(
                f"Permission denied creating cgroup. "
                f"Run as root or configure cgroup delegation: {e}"
            )
        except Exception as e:
            raise CgroupOperationError(f"Failed to create cgroup: {e}")

    async def _create_cgroup_directory(self, path: Path) -> None:
        """Crée un répertoire cgroup"""
        def mkdir():
            path.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, mkdir)

    async def _enable_controllers(self, parent_path: Path) -> None:
        """Active les contrôleurs sur un cgroup parent"""
        subtree_control = parent_path / "cgroup.subtree_control"

        if not subtree_control.exists():
            return

        # Contrôleurs à activer
        controllers_to_enable = []
        for controller in ["memory", "cpu", "io", "pids"]:
            if controller in self._controllers:
                controllers_to_enable.append(f"+{controller}")

        if not controllers_to_enable:
            return

        try:
            content = " ".join(controllers_to_enable)

            def write_controllers():
                subtree_control.write_text(content)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, write_controllers)

        except Exception as e:
            logger.debug(f"Failed to enable controllers on {parent_path}: {e}")

    async def _apply_limits(self, cgroup_path: Path, limits: ResourceLimits) -> None:
        """Applique les limites de ressources au cgroup"""

        # Limites mémoire
        if limits.max_memory_mb and "memory" in self._controllers:
            await self._write_cgroup_file(
                cgroup_path / "memory.max",
                str(limits.max_memory_mb * 1024 * 1024)
            )

            if limits.memory_high_mb:
                await self._write_cgroup_file(
                    cgroup_path / "memory.high",
                    str(limits.memory_high_mb * 1024 * 1024)
                )

            if limits.swap_max_mb is not None:
                await self._write_cgroup_file(
                    cgroup_path / "memory.swap.max",
                    str(limits.swap_max_mb * 1024 * 1024) if limits.swap_max_mb > 0 else "0"
                )

        # Limites CPU
        if limits.max_cpu_percent and "cpu" in self._controllers:
            # cpu.max format: "quota period"
            # quota en microsecondes par période
            period = 100000  # 100ms
            quota = int(period * limits.max_cpu_percent / 100)
            await self._write_cgroup_file(
                cgroup_path / "cpu.max",
                f"{quota} {period}"
            )

            await self._write_cgroup_file(
                cgroup_path / "cpu.weight",
                str(limits.cpu_weight)
            )

        # Limites I/O
        if "io" in self._controllers:
            if limits.io_weight:
                await self._write_cgroup_file(
                    cgroup_path / "io.weight",
                    f"default {limits.io_weight}"
                )

            # io.max nécessite le device major:minor
            # Format: "major:minor rbps=X wbps=Y riops=Z wiops=W"
            # On le fait pour le device root par défaut
            io_limits = []
            if limits.io_max_read_bps:
                io_limits.append(f"rbps={limits.io_max_read_bps}")
            if limits.io_max_write_bps:
                io_limits.append(f"wbps={limits.io_max_write_bps}")
            if limits.io_max_read_iops:
                io_limits.append(f"riops={limits.io_max_read_iops}")
            if limits.io_max_write_iops:
                io_limits.append(f"wiops={limits.io_max_write_iops}")

            if io_limits:
                # Obtenir le device du système de fichiers racine
                root_device = await self._get_root_device()
                if root_device:
                    io_max_content = f"{root_device} " + " ".join(io_limits)
                    await self._write_cgroup_file(
                        cgroup_path / "io.max",
                        io_max_content
                    )

        # Limite PIDs
        if limits.max_pids and "pids" in self._controllers:
            await self._write_cgroup_file(
                cgroup_path / "pids.max",
                str(limits.max_pids)
            )

    async def _write_cgroup_file(self, path: Path, content: str) -> None:
        """Écrit dans un fichier cgroup"""
        try:
            def write():
                path.write_text(content)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, write)
            logger.debug(f"Wrote to {path}: {content}")

        except Exception as e:
            logger.warning(f"Failed to write {path}: {e}")

    async def _get_root_device(self) -> Optional[str]:
        """Obtient le major:minor du device racine"""
        try:
            stat_info = os.stat("/")
            major = os.major(stat_info.st_dev)
            minor = os.minor(stat_info.st_dev)
            return f"{major}:{minor}"
        except Exception:
            return None

    async def add_process_to_cgroup(self, env_id: str, pid: int) -> bool:
        """Ajoute un processus au cgroup d'un environnement

        Args:
            env_id: Identifiant de l'environnement
            pid: PID du processus à ajouter

        Returns:
            True si succès
        """
        if env_id not in self._cgroups:
            logger.warning(f"No cgroup for environment {env_id}")
            return False

        cgroup_info = self._cgroups[env_id]
        procs_path = cgroup_info.path / "cgroup.procs"

        try:
            await self._write_cgroup_file(procs_path, str(pid))
            logger.debug(f"Added PID {pid} to cgroup {cgroup_info.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to add PID {pid} to cgroup: {e}")
            return False

    async def get_statistics(self, env_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les statistiques d'utilisation des ressources

        Args:
            env_id: Identifiant de l'environnement

        Returns:
            Dict avec les statistiques ou None
        """
        if env_id not in self._cgroups:
            return None

        cgroup_info = self._cgroups[env_id]
        stats = {}

        try:
            # Statistiques mémoire
            if "memory" in self._controllers:
                stats["memory"] = await self._read_memory_stats(cgroup_info.path)

            # Statistiques CPU
            if "cpu" in self._controllers:
                stats["cpu"] = await self._read_cpu_stats(cgroup_info.path)

            # Statistiques I/O
            if "io" in self._controllers:
                stats["io"] = await self._read_io_stats(cgroup_info.path)

            # Statistiques PIDs
            if "pids" in self._controllers:
                stats["pids"] = await self._read_pids_stats(cgroup_info.path)

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics for {env_id}: {e}")
            return None

    async def _read_memory_stats(self, cgroup_path: Path) -> Dict[str, Any]:
        """Lit les statistiques mémoire"""
        stats = {}

        try:
            # Utilisation courante
            current_path = cgroup_path / "memory.current"
            if current_path.exists():
                stats["current_bytes"] = int(current_path.read_text().strip())

            # Pic d'utilisation
            peak_path = cgroup_path / "memory.peak"
            if peak_path.exists():
                stats["peak_bytes"] = int(peak_path.read_text().strip())

            # Limite
            max_path = cgroup_path / "memory.max"
            if max_path.exists():
                max_val = max_path.read_text().strip()
                stats["max_bytes"] = int(max_val) if max_val != "max" else None

            # Statistiques détaillées
            stat_path = cgroup_path / "memory.stat"
            if stat_path.exists():
                for line in stat_path.read_text().strip().split("\n"):
                    parts = line.split()
                    if len(parts) == 2:
                        stats[f"stat_{parts[0]}"] = int(parts[1])

        except Exception as e:
            logger.debug(f"Error reading memory stats: {e}")

        return stats

    async def _read_cpu_stats(self, cgroup_path: Path) -> Dict[str, Any]:
        """Lit les statistiques CPU"""
        stats = {}

        try:
            # Statistiques CPU
            stat_path = cgroup_path / "cpu.stat"
            if stat_path.exists():
                for line in stat_path.read_text().strip().split("\n"):
                    parts = line.split()
                    if len(parts) == 2:
                        stats[parts[0]] = int(parts[1])

            # Pression CPU (si disponible)
            pressure_path = cgroup_path / "cpu.pressure"
            if pressure_path.exists():
                stats["pressure"] = pressure_path.read_text().strip()

        except Exception as e:
            logger.debug(f"Error reading CPU stats: {e}")

        return stats

    async def _read_io_stats(self, cgroup_path: Path) -> Dict[str, Any]:
        """Lit les statistiques I/O"""
        stats = {}

        try:
            stat_path = cgroup_path / "io.stat"
            if stat_path.exists():
                content = stat_path.read_text().strip()
                stats["raw"] = content

                # Parser les stats par device
                for line in content.split("\n"):
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        device = parts[0]
                        device_stats = {}
                        for part in parts[1:]:
                            if "=" in part:
                                key, value = part.split("=")
                                device_stats[key] = int(value)
                        stats[f"device_{device}"] = device_stats

        except Exception as e:
            logger.debug(f"Error reading I/O stats: {e}")

        return stats

    async def _read_pids_stats(self, cgroup_path: Path) -> Dict[str, Any]:
        """Lit les statistiques PIDs"""
        stats = {}

        try:
            # Nombre actuel de PIDs
            current_path = cgroup_path / "pids.current"
            if current_path.exists():
                stats["current"] = int(current_path.read_text().strip())

            # Limite
            max_path = cgroup_path / "pids.max"
            if max_path.exists():
                max_val = max_path.read_text().strip()
                stats["max"] = int(max_val) if max_val != "max" else None

            # Pic
            peak_path = cgroup_path / "pids.peak"
            if peak_path.exists():
                stats["peak"] = int(peak_path.read_text().strip())

        except Exception as e:
            logger.debug(f"Error reading PIDs stats: {e}")

        return stats

    async def update_limits(self, env_id: str, limits: ResourceLimits) -> bool:
        """Met à jour les limites d'un cgroup existant

        Args:
            env_id: Identifiant de l'environnement
            limits: Nouvelles limites

        Returns:
            True si succès
        """
        if env_id not in self._cgroups:
            return False

        cgroup_info = self._cgroups[env_id]

        try:
            await self._apply_limits(cgroup_info.path, limits)
            cgroup_info.limits = limits
            return True

        except Exception as e:
            logger.error(f"Failed to update limits for {env_id}: {e}")
            return False

    async def delete_cgroup(self, env_id: str) -> bool:
        """Supprime le cgroup d'un environnement

        Args:
            env_id: Identifiant de l'environnement

        Returns:
            True si succès
        """
        if env_id not in self._cgroups:
            return True  # Déjà supprimé

        cgroup_info = self._cgroups[env_id]

        try:
            # D'abord, tuer tous les processus dans le cgroup
            await self._kill_cgroup_processes(cgroup_info.path)

            # Ensuite, supprimer le répertoire cgroup
            def rmdir():
                if cgroup_info.path.exists():
                    cgroup_info.path.rmdir()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, rmdir)

            del self._cgroups[env_id]
            logger.info(f"Deleted cgroup: {cgroup_info.path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete cgroup for {env_id}: {e}")
            return False

    async def _kill_cgroup_processes(self, cgroup_path: Path) -> None:
        """Tue tous les processus dans un cgroup"""
        procs_path = cgroup_path / "cgroup.procs"

        if not procs_path.exists():
            return

        try:
            # Lire les PIDs
            content = procs_path.read_text().strip()
            if not content:
                return

            pids = [int(pid) for pid in content.split("\n") if pid]

            # Envoyer SIGTERM
            for pid in pids:
                try:
                    os.kill(pid, 15)  # SIGTERM
                except ProcessLookupError:
                    pass

            # Attendre un peu
            await asyncio.sleep(0.5)

            # Envoyer SIGKILL si nécessaire
            content = procs_path.read_text().strip()
            if content:
                pids = [int(pid) for pid in content.split("\n") if pid]
                for pid in pids:
                    try:
                        os.kill(pid, 9)  # SIGKILL
                    except ProcessLookupError:
                        pass

        except Exception as e:
            logger.debug(f"Error killing cgroup processes: {e}")

    async def cleanup_all(self) -> None:
        """Nettoie tous les cgroups créés"""
        env_ids = list(self._cgroups.keys())

        for env_id in env_ids:
            await self.delete_cgroup(env_id)

        # Nettoyer le répertoire racine GestVenv si vide
        try:
            gestvenv_root = self._get_gestvenv_cgroup_root()
            if gestvenv_root.exists() and not any(gestvenv_root.iterdir()):
                gestvenv_root.rmdir()
        except Exception:
            pass


# Instance globale
cgroup_manager = CgroupManager()


# Fonctions utilitaires
async def setup_resource_limits(
    env_id: str,
    max_memory_mb: Optional[int] = None,
    max_cpu_percent: Optional[int] = None,
    max_pids: Optional[int] = None
) -> Optional[CgroupInfo]:
    """Fonction utilitaire pour configurer des limites de ressources

    Args:
        env_id: Identifiant de l'environnement
        max_memory_mb: Limite mémoire en MB
        max_cpu_percent: Pourcentage CPU max
        max_pids: Nombre max de processus

    Returns:
        CgroupInfo ou None si cgroups non disponible
    """
    if not cgroup_manager.is_available:
        logger.warning("cgroups v2 not available, resource limits not enforced")
        return None

    limits = ResourceLimits(
        max_memory_mb=max_memory_mb,
        max_cpu_percent=max_cpu_percent,
        max_pids=max_pids
    )

    try:
        return await cgroup_manager.create_cgroup(env_id, limits)
    except CgroupOperationError as e:
        logger.warning(f"Failed to set resource limits: {e}")
        return None


async def check_cgroups_available() -> bool:
    """Vérifie si cgroups v2 est disponible"""
    return cgroup_manager.is_available
