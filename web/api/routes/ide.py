"""
Routes API pour l'intégration IDE
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import importlib.metadata
import ast

from ..services.environment_service import EnvironmentService
from ..models.environment import Environment
from ..core.dependencies import get_environment_service

router = APIRouter(prefix="/api/v1/ide", tags=["IDE Integration"])


class PackageDetails(BaseModel):
    """Détails d'un package avec métadonnées complètes"""
    name: str
    version: str
    location: str
    modules: List[str]
    entry_points: Dict[str, List[str]]
    metadata: Dict[str, Any]
    description: Optional[str] = None


class CompletionContext(BaseModel):
    """Contexte pour la complétion de code"""
    file_path: str
    line: int
    column: int
    context: str


class CompletionItem(BaseModel):
    """Item de complétion"""
    label: str
    kind: str
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insertText: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ImportAnalysis(BaseModel):
    """Analyse des imports d'un fichier"""
    imports: List[Dict[str, Any]]
    missing: List[str]
    suggestions: List[Dict[str, Any]]


class AttributeInfo(BaseModel):
    """Information sur un attribut"""
    name: str
    type: str
    signature: Optional[str] = None
    doc: Optional[str] = None
    parameters: Optional[List[Dict[str, Any]]] = None


@router.get("/environments/{env_id}/packages", response_model=List[PackageDetails])
async def get_packages_with_details(
    env_id: str,
    service: EnvironmentService = Depends(get_environment_service)
) -> List[PackageDetails]:
    """Récupère la liste détaillée des packages avec métadonnées"""
    env = service.get_environment_info(env_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    packages = []
    
    # Utiliser pip pour lister les packages
    result = service.run_command_in_environment(
        env_id,
        "pip list --format=json"
    )
    
    if result.success:
        package_list = json.loads(result.stdout)
        
        for pkg_info in package_list:
            try:
                # Récupérer les métadonnées détaillées
                metadata_result = service.run_command_in_environment(
                    env_id,
                    f"pip show {pkg_info['name']} --verbose"
                )
                
                if metadata_result.success:
                    details = _parse_pip_show(metadata_result.stdout)
                    
                    # Récupérer les modules
                    modules = _get_package_modules(env, pkg_info['name'])
                    
                    # Récupérer les entry points
                    entry_points = _get_entry_points(env, pkg_info['name'])
                    
                    # Statistiques PyPI (simulées pour l'instant)
                    download_stats = {
                        "last_month": _estimate_downloads(pkg_info['name']),
                        "last_week": _estimate_downloads(pkg_info['name']) // 4
                    }
                    
                    packages.append(PackageDetails(
                        name=pkg_info['name'],
                        version=pkg_info['version'],
                        location=details.get('location', ''),
                        modules=modules,
                        entry_points=entry_points,
                        metadata={
                            'home_page': details.get('home-page', ''),
                            'author': details.get('author', ''),
                            'license': details.get('license', ''),
                            'requires_dist': details.get('requires', []),
                            'download_stats': download_stats
                        },
                        description=details.get('summary', '')
                    ))
            except Exception as e:
                # En cas d'erreur, ajouter le package avec des infos minimales
                packages.append(PackageDetails(
                    name=pkg_info['name'],
                    version=pkg_info['version'],
                    location='',
                    modules=[pkg_info['name']],
                    entry_points={},
                    metadata={}
                ))
    
    return packages


@router.get("/environments/{env_id}/packages/{package_name}", response_model=PackageDetails)
async def get_package_details(
    env_id: str,
    package_name: str,
    service: EnvironmentService = Depends(get_environment_service)
) -> PackageDetails:
    """Récupère les détails complets d'un package spécifique"""
    env = service.get_environment_info(env_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    # Récupérer les infos du package
    result = service.run_command_in_environment(
        env_id,
        f"pip show {package_name} --verbose"
    )
    
    if not result.success:
        raise HTTPException(status_code=404, detail=f"Package {package_name} not found")
    
    details = _parse_pip_show(result.stdout)
    modules = _get_package_modules(env, package_name)
    entry_points = _get_entry_points(env, package_name)
    
    return PackageDetails(
        name=package_name,
        version=details.get('version', ''),
        location=details.get('location', ''),
        modules=modules,
        entry_points=entry_points,
        metadata={
            'home_page': details.get('home-page', ''),
            'author': details.get('author', ''),
            'license': details.get('license', ''),
            'requires_dist': details.get('requires', [])
        },
        description=details.get('summary', '')
    )


@router.get("/environments/{env_id}/python")
async def get_python_info(
    env_id: str,
    service: EnvironmentService = Depends(get_environment_service)
) -> Dict[str, Any]:
    """Récupère les informations sur l'interpréteur Python"""
    env = service.get_environment_info(env_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    # Récupérer les infos Python
    result = service.run_command_in_environment(
        env_id,
        "python -c \"import sys, json; print(json.dumps({'executable': sys.executable, 'version': sys.version, 'path': sys.path}))\""
    )
    
    if result.success:
        info = json.loads(result.stdout)
        
        # Ajouter le chemin site-packages
        site_packages = []
        for p in info['path']:
            if 'site-packages' in p:
                site_packages.append(p)
        
        return {
            "executable": info['executable'],
            "version": info['version'].split()[0],
            "site_packages": site_packages,
            "sys_path": info['path']
        }
    
    raise HTTPException(status_code=500, detail="Failed to get Python info")


@router.post("/environments/{env_id}/completion")
async def get_completion(
    env_id: str,
    context: CompletionContext,
    service: EnvironmentService = Depends(get_environment_service)
) -> Dict[str, List[CompletionItem]]:
    """Fournit des suggestions de complétion contextuelle"""
    env = service.get_environment_info(env_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    # Pour l'instant, retourner une complétion basique
    # Dans une vraie implémentation, on utiliserait Jedi ou Rope
    completions = []
    
    # Si on est dans un contexte d'import
    if "import" in context.context:
        packages = await get_packages_with_details(env_id, manager)
        for pkg in packages:
            completions.append(CompletionItem(
                label=pkg.name,
                kind="Module",
                detail=f"{pkg.name} {pkg.version}",
                documentation=pkg.description
            ))
    
    return {"completions": completions}


@router.post("/analysis/imports")
async def analyze_imports(
    file_content: str,
    file_path: str
) -> ImportAnalysis:
    """Analyse les imports d'un fichier Python"""
    imports = []
    missing = []
    suggestions = []
    
    try:
        # Parser le fichier Python
        tree = ast.parse(file_content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                imports.append({
                    "module": node.module or '',
                    "names": [alias.name for alias in node.names],
                    "line": node.lineno
                })
        
        # Vérifier les modules manquants (simplifié)
        # Dans une vraie implémentation, on vérifierait contre l'environnement actif
        stdlib_modules = {'os', 'sys', 'json', 'math', 'random', 'datetime', 're'}
        
        for imp in imports:
            module = imp['module']
            if module and module not in stdlib_modules:
                # Suggérer le package si on le connait
                if module in ['requests', 'flask', 'django', 'numpy', 'pandas']:
                    missing.append(module)
                    suggestions.append({
                        "name": module,
                        "version": "latest"
                    })
    
    except SyntaxError:
        # Fichier non parsable
        pass
    
    return ImportAnalysis(
        imports=imports,
        missing=missing,
        suggestions=suggestions
    )


@router.post("/analysis/attributes")
async def get_object_attributes(
    environment_id: str,
    object_path: str,
    context: str,
    service: EnvironmentService = Depends(get_environment_service)
) -> Dict[str, List[AttributeInfo]]:
    """Récupère les attributs disponibles pour un objet"""
    env = service.get_environment_info(environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    # Pour l'instant, retourner des attributs simulés
    # Dans une vraie implémentation, on utiliserait l'introspection Python
    attributes = []
    
    # Exemple pour requests
    if object_path == "requests":
        attributes = [
            AttributeInfo(
                name="get",
                type="function",
                signature="get(url, **kwargs)",
                doc="Sends a GET request.",
                parameters=[
                    {"name": "url", "type": "str"},
                    {"name": "kwargs", "type": "dict", "optional": True}
                ]
            ),
            AttributeInfo(
                name="post",
                type="function",
                signature="post(url, data=None, json=None, **kwargs)",
                doc="Sends a POST request."
            ),
            AttributeInfo(
                name="Session",
                type="class",
                doc="A Requests session."
            )
        ]
    
    return {"attributes": attributes}


@router.get("/diagnostics/check")
async def check_code(
    file_path: str,
    service: EnvironmentService = Depends(get_environment_service)
) -> Dict[str, Any]:
    """Vérifie le code et retourne des diagnostics"""
    # Pour l'instant, retourner des diagnostics basiques
    return {
        "diagnostics": [],
        "quick_fixes": []
    }


# Fonctions utilitaires

def _parse_pip_show(output: str) -> Dict[str, Any]:
    """Parse la sortie de pip show"""
    result = {}
    for line in output.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip().lower()] = value.strip()
    
    # Parser les requirements
    if 'requires' in result and result['requires']:
        result['requires'] = [r.strip() for r in result['requires'].split(',')]
    else:
        result['requires'] = []
    
    return result


def _get_package_modules(env: Environment, package_name: str) -> List[str]:
    """Récupère les modules d'un package"""
    # Méthode simplifiée - dans une vraie implémentation,
    # on inspecterait le package installé
    modules = [package_name]
    
    # Ajouter des sous-modules connus
    known_submodules = {
        'django': ['django.db', 'django.contrib', 'django.conf', 'django.urls'],
        'flask': ['flask.blueprints', 'flask.cli', 'flask.helpers'],
        'numpy': ['numpy.linalg', 'numpy.random', 'numpy.fft'],
        'pandas': ['pandas.io', 'pandas.plotting', 'pandas.testing']
    }
    
    if package_name in known_submodules:
        modules.extend(known_submodules[package_name])
    
    return modules


def _get_entry_points(env: Environment, package_name: str) -> Dict[str, List[str]]:
    """Récupère les entry points d'un package"""
    # Pour l'instant, retourner un dict vide
    # Dans une vraie implémentation, on lirait les métadonnées
    return {}


def _estimate_downloads(package_name: str) -> int:
    """Estime le nombre de téléchargements (simulé)"""
    # Simulation basée sur la popularité connue
    popular_packages = {
        'requests': 50000000,
        'numpy': 30000000,
        'pandas': 25000000,
        'flask': 10000000,
        'django': 8000000,
        'pytest': 5000000,
        'black': 3000000
    }
    
    return popular_packages.get(package_name, 10000)