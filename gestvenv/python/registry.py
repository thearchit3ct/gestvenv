"""
Registre des versions Python disponibles

Gère la liste des versions Python disponibles et leurs métadonnées.
"""

import json
import platform
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum


class PythonStatus(Enum):
    """Statut d'une version Python"""
    AVAILABLE = "available"       # Disponible au téléchargement
    INSTALLED = "installed"       # Installée localement
    ACTIVE = "active"             # Version active par défaut
    DEPRECATED = "deprecated"     # Version obsolète
    PRERELEASE = "prerelease"     # Version beta/rc


@dataclass
class PythonVersion:
    """Représente une version de Python"""
    major: int
    minor: int
    patch: int = 0
    prerelease: Optional[str] = None  # ex: "rc1", "b2"

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += self.prerelease
        return version

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, PythonVersion):
            return str(self) == str(other)
        return False

    def __lt__(self, other):
        if isinstance(other, PythonVersion):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        return NotImplemented

    @classmethod
    def parse(cls, version_str: str) -> 'PythonVersion':
        """Parse une chaîne de version"""
        # Patterns: 3.12, 3.12.1, 3.12.1rc1, 3.12.0b2
        match = re.match(r'^(\d+)\.(\d+)(?:\.(\d+))?([a-z]+\d+)?$', version_str)
        if not match:
            raise ValueError(f"Format de version invalide: {version_str}")

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3)) if match.group(3) else 0
        prerelease = match.group(4)

        return cls(major=major, minor=minor, patch=patch, prerelease=prerelease)

    @property
    def short(self) -> str:
        """Version courte (ex: 3.12)"""
        return f"{self.major}.{self.minor}"

    @property
    def is_prerelease(self) -> bool:
        """Est-ce une version préliminaire"""
        return self.prerelease is not None


@dataclass
class PythonInstallation:
    """Représente une installation Python"""
    version: PythonVersion
    path: Path
    status: PythonStatus = PythonStatus.INSTALLED
    installed_at: Optional[datetime] = None
    source: str = "python-build-standalone"  # pyenv, system, python-build-standalone

    def __post_init__(self):
        if self.installed_at is None:
            self.installed_at = datetime.now()

    @property
    def python_executable(self) -> Path:
        """Chemin vers l'exécutable Python"""
        if platform.system() == "Windows":
            return self.path / "python.exe"
        return self.path / "bin" / "python3"

    @property
    def pip_executable(self) -> Path:
        """Chemin vers pip"""
        if platform.system() == "Windows":
            return self.path / "Scripts" / "pip.exe"
        return self.path / "bin" / "pip3"

    def is_valid(self) -> bool:
        """Vérifie si l'installation est valide"""
        return self.python_executable.exists()

    def to_dict(self) -> Dict:
        """Sérialise en dictionnaire"""
        return {
            "version": str(self.version),
            "path": str(self.path),
            "status": self.status.value,
            "installed_at": self.installed_at.isoformat() if self.installed_at else None,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'PythonInstallation':
        """Désérialise depuis un dictionnaire"""
        return cls(
            version=PythonVersion.parse(data["version"]),
            path=Path(data["path"]),
            status=PythonStatus(data.get("status", "installed")),
            installed_at=datetime.fromisoformat(data["installed_at"]) if data.get("installed_at") else None,
            source=data.get("source", "unknown")
        )


class PythonRegistry:
    """Registre des versions Python"""

    # Versions Python disponibles (mise à jour périodique)
    AVAILABLE_VERSIONS = [
        "3.13.0", "3.13.0rc3",
        "3.12.7", "3.12.6", "3.12.5", "3.12.4", "3.12.3", "3.12.2", "3.12.1", "3.12.0",
        "3.11.10", "3.11.9", "3.11.8", "3.11.7", "3.11.6", "3.11.5", "3.11.4", "3.11.3", "3.11.2", "3.11.1", "3.11.0",
        "3.10.15", "3.10.14", "3.10.13", "3.10.12", "3.10.11", "3.10.10", "3.10.9", "3.10.8",
        "3.9.20", "3.9.19", "3.9.18", "3.9.17", "3.9.16",
        "3.8.20", "3.8.19", "3.8.18",
    ]

    # URLs de téléchargement python-build-standalone
    DOWNLOAD_BASE_URL = "https://github.com/indygreg/python-build-standalone/releases/download"

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or (Path.home() / ".gestvenv" / "pythons")
        self.registry_file = self.base_path / "registry.json"
        self._installations: Dict[str, PythonInstallation] = {}
        self._active_version: Optional[str] = None

        self._ensure_directories()
        self._load_registry()

    def _ensure_directories(self):
        """Crée les répertoires nécessaires"""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _load_registry(self):
        """Charge le registre depuis le fichier"""
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text(encoding='utf-8'))
                self._active_version = data.get("active")
                for version, info in data.get("installations", {}).items():
                    self._installations[version] = PythonInstallation.from_dict(info)
            except Exception:
                pass

    def _save_registry(self):
        """Sauvegarde le registre"""
        data = {
            "active": self._active_version,
            "installations": {
                version: install.to_dict()
                for version, install in self._installations.items()
            }
        }
        self.registry_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def get_available_versions(self, include_prerelease: bool = False) -> List[PythonVersion]:
        """Liste les versions disponibles au téléchargement"""
        versions = []
        for v in self.AVAILABLE_VERSIONS:
            try:
                pv = PythonVersion.parse(v)
                if include_prerelease or not pv.is_prerelease:
                    versions.append(pv)
            except ValueError:
                continue
        return sorted(versions, reverse=True)

    def get_installed_versions(self) -> List[PythonInstallation]:
        """Liste les versions installées"""
        return list(self._installations.values())

    def get_installation(self, version: str) -> Optional[PythonInstallation]:
        """Récupère une installation par version"""
        # Essayer version exacte
        if version in self._installations:
            return self._installations[version]

        # Essayer version courte (3.12 -> 3.12.x le plus récent)
        for v, install in sorted(self._installations.items(), reverse=True):
            if v.startswith(version):
                return install

        return None

    def is_installed(self, version: str) -> bool:
        """Vérifie si une version est installée"""
        return self.get_installation(version) is not None

    def register_installation(self, installation: PythonInstallation):
        """Enregistre une nouvelle installation"""
        version_str = str(installation.version)
        self._installations[version_str] = installation
        self._save_registry()

    def unregister_installation(self, version: str) -> bool:
        """Supprime une installation du registre"""
        if version in self._installations:
            del self._installations[version]
            if self._active_version == version:
                self._active_version = None
            self._save_registry()
            return True
        return False

    def set_active(self, version: str) -> bool:
        """Définit la version active par défaut"""
        if version in self._installations:
            self._active_version = version
            self._save_registry()
            return True
        return False

    def get_active(self) -> Optional[PythonInstallation]:
        """Récupère la version active"""
        if self._active_version:
            return self._installations.get(self._active_version)
        return None

    def get_latest_available(self, major_minor: Optional[str] = None) -> Optional[PythonVersion]:
        """Récupère la dernière version disponible"""
        versions = self.get_available_versions(include_prerelease=False)

        if major_minor:
            # Filtrer par major.minor
            versions = [v for v in versions if v.short == major_minor]

        return versions[0] if versions else None

    def get_download_url(self, version: PythonVersion) -> Optional[str]:
        """Génère l'URL de téléchargement pour une version"""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Mapper les architectures
        arch_map = {
            "x86_64": "x86_64",
            "amd64": "x86_64",
            "arm64": "aarch64",
            "aarch64": "aarch64",
        }
        arch = arch_map.get(machine, machine)

        # Mapper les systèmes
        if system == "linux":
            os_suffix = f"{arch}-unknown-linux-gnu"
        elif system == "darwin":
            os_suffix = f"{arch}-apple-darwin"
        elif system == "windows":
            os_suffix = f"{arch}-pc-windows-msvc-shared"
        else:
            return None

        # Format: cpython-3.12.0+20231002-x86_64-unknown-linux-gnu-install_only.tar.gz
        # Note: La date change selon les releases, on utilise un pattern générique
        version_str = str(version)

        return f"{self.DOWNLOAD_BASE_URL}/20231002/cpython-{version_str}%2B20231002-{os_suffix}-install_only.tar.gz"

    def find_best_match(self, version_spec: str) -> Optional[PythonVersion]:
        """
        Trouve la meilleure version correspondant à une spécification.

        Args:
            version_spec: "3.12", "3.12.1", "latest", "3.11+"

        Returns:
            La meilleure version correspondante
        """
        if version_spec == "latest":
            return self.get_latest_available()

        available = self.get_available_versions()

        # Version exacte
        try:
            exact = PythonVersion.parse(version_spec)
            if exact in available:
                return exact
        except ValueError:
            pass

        # Version partielle (3.12 -> 3.12.x le plus récent)
        for v in available:
            if str(v).startswith(version_spec):
                return v

        return None
