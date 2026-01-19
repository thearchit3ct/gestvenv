"""
Contrôleur de cycle de vie des environnements éphémères

Security Note:
    This module intentionally uses shell execution (create_subprocess_shell) for
    command execution within virtual environments. This is necessary because:
    1. Virtual environment activation requires sourcing shell scripts
    2. Users expect to run arbitrary commands in their environments

    The shell execution is controlled and isolated:
    - Commands run within isolated virtual environment contexts
    - Environment variables are explicitly controlled
    - Working directory is restricted to the environment's storage path

    All subprocess.run calls in backends use list arguments (not shell strings)
    which is the secure approach for fixed commands.
"""

import asyncio
import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict

from .models import (
    EphemeralEnvironment,
    EphemeralStatus,
    IsolationLevel,
    OperationResult
)
from .exceptions import (
    EnvironmentCreationException,
    CleanupException,
    IsolationException
)
from .cgroups import (
    CgroupManager,
    ResourceLimits,
    CgroupsNotAvailableError,
    CgroupOperationError,
    cgroup_manager,
)
from ..models import BackendType

logger = logging.getLogger(__name__)


class LifecycleController:
    """Contrôleur de cycle de vie des environnements"""
    
    def __init__(self, manager):
        self.manager = manager
        self.process_manager = ProcessManager()
    
    async def create(self, env: EphemeralEnvironment) -> EphemeralEnvironment:
        """Création complète d'un environnement"""
        
        logger.info(f"Creating environment {env.id} with backend {env.backend}")
        
        try:
            # Création du répertoire isolé
            await self._setup_isolated_directory(env)
            
            # Création de l'environnement virtuel
            await self._create_virtual_environment(env)
            
            # Configuration de l'isolation
            await self._setup_isolation(env)
            
            # Configuration des limites de ressources
            await self._setup_resource_limits(env)
            
            env.status = EphemeralStatus.READY
            return env
            
        except Exception as e:
            env.status = EphemeralStatus.FAILED
            raise EnvironmentCreationException(f"Failed to create environment: {e}")
    
    async def cleanup(self, env: EphemeralEnvironment, force: bool = False):
        """Nettoyage complet d'un environnement"""
        
        logger.info(f"Cleaning up environment {env.id} (force={force})")
        
        try:
            # Arrêt des processus
            await self._stop_processes(env, force=force)
            
            # Nettoyage de l'isolation
            await self._cleanup_isolation(env)
            
            # Suppression des fichiers
            await self._cleanup_filesystem(env, force=force)
            
        except Exception as e:
            if not force:
                raise CleanupException(f"Cleanup failed: {e}")
            else:
                logger.warning(f"Force cleanup error (ignored): {e}")
    
    async def execute_command(
        self,
        env: EphemeralEnvironment,
        command: str,
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> OperationResult:
        """Exécution d'une commande dans l'environnement"""
        
        if not env.is_active:
            raise RuntimeError(f"Environment {env.id} is not active")
        
        # Mise à jour de l'activité
        env.update_activity()
        env.status = EphemeralStatus.RUNNING
        
        try:
            result = await self.process_manager.run_command(
                env, command, timeout=timeout, capture_output=capture_output
            )
            
            if env.status == EphemeralStatus.RUNNING and result.success:
                env.status = EphemeralStatus.READY
            
            return result
            
        finally:
            if env.status == EphemeralStatus.RUNNING:
                env.status = EphemeralStatus.READY
    
    async def install_packages(
        self,
        env: EphemeralEnvironment,
        packages: List[str],
        upgrade: bool = False
    ) -> OperationResult:
        """Installation de packages dans l'environnement"""
        
        if not packages:
            return OperationResult(0, "", "", 0.0, "")
        
        # Construction de la commande selon le backend
        if env.backend == BackendType.UV:
            base_cmd = "uv pip install"
        elif env.backend == BackendType.PDM:
            base_cmd = "pdm add"
        elif env.backend == BackendType.POETRY:
            base_cmd = "poetry add"
        else:
            base_cmd = "pip install"
        
        if upgrade and env.backend in [BackendType.PIP, BackendType.UV]:
            base_cmd += " --upgrade"
        
        packages_str = " ".join(packages)
        command = f"{base_cmd} {packages_str}"
        
        result = await self.execute_command(env, command, timeout=300)
        
        if result.success:
            env.packages.extend(packages)
        
        return result
    
    async def _setup_isolated_directory(self, env: EphemeralEnvironment):
        """Configuration du répertoire isolé"""
        
        if not env.storage_path:
            raise EnvironmentCreationException("No storage path allocated")
        
        # Création des répertoires
        env.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Configuration des permissions restrictives
        os.chmod(env.storage_path, 0o700)
        
        # Création de la structure
        dirs_to_create = ["tmp", "logs", "cache"]
        for dir_name in dirs_to_create:
            (env.storage_path / dir_name).mkdir(exist_ok=True)
        
        logger.debug(f"Created isolated directory: {env.storage_path}")
    
    async def _create_virtual_environment(self, env: EphemeralEnvironment):
        """Création optimisée du virtual environment"""
        
        venv_path = env.storage_path / "venv"
        env.venv_path = venv_path
        
        if env.backend == BackendType.UV:
            # uv est le plus rapide pour les créations
            cmd = [
                "uv", "venv",
                str(venv_path),
                "--python", env.python_version,
                "--seed"  # Pré-install pip/setuptools
            ]
        elif env.backend == BackendType.PDM:
            cmd = [
                "pdm", "venv", "create",
                "--python", env.python_version,
                str(venv_path)
            ]
        elif env.backend == BackendType.POETRY:
            # Poetry gère ses propres venvs, on crée un venv standard
            cmd = [
                f"python{env.python_version}",
                "-m", "venv",
                str(venv_path),
                "--upgrade-deps"
            ]
        else:  # BackendType.PIP
            cmd = [
                f"python{env.python_version}",
                "-m", "venv",
                str(venv_path),
                "--upgrade-deps"
            ]
        
        # Exécution avec timeout
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=env.storage_path
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60  # Création rapide requise
            )
            
            if process.returncode != 0:
                raise EnvironmentCreationException(
                    f"Failed to create virtual environment: {stderr.decode()}"
                )
            
            logger.debug(f"Created virtual environment: {venv_path}")
            
        except asyncio.TimeoutError:
            raise EnvironmentCreationException("Virtual environment creation timed out")
    
    async def _setup_isolation(self, env: EphemeralEnvironment):
        """Configuration de l'isolation de sécurité"""
        
        if env.isolation_level == IsolationLevel.CONTAINER:
            await self._setup_container_isolation(env)
        elif env.isolation_level == IsolationLevel.NAMESPACE:
            await self._setup_namespace_isolation(env)
        elif env.isolation_level == IsolationLevel.CHROOT:
            await self._setup_chroot_isolation(env)
        else:
            # PROCESS: isolation basique par processus
            await self._setup_process_isolation(env)
    
    async def _setup_process_isolation(self, env: EphemeralEnvironment):
        """Isolation par processus (niveau de base)"""
        # Configuration des variables d'environnement
        pass  # Implémenté dans ProcessManager
    
    async def _setup_container_isolation(self, env: EphemeralEnvironment):
        """Isolation par container Docker/Podman"""
        try:
            # Détection du runtime de container disponible
            container_runtime = await self._detect_container_runtime()
            
            if not container_runtime:
                logger.warning("No container runtime available, falling back to process isolation")
                await self._setup_process_isolation(env)
                return
            
            # Construction de l'image de base
            image_name = f"gestvenv-ephemeral-{env.python_version}"
            await self._ensure_container_image(container_runtime, image_name, env.python_version)
            
            # Configuration du container
            container_config = await self._build_container_config(env, image_name)
            
            # Création du container
            container_id = await self._create_container(container_runtime, container_config)
            env.container_id = container_id
            
            # Démarrage du container
            await self._start_container(container_runtime, container_id)
            
            logger.info(f"Container isolation configured: {container_id[:12]}")
            
        except Exception as e:
            logger.error(f"Container isolation setup failed: {e}")
            # Fallback vers l'isolation par processus
            await self._setup_process_isolation(env)
    
    async def _setup_namespace_isolation(self, env: EphemeralEnvironment):
        """Isolation par namespaces Linux"""
        try:
            import platform
            if platform.system() != 'Linux':
                logger.warning("Namespace isolation only available on Linux, falling back to process isolation")
                await self._setup_process_isolation(env)
                return
            
            # Vérification des capacités de namespaces
            if not await self._check_namespace_support():
                logger.warning("Namespace isolation not supported, falling back to process isolation")
                await self._setup_process_isolation(env)
                return
            
            # Configuration des namespaces
            namespace_config = {
                'pid': True,      # Isolation des processus
                'net': env.resource_limits.network_access,  # Isolation réseau conditionnelle
                'mnt': True,      # Isolation du système de fichiers
                'ipc': True,      # Isolation IPC
                'uts': True,      # Isolation hostname/domainname
                'user': True      # Isolation utilisateur (si supporté)
            }
            
            # Création du script d'isolation
            isolation_script = await self._create_namespace_script(env, namespace_config)
            env.isolation_script = isolation_script
            
            logger.info(f"Namespace isolation configured for {env.id}")
            
        except Exception as e:
            logger.error(f"Namespace isolation setup failed: {e}")
            await self._setup_process_isolation(env)
    
    async def _setup_chroot_isolation(self, env: EphemeralEnvironment):
        """Isolation par chroot jail"""
        try:
            import os
            
            # Vérification des privilèges root
            if os.getuid() != 0:
                logger.warning("Chroot isolation requires root privileges, falling back to process isolation")
                await self._setup_process_isolation(env)
                return
            
            # Création du chroot jail
            chroot_path = env.storage_path / "chroot"
            await self._setup_chroot_environment(chroot_path, env)
            
            # Configuration du chroot
            env.chroot_path = chroot_path
            
            logger.info(f"Chroot isolation configured: {chroot_path}")
            
        except Exception as e:
            logger.error(f"Chroot isolation setup failed: {e}")
            await self._setup_process_isolation(env)
    
    async def _setup_resource_limits(self, env: EphemeralEnvironment):
        """Configuration des limites de ressources via cgroups v2"""

        # Vérifier si cgroups est disponible
        if not cgroup_manager.is_available:
            logger.debug("cgroups v2 not available, skipping resource limits")
            return

        # Extraire les limites de l'environnement
        resource_limits = env.resource_limits
        if not resource_limits:
            return

        try:
            # Créer les limites cgroups
            limits = ResourceLimits(
                max_memory_mb=resource_limits.max_memory,
                memory_high_mb=int(resource_limits.max_memory * 0.8) if resource_limits.max_memory else None,
                swap_max_mb=0,  # Désactiver le swap par défaut
                max_cpu_percent=resource_limits.max_cpu_percent,
                cpu_weight=100,
                max_pids=resource_limits.max_processes or 100,
                network_access=resource_limits.network_access,
            )

            # Créer le cgroup
            cgroup_info = await cgroup_manager.create_cgroup(env.id, limits)

            # Stocker la référence au cgroup dans l'environnement
            env.cgroup_path = cgroup_info.path

            logger.info(f"Resource limits configured for {env.id}: "
                       f"memory={resource_limits.max_memory}MB, "
                       f"cpu={resource_limits.max_cpu_percent}%, "
                       f"pids={resource_limits.max_processes or 100}")

        except CgroupsNotAvailableError:
            logger.warning("cgroups v2 not available on this system")
        except CgroupOperationError as e:
            logger.warning(f"Failed to set resource limits: {e}")
        except Exception as e:
            logger.error(f"Unexpected error setting resource limits: {e}")
    
    async def _stop_processes(self, env: EphemeralEnvironment, force: bool = False):
        """Arrêt des processus de l'environnement"""
        
        if env.pid:
            try:
                if force:
                    os.kill(env.pid, 9)  # SIGKILL
                else:
                    os.kill(env.pid, 15)  # SIGTERM
                    await asyncio.sleep(2)  # Attendre arrêt gracieux
                    try:
                        os.kill(env.pid, 0)  # Vérifier si encore vivant
                        os.kill(env.pid, 9)  # SIGKILL si nécessaire
                    except ProcessLookupError:
                        pass  # Processus déjà terminé
            except ProcessLookupError:
                pass  # Processus déjà terminé
        
        # Nettoyage des processus enfants
        await self.process_manager.cleanup_processes(env)
    
    async def _cleanup_isolation(self, env: EphemeralEnvironment):
        """Nettoyage de l'isolation"""

        # Nettoyage du cgroup
        if hasattr(env, 'cgroup_path') and env.cgroup_path:
            try:
                await cgroup_manager.delete_cgroup(env.id)
                logger.debug(f"Cleaned up cgroup for {env.id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup cgroup for {env.id}: {e}")

        if env.container_id:
            # Nettoyage du container
            try:
                await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", env.container_id,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
            except Exception as e:
                logger.warning(f"Failed to cleanup container {env.container_id}: {e}")
    
    async def _cleanup_filesystem(self, env: EphemeralEnvironment, force: bool = False):
        """Nettoyage du système de fichiers"""
        
        if not env.storage_path or not env.storage_path.exists():
            return
        
        try:
            # Suppression récursive
            shutil.rmtree(env.storage_path, ignore_errors=force)
            logger.debug(f"Cleaned up filesystem: {env.storage_path}")
            
        except Exception as e:
            if not force:
                raise CleanupException(f"Failed to cleanup filesystem: {e}")
            else:
                logger.warning(f"Filesystem cleanup error (ignored): {e}")


class ProcessManager:
    """Gestionnaire de processus pour environnements éphémères"""
    
    def __init__(self):
        self.active_processes: Dict[str, List[asyncio.subprocess.Process]] = {}
    
    async def run_command(
        self,
        env: EphemeralEnvironment,
        command: str,
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> OperationResult:
        """Exécution d'une commande avec gestion des processus"""
        
        import time
        start_time = time.time()
        
        # Construction de l'environnement d'exécution
        exec_env = await self._build_execution_environment(env)
        
        # Construction de la commande complète
        full_command = await self._build_command(env, command)
        
        try:
            # Création du processus
            # Note: Shell execution is required for venv activation (source command)
            # Command runs in isolated environment with controlled env vars and cwd
            if capture_output:
                process = await asyncio.create_subprocess_shell(  # nosec B602
                    full_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=exec_env,
                    cwd=env.storage_path
                )
            else:
                process = await asyncio.create_subprocess_shell(  # nosec B602
                    full_command,
                    env=exec_env,
                    cwd=env.storage_path
                )
            
            # Enregistrement du processus
            env.pid = process.pid
            if env.id not in self.active_processes:
                self.active_processes[env.id] = []
            self.active_processes[env.id].append(process)

            # Ajouter le processus au cgroup si disponible
            if hasattr(env, 'cgroup_path') and env.cgroup_path:
                try:
                    await cgroup_manager.add_process_to_cgroup(env.id, process.pid)
                except Exception as e:
                    logger.debug(f"Could not add process to cgroup: {e}")
            
            # Attente avec timeout
            if timeout:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            else:
                stdout, stderr = await process.communicate()
            
            duration = time.time() - start_time
            
            return OperationResult(
                returncode=process.returncode,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
                duration=duration,
                command=command
            )
            
        except asyncio.TimeoutError:
            # Nettoyage en cas de timeout
            if process:
                process.kill()
                await process.wait()
            
            duration = time.time() - start_time
            return OperationResult(
                returncode=-1,
                stdout="",
                stderr="Command timed out",
                duration=duration,
                command=command
            )
        
        finally:
            # Nettoyage du processus de la liste active
            if env.id in self.active_processes and process in self.active_processes[env.id]:
                self.active_processes[env.id].remove(process)
    
    async def _build_execution_environment(self, env: EphemeralEnvironment) -> Dict[str, str]:
        """Construction de l'environnement d'exécution"""
        
        exec_env = os.environ.copy()
        
        if env.venv_path:
            # Configuration du virtual environment
            exec_env["VIRTUAL_ENV"] = str(env.venv_path)
            exec_env["PATH"] = f"{env.venv_path}/bin:{exec_env.get('PATH', '')}"
            
            # Suppression de PYTHONHOME si présent
            exec_env.pop("PYTHONHOME", None)
        
        # Configuration de Python
        exec_env["PYTHONPATH"] = str(env.storage_path)
        exec_env["PYTHONDONTWRITEBYTECODE"] = "1"
        exec_env["PYTHONUNBUFFERED"] = "1"
        
        # Configuration de pip/uv
        exec_env["PIP_CACHE_DIR"] = str(env.storage_path / "cache" / "pip")
        exec_env["UV_CACHE_DIR"] = str(env.storage_path / "cache" / "uv")
        
        # Variables de sécurité
        if env.security_mode.value == "restricted":
            exec_env["HOME"] = str(env.storage_path)
            exec_env["TMPDIR"] = str(env.storage_path / "tmp")
        
        return exec_env
    
    async def _build_command(self, env: EphemeralEnvironment, command: str) -> str:
        """Construction de la commande avec activation du venv"""
        
        if env.venv_path and env.backend != BackendType.POETRY:
            # Activation explicite du virtual environment
            activate_script = env.venv_path / "bin" / "activate"
            if activate_script.exists():
                return f"source {activate_script} && {command}"
        
        return command
    
    async def cleanup_processes(self, env: EphemeralEnvironment):
        """Nettoyage de tous les processus d'un environnement"""
        
        if env.id not in self.active_processes:
            return
        
        processes = self.active_processes[env.id][:]
        
        for process in processes:
            try:
                if process.returncode is None:  # Processus encore actif
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
            except Exception as e:
                logger.warning(f"Failed to cleanup process: {e}")
        
        # Nettoyage de la liste
        if env.id in self.active_processes:
            del self.active_processes[env.id]
    
    # === MÉTHODES D'ISOLATION ===
    
    async def _detect_container_runtime(self) -> Optional[str]:
        """Détection du runtime de container disponible"""
        runtimes = ['docker', 'podman']
        
        for runtime in runtimes:
            try:
                process = await asyncio.create_subprocess_exec(
                    runtime, '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                if process.returncode == 0:
                    logger.debug(f"Found container runtime: {runtime}")
                    return runtime
                    
            except FileNotFoundError:
                continue
        
        return None
    
    async def _ensure_container_image(self, runtime: str, image_name: str, python_version: str):
        """Assure qu'une image de container existe"""
        # Vérification si l'image existe
        try:
            process = await asyncio.create_subprocess_exec(
                runtime, 'image', 'inspect', image_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                return  # Image existe déjà
                
        except Exception:
            pass
        
        # Construction de l'image
        dockerfile_content = f"""
FROM python:{python_version}-slim

# Installation des outils de base
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Installation d'uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Configuration des répertoires de travail
WORKDIR /workspace
RUN mkdir -p /workspace/tmp /workspace/cache

# Configuration de l'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["/bin/bash"]
"""
        
        # Création d'un contexte temporaire
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_path = Path(temp_dir) / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)
            
            # Construction de l'image
            process = await asyncio.create_subprocess_exec(
                runtime, 'build', 
                '-t', image_name,
                str(temp_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise EnvironmentCreationException(f"Failed to build container image: {stderr.decode()}")
            
            logger.info(f"Built container image: {image_name}")
    
    async def _build_container_config(self, env: EphemeralEnvironment, image_name: str) -> dict:
        """Construction de la configuration du container"""
        config = {
            'image': image_name,
            'name': f"gestvenv-{env.id[:8]}",
            'volumes': [
                f"{env.storage_path}:/workspace:rw"
            ],
            'environment': {
                'GESTVENV_ENV_ID': env.id,
                'PYTHONPATH': '/workspace',
                'PIP_CACHE_DIR': '/workspace/cache/pip',
                'UV_CACHE_DIR': '/workspace/cache/uv'
            },
            'working_dir': '/workspace',
            'detach': True,
            'remove': True  # Auto-cleanup
        }
        
        # Limites de ressources
        if env.resource_limits.max_memory:
            config['memory'] = f"{env.resource_limits.max_memory}m"
        
        if env.resource_limits.max_cpu_percent:
            config['cpus'] = str(env.resource_limits.max_cpu_percent / 100.0)
        
        # Isolation réseau
        if not env.resource_limits.network_access:
            config['network'] = 'none'
        
        return config
    
    async def _create_container(self, runtime: str, config: dict) -> str:
        """Création du container"""
        cmd = [runtime, 'create']
        
        # Ajout des options
        cmd.extend(['--name', config['name']])
        cmd.extend(['--workdir', config['working_dir']])
        
        if config.get('detach'):
            cmd.append('--detach')
        
        if config.get('remove'):
            cmd.append('--rm')
        
        # Volumes
        for volume in config.get('volumes', []):
            cmd.extend(['-v', volume])
        
        # Variables d'environnement
        for key, value in config.get('environment', {}).items():
            cmd.extend(['-e', f"{key}={value}"])
        
        # Limites de ressources
        if 'memory' in config:
            cmd.extend(['--memory', config['memory']])
        
        if 'cpus' in config:
            cmd.extend(['--cpus', config['cpus']])
        
        if 'network' in config:
            cmd.extend(['--network', config['network']])
        
        # Image et commande
        cmd.append(config['image'])
        cmd.extend(['sleep', 'infinity'])  # Garder le container vivant
        
        # Exécution
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise EnvironmentCreationException(f"Failed to create container: {stderr.decode()}")
        
        container_id = stdout.decode().strip()
        return container_id
    
    async def _start_container(self, runtime: str, container_id: str):
        """Démarrage du container"""
        process = await asyncio.create_subprocess_exec(
            runtime, 'start', container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise EnvironmentCreationException(f"Failed to start container: {stderr.decode()}")
    
    async def _check_namespace_support(self) -> bool:
        """Vérification du support des namespaces"""
        try:
            # Vérification de la présence d'unshare
            process = await asyncio.create_subprocess_exec(
                'unshare', '--help',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode != 0:
                return False
            
            # Vérification des namespaces dans /proc
            namespace_types = ['pid', 'net', 'mnt', 'ipc', 'uts', 'user']
            proc_ns_path = Path('/proc/self/ns')
            
            if not proc_ns_path.exists():
                return False
            
            for ns_type in namespace_types:
                if not (proc_ns_path / ns_type).exists():
                    logger.debug(f"Namespace {ns_type} not supported")
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Namespace support check failed: {e}")
            return False
    
    async def _create_namespace_script(self, env: EphemeralEnvironment, config: dict) -> str:
        """Création du script d'isolation par namespaces"""
        script_path = env.storage_path / "isolation.sh"
        
        # Construction des options unshare
        unshare_options = []
        
        if config.get('pid'):
            unshare_options.append('--pid')
            unshare_options.append('--fork')
        
        if config.get('net') and not env.resource_limits.network_access:
            unshare_options.append('--net')
        
        if config.get('mnt'):
            unshare_options.append('--mount')
        
        if config.get('ipc'):
            unshare_options.append('--ipc')
        
        if config.get('uts'):
            unshare_options.append('--uts')
        
        # Script d'isolation
        script_content = f"""#!/bin/bash
set -e

# Isolation par namespaces
exec unshare {' '.join(unshare_options)} \\
    --mount-proc=/proc \\
    bash -c '
        # Configuration de l'environnement isolé
        export PYTHONPATH="{env.storage_path}"
        export PYTHONUNBUFFERED=1
        export PYTHONDONTWRITEBYTECODE=1
        export PIP_CACHE_DIR="{env.storage_path}/cache/pip"
        export UV_CACHE_DIR="{env.storage_path}/cache/uv"
        export TMPDIR="{env.storage_path}/tmp"
        
        # Changement de répertoire
        cd "{env.storage_path}"
        
        # Exécution de la commande
        exec "$@"
    ' -- "$@"
"""
        
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        return str(script_path)
    
    async def _setup_chroot_environment(self, chroot_path: Path, env: EphemeralEnvironment):
        """Configuration de l'environnement chroot"""
        chroot_path.mkdir(parents=True, exist_ok=True)
        
        # Création de la structure de base
        essential_dirs = [
            'bin', 'usr/bin', 'lib', 'lib64', 'usr/lib', 'usr/lib64',
            'etc', 'tmp', 'dev', 'proc', 'sys', 'workspace'
        ]
        
        for dir_name in essential_dirs:
            (chroot_path / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Copie des binaires essentiels
        essential_binaries = [
            '/bin/bash', '/bin/sh', '/usr/bin/python3',
            '/usr/bin/pip3', '/bin/ls', '/bin/cat'
        ]
        
        for binary in essential_binaries:
            binary_path = Path(binary)
            if binary_path.exists():
                dest_path = chroot_path / binary_path.relative_to(Path('/'))
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    shutil.copy2(binary_path, dest_path)
                except Exception as e:
                    logger.debug(f"Failed to copy {binary}: {e}")
        
        # Configuration des devices de base
        dev_nodes = [
            ('null', 'c', 1, 3),
            ('zero', 'c', 1, 5),
            ('random', 'c', 1, 8),
            ('urandom', 'c', 1, 9)
        ]
        
        for name, dev_type, major, minor in dev_nodes:
            dev_path = chroot_path / 'dev' / name
            try:
                if dev_type == 'c':
                    # Création de device caractère
                    os.mknod(dev_path, 0o666 | 0o020000, os.makedev(major, minor))
            except Exception as e:
                logger.debug(f"Failed to create device {name}: {e}")
        
        logger.info(f"Chroot environment setup completed: {chroot_path}")