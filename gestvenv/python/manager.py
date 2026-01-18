"""
Gestionnaire de versions Python

Gère l'installation, la suppression et la sélection des versions Python.
"""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from .registry import PythonRegistry, PythonVersion, PythonInstallation, PythonStatus
from .downloader import PythonDownloader, DownloadProgress, DownloadResult

logger = logging.getLogger(__name__)


@dataclass
class InstallResult:
    """Résultat d'installation"""
    success: bool
    message: str
    installation: Optional[PythonInstallation] = None


@dataclass
class RemoveResult:
    """Résultat de suppression"""
    success: bool
    message: str


class PythonVersionManager:
    """Gestionnaire de versions Python"""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or (Path.home() / ".gestvenv" / "pythons")
        self.registry = PythonRegistry(self.base_path)
        self.downloader = PythonDownloader()

        self.base_path.mkdir(parents=True, exist_ok=True)

    def list_available(self, include_prerelease: bool = False) -> List[PythonVersion]:
        """
        Liste les versions Python disponibles au téléchargement.

        Args:
            include_prerelease: Inclure les versions beta/rc

        Returns:
            Liste des versions disponibles
        """
        return self.registry.get_available_versions(include_prerelease)

    def list_installed(self) -> List[PythonInstallation]:
        """
        Liste les versions Python installées.

        Returns:
            Liste des installations
        """
        installations = self.registry.get_installed_versions()
        # Vérifier que les installations sont toujours valides
        valid = []
        for install in installations:
            if install.is_valid():
                valid.append(install)
            else:
                logger.warning(f"Installation invalide: {install.version}")
        return valid

    def get_active(self) -> Optional[PythonInstallation]:
        """
        Récupère la version Python active.

        Returns:
            Installation active ou None
        """
        return self.registry.get_active()

    def is_installed(self, version: str) -> bool:
        """
        Vérifie si une version est installée.

        Args:
            version: Version à vérifier (ex: "3.12", "3.12.1")

        Returns:
            True si installée
        """
        return self.registry.is_installed(version)

    def install(
        self,
        version_spec: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> InstallResult:
        """
        Installe une version de Python.

        Args:
            version_spec: Spécification de version ("3.12", "3.12.1", "latest")
            progress_callback: Callback pour la progression

        Returns:
            Résultat de l'installation
        """
        # Résoudre la version
        version = self.registry.find_best_match(version_spec)
        if not version:
            return InstallResult(
                success=False,
                message=f"Version non trouvée: {version_spec}"
            )

        # Vérifier si déjà installée
        if self.registry.is_installed(str(version)):
            existing = self.registry.get_installation(str(version))
            return InstallResult(
                success=True,
                message=f"Python {version} est déjà installé",
                installation=existing
            )

        # Destination
        install_path = self.base_path / f"python-{version}"

        # Télécharger et extraire
        logger.info(f"Installation de Python {version}...")
        result = self.downloader.download(
            version=version,
            destination=self.base_path,
            progress_callback=progress_callback
        )

        if not result.success:
            return InstallResult(
                success=False,
                message=result.message
            )

        # Vérifier l'installation
        actual_path = result.path or install_path
        if not self.downloader.verify_installation(actual_path):
            return InstallResult(
                success=False,
                message="L'installation n'a pas pu être vérifiée"
            )

        # Enregistrer
        installation = PythonInstallation(
            version=version,
            path=actual_path,
            status=PythonStatus.INSTALLED,
            source="python-build-standalone"
        )
        self.registry.register_installation(installation)

        # Si c'est la première installation, la définir comme active
        if not self.registry.get_active():
            self.registry.set_active(str(version))
            installation.status = PythonStatus.ACTIVE

        logger.info(f"Python {version} installé avec succès dans {actual_path}")

        return InstallResult(
            success=True,
            message=f"Python {version} installé avec succès",
            installation=installation
        )

    def remove(self, version: str, force: bool = False) -> RemoveResult:
        """
        Supprime une version de Python.

        Args:
            version: Version à supprimer
            force: Forcer la suppression même si active

        Returns:
            Résultat de la suppression
        """
        installation = self.registry.get_installation(version)

        if not installation:
            return RemoveResult(
                success=False,
                message=f"Version non installée: {version}"
            )

        # Vérifier si c'est la version active
        active = self.registry.get_active()
        if active and str(active.version) == str(installation.version) and not force:
            return RemoveResult(
                success=False,
                message=f"Python {version} est la version active. Utilisez --force pour supprimer."
            )

        # Supprimer les fichiers
        try:
            if installation.path.exists():
                shutil.rmtree(installation.path)
        except Exception as e:
            return RemoveResult(
                success=False,
                message=f"Erreur lors de la suppression des fichiers: {e}"
            )

        # Supprimer du registre
        self.registry.unregister_installation(str(installation.version))

        logger.info(f"Python {version} supprimé")

        return RemoveResult(
            success=True,
            message=f"Python {version} supprimé avec succès"
        )

    def use(self, version: str) -> bool:
        """
        Définit la version Python active par défaut.

        Args:
            version: Version à activer

        Returns:
            True si réussi
        """
        installation = self.registry.get_installation(version)
        if not installation:
            return False

        return self.registry.set_active(str(installation.version))

    def which(self) -> Optional[Path]:
        """
        Retourne le chemin de l'exécutable Python actif.

        Returns:
            Chemin vers python ou None
        """
        active = self.registry.get_active()
        if active:
            return active.python_executable
        return None

    def get_python_for_version(self, version_spec: str) -> Optional[Path]:
        """
        Récupère le chemin Python pour une version spécifique.

        Args:
            version_spec: Spécification de version

        Returns:
            Chemin vers l'exécutable ou None
        """
        installation = self.registry.get_installation(version_spec)
        if installation and installation.is_valid():
            return installation.python_executable
        return None

    def ensure_version(
        self,
        version_spec: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> Optional[Path]:
        """
        S'assure qu'une version est disponible, l'installe si nécessaire.

        Args:
            version_spec: Version requise
            progress_callback: Callback pour la progression

        Returns:
            Chemin vers Python ou None si échec
        """
        # Vérifier si déjà installée
        python_path = self.get_python_for_version(version_spec)
        if python_path:
            return python_path

        # Installer
        result = self.install(version_spec, progress_callback)
        if result.success and result.installation:
            return result.installation.python_executable

        return None

    def detect_system_pythons(self) -> List[PythonInstallation]:
        """
        Détecte les installations Python système.

        Returns:
            Liste des Pythons détectés
        """
        detected = []
        search_paths = [
            "/usr/bin",
            "/usr/local/bin",
            "/opt/homebrew/bin",
            "C:\\Python*",
            "C:\\Users\\*\\AppData\\Local\\Programs\\Python\\*",
        ]

        import glob
        for pattern in search_paths:
            for path in glob.glob(pattern):
                path = Path(path)
                for name in ["python3", "python", "python.exe"]:
                    executable = path / name if path.is_dir() else path
                    if executable.exists() and executable.is_file():
                        try:
                            result = subprocess.run(
                                [str(executable), "--version"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.returncode == 0:
                                version_str = result.stdout.strip().split()[-1]
                                version = PythonVersion.parse(version_str)
                                detected.append(PythonInstallation(
                                    version=version,
                                    path=executable.parent.parent if executable.parent.name == "bin" else executable.parent,
                                    status=PythonStatus.INSTALLED,
                                    source="system"
                                ))
                        except Exception:
                            continue

        return detected


# Instance globale
python_manager = PythonVersionManager()
