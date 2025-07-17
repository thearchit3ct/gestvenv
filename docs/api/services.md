# API Services - GestVenv v1.1

Services métier de GestVenv v1.1 fournissant la logique applicative spécialisée.

## Vue d'ensemble

Le module `gestvenv.services` contient six services principaux :
- **PackageService** : Gestion unifiée des packages
- **CacheService** : Cache intelligent et mode hors ligne
- **MigrationService** : Migration et conversion de formats
- **SystemService** : Intégration système
- **DiagnosticService** : Diagnostic et réparation automatique
- **TemplateService** : Gestion des templates de projets

## PackageService

Service unifié de gestion des packages avec support multi-backend et cache intégré.

### Initialisation
```python
def __init__(self, backend_manager: BackendManager, cache_service: CacheService):
    self.backend_manager = backend_manager
    self.cache_service = cache_service
```

### Installation et désinstallation

#### install_package
```python
def install_package(
    self, 
    env: EnvironmentInfo, 
    package: str, 
    **kwargs
) -> InstallResult:
```
Installation avec sélection automatique du backend optimal et utilisation du cache.

**Paramètres:**
- `env`: Informations de l'environnement cible
- `package`: Spécification du package (ex: "django>=4.0")
- `kwargs`: Options spécifiques au backend

**Processus:**
1. Validation de la spécification du package
2. Sélection du backend optimal
3. Tentative d'installation depuis le cache (mode hors ligne)
4. Installation via le backend sélectionné
5. Mise en cache du package installé
6. Mise à jour des métadonnées de l'environnement

#### uninstall_package
```python
def uninstall_package(self, env: EnvironmentInfo, package: str) -> bool:
```
Désinstallation avec nettoyage automatique du cache.

#### update_package
```python
def update_package(
    self, 
    env: EnvironmentInfo, 
    package: str, 
    target_version: Optional[str] = None
) -> InstallResult:
```
Mise à jour d'un package vers une version spécifique ou la dernière disponible.

### Gestion des dépendances

#### list_packages
```python
def list_packages(self, env: EnvironmentInfo) -> List[PackageInfo]:
```
Liste tous les packages installés avec métadonnées complètes.

#### install_from_requirements
```python
def install_from_requirements(
    self, 
    env: EnvironmentInfo, 
    req_path: Path,
    upgrade: bool = False
) -> InstallResult:
```
Installation depuis un fichier requirements.txt avec options d'upgrade.

#### install_from_pyproject
```python
def install_from_pyproject(
    self, 
    env: EnvironmentInfo, 
    pyproject: PyProjectInfo,
    groups: Optional[List[str]] = None
) -> InstallResult:
```
Installation depuis pyproject.toml avec support des groupes de dépendances.

#### sync_environment
```python
def sync_environment(self, env: EnvironmentInfo) -> SyncResult:
```
Synchronisation complète de l'environnement selon la configuration source.

### Lock files et résolution

#### create_lock_file
```python
def create_lock_file(self, env: EnvironmentInfo) -> Optional[Path]:
```
Génère un fichier de verrouillage des versions pour reproductibilité.

#### install_from_lock
```python
def install_from_lock(self, env: EnvironmentInfo, lock_path: Path) -> bool:
```
Installation exacte depuis un fichier de lock.

#### resolve_dependencies
```python
def resolve_dependencies(self, packages: List[str]) -> Dict[str, str]:
```
Résolution des dépendances avec détection de conflits.

#### check_outdated_packages
```python
def check_outdated_packages(self, env: EnvironmentInfo) -> List[PackageInfo]:
```
Détection des packages obsolètes avec versions recommandées.

## CacheService

Cache intelligent multi-niveaux avec mode hors ligne intégré.

### Initialisation
```python
def __init__(self, config: Config):
    self.config = config
    self.cache_path = config.cache_dir
    self.max_size_mb = config.cache_size_mb
    self.offline_mode = config.offline_mode
```

### Gestion du cache

#### cache_package
```python
def cache_package(
    self, 
    package: str, 
    version: str, 
    platform: str, 
    data: bytes
) -> bool:
```
Met en cache un package téléchargé avec métadonnées.

#### get_cached_package
```python
def get_cached_package(
    self, 
    package: str, 
    version: str, 
    platform: str
) -> Optional[bytes]:
```
Récupère un package depuis le cache.

#### is_package_cached
```python
def is_package_cached(
    self, 
    package: str, 
    version: str, 
    platform: str
) -> bool:
```
Vérifie la disponibilité d'un package en cache.

#### cache_installed_package
```python
def cache_installed_package(self, env: EnvironmentInfo, package: str) -> bool:
```
Met en cache un package après installation réussie.

### Mode hors ligne

#### install_from_cache
```python
def install_from_cache(self, env: EnvironmentInfo, package: str) -> bool:
```
Installation complète depuis le cache uniquement.

#### set_offline_mode
```python
def set_offline_mode(self, enabled: bool) -> None:
```
Active/désactive le mode hors ligne.

#### is_offline_mode_enabled
```python
def is_offline_mode_enabled(self) -> bool:
```

### Maintenance

#### clear_cache
```python
def clear_cache(self, selective: bool = False) -> bool:
```
Nettoyage complet ou sélectif du cache.

#### optimize_cache
```python
def optimize_cache(self) -> bool:
```
Optimisation automatique avec suppression des doublons et compression.

#### get_cache_size
```python
def get_cache_size(self) -> int:
```
Taille totale du cache en bytes.

#### get_cache_stats
```python
def get_cache_stats(self) -> Dict[str, Any]:
```
Statistiques détaillées du cache (hit rate, packages count, etc.).

#### export_cache
```python
def export_cache(self, output_path: Path) -> bool:
```
Exportation du cache pour partage ou sauvegarde.

#### import_cache
```python
def import_cache(self, cache_path: Path) -> bool:
```
Importation d'un cache externe.

## MigrationService

Service de migration automatique entre versions et formats.

### Migration de versions

#### auto_migrate_if_needed
```python
def auto_migrate_if_needed(self) -> bool:
```
Détection et migration automatique si nécessaire.

#### migrate_from_v1_0
```python
def migrate_from_v1_0(self) -> bool:
```
Migration complète depuis GestVenv v1.0.

### Conversion de formats

#### migrate_requirements_to_pyproject
```python
def migrate_requirements_to_pyproject(
    self, 
    req_path: Path, 
    output_path: Optional[Path] = None
) -> PyProjectInfo:
```
Conversion requirements.txt vers pyproject.toml avec détection intelligente des dépendances.

#### detect_migration_candidates
```python
def detect_migration_candidates(self) -> List[Path]:
```
Détection automatique des projets candidats à la migration.

### Sauvegarde et restauration

#### backup_environment
```python
def backup_environment(self, env_info: EnvironmentInfo) -> Path:
```
Sauvegarde complète d'un environnement.

#### rollback_migration
```python
def rollback_migration(self, backup_path: Path, target_path: Path) -> bool:
```
Restauration depuis une sauvegarde.

## SystemService  

Service d'intégration système et détection de l'environnement.

### Détection Python

#### detect_python_versions
```python
def detect_python_versions(self) -> List[str]:
```
Détection de toutes les versions Python disponibles.

#### validate_python_version
```python
def validate_python_version(self, version: str) -> bool:
```
Validation d'une version Python spécifique.

### Informations système

#### get_system_info
```python
def get_system_info(self) -> Dict[str, Any]:
```
Informations complètes du système (OS, architecture, Python, backends).

#### check_backend_availability
```python
def check_backend_availability(self) -> Dict[str, bool]:
```
Vérification de disponibilité de tous les backends.

#### get_shell_info
```python
def get_shell_info(self) -> Dict[str, str]:
```
Détection du shell et génération des scripts d'activation.

### Intégration CI/CD

#### generate_ci_config
```python
def generate_ci_config(
    self, 
    platform: str, 
    env_info: EnvironmentInfo
) -> str:
```
Génération de configuration CI/CD pour différentes plateformes.

#### validate_ci_environment
```python
def validate_ci_environment(self) -> Dict[str, Any]:
```
Validation de l'environnement CI/CD.

## DiagnosticService

Service de diagnostic automatique et réparation.

### Diagnostic

#### run_full_diagnostic
```python
def run_full_diagnostic(self, target: Optional[str] = None) -> DiagnosticReport:
```
Diagnostic complet du système ou d'un environnement spécifique.

#### diagnose_environment
```python
def diagnose_environment(self, env_name: str) -> DiagnosticReport:
```
Diagnostic ciblé d'un environnement.

#### diagnose_cache
```python
def diagnose_cache(self) -> DiagnosticReport:
```
Diagnostic spécifique du cache.

### Réparation automatique

#### auto_repair_environment
```python
def auto_repair_environment(
    self, 
    env_name: str, 
    issues: List[DiagnosticIssue]
) -> RepairResult:
```
Réparation automatique des problèmes détectés.

#### repair_broken_packages
```python
def repair_broken_packages(self, env: EnvironmentInfo) -> RepairResult:
```
Réparation des packages corrompus ou manquants.

#### repair_environment_metadata
```python
def repair_environment_metadata(self, env: EnvironmentInfo) -> bool:
```
Réparation des métadonnées d'environnement.

### Optimisation

#### suggest_optimizations
```python
def suggest_optimizations(self, env: EnvironmentInfo) -> List[OptimizationSuggestion]:
```
Suggestions d'optimisation personnalisées.

#### check_security_issues
```python
def check_security_issues(self, env: EnvironmentInfo) -> List[DiagnosticIssue]:
```
Vérification de sécurité (packages vulnérables, permissions).

## TemplateService

Service de gestion des templates de projets.

### Gestion des templates

#### list_templates
```python
def list_templates(self) -> List[ProjectTemplate]:
```
Liste tous les templates disponibles (builtin + user).

#### get_template
```python
def get_template(self, name: str) -> Optional[ProjectTemplate]:
```
Récupération d'un template spécifique.

#### apply_template
```python
def apply_template(
    self, 
    template_name: str, 
    env: EnvironmentInfo,
    variables: Optional[Dict[str, str]] = None
) -> bool:
```
Application d'un template à un environnement.

### Templates personnalisés

#### create_template
```python
def create_template(
    self, 
    name: str, 
    source_env: EnvironmentInfo,
    description: Optional[str] = None
) -> ProjectTemplate:
```
Création d'un template depuis un environnement existant.

#### import_template
```python
def import_template(self, template_path: Path) -> ProjectTemplate:
```
Importation d'un template externe.

#### export_template
```python
def export_template(self, template_name: str, output_path: Path) -> bool:
```
Exportation d'un template pour partage.

### Validation

#### validate_template
```python
def validate_template(self, template: ProjectTemplate) -> List[str]:
```
Validation de la structure et contenu d'un template.

#### test_template
```python
def test_template(self, template_name: str) -> bool:
```
Test d'application d'un template dans un environnement temporaire.

## Usage Examples

### Installation avec cache
```python
from gestvenv.services import PackageService
from gestvenv.backends import BackendManager

backend_manager = BackendManager(config)
package_service = PackageService(backend_manager, cache_service)

result = package_service.install_package(env, "django[postgres]>=4.2")
print(f"Backend utilisé: {result.backend_used}")
```

### Diagnostic et réparation
```python
diagnostic_service = DiagnosticService(env_manager)
report = diagnostic_service.run_full_diagnostic("monprojet")

if report.issues:
    repair_result = diagnostic_service.auto_repair_environment(
        "monprojet", report.issues
    )
    print(f"Réparations effectuées: {repair_result.repairs_applied}")
```

### Migration automatique
```python
migration_service = MigrationService()
pyproject_info = migration_service.migrate_requirements_to_pyproject(
    Path("requirements.txt")
)
print(f"Dépendances migrées: {len(pyproject_info.dependencies)}")
```
