"""
Téléchargeur de versions Python

Télécharge et extrait les binaires Python depuis python-build-standalone.
"""

import hashlib
import logging
import platform
import shutil
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from .registry import PythonVersion

logger = logging.getLogger(__name__)


def _is_safe_path(base_path: Path, target_path: Path) -> bool:
    """Vérifie qu'un chemin d'extraction est sûr (pas de path traversal)"""
    try:
        resolved_base = base_path.resolve()
        resolved_target = (base_path / target_path).resolve()
        return str(resolved_target).startswith(str(resolved_base))
    except (ValueError, OSError):
        return False


def _safe_tar_extract(tar: tarfile.TarFile, destination: Path) -> None:
    """Extrait un tarfile de manière sécurisée en filtrant les membres dangereux"""
    for member in tar.getmembers():
        member_path = Path(member.name)
        # Vérifier les chemins absolus et path traversal
        if member_path.is_absolute() or '..' in member_path.parts:
            logger.warning(f"Membre tar ignoré (chemin dangereux): {member.name}")
            continue
        if not _is_safe_path(destination, member_path):
            logger.warning(f"Membre tar ignoré (path traversal): {member.name}")
            continue
        # Extraire de manière sécurisée
        tar.extract(member, destination)  # nosec B202


def _safe_zip_extract(zf: zipfile.ZipFile, destination: Path) -> None:
    """Extrait un zipfile de manière sécurisée en filtrant les membres dangereux"""
    for member in zf.namelist():
        member_path = Path(member)
        # Vérifier les chemins absolus et path traversal
        if member_path.is_absolute() or '..' in member_path.parts:
            logger.warning(f"Membre zip ignoré (chemin dangereux): {member}")
            continue
        if not _is_safe_path(destination, member_path):
            logger.warning(f"Membre zip ignoré (path traversal): {member}")
            continue
        # Extraire de manière sécurisée
        zf.extract(member, destination)  # nosec B202


@dataclass
class DownloadProgress:
    """Progression du téléchargement"""
    total_bytes: int
    downloaded_bytes: int
    speed_bps: float = 0.0

    @property
    def percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.downloaded_bytes / self.total_bytes) * 100

    @property
    def is_complete(self) -> bool:
        return self.downloaded_bytes >= self.total_bytes


@dataclass
class DownloadResult:
    """Résultat du téléchargement"""
    success: bool
    message: str
    path: Optional[Path] = None
    version: Optional[PythonVersion] = None


class PythonDownloader:
    """Téléchargeur de binaires Python"""

    # URLs de base pour différentes sources
    SOURCES = {
        "python-build-standalone": "https://github.com/indygreg/python-build-standalone/releases/download",
        "python-org": "https://www.python.org/ftp/python",
    }

    # Taille de buffer pour le téléchargement
    CHUNK_SIZE = 8192

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (Path.home() / ".gestvenv" / "cache" / "python")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_platform_info(self) -> dict:
        """Récupère les informations de la plateforme"""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normaliser l'architecture
        arch_map = {
            "x86_64": "x86_64",
            "amd64": "x86_64",
            "arm64": "aarch64",
            "aarch64": "aarch64",
            "i386": "i686",
            "i686": "i686",
        }
        arch = arch_map.get(machine, machine)

        return {
            "system": system,
            "arch": arch,
            "machine": machine,
        }

    def get_download_url(self, version: PythonVersion, source: str = "python-build-standalone") -> Optional[str]:
        """
        Génère l'URL de téléchargement.

        Args:
            version: Version Python à télécharger
            source: Source des binaires

        Returns:
            URL de téléchargement ou None si non disponible
        """
        info = self.get_platform_info()

        if source == "python-build-standalone":
            return self._get_pbs_url(version, info)
        elif source == "python-org":
            return self._get_python_org_url(version, info)

        return None

    def _get_pbs_url(self, version: PythonVersion, info: dict) -> Optional[str]:
        """URL pour python-build-standalone"""
        base = self.SOURCES["python-build-standalone"]

        # Construire le suffixe de plateforme
        if info["system"] == "linux":
            platform_suffix = f"{info['arch']}-unknown-linux-gnu"
        elif info["system"] == "darwin":
            platform_suffix = f"{info['arch']}-apple-darwin"
        elif info["system"] == "windows":
            platform_suffix = f"{info['arch']}-pc-windows-msvc-shared"
        else:
            return None

        # Release date (à mettre à jour périodiquement)
        release_dates = {
            "3.13": "20241016",
            "3.12": "20241016",
            "3.11": "20241016",
            "3.10": "20241016",
            "3.9": "20241016",
            "3.8": "20241016",
        }
        release_date = release_dates.get(version.short, "20241016")

        # Format: cpython-3.12.0+20231002-x86_64-unknown-linux-gnu-install_only.tar.gz
        filename = f"cpython-{version}+{release_date}-{platform_suffix}-install_only.tar.gz"

        return f"{base}/{release_date}/{filename}"

    def _get_python_org_url(self, version: PythonVersion, info: dict) -> Optional[str]:
        """URL pour python.org (sources ou installers)"""
        base = self.SOURCES["python-org"]

        if info["system"] == "windows":
            if info["arch"] == "x86_64":
                return f"{base}/{version}/python-{version}-amd64.exe"
            else:
                return f"{base}/{version}/python-{version}.exe"
        elif info["system"] == "darwin":
            return f"{base}/{version}/python-{version}-macos11.pkg"
        else:
            # Source tarball pour Linux
            return f"{base}/{version}/Python-{version}.tgz"

    def download(
        self,
        version: PythonVersion,
        destination: Path,
        source: str = "python-build-standalone",
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> DownloadResult:
        """
        Télécharge une version de Python.

        Args:
            version: Version à télécharger
            destination: Répertoire de destination
            source: Source des binaires
            progress_callback: Fonction appelée avec la progression

        Returns:
            Résultat du téléchargement
        """
        url = self.get_download_url(version, source)
        if not url:
            return DownloadResult(
                success=False,
                message=f"Pas d'URL de téléchargement pour {version} sur cette plateforme"
            )

        # Vérifier le cache
        cache_file = self._get_cache_path(url)
        if cache_file.exists():
            logger.info(f"Utilisation du cache: {cache_file}")
            return self._extract(cache_file, destination, version)

        # Télécharger
        try:
            logger.info(f"Téléchargement de Python {version} depuis {url}")
            temp_file = self._download_file(url, progress_callback)

            if temp_file:
                # Mettre en cache
                shutil.copy2(temp_file, cache_file)

                # Extraire
                result = self._extract(Path(temp_file), destination, version)

                # Nettoyer
                Path(temp_file).unlink(missing_ok=True)

                return result
            else:
                return DownloadResult(
                    success=False,
                    message="Échec du téléchargement"
                )

        except HTTPError as e:
            return DownloadResult(
                success=False,
                message=f"Erreur HTTP {e.code}: {e.reason}"
            )
        except URLError as e:
            return DownloadResult(
                success=False,
                message=f"Erreur réseau: {e.reason}"
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                message=f"Erreur: {str(e)}"
            )

    def _get_cache_path(self, url: str) -> Path:
        """Génère le chemin de cache pour une URL"""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        filename = url.split("/")[-1]
        return self.cache_dir / f"{url_hash}_{filename}"

    def _download_file(
        self,
        url: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> Optional[str]:
        """Télécharge un fichier avec progression"""
        request = Request(url, headers={"User-Agent": "GestVenv/2.0"})

        with urlopen(request, timeout=300) as response:
            total_size = int(response.headers.get("Content-Length", 0))

            # Créer fichier temporaire
            suffix = ".tar.gz" if url.endswith(".tar.gz") else ".zip"
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)

            downloaded = 0
            with open(temp_path, "wb") as f:
                while True:
                    chunk = response.read(self.CHUNK_SIZE)
                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress = DownloadProgress(
                            total_bytes=total_size,
                            downloaded_bytes=downloaded
                        )
                        progress_callback(progress)

            return temp_path

    def _extract(self, archive_path: Path, destination: Path, version: PythonVersion) -> DownloadResult:
        """Extrait une archive Python"""
        try:
            destination.mkdir(parents=True, exist_ok=True)

            if archive_path.suffix == ".gz" or str(archive_path).endswith(".tar.gz"):
                # Archive tar.gz
                with tarfile.open(archive_path, "r:gz") as tar:
                    # python-build-standalone extrait dans un dossier "python"
                    _safe_tar_extract(tar, destination)

                    # Renommer si nécessaire
                    extracted_dir = destination / "python"
                    if extracted_dir.exists():
                        final_dir = destination / f"python-{version}"
                        if final_dir.exists():
                            shutil.rmtree(final_dir)
                        extracted_dir.rename(final_dir)
                        return DownloadResult(
                            success=True,
                            message=f"Python {version} installé",
                            path=final_dir,
                            version=version
                        )

            elif archive_path.suffix == ".zip":
                # Archive zip
                with zipfile.ZipFile(archive_path, "r") as zf:
                    _safe_zip_extract(zf, destination)

            return DownloadResult(
                success=True,
                message=f"Python {version} extrait vers {destination}",
                path=destination,
                version=version
            )

        except Exception as e:
            return DownloadResult(
                success=False,
                message=f"Erreur d'extraction: {str(e)}"
            )

    def verify_installation(self, python_path: Path) -> bool:
        """Vérifie qu'une installation Python fonctionne"""
        import subprocess

        executable = python_path / "bin" / "python3"
        if platform.system() == "Windows":
            executable = python_path / "python.exe"

        if not executable.exists():
            return False

        try:
            result = subprocess.run(
                [str(executable), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def cleanup_cache(self, max_age_days: int = 30) -> int:
        """Nettoie le cache des téléchargements anciens"""
        import time

        cleaned = 0
        now = time.time()
        max_age_seconds = max_age_days * 24 * 3600

        for file in self.cache_dir.iterdir():
            if file.is_file():
                age = now - file.stat().st_mtime
                if age > max_age_seconds:
                    file.unlink()
                    cleaned += 1

        return cleaned
