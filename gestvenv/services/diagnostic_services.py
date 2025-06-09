"""
DiagnosticService - Service de diagnostic et réparation automatique.

Ce service effectue des diagnostics complets des environnements GestVenv et propose
des réparations automatiques pour :
- Environnements corrompus ou endommagés
- Problèmes de configuration
- Incohérences de cache
- Conflits de dépendances
- Problèmes de performance
- Validation de l'intégrité globale

Il utilise tous les autres services pour effectuer des analyses approfondies
et proposer des solutions ciblées.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import json

logger = logging.getLogger(__name__)


class DiagnosticLevel(Enum):
    """Niveaux de diagnostic."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DiagnosticCategory(Enum):
    """Catégories de diagnostic."""
    ENVIRONMENT = "environment"
    PACKAGES = "packages"
    CONFIGURATION = "configuration"
    CACHE = "cache"
    SYSTEM = "system"
    PERFORMANCE = "performance"
    MIGRATION = "migration"


class RepairAction(Enum):
    """Actions de réparation disponibles."""
    AUTO_REPAIR = "auto_repair"
    MANUAL_INTERVENTION = "manual_intervention"
    RECREATE = "recreate"
    UPDATE = "update"
    CLEANUP = "cleanup"
    MIGRATE = "migrate"


@dataclass
class DiagnosticIssue:
    """Représente un problème détecté lors du diagnostic."""
    id: str
    level: DiagnosticLevel
    category: DiagnosticCategory
    title: str
    description: str
    affected_items: List[str] = field(default_factory=list)
    repair_action: Optional[RepairAction] = None
    repair_description: Optional[str] = None
    auto_repairable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def severity_score(self) -> int:
        """Score de sévérité pour priorisation."""
        scores = {
            DiagnosticLevel.INFO: 1,
            DiagnosticLevel.WARNING: 2,
            DiagnosticLevel.ERROR: 3,
            DiagnosticLevel.CRITICAL: 4
        }
        return scores.get(self.level, 0)


@dataclass
class RepairResult:
    """Résultat d'une opération de réparation."""
    issue_id: str
    success: bool
    message: str
    actions_taken: List[str] = field(default_factory=list)
    duration: float = 0.0
    
    @property
    def formatted_message(self) -> str:
        """Message formaté avec détails des actions."""
        if self.actions_taken:
            return f"{self.message} (Actions: {', '.join(self.actions_taken)})"
        return self.message


@dataclass
class DiagnosticReport:
    """Rapport complet de diagnostic."""
    timestamp: float
    total_issues: int
    issues_by_level: Dict[DiagnosticLevel, int]
    issues_by_category: Dict[DiagnosticCategory, int]
    issues: List[DiagnosticIssue]
    auto_repairable_count: int
    system_info: Dict[str, Any]
    duration: float = 0.0
    
    @property
    def has_critical_issues(self) -> bool:
        """True s'il y a des problèmes critiques."""
        return self.issues_by_level.get(DiagnosticLevel.CRITICAL, 0) > 0
    
    @property
    def has_errors(self) -> bool:
        """True s'il y a des erreurs."""
        return self.issues_by_level.get(DiagnosticLevel.ERROR, 0) > 0
    
    @property
    def health_score(self) -> float:
        """Score de santé global (0-100)."""
        if not self.total_issues:
            return 100.0
        
        # Calcul basé sur la sévérité des problèmes
        total_severity = sum(issue.severity_score for issue in self.issues)
        max_possible_severity = len(self.issues) * 4  # Max = tous critiques
        
        health = 100.0 - (total_severity / max_possible_severity * 100.0)
        return max(0.0, health)
    
    def get_issues_by_category(self, category: DiagnosticCategory) -> List[DiagnosticIssue]:
        """Retourne les problèmes d'une catégorie spécifique."""
        return [issue for issue in self.issues if issue.category == category]
    
    def get_auto_repairable_issues(self) -> List[DiagnosticIssue]:
        """Retourne les problèmes réparables automatiquement."""
        return [issue for issue in self.issues if issue.auto_repairable]


class DiagnosticService:
    """
    Service de diagnostic et réparation automatique des environnements GestVenv.
    
    Responsabilités:
    - Diagnostic complet de l'état du système
    - Détection de problèmes et incohérences
    - Réparation automatique quand possible
    - Recommandations pour résolutions manuelles
    - Monitoring et alertes
    """
    
    def __init__(self, environment_service=None, package_service=None,
                 system_service=None, cache_service=None, migration_service=None,
                 config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialise le service de diagnostic.
        
        Args:
            environment_service: Service d'environnements
            package_service: Service de packages
            system_service: Service système
            cache_service: Service de cache
            migration_service: Service de migration
            config: Configuration optionnelle
        """
        self.environment_service = environment_service
        self.package_service = package_service
        self.system_service = system_service
        self.cache_service = cache_service
        self.migration_service = migration_service
        self.config = config or {}
        
        # Configuration
        self.auto_repair_enabled = self.config.get('auto_repair_enabled', True)
        self.max_repair_attempts = self.config.get('max_repair_attempts', 3)
        self.deep_analysis = self.config.get('deep_analysis', True)
        self.performance_checks = self.config.get('performance_checks', True)
        
        # Registre des vérifications
        self.checks = self._register_diagnostic_checks()
        
        logger.debug(f"DiagnosticService initialisé avec {len(self.checks)} vérifications")
    
    def run_full_diagnostic(self, environments_path: Optional[Path] = None) -> DiagnosticReport:
        """
        Lance un diagnostic complet du système GestVenv.
        
        Args:
            environments_path: Chemin vers les environnements (optionnel)
            
        Returns:
            DiagnosticReport: Rapport de diagnostic complet
        """
        start_time = time.time()
        logger.info("Début du diagnostic complet...")
        
        # Initialisation du rapport
        issues = []
        system_info = self._collect_system_info()
        
        # Détermination du chemin des environnements
        if environments_path is None:
            environments_path = Path.home() / '.gestvenv' / 'environments'
        
        # Exécution de toutes les vérifications
        for check_name, check_func in self.checks.items():
            try:
                logger.debug(f"Exécution de la vérification: {check_name}")
                check_issues = check_func(environments_path)
                issues.extend(check_issues)
            except Exception as e:
                logger.error(f"Erreur lors de la vérification {check_name}: {e}")
                # Ajouter l'erreur comme problème critique
                issues.append(DiagnosticIssue(
                    id=f"check_error_{check_name}",
                    level=DiagnosticLevel.CRITICAL,
                    category=DiagnosticCategory.SYSTEM,
                    title=f"Erreur de vérification: {check_name}",
                    description=f"Erreur inattendue lors de la vérification: {str(e)}",
                    repair_action=RepairAction.MANUAL_INTERVENTION,
                    auto_repairable=False
                ))
        
        # Compilation des statistiques
        issues_by_level = {}
        issues_by_category = {}
        auto_repairable_count = 0
        
        for issue in issues:
            # Par niveau
            issues_by_level[issue.level] = issues_by_level.get(issue.level, 0) + 1
            # Par catégorie
            issues_by_category[issue.category] = issues_by_category.get(issue.category, 0) + 1
            # Auto-réparables
            if issue.auto_repairable:
                auto_repairable_count += 1
        
        duration = time.time() - start_time
        
        report = DiagnosticReport(
            timestamp=start_time,
            total_issues=len(issues),
            issues_by_level=issues_by_level,
            issues_by_category=issues_by_category,
            issues=issues,
            auto_repairable_count=auto_repairable_count,
            system_info=system_info,
            duration=duration
        )
        
        logger.info(f"Diagnostic terminé en {duration:.2f}s: {len(issues)} problème(s) détecté(s)")
        logger.info(f"Score de santé: {report.health_score:.1f}/100")
        
        return report
    
    def run_environment_diagnostic(self, env_name: str, 
                                  environments_path: Optional[Path] = None) -> DiagnosticReport:
        """
        Lance un diagnostic spécifique à un environnement.
        
        Args:
            env_name: Nom de l'environnement
            environments_path: Chemin vers les environnements
            
        Returns:
            DiagnosticReport: Rapport de diagnostic pour cet environnement
        """
        start_time = time.time()
        logger.info(f"Diagnostic de l'environnement '{env_name}'...")
        
        if environments_path is None:
            environments_path = Path.home() / '.gestvenv' / 'environments'
        
        env_path = environments_path / env_name
        
        issues = []
        
        # Vérifications spécifiques à l'environnement
        env_checks = [
            'check_environment_integrity',
            'check_environment_packages',
            'check_environment_configuration'
        ]
        
        for check_name in env_checks:
            if check_name in self.checks:
                try:
                    check_issues = self.checks[check_name](environments_path, specific_env=env_name)
                    issues.extend(check_issues)
                except Exception as e:
                    logger.error(f"Erreur lors de {check_name}: {e}")
        
        # Compilation du rapport
        issues_by_level = {}
        issues_by_category = {}
        auto_repairable_count = sum(1 for issue in issues if issue.auto_repairable)
        
        for issue in issues:
            issues_by_level[issue.level] = issues_by_level.get(issue.level, 0) + 1
            issues_by_category[issue.category] = issues_by_category.get(issue.category, 0) + 1
        
        duration = time.time() - start_time
        
        return DiagnosticReport(
            timestamp=start_time,
            total_issues=len(issues),
            issues_by_level=issues_by_level,
            issues_by_category=issues_by_category,
            issues=issues,
            auto_repairable_count=auto_repairable_count,
            system_info=self._collect_system_info(),
            duration=duration
        )
    
    def auto_repair(self, report: DiagnosticReport) -> Dict[str, RepairResult]:
        """
        Effectue les réparations automatiques possibles.
        
        Args:
            report: Rapport de diagnostic
            
        Returns:
            Dict[str, RepairResult]: Résultats des réparations par ID de problème
        """
        if not self.auto_repair_enabled:
            logger.info("Réparation automatique désactivée")
            return {}
        
        auto_repairable = report.get_auto_repairable_issues()
        if not auto_repairable:
            logger.info("Aucun problème réparable automatiquement")
            return {}
        
        logger.info(f"Début de la réparation automatique: {len(auto_repairable)} problème(s)")
        
        results = {}
        
        # Tri par sévérité (critiques en premier)
        auto_repairable.sort(key=lambda x: x.severity_score, reverse=True)
        
        for issue in auto_repairable:
            try:
                result = self._repair_issue(issue)
                results[issue.id] = result
                
                if result.success:
                    logger.info(f"✓ Réparation réussie: {issue.title}")
                else:
                    logger.warning(f"✗ Échec de réparation: {issue.title} - {result.message}")
                    
            except Exception as e:
                logger.error(f"Erreur lors de la réparation de {issue.id}: {e}")
                results[issue.id] = RepairResult(
                    issue.id, False, f"Erreur interne: {str(e)}"
                )
        
        successful_repairs = sum(1 for r in results.values() if r.success)
        logger.info(f"Réparation automatique terminée: {successful_repairs}/{len(auto_repairable)} réussies")
        
        return results
    
    def _register_diagnostic_checks(self) -> Dict[str, callable]:
        """Enregistre toutes les vérifications de diagnostic."""
        return {
            'check_system_requirements': self._check_system_requirements,
            'check_environment_integrity': self._check_environment_integrity,
            'check_environment_packages': self._check_environment_packages,
            'check_environment_configuration': self._check_environment_configuration,
            'check_cache_integrity': self._check_cache_integrity,
            'check_cache_performance': self._check_cache_performance,
            'check_backend_availability': self._check_backend_availability,
            'check_configuration_consistency': self._check_configuration_consistency,
            'check_migration_status': self._check_migration_status,
            'check_disk_space': self._check_disk_space,
            'check_permissions': self._check_permissions,
        }
    
    def _check_system_requirements(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie les prérequis système."""
        issues = []
        
        # Vérification de Python
        if self.system_service:
            python_versions = self.system_service.get_available_python_versions()
            if not python_versions:
                issues.append(DiagnosticIssue(
                    id="no_python_found",
                    level=DiagnosticLevel.CRITICAL,
                    category=DiagnosticCategory.SYSTEM,
                    title="Aucune version Python détectée",
                    description="Aucune installation Python valide n'a été trouvée sur le système.",
                    repair_action=RepairAction.MANUAL_INTERVENTION,
                    repair_description="Installer Python 3.8+ sur le système",
                    auto_repairable=False
                ))
            else:
                # Vérifier versions obsolètes
                modern_versions = [v for v in python_versions if v.version_info >= (3, 8)]
                if not modern_versions:
                    issues.append(DiagnosticIssue(
                        id="python_version_outdated",
                        level=DiagnosticLevel.ERROR,
                        category=DiagnosticCategory.SYSTEM,
                        title="Versions Python obsolètes",
                        description="Aucune version Python moderne (3.8+) détectée.",
                        repair_action=RepairAction.MANUAL_INTERVENTION,
                        repair_description="Mettre à jour Python vers une version 3.8+",
                        auto_repairable=False
                    ))
        
        # Vérification de l'espace disque
        try:
            import shutil
            total, used, free = shutil.disk_usage(environments_path.parent)
            free_gb = free / (1024**3)
            
            if free_gb < 0.5:  # Moins de 500MB
                issues.append(DiagnosticIssue(
                    id="low_disk_space",
                    level=DiagnosticLevel.WARNING,
                    category=DiagnosticCategory.SYSTEM,
                    title="Espace disque faible",
                    description=f"Espace libre: {free_gb:.1f} GB",
                    repair_action=RepairAction.CLEANUP,
                    repair_description="Nettoyer les caches et environnements inutilisés",
                    auto_repairable=True
                ))
        except Exception:
            pass
        
        return issues
    
    def _check_environment_integrity(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie l'intégrité des environnements."""
        issues = []
        specific_env = kwargs.get('specific_env')
        
        if not environments_path.exists():
            issues.append(DiagnosticIssue(
                id="environments_dir_missing",
                level=DiagnosticLevel.ERROR,
                category=DiagnosticCategory.ENVIRONMENT,
                title="Répertoire des environnements manquant",
                description=f"Le répertoire {environments_path} n'existe pas.",
                repair_action=RepairAction.AUTO_REPAIR,
                repair_description="Créer le répertoire des environnements",
                auto_repairable=True
            ))
            return issues
        
        # Vérification des environnements individuels
        if specific_env:
            env_dirs = [environments_path / specific_env] if (environments_path / specific_env).exists() else []
        else:
            env_dirs = [d for d in environments_path.iterdir() if d.is_dir()]
        
        for env_dir in env_dirs:
            if self.environment_service:
                health = self.environment_service.check_environment_health(env_dir.name, environments_path)
                
                if not health.is_healthy:
                    level = DiagnosticLevel.CRITICAL if health.status.value == 'broken' else DiagnosticLevel.WARNING
                    
                    issues.append(DiagnosticIssue(
                        id=f"env_unhealthy_{env_dir.name}",
                        level=level,
                        category=DiagnosticCategory.ENVIRONMENT,
                        title=f"Environnement endommagé: {env_dir.name}",
                        description=f"Problèmes détectés: {', '.join(health.issues)}",
                        affected_items=[env_dir.name],
                        repair_action=RepairAction.RECREATE if health.status.value == 'broken' else RepairAction.AUTO_REPAIR,
                        repair_description="Recréer l'environnement" if health.status.value == 'broken' else "Réparer l'environnement",
                        auto_repairable=health.status.value != 'broken',
                        metadata={'health_status': health.status.value, 'issues': health.issues}
                    ))
        
        return issues
    
    def _check_environment_packages(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie l'état des packages dans les environnements."""
        issues = []
        specific_env = kwargs.get('specific_env')
        
        if not self.package_service:
            return issues
        
        if specific_env:
            env_names = [specific_env]
        else:
            env_names = [d.name for d in environments_path.iterdir() if d.is_dir()]
        
        for env_name in env_names:
            try:
                packages = self.package_service.list_packages(env_name)
                
                # Vérification de packages critiques manquants
                critical_packages = ['pip', 'setuptools']
                installed_names = {pkg.name.lower() for pkg in packages}
                
                missing_critical = [pkg for pkg in critical_packages if pkg not in installed_names]
                if missing_critical:
                    issues.append(DiagnosticIssue(
                        id=f"missing_critical_packages_{env_name}",
                        level=DiagnosticLevel.ERROR,
                        category=DiagnosticCategory.PACKAGES,
                        title=f"Packages critiques manquants dans {env_name}",
                        description=f"Packages manquants: {', '.join(missing_critical)}",
                        affected_items=[env_name],
                        repair_action=RepairAction.AUTO_REPAIR,
                        repair_description="Installer les packages critiques manquants",
                        auto_repairable=True,
                        metadata={'missing_packages': missing_critical}
                    ))
                
                # Vérification de packages obsolètes
                # TODO: Implémenter la vérification de versions obsolètes
                
            except Exception as e:
                issues.append(DiagnosticIssue(
                    id=f"package_check_error_{env_name}",
                    level=DiagnosticLevel.WARNING,
                    category=DiagnosticCategory.PACKAGES,
                    title=f"Impossible de vérifier les packages de {env_name}",
                    description=f"Erreur lors de la vérification: {str(e)}",
                    affected_items=[env_name],
                    auto_repairable=False
                ))
        
        return issues
    
    def _check_environment_configuration(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie la configuration des environnements."""
        issues = []
        
        # TODO: Vérifier les fichiers de configuration des environnements
        # - pyvenv.cfg
        # - variables d'environnement
        # - scripts d'activation
        
        return issues
    
    def _check_cache_integrity(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie l'intégrité du cache."""
        issues = []
        
        if not self.cache_service:
            return issues
        
        try:
            stats = self.cache_service.get_cache_stats()
            
            # Cache trop volumineux
            if stats.total_size_mb > 5000:  # 5GB
                issues.append(DiagnosticIssue(
                    id="cache_too_large",
                    level=DiagnosticLevel.WARNING,
                    category=DiagnosticCategory.CACHE,
                    title="Cache volumineux",
                    description=f"Taille du cache: {stats.total_size_mb:.1f} MB",
                    repair_action=RepairAction.CLEANUP,
                    repair_description="Optimiser et nettoyer le cache",
                    auto_repairable=True,
                    metadata={'cache_size_mb': stats.total_size_mb}
                ))
            
            # Taux de hit faible
            if stats.hit_rate < 0.3 and stats.total_entries > 10:
                issues.append(DiagnosticIssue(
                    id="low_cache_hit_rate",
                    level=DiagnosticLevel.INFO,
                    category=DiagnosticCategory.CACHE,
                    title="Taux de hit du cache faible",
                    description=f"Taux de hit: {stats.hit_rate:.1%}",
                    repair_action=RepairAction.UPDATE,
                    repair_description="Optimiser la stratégie de cache",
                    auto_repairable=True,
                    metadata={'hit_rate': stats.hit_rate}
                ))
        
        except Exception as e:
            issues.append(DiagnosticIssue(
                id="cache_check_error",
                level=DiagnosticLevel.WARNING,
                category=DiagnosticCategory.CACHE,
                title="Erreur de vérification du cache",
                description=f"Impossible de vérifier le cache: {str(e)}",
                auto_repairable=False
            ))
        
        return issues
    
    def _check_cache_performance(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie les performances du cache."""
        issues = []
        
        if not self.cache_service or not self.performance_checks:
            return issues
        
        # TODO: Tests de performance du cache
        # - Temps d'accès
        # - Efficacité de compression
        # - Fragmentation
        
        return issues
    
    def _check_backend_availability(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie la disponibilité des backends."""
        issues = []
        
        if not self.package_service:
            return issues
        
        try:
            available_backends = self.package_service.get_available_backends()
            
            if not available_backends:
                issues.append(DiagnosticIssue(
                    id="no_backends_available",
                    level=DiagnosticLevel.CRITICAL,
                    category=DiagnosticCategory.PACKAGES,
                    title="Aucun backend de packages disponible",
                    description="Aucun backend (pip, uv, etc.) n'est disponible.",
                    repair_action=RepairAction.MANUAL_INTERVENTION,
                    repair_description="Installer pip ou un autre gestionnaire de packages",
                    auto_repairable=False
                ))
            elif 'pip' not in available_backends:
                issues.append(DiagnosticIssue(
                    id="pip_not_available",
                    level=DiagnosticLevel.ERROR,
                    category=DiagnosticCategory.PACKAGES,
                    title="pip non disponible",
                    description="Le gestionnaire de packages pip n'est pas disponible.",
                    repair_action=RepairAction.MANUAL_INTERVENTION,
                    repair_description="Installer ou réparer pip",
                    auto_repairable=False
                ))
            
            # Recommandation pour uv
            if 'uv' not in available_backends:
                issues.append(DiagnosticIssue(
                    id="uv_not_available",
                    level=DiagnosticLevel.INFO,
                    category=DiagnosticCategory.PACKAGES,
                    title="uv non disponible",
                    description="Le gestionnaire rapide uv n'est pas installé.",
                    repair_action=RepairAction.MANUAL_INTERVENTION,
                    repair_description="Installer uv pour des performances améliorées",
                    auto_repairable=False
                ))
        
        except Exception as e:
            issues.append(DiagnosticIssue(
                id="backend_check_error",
                level=DiagnosticLevel.WARNING,
                category=DiagnosticCategory.PACKAGES,
                title="Erreur de vérification des backends",
                description=f"Impossible de vérifier les backends: {str(e)}",
                auto_repairable=False
            ))
        
        return issues
    
    def _check_configuration_consistency(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie la cohérence de la configuration."""
        issues = []
        
        # TODO: Vérifier la configuration GestVenv
        # - Fichiers de config
        # - Paramètres incohérents
        # - Migrations nécessaires
        
        return issues
    
    def _check_migration_status(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie le statut des migrations."""
        issues = []
        
        if not self.migration_service:
            return issues
        
        # TODO: Vérifier les migrations en attente
        # - Versions obsolètes
        # - Formats à migrer
        # - Compatibilité
        
        return issues
    
    def _check_disk_space(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie l'espace disque disponible."""
        issues = []
        
        try:
            import shutil
            
            # Vérification de l'espace pour les environnements
            total, used, free = shutil.disk_usage(environments_path)
            free_gb = free / (1024**3)
            
            if free_gb < 1.0:  # Moins de 1GB
                issues.append(DiagnosticIssue(
                    id="critical_disk_space",
                    level=DiagnosticLevel.CRITICAL,
                    category=DiagnosticCategory.SYSTEM,
                    title="Espace disque critique",
                    description=f"Espace libre: {free_gb:.1f} GB",
                    repair_action=RepairAction.CLEANUP,
                    repair_description="Nettoyer les fichiers temporaires et caches",
                    auto_repairable=True
                ))
            elif free_gb < 2.0:  # Moins de 2GB
                issues.append(DiagnosticIssue(
                    id="low_disk_space",
                    level=DiagnosticLevel.WARNING,
                    category=DiagnosticCategory.SYSTEM,
                    title="Espace disque faible",
                    description=f"Espace libre: {free_gb:.1f} GB",
                    repair_action=RepairAction.CLEANUP,
                    repair_description="Nettoyer les fichiers inutiles",
                    auto_repairable=True
                ))
        
        except Exception:
            pass
        
        return issues
    
    def _check_permissions(self, environments_path: Path, **kwargs) -> List[DiagnosticIssue]:
        """Vérifie les permissions sur les fichiers/dossiers."""
        issues = []
        
        # Vérification des permissions d'écriture
        if not os.access(environments_path.parent, os.W_OK):
            issues.append(DiagnosticIssue(
                id="no_write_permission",
                level=DiagnosticLevel.ERROR,
                category=DiagnosticCategory.SYSTEM,
                title="Permissions d'écriture insuffisantes",
                description=f"Pas de permission d'écriture sur {environments_path.parent}",
                repair_action=RepairAction.MANUAL_INTERVENTION,
                repair_description="Ajuster les permissions du répertoire",
                auto_repairable=False
            ))
        
        return issues
    
    def _repair_issue(self, issue: DiagnosticIssue) -> RepairResult:
        """
        Effectue la réparation d'un problème spécifique.
        
        Args:
            issue: Problème à réparer
            
        Returns:
            RepairResult: Résultat de la réparation
        """
        start_time = time.time()
        actions_taken = []
        
        try:
            if issue.repair_action == RepairAction.CLEANUP:
                return self._repair_cleanup(issue, actions_taken)
            elif issue.repair_action == RepairAction.AUTO_REPAIR:
                return self._repair_auto(issue, actions_taken)
            elif issue.repair_action == RepairAction.RECREATE:
                return self._repair_recreate(issue, actions_taken)
            elif issue.repair_action == RepairAction.UPDATE:
                return self._repair_update(issue, actions_taken)
            else:
                return RepairResult(
                    issue.id, False, "Action de réparation non supportée",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            logger.error(f"Erreur lors de la réparation de {issue.id}: {e}")
            return RepairResult(
                issue.id, False, f"Erreur lors de la réparation: {str(e)}",
                actions_taken, time.time() - start_time
            )
    
    def _repair_cleanup(self, issue: DiagnosticIssue, actions_taken: List[str]) -> RepairResult:
        """Effectue un nettoyage."""
        if issue.id.startswith("cache_") and self.cache_service:
            # Nettoyage du cache
            cleaned = self.cache_service.optimize_cache()
            actions_taken.append(f"Cache optimisé: {cleaned.get('removed_entries', 0)} entrées supprimées")
            return RepairResult(issue.id, True, "Cache nettoyé avec succès", actions_taken)
        
        return RepairResult(issue.id, False, "Type de nettoyage non supporté", actions_taken)
    
    def _repair_auto(self, issue: DiagnosticIssue, actions_taken: List[str]) -> RepairResult:
        """Effectue une réparation automatique."""
        if issue.id == "environments_dir_missing":
            # Création du répertoire des environnements
            try:
                Path.home().joinpath('.gestvenv', 'environments').mkdir(parents=True, exist_ok=True)
                actions_taken.append("Répertoire des environnements créé")
                return RepairResult(issue.id, True, "Répertoire créé", actions_taken)
            except Exception as e:
                return RepairResult(issue.id, False, f"Impossible de créer le répertoire: {e}", actions_taken)
        
        elif issue.id.startswith("missing_critical_packages_"):
            # Installation de packages critiques
            env_name = issue.affected_items[0] if issue.affected_items else None
            if env_name and self.package_service:
                missing_packages = issue.metadata.get('missing_packages', [])
                result = self.package_service.install_packages(env_name, missing_packages)
                if result.success:
                    actions_taken.append(f"Packages installés: {', '.join(missing_packages)}")
                    return RepairResult(issue.id, True, "Packages critiques installés", actions_taken)
                else:
                    return RepairResult(issue.id, False, f"Échec installation: {result.message}", actions_taken)
        
        return RepairResult(issue.id, False, "Type de réparation automatique non supporté", actions_taken)
    
    def _repair_recreate(self, issue: DiagnosticIssue, actions_taken: List[str]) -> RepairResult:
        """Effectue une recréation."""
        if issue.id.startswith("env_unhealthy_") and self.environment_service:
            env_name = issue.affected_items[0] if issue.affected_items else None
            if env_name:
                # TODO: Recréer l'environnement
                actions_taken.append(f"Environnement {env_name} marqué pour recréation")
                return RepairResult(issue.id, False, "Recréation manuelle requise", actions_taken)
        
        return RepairResult(issue.id, False, "Type de recréation non supporté", actions_taken)
    
    def _repair_update(self, issue: DiagnosticIssue, actions_taken: List[str]) -> RepairResult:
        """Effectue une mise à jour."""
        if issue.id == "low_cache_hit_rate" and self.cache_service:
            # Optimisation de la stratégie de cache
            try:
                optimized = self.cache_service.optimize_cache()
                actions_taken.append("Stratégie de cache optimisée")
                return RepairResult(issue.id, True, "Cache optimisé", actions_taken)
            except Exception as e:
                return RepairResult(issue.id, False, f"Erreur d'optimisation: {e}", actions_taken)
        
        return RepairResult(issue.id, False, "Type de mise à jour non supporté", actions_taken)
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collecte les informations système."""
        info = {
            'timestamp': time.time(),
            'gestvenv_version': '1.1.0'
        }
        
        if self.system_service:
            try:
                system_info = self.system_service.get_system_info()
                info.update({
                    'platform': system_info.platform,
                    'architecture': system_info.architecture,
                    'python_version': system_info.python_version,
                    'python_executable': str(system_info.python_executable)
                })
                
                # Versions Python disponibles
                python_versions = self.system_service.get_available_python_versions()
                info['available_python_versions'] = [
                    f"{v.version} ({v.executable})" for v in python_versions
                ]
            except Exception as e:
                info['system_info_error'] = str(e)
        
        if self.package_service:
            try:
                info['available_backends'] = self.package_service.get_available_backends()
            except Exception as e:
                info['backend_info_error'] = str(e)
        
        if self.cache_service:
            try:
                cache_stats = self.cache_service.get_cache_stats()
                info['cache_stats'] = {
                    'total_entries': cache_stats.total_entries,
                    'total_size_mb': cache_stats.total_size_mb,
                    'hit_rate': cache_stats.hit_rate,
                    'health_score': cache_stats.cache_efficiency
                }
            except Exception as e:
                info['cache_stats_error'] = str(e)
        
        return info
    
    def export_report(self, report: DiagnosticReport, output_path: Path,
                     format_type: str = 'json') -> bool:
        """
        Exporte un rapport de diagnostic.
        
        Args:
            report: Rapport à exporter
            output_path: Chemin de sortie
            format_type: Format d'export ('json', 'txt', 'html')
            
        Returns:
            bool: True si l'export a réussi
        """
        try:
            if format_type == 'json':
                return self._export_json(report, output_path)
            elif format_type == 'txt':
                return self._export_text(report, output_path)
            elif format_type == 'html':
                return self._export_html(report, output_path)
            else:
                logger.error(f"Format d'export non supporté: {format_type}")
                return False
        
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}")
            return False
    
    def _export_json(self, report: DiagnosticReport, output_path: Path) -> bool:
        """Exporte en format JSON."""
        try:
            # Conversion en dictionnaire sérialisable
            report_dict = {
                'timestamp': report.timestamp,
                'total_issues': report.total_issues,
                'issues_by_level': {level.value: count for level, count in report.issues_by_level.items()},
                'issues_by_category': {cat.value: count for cat, count in report.issues_by_category.items()},
                'auto_repairable_count': report.auto_repairable_count,
                'health_score': report.health_score,
                'duration': report.duration,
                'system_info': report.system_info,
                'issues': []
            }
            
            for issue in report.issues:
                issue_dict = {
                    'id': issue.id,
                    'level': issue.level.value,
                    'category': issue.category.value,
                    'title': issue.title,
                    'description': issue.description,
                    'affected_items': issue.affected_items,
                    'auto_repairable': issue.auto_repairable,
                    'repair_action': issue.repair_action.value if issue.repair_action else None,
                    'repair_description': issue.repair_description,
                    'metadata': issue.metadata
                }
                report_dict['issues'].append(issue_dict)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
            return True
        
        except Exception as e:
            logger.error(f"Erreur export JSON: {e}")
            return False
    
    def _export_text(self, report: DiagnosticReport, output_path: Path) -> bool:
        """Exporte en format texte."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=== RAPPORT DE DIAGNOSTIC GESTVENV ===\n\n")
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.timestamp))}\n")
                f.write(f"Durée: {report.duration:.2f}s\n")
                f.write(f"Score de santé: {report.health_score:.1f}/100\n\n")
                
                f.write("=== RÉSUMÉ ===\n")
                f.write(f"Total des problèmes: {report.total_issues}\n")
                f.write(f"Réparables automatiquement: {report.auto_repairable_count}\n\n")
                
                if report.issues:
                    f.write("=== PROBLÈMES DÉTECTÉS ===\n\n")
                    for issue in sorted(report.issues, key=lambda x: x.severity_score, reverse=True):
                        f.write(f"[{issue.level.value.upper()}] {issue.title}\n")
                        f.write(f"Catégorie: {issue.category.value}\n")
                        f.write(f"Description: {issue.description}\n")
                        if issue.affected_items:
                            f.write(f"Éléments affectés: {', '.join(issue.affected_items)}\n")
                        if issue.repair_description:
                            f.write(f"Réparation: {issue.repair_description}\n")
                        f.write("\n")
                else:
                    f.write("Aucun problème détecté.\n")
            
            return True
        
        except Exception as e:
            logger.error(f"Erreur export texte: {e}")
            return False
    
    def _export_html(self, report: DiagnosticReport, output_path: Path) -> bool:
        """Exporte en format HTML."""
        # TODO: Implémenter l'export HTML avec style CSS
        return self._export_text(output_path.with_suffix('.txt'))


# Import conditionnel pour éviter les erreurs si os n'est pas disponible
import os