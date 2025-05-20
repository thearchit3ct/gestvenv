"""
Service pour les interactions avec le système d'exploitation.

Ce module fournit les fonctionnalités pour interagir avec le système d'exploitation,
exécuter des commandes et récupérer des informations système.
"""

import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

# Configuration du logger
logger = logging.getLogger(__name__)

class SystemService:
    """Service pour les interactions avec le système d'exploitation."""
    
    def __init__(self) -> None:
        """Initialise le service système."""
        self.system = platform.system().lower()  # 'windows', 'linux', 'darwin' (macOS)
        
        # Initialiser le service d'environnement sans créer d'imports circulaires
        from .environment_service import EnvironmentService
        self.env_service = EnvironmentService()
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None,
                  capture_output: bool = True, check: bool = False) -> Dict[str, Any]:
        """
        Exécute une commande système.
        
        Args:
            cmd: Liste des éléments de la commande à exécuter.
            cwd: Répertoire de travail pour l'exécution.
            capture_output: Si True, capture les sorties standard et d'erreur.
            check: Si True, lève une exception en cas d'erreur.
            
        Returns:
            Dictionnaire contenant le code de retour et les sorties.
        """
        try:
            logger.debug(f"Exécution de la commande: {' '.join(cmd)}")
            
            # Configuration de l'environnement pour subprocess
            env = os.environ.copy()
            
            # Exécuter la commande
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                check=check,
                env=env
            )
            
            # Préparer le résultat
            output = {
                'returncode': result.returncode,
                'stdout': result.stdout if capture_output else "",
                'stderr': result.stderr if capture_output else ""
            }
            
            # Journaliser le résultat
            if result.returncode != 0:
                logger.warning(f"Commande terminée avec code de retour non nul: {result.returncode}")
                if result.stderr and capture_output:
                    logger.warning(f"Erreur: {result.stderr}")
            else:
                logger.debug("Commande exécutée avec succès")
            
            return output
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la commande: {str(e)}")
            return {
                'returncode': 1,
                'stdout': "",
                'stderr': str(e)
            }
    
    def get_activation_command(self, env_name: str, env_path: Path) -> Optional[str]:
        """
        Obtient la commande d'activation d'un environnement virtuel.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            
        Returns:
            Commande d'activation ou None si non disponible.
        """
        # Obtenir le chemin du script d'activation
        activation_script = self.env_service.get_activation_script_path(env_name, env_path)
        
        if not activation_script:
            return None
        
        # Générer la commande selon le système d'exploitation
        if self.system == "windows":
            # Sous Windows, on peut exécuter directement le script batch
            return f'"{activation_script}"'
        else:
            # Sous Unix (Linux, macOS), il faut sourcer le script
            return f'source "{activation_script}"'
    
    def run_in_environment(self, env_name: str, env_path: Path, 
                         command: List[str]) -> Tuple[int, str, str]:
        """
        Exécute une commande dans un environnement virtuel spécifique.
        
        Args:
            env_name: Nom de l'environnement virtuel.
            env_path: Chemin vers l'environnement virtuel.
            command: Commande à exécuter.
            
        Returns:
            Tuple contenant (code de retour, sortie standard, sortie d'erreur).
        """
        # Obtenir l'exécutable Python de l'environnement
        python_exe = self.env_service.get_python_executable(env_name, env_path)
        
        if not python_exe:
            logger.error(f"Impossible de trouver l'exécutable Python pour l'environnement '{env_name}'")
            return 1, "", f"Environnement '{env_name}' introuvable ou corrompu"
        
        # Préparer la commande avec l'exécutable Python de l'environnement
        cmd = [str(python_exe)] + command
        
        # Exécuter la commande
        result = self.run_command(cmd)
        
        return result['returncode'], result['stdout'], result['stderr']
    
    def check_python_version(self, python_cmd: str) -> Optional[str]:
        """
        Vérifie la version de Python pour une commande donnée.
        
        Args:
            python_cmd: Commande Python à vérifier (ex: 'python', 'python3.9').
            
        Returns:
            Version de Python ou None si non disponible.
        """
        try:
            # Exécuter la commande pour obtenir la version Python
            cmd = [python_cmd, "--version"]
            result = self.run_command(cmd)
            
            if result['returncode'] != 0:
                logger.warning(f"La commande '{python_cmd}' n'est pas disponible: {result['stderr']}")
                return None
            
            # Extraire la version du format "Python X.Y.Z"
            version_output = result['stdout'].strip()
            
            # Si la sortie est vide (ancien comportement de Python 2.x), vérifier stderr
            if not version_output and result['stderr']:
                version_output = result['stderr'].strip()
            
            # Extraire la version
            import re
            match = re.search(r'Python (\d+\.\d+\.\d+)', version_output)
            if match:
                version = match.group(1)
                logger.debug(f"Version de Python pour '{python_cmd}': {version}")
                return version
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la version Python: {str(e)}")
            return None
    
    def get_available_python_versions(self) -> List[Dict[str, str]]:
        """
        Récupère les versions Python disponibles sur le système.
        
        Returns:
            Liste des versions Python disponibles avec commande et version.
        """
        python_commands = ["python", "python3"]
        
        # Ajouter des versions spécifiques à vérifier
        for minor in range(9, 14):  # Python 3.9 à 3.13
            python_commands.append(f"python3.{minor}")
        
        # Sous Windows, vérifier aussi 'py' avec différents sélecteurs
        if self.system == "windows":
            python_commands.extend(["py", "py -3"])
            for minor in range(7, 14):
                python_commands.append(f"py -3.{minor}")
        
        available_versions = []
        
        for cmd in python_commands:
            version = self.check_python_version(cmd)
            if version:
                available_versions.append({
                    "command": cmd,
                    "version": version
                })
        
        return available_versions
    
    def get_system_info(self) -> Dict[str, str]:
        """
        Récupère des informations sur le système d'exploitation.
        
        Returns:
            Dictionnaire d'informations système.
        """
        system_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
        
        return system_info
    
    def check_command_exists(self, command: str) -> bool:
        """
        Vérifie si une commande existe dans le système.
        
        Args:
            command: Nom de la commande à vérifier.
            
        Returns:
            True si la commande existe, False sinon.
        """
        try:
            # Utiliser 'where' sous Windows et 'which' sous Unix
            if self.system == "windows":
                result = self.run_command(["where", command])
            else:
                result = self.run_command(["which", command])
            
            return result['returncode'] == 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la commande '{command}': {str(e)}")
            return False
    
    def create_directory(self, path: Path) -> bool:
        """
        Crée un répertoire si nécessaire.
        
        Args:
            path: Chemin du répertoire à créer.
            
        Returns:
            True si le répertoire existe ou a été créé, False sinon.
        """
        try:
            # Créer le répertoire et ses parents si nécessaire
            path.mkdir(parents=True, exist_ok=True)
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du répertoire '{path}': {str(e)}")
            return False
    
    def file_exists(self, path: Path) -> bool:
        """
        Vérifie si un fichier existe.
        
        Args:
            path: Chemin du fichier à vérifier.
            
        Returns:
            True si le fichier existe, False sinon.
        """
        return path.exists() and path.is_file()
    
    def directory_exists(self, path: Path) -> bool:
        """
        Vérifie si un répertoire existe.
        
        Args:
            path: Chemin du répertoire à vérifier.
            
        Returns:
            True si le répertoire existe, False sinon.
        """
        return path.exists() and path.is_dir()
    
    def delete_file(self, path: Path) -> bool:
        """
        Supprime un fichier.
        
        Args:
            path: Chemin du fichier à supprimer.
            
        Returns:
            True si le fichier a été supprimé ou n'existait pas, False sinon.
        """
        try:
            if path.exists() and path.is_file():
                path.unlink()
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du fichier '{path}': {str(e)}")
            return False