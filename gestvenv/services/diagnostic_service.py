"""
Service de diagnostic automatique pour GestVenv v1.1
"""

from dataclasses import dataclass
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core.models import (
    EnvironmentInfo, 
    DiagnosticReport, 
    DiagnosticIssue, 
    OptimizationSuggestion,
    EnvironmentHealth,
    IssueLevel,
    RepairResult
)
from ..core.exceptions import DiagnosticError
from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class DiagnosticService:
    """Service de diagnostic et réparation automatique"""
    
    def __init__(self, env_manager):
        self.env_manager = env_manager
        self.checkers = [
            EnvironmentIntegrityChecker(),
            DependencyIntegrityChecker(),
            PerformanceChecker(),
            SecurityChecker(),
            CacheHealthChecker()
        ]
        
    def run_full_diagnostic(self, target: Optional[str] = None) -> DiagnosticReport:
        """Diagnostic complet du système ou d'un environnement"""
        start_time = datetime.now()
        
        if target:
            report = self._diagnose_environment(target)
        else:
            report = self._diagnose_system()
            
        report.execution_time = (datetime.now() - start_time).total_seconds()
        report.generated_at = datetime.now()
        report.overall_status = self._calculate_overall_status(report)
        
        return report
        
    def diagnose_environment(self, env_name: str) -> DiagnosticReport:
        """Diagnostic environnement spécifique"""
        return self._diagnose_environment(env_name)
        
    def diagnose_system(self) -> DiagnosticReport:
        """Diagnostic système complet"""
        return self._diagnose_system()
        
    def diagnose_cache(self) -> DiagnosticReport:
        """Diagnostic du cache"""
        report = DiagnosticReport()
        report.issues.extend(self._check_cache_health())
        return report
        
    def auto_repair_environment(self, env_name: str, issues: List[DiagnosticIssue]) -> RepairResult:
        """Réparation automatique d'un environnement"""
        env_info = self.env_manager.get_environment_info(env_name)
        if not env_info:
            return RepairResult(
                success=False,
                message=f"Environnement '{env_name}' introuvable"
            )
            
        backup_path = self._backup_environment(env_info)
        
        repair_actions = []
        issues_fixed = []
        issues_remaining = []
        
        for issue in issues:
            if not issue.auto_fixable:
                issues_remaining.append(issue.description)
                continue
                
            try:
                action_result = self._apply_auto_fix(env_info, issue)
                if action_result.success:
                    issues_fixed.append(issue.description)
                    repair_actions.append(action_result.action)
                else:
                    issues_remaining.append(issue.description)
                    
            except Exception as e:
                issues_remaining.append(f"{issue.description} (erreur: {e})")
                
        post_repair_report = self._diagnose_environment(env_name)
        remaining_critical = [i for i in post_repair_report.issues 
                            if i.level == IssueLevel.CRITICAL]
        
        success = len(remaining_critical) == 0
        
        return RepairResult(
            success=success,
            message=f"Réparation {'réussie' if success else 'partielle'}",
            issues_fixed=issues_fixed,
            issues_remaining=issues_remaining,
            actions_taken=repair_actions
        )
        
    def check_environment_health(self, env_info: EnvironmentInfo) -> EnvironmentHealth:
        """Vérifie la santé d'un environnement"""
        issues = []
        
        for checker in self.checkers:
            try:
                checker_issues = checker.check_environment(env_info)
                issues.extend(checker_issues)
            except Exception as e:
                logger.warning(f"Erreur checker {checker.__class__.__name__}: {e}")
        
        # Calcul santé globale
        critical_count = sum(1 for issue in issues if issue.level == IssueLevel.CRITICAL)
        error_count = sum(1 for issue in issues if issue.level == IssueLevel.ERROR)
        warning_count = sum(1 for issue in issues if issue.level == IssueLevel.WARNING)
        
        if critical_count > 0:
            return EnvironmentHealth.CORRUPTED
        elif error_count > 0:
            return EnvironmentHealth.HAS_ERRORS
        elif warning_count > 0:
            return EnvironmentHealth.HAS_WARNINGS
        else:
            return EnvironmentHealth.HEALTHY
            
    def validate_configuration(self) -> List[ValidationError]:
        """Valide la configuration"""
        errors = []
        
        try:
            config_errors = self.env_manager.config_manager.validate_config()
            errors.extend([ValidationError(error) for error in config_errors])
        except Exception as e:
            errors.append(ValidationError(f"Erreur validation config: {e}"))
            
        return errors
        
    def check_dependencies_integrity(self, env_info: EnvironmentInfo) -> List[str]:
        """Vérifie l'intégrité des dépendances"""
        issues = []
        
        if env_info.pyproject_info:
            expected_packages = set(
                dep.split('>=')[0].split('==')[0].split('[')[0] 
                for dep in env_info.pyproject_info.dependencies
            )
            installed_packages = set(pkg.name for pkg in env_info.packages)
            
            missing = expected_packages - installed_packages
            if missing:
                issues.append(f"Packages manquants: {', '.join(missing)}")
                
            extra = installed_packages - expected_packages
            if extra:
                issues.append(f"Packages supplémentaires: {', '.join(extra)}")
        
        return issues
        
    def suggest_optimizations(self, env_info: EnvironmentInfo = None) -> List[OptimizationSuggestion]:
        """Suggère des optimisations"""
        suggestions = []
        
        if env_info:
            # Optimisations spécifiques à l'environnement
            suggestions.extend(self._suggest_env_optimizations(env_info))
        else:
            # Optimisations globales
            suggestions.extend(self._suggest_global_optimizations())
        
        return suggestions
    
    # Méthodes privées
    
    def _diagnose_environment(self, env_name: str) -> DiagnosticReport:
        """Diagnostic environnement spécifique"""
        env_info = self.env_manager.get_environment_info(env_name)
        if not env_info:
            return DiagnosticReport(
                overall_status=EnvironmentHealth.UNKNOWN,
                issues=[DiagnosticIssue(
                    level=IssueLevel.ERROR,
                    category="environment",
                    description=f"Environnement '{env_name}' introuvable"
                )]
            )
            
        report = DiagnosticReport()
        
        for checker in self.checkers:
            try:
                checker_issues = checker.check_environment(env_info)
                report.issues.extend(checker_issues)
            except Exception as e:
                report.warnings.append(f"Erreur checker {checker.__class__.__name__}: {e}")
                
        report.recommendations = self._generate_recommendations(env_info, report.issues)
        
        return report
        
    def _diagnose_system(self) -> DiagnosticReport:
        """Diagnostic système complet"""
        report = DiagnosticReport()
        
        environments = self.env_manager.list_environments()
        
        for env in environments:
            env_issues = []
            for checker in self.checkers:
                try:
                    issues = checker.check_environment(env)
                    env_issues.extend(issues)
                except Exception as e:
                    report.warnings.append(f"Erreur check {env.name}: {e}")
                    
            report.issues.extend(env_issues)
            
        config_issues = self._check_configuration()
        report.issues.extend(config_issues)
        
        cache_issues = self._check_cache_health()
        report.issues.extend(cache_issues)
        
        report.recommendations = self._generate_system_recommendations(report.issues)
        
        return report
        
    def _calculate_overall_status(self, report: DiagnosticReport) -> EnvironmentHealth:
        """Calcule le statut global"""
        critical_count = sum(1 for issue in report.issues if issue.level == IssueLevel.CRITICAL)
        error_count = sum(1 for issue in report.issues if issue.level == IssueLevel.ERROR)
        warning_count = sum(1 for issue in report.issues if issue.level == IssueLevel.WARNING)
        
        if critical_count > 0:
            return EnvironmentHealth.CORRUPTED
        elif error_count > 0:
            return EnvironmentHealth.HAS_ERRORS
        elif warning_count > 0:
            return EnvironmentHealth.HAS_WARNINGS
        else:
            return EnvironmentHealth.HEALTHY
            
    def _apply_auto_fix(self, env_info: EnvironmentInfo, issue: DiagnosticIssue):
        """Applique un correctif automatique"""
        fix_category = issue.category
        
        if fix_category == "missing_packages":
            return self._fix_missing_packages(env_info, issue)
        elif fix_category == "corrupted_packages":
            return self._fix_corrupted_packages(env_info, issue)
        elif fix_category == "permissions":
            return self._fix_permissions(env_info, issue)
        elif fix_category == "python_version":
            return self._fix_python_version(env_info, issue)
        else:
            return AutoFixResult(
                success=False,
                action=f"Correctif automatique non disponible pour: {fix_category}"
            )
            
    def _backup_environment(self, env_info: EnvironmentInfo) -> Optional[Path]:
        """Sauvegarde un environnement"""
        try:
            return self.env_manager.migration_service.backup_environment(env_info)
        except Exception as e:
            logger.error(f"Erreur sauvegarde environnement: {e}")
            return None
            
    def _check_configuration(self) -> List[DiagnosticIssue]:
        """Vérifie la configuration"""
        issues = []
        
        try:
            config_errors = self.env_manager.config_manager.validate_config()
            for error in config_errors:
                issues.append(DiagnosticIssue(
                    level=IssueLevel.WARNING,
                    category="configuration",
                    description=error,
                    auto_fixable=False
                ))
        except Exception as e:
            issues.append(DiagnosticIssue(
                level=IssueLevel.ERROR,
                category="configuration",
                description=f"Erreur validation config: {e}",
                auto_fixable=False
            ))
            
        return issues
        
    def _check_cache_health(self) -> List[DiagnosticIssue]:
        """Vérifie la santé du cache"""
        issues = []
        
        try:
            cache_service = self.env_manager.cache_service
            cache_size = cache_service.get_cache_size()
            max_size = cache_service.max_size_mb * 1024 * 1024
            
            if cache_size > max_size:
                issues.append(DiagnosticIssue(
                    level=IssueLevel.WARNING,
                    category="cache_size",
                    description=f"Cache trop volumineux: {cache_size / (1024*1024):.1f}MB",
                    solution="Nettoyer le cache",
                    auto_fixable=True
                ))
                
        except Exception as e:
            issues.append(DiagnosticIssue(
                level=IssueLevel.WARNING,
                category="cache",
                description=f"Erreur vérification cache: {e}",
                auto_fixable=False
            ))
            
        return issues
        
    def _generate_recommendations(self, env_info: EnvironmentInfo, issues: List[DiagnosticIssue]) -> List[OptimizationSuggestion]:
        """Génère des recommandations spécifiques"""
        suggestions = []
        
        # Backend optimization
        if env_info.backend_type.value == "pip":
            if self.env_manager.backend_manager.backends.get('uv', {}).available:
                suggestions.append(OptimizationSuggestion(
                    category="performance",
                    description="Migrer vers backend uv pour 10x plus de performance",
                    command=f"gestvenv backend set uv",
                    impact_score=0.9,
                    safe_to_apply=True
                ))
        
        return suggestions
        
    def _generate_system_recommendations(self, issues: List[DiagnosticIssue]) -> List[OptimizationSuggestion]:
        """Génère des recommandations système"""
        return []
        
    def _suggest_env_optimizations(self, env_info: EnvironmentInfo) -> List[OptimizationSuggestion]:
        """Optimisations spécifiques environnement"""
        return []
        
    def _suggest_global_optimizations(self) -> List[OptimizationSuggestion]:
        """Optimisations globales"""
        return []


class EnvironmentIntegrityChecker:
    """Vérificateur d'intégrité des environnements"""
    
    def check_environment(self, env_info: EnvironmentInfo) -> List[DiagnosticIssue]:
        """Vérifie l'intégrité d'un environnement"""
        issues = []
        
        if not env_info.path.exists():
            issues.append(DiagnosticIssue(
                level=IssueLevel.CRITICAL,
                category="missing_directory",
                description=f"Répertoire environnement manquant: {env_info.path}",
                solution="Recréer l'environnement ou supprimer la référence",
                auto_fixable=False
            ))
            return issues
            
        python_exe = self._get_python_executable(env_info.path)
        if not python_exe.exists():
            issues.append(DiagnosticIssue(
                level=IssueLevel.CRITICAL,
                category="missing_python",
                description="Exécutable Python manquant",
                solution="Recréer l'environnement",
                auto_fixable=True
            ))
            
        try:
            result = subprocess.run(
                [str(python_exe), "-m", "pip", "--version"], 
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                issues.append(DiagnosticIssue(
                    level=IssueLevel.ERROR,
                    category="pip_broken",
                    description="pip non fonctionnel",
                    solution="Réinstaller pip",
                    auto_fixable=True
                ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            issues.append(DiagnosticIssue(
                level=IssueLevel.ERROR,
                category="pip_timeout",
                description="pip ne répond pas",
                auto_fixable=True
            ))
            
        if not os.access(env_info.path, os.R_OK | os.W_OK):
            issues.append(DiagnosticIssue(
                level=IssueLevel.ERROR,
                category="permissions",
                description="Permissions insuffisantes sur l'environnement",
                solution="Corriger les permissions",
                auto_fixable=True
            ))
            
        return issues
        
    def _get_python_executable(self, env_path: Path) -> Path:
        """Exécutable Python de l'environnement"""
        if os.name == 'nt':
            return env_path / "Scripts" / "python.exe"
        else:
            return env_path / "bin" / "python"


class DependencyIntegrityChecker:
    """Vérificateur d'intégrité des dépendances"""
    
    def check_environment(self, env_info: EnvironmentInfo) -> List[DiagnosticIssue]:
        issues = []
        
        if env_info.pyproject_info:
            expected_packages = set(
                pkg.split('>=')[0].split('==')[0].split('[')[0]
                for pkg in env_info.pyproject_info.dependencies
            )
            installed_packages = set(pkg.name for pkg in env_info.packages)
            
            missing_packages = expected_packages - installed_packages
            if missing_packages:
                issues.append(DiagnosticIssue(
                    level=IssueLevel.WARNING,
                    category="missing_packages",
                    description=f"Packages manquants: {', '.join(missing_packages)}",
                    solution="Synchroniser l'environnement",
                    auto_fixable=True,
                    metadata={"missing_packages": list(missing_packages)}
                ))
        
        return issues


class PerformanceChecker:
    """Vérificateur de performance"""
    
    def check_environment(self, env_info: EnvironmentInfo) -> List[DiagnosticIssue]:
        issues = []
        
        if env_info.backend_type.value == "pip":
            issues.append(DiagnosticIssue(
                level=IssueLevel.INFO,
                category="suboptimal_backend",
                description="Backend pip utilisé, uv disponible pour 10x plus de performance",
                solution="Migrer vers uv: gestvenv backend set uv",
                auto_fixable=True
            ))
            
        env_size_mb = self._calculate_environment_size(env_info.path)
        if env_size_mb > 1000:
            issues.append(DiagnosticIssue(
                level=IssueLevel.WARNING,
                category="large_environment",
                description=f"Environnement volumineux: {env_size_mb:.1f}MB",
                solution="Nettoyer les packages inutilisés",
                auto_fixable=False,
                metadata={"size_mb": env_size_mb}
            ))
            
        return issues
        
    def _calculate_environment_size(self, env_path: Path) -> float:
        """Calcule la taille d'un environnement"""
        try:
            total_size = sum(f.stat().st_size for f in env_path.rglob('*') if f.is_file())
            return total_size / (1024 * 1024)
        except Exception:
            return 0.0


class SecurityChecker:
    """Vérificateur de sécurité"""
    
    def check_environment(self, env_info: EnvironmentInfo) -> List[DiagnosticIssue]:
        return []


class CacheHealthChecker:
    """Vérificateur de santé du cache"""
    
    def check_environment(self, env_info: EnvironmentInfo) -> List[DiagnosticIssue]:
        return []


@dataclass 
class AutoFixResult:
    """Résultat d'un correctif automatique"""
    success: bool
    action: str