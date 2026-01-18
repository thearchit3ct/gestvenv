# ADR 0003: Sélection des Backends

## Statut
Accepté

## Contexte
GestVenv doit supporter plusieurs gestionnaires de packages Python:
- pip (standard)
- uv (rapide, Rust-based)
- poetry (gestion de projets)
- pdm (PEP 582)

Chaque backend a ses avantages et cas d'usage.

## Décision
Implémenter un système de sélection de backend avec:

### Backends supportés
| Backend | Cas d'usage | Performance |
|---------|-------------|-------------|
| pip | Standard, compatibilité maximale | Baseline |
| uv | Performance, projets modernes | 10-100x plus rapide |
| poetry | Projets avec pyproject.toml | Modéré |
| pdm | PEP 582, isolation | Modéré |

### Algorithme de sélection automatique
```python
def select_backend(project_path: Path) -> Backend:
    # 1. Vérifier la configuration utilisateur
    if config.preferred_backend:
        return config.preferred_backend

    # 2. Détecter selon les fichiers projet
    if (project_path / "poetry.lock").exists():
        return Backend.POETRY
    if (project_path / "pdm.lock").exists():
        return Backend.PDM

    # 3. Préférer uv si disponible
    if is_uv_available():
        return Backend.UV

    # 4. Fallback sur pip
    return Backend.PIP
```

### Interface commune
```python
class BackendInterface(Protocol):
    def create_venv(self, path: Path) -> bool
    def install(self, packages: List[str]) -> InstallResult
    def uninstall(self, packages: List[str]) -> bool
    def list_packages(self) -> List[PackageInfo]
    def freeze(self) -> str
```

## Conséquences

### Positives
- Flexibilité pour les utilisateurs
- Performances optimales avec uv
- Compatibilité avec les workflows existants

### Négatives
- Maintenance de plusieurs backends
- Différences subtiles de comportement
- Tests multipliés par le nombre de backends

### Neutres
- Configuration optionnelle
- Migration transparente entre backends
- Fallback automatique si backend indisponible

## Notes d'implémentation
- Chaque backend dans `gestvenv/backends/`
- Tests paramétrés pour tous les backends
- Documentation des différences de comportement
