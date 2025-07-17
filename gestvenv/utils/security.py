"""
Utilitaires de sécurité pour GestVenv v1.1
"""

import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..core.models import EnvironmentInfo, PackageInfo
from ..core.exceptions import SecurityValidationError

import logging
logger = logging.getLogger(__name__)

# Classes de résultats
class SecurityValidationResult:
    def __init__(self, valid: bool, issues: List[str]):
        self.valid = valid
        self.issues = issues


class CommandResult:
    def __init__(self, success: bool, stdout: str = "", stderr: str = "", 
                 return_code: int = 0, error: str = ""):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.error = error


class SecurityAuditReport:
    def __init__(self, environment: str, overall_security_level: str,
                 critical_issues: List[str], warnings: List[str],
                 recommendations: List[str]):
        self.environment = environment
        self.overall_security_level = overall_security_level
        self.critical_issues = critical_issues
        self.warnings = warnings
        self.recommendations = recommendations


class SystemSecurityReport:
    def __init__(self, is_secure: bool, issues: List[str], 
                 recommendations: List[str]):
        self.is_secure = is_secure
        self.issues = issues
        self.recommendations = recommendations
        
class SecurityUtils:
    """Utilitaires de sécurité et validation"""
    
    # Patterns de sécurité
    SAFE_PATH_PATTERN = re.compile(r'^[a-zA-Z0-9._/-]+$')
    PACKAGE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    
    @staticmethod
    def validate_environment_name(name: str) -> SecurityValidationResult:
        """Valide la sécurité d'un nom d'environnement"""
        issues = []
        
        if len(name) > 100:
            issues.append("Nom trop long (max 100 caractères)")
        
        if not SecurityUtils.SAFE_PATH_PATTERN.match(name):
            issues.append("Caractères non autorisés détectés")
        
        if '..' in name or name.startswith('/') or ':' in name:
            issues.append("Tentative de path traversal détectée")
        
        reserved_names = ['con', 'prn', 'aux', 'nul', 'com1', 'lpt1']
        if name.lower() in reserved_names:
            issues.append("Nom réservé système")
        
        return SecurityValidationResult(
            valid=len(issues) == 0,
            issues=issues
        )
    
    @staticmethod
    def validate_package_specification(package_spec: str) -> SecurityValidationResult:
        """Valide la sécurité d'une spécification de package"""
        issues = []
        
        # URL suspectes
        suspicious_urls = ['file://', 'ftp://', 'data:']
        if any(url in package_spec.lower() for url in suspicious_urls):
            issues.append("URL potentiellement dangereuse détectée")
        
        # Caractères de commande
        dangerous_chars = [';', '|', '&', '`', '$', '(', ')']
        if any(char in package_spec for char in dangerous_chars):
            issues.append("Caractères de commande shell détectés")
        
        # Injection potentielle
        if '--' in package_spec:
            dangerous_flags = ['--trusted-host', '--index-url', '--extra-index-url']
            if any(flag in package_spec for flag in dangerous_flags):
                issues.append("Flags pip potentiellement dangereux")
        
        return SecurityValidationResult(
            valid=len(issues) == 0,
            issues=issues
        )
    
    @staticmethod
    def sandbox_command_execution(command: List[str], env_path: Path) -> CommandResult:
        """Exécution sandboxée de commandes"""
        if not command or not command[0]:
            return CommandResult(success=False, error="Commande vide")
        
        executable = command[0]
        
        # Whitelist exécutables autorisés
        allowed_executables = ['python', 'pip', 'uv', 'poetry', 'pdm']
        if not any(exec_name in executable for exec_name in allowed_executables):
            return CommandResult(success=False, error="Exécutable non autorisé")
        
        # Variables d'environnement sécurisées
        secure_env = SecurityUtils._create_secure_environment(env_path)
        
        timeout = 300  # 5 minutes max
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=secure_env,
                cwd=env_path
            )
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            return CommandResult(success=False, error="Timeout de la commande")
        except Exception as e:
            return CommandResult(success=False, error=str(e))
    
    @staticmethod
    def audit_environment_security(env_info: EnvironmentInfo) -> SecurityAuditReport:
        """Audit de sécurité d'un environnement"""
        issues = []
        warnings = []
        
        # Vérification permissions
        if not SecurityUtils._check_permissions_security(env_info.path):
            issues.append("Permissions d'environnement non sécurisées")
        
        # Packages suspects
        suspicious_packages = SecurityUtils._scan_suspicious_packages(env_info.packages)
        if suspicious_packages:
            warnings.extend([f"Package suspect: {pkg}" for pkg in suspicious_packages])
        
        # Scripts exécutables suspects
        suspicious_scripts = SecurityUtils._scan_suspicious_scripts(env_info.path)
        if suspicious_scripts:
            issues.extend([f"Script suspect: {script}" for script in suspicious_scripts])
        
        return SecurityAuditReport(
            environment=env_info.name,
            overall_security_level=SecurityUtils._calculate_security_level(issues, warnings),
            critical_issues=issues,
            warnings=warnings,
            recommendations=SecurityUtils._generate_security_recommendations(issues, warnings)
        )
    
    @staticmethod
    def verify_file_integrity(file_path: Path, expected_hash: Optional[str] = None) -> bool:
        """Vérifie l'intégrité d'un fichier"""
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            if expected_hash:
                return file_hash == expected_hash
            
            # Stockage du hash pour vérification future
            hash_file = file_path.with_suffix(file_path.suffix + '.sha256')
            if not hash_file.exists():
                hash_file.write_text(file_hash)
                return True
            else:
                stored_hash = hash_file.read_text().strip()
                return file_hash == stored_hash
                
        except Exception as e:
            logger.error(f"Erreur vérification intégrité {file_path}: {e}")
            return False
    
    @staticmethod
    def secure_delete(file_path: Path) -> bool:
        """Suppression sécurisée d'un fichier"""
        if not file_path.exists():
            return True
        
        try:
            # Écrasement multiple (3 passes)
            file_size = file_path.stat().st_size
            
            with open(file_path, 'r+b') as f:
                for _ in range(3):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Suppression finale
            file_path.unlink()
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression sécurisée {file_path}: {e}")
            return False
    
    @staticmethod
    def check_system_security() -> SystemSecurityReport:
        """Vérification sécurité système"""
        issues = []
        
        # Vérification permissions utilisateur
        if hasattr(os, 'getuid') and os.getuid() == 0:
            issues.append("Exécution en tant que root détectée (déconseillé)")
        
        # Vérification variables d'environnement sensibles
        sensitive_vars = ['PATH', 'PYTHONPATH', 'LD_LIBRARY_PATH']
        for var in sensitive_vars:
            if var in os.environ:
                value = os.environ[var]
                if SecurityUtils._check_path_injection(value):
                    issues.append(f"Injection potentielle dans {var}")
        
        return SystemSecurityReport(
            is_secure=len(issues) == 0,
            issues=issues,
            recommendations=SecurityUtils._generate_system_security_recommendations(issues)
        )
    
    # Méthodes privées
    
    @staticmethod
    def _create_secure_environment(env_path: Path) -> Dict[str, str]:
        """Crée un environnement sécurisé pour l'exécution"""
        secure_env = {
            'PATH': str(env_path / 'bin') + ':' + os.environ.get('PATH', ''),
            'VIRTUAL_ENV': str(env_path),
            'PYTHONPATH': '',
            'PYTHONHOME': '',
        }
        
        # Variables système essentielles
        essential_vars = ['HOME', 'USER', 'LANG', 'LC_ALL', 'TZ']
        for var in essential_vars:
            if var in os.environ:
                secure_env[var] = os.environ[var]
        
        return secure_env
    
    @staticmethod
    def _check_permissions_security(path: Path) -> bool:
        """Vérifie la sécurité des permissions"""
        try:
            stat = path.stat()
            
            # Vérification permissions world-writable
            if stat.st_mode & 0o002:
                return False
            
            # Vérification ownership (Unix)
            if hasattr(os, 'getuid'):
                if stat.st_uid != os.getuid():
                    return False
            
            return True
        except OSError:
            return False
    
    @staticmethod
    def _scan_suspicious_packages(packages: List[PackageInfo]) -> List[str]:
        """Scanne les packages suspects"""
        suspicious = []
        
        suspicious_patterns = [
            r'.*password.*',
            r'.*secret.*', 
            r'.*backdoor.*',
            r'.*malware.*',
            r'.*virus.*'
        ]
        
        for package in packages:
            package_name = package.name.lower()
            if any(re.match(pattern, package_name) for pattern in suspicious_patterns):
                suspicious.append(package.name)
        
        return suspicious
    
    @staticmethod
    def _scan_suspicious_scripts(env_path: Path) -> List[str]:
        """Scanne les scripts suspects"""
        suspicious = []
        
        try:
            scripts_dirs = [env_path / 'bin', env_path / 'Scripts']
            
            for scripts_dir in scripts_dirs:
                if scripts_dir.exists():
                    for script in scripts_dir.iterdir():
                        if script.is_file() and SecurityUtils._is_suspicious_script(script):
                            suspicious.append(str(script.relative_to(env_path)))
        except OSError:
            pass
        
        return suspicious
    
    @staticmethod
    def _is_suspicious_script(script_path: Path) -> bool:
        """Vérifie si un script est suspect"""
        try:
            if script_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                return True
            
            if script_path.suffix in ['.exe', '.dll', '.so']:
                content = script_path.read_bytes()[:1024]
                if b'eval' in content or b'exec' in content:
                    return True
            
            return False
        except (OSError, PermissionError):
            return False
    
    @staticmethod
    def _check_path_injection(path_value: str) -> bool:
        """Vérifie l'injection dans les chemins"""
        dangerous_patterns = [
            r'\.\.',
            r'/tmp/[a-f0-9]{32}',
            r'file://',
            r'\\\\[a-zA-Z0-9]+'
        ]
        
        return any(re.search(pattern, path_value) for pattern in dangerous_patterns)
    
    @staticmethod
    def _calculate_security_level(issues: List[str], warnings: List[str]) -> str:
        """Calcule le niveau de sécurité"""
        if issues:
            return "critical" if len(issues) > 2 else "warning"
        elif warnings:
            return "info"
        else:
            return "secure"
    
    @staticmethod
    def _generate_security_recommendations(issues: List[str], warnings: List[str]) -> List[str]:
        """Génère des recommandations de sécurité"""
        recommendations = []
        
        if issues:
            recommendations.append("Corriger les problèmes critiques identifiés")
        
        if warnings:
            recommendations.append("Examiner les avertissements de sécurité")
        
        recommendations.extend([
            "Maintenir les packages à jour",
            "Vérifier régulièrement les permissions",
            "Utiliser des environnements dédiés"
        ])
        
        return recommendations
    
    @staticmethod
    def _generate_system_security_recommendations(issues: List[str]) -> List[str]:
        """Génère des recommandations sécurité système"""
        recommendations = []
        
        if any("root" in issue for issue in issues):
            recommendations.append("Éviter l'exécution en tant que root")
        
        if any("injection" in issue for issue in issues):
            recommendations.append("Nettoyer les variables d'environnement")
        
        recommendations.extend([
            "Utiliser un utilisateur dédié",
            "Configurer un firewall",
            "Activer la surveillance des logs"
        ])
        
        return recommendations


