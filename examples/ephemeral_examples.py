#!/usr/bin/env python3
"""
Exemples d'utilisation des environnements éphémères GestVenv
"""

import asyncio
import sys
from pathlib import Path
from typing import List

# Ajouter le répertoire parent au path pour l'import
sys.path.insert(0, str(Path(__file__).parent.parent))

import gestvenv
from gestvenv.core.ephemeral import (
    IsolationLevel,
    ResourceLimits,
    StorageBackend,
    list_active_environments,
    get_resource_usage
)
from gestvenv.core.models import Backend


async def example_basic():
    """Exemple basique d'utilisation"""
    print("=== Exemple Basique ===")
    
    async with gestvenv.ephemeral("demo-basic") as env:
        print(f"✅ Environnement créé: {env.name}")
        print(f"📁 Stockage: {env.storage_path}")
        
        # Installation de packages
        print("📦 Installation de requests...")
        result = await env.install(["requests"])
        if result.success:
            print("✅ Installation réussie")
        
        # Exécution de code
        result = await env.execute("python -c 'import requests; print(requests.__version__)'")
        print(f"📌 Version requests: {result.stdout.strip()}")
    
    print("🧹 Environnement nettoyé automatiquement\n")


async def example_multiple_packages():
    """Installation de plusieurs packages et dépendances"""
    print("=== Exemple Multi-Packages ===")
    
    packages = ["pandas", "numpy", "matplotlib", "seaborn"]
    
    async with gestvenv.ephemeral("data-science") as env:
        print(f"📦 Installation de {len(packages)} packages...")
        result = await env.install(packages)
        
        if result.success:
            # Vérifier les imports
            check_script = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

print(f"Pandas: {pd.__version__}")
print(f"NumPy: {np.__version__}")
print(f"Matplotlib: {plt.matplotlib.__version__}")
print(f"Seaborn: {sns.__version__}")
"""
            result = await env.execute(f"python -c '{check_script}'")
            print("✅ Versions installées:")
            print(result.stdout)
        else:
            print(f"❌ Erreur: {result.stderr}")


async def example_isolation_levels():
    """Démonstration des différents niveaux d'isolation"""
    print("=== Niveaux d'Isolation ===")
    
    isolation_levels = [
        IsolationLevel.PROCESS,
        IsolationLevel.NAMESPACE,
        IsolationLevel.CONTAINER,
    ]
    
    for level in isolation_levels:
        try:
            print(f"\n🔒 Test isolation {level.value}...")
            
            async with gestvenv.ephemeral(
                f"isolated-{level.value}",
                isolation_level=level,
                resource_limits=ResourceLimits(network_access=False)
            ) as env:
                print(f"✅ Environnement créé avec isolation {level.value}")
                
                # Test d'isolation réseau
                result = await env.execute("python -c 'import urllib.request; urllib.request.urlopen(\"http://google.com\")'")
                if not result.success:
                    print("✅ Isolation réseau fonctionnelle (accès bloqué)")
                else:
                    print("⚠️ Accès réseau non bloqué")
                    
        except Exception as e:
            print(f"⚠️ Isolation {level.value} non disponible: {e}")


async def example_resource_limits():
    """Gestion des limites de ressources"""
    print("=== Limites de Ressources ===")
    
    # Configuration stricte
    limits = ResourceLimits(
        max_memory=512,      # 512MB
        max_disk=1024,       # 1GB
        max_processes=5,
        max_cpu_percent=25.0
    )
    
    async with gestvenv.ephemeral(
        "limited-env",
        resource_limits=limits
    ) as env:
        print(f"📊 Limites configurées:")
        print(f"   Mémoire: {limits.max_memory}MB")
        print(f"   Disque: {limits.max_disk}MB")
        print(f"   Processus: {limits.max_processes}")
        print(f"   CPU: {limits.max_cpu_percent}%")
        
        # Test de consommation mémoire
        memory_test = """
import numpy as np
# Créer un tableau de ~100MB
arr = np.zeros((13_000, 1000), dtype=np.float64)
print(f"Taille array: {arr.nbytes / 1024 / 1024:.1f}MB")
"""
        result = await env.execute(f"python -c '{memory_test}'")
        if result.success:
            print(f"✅ Test mémoire: {result.stdout.strip()}")


async def example_parallel_environments():
    """Création et utilisation d'environnements en parallèle"""
    print("=== Environnements Parallèles ===")
    
    async def test_package(package: str) -> str:
        """Teste un package dans un environnement isolé"""
        async with gestvenv.ephemeral(f"test-{package}") as env:
            await env.install([package])
            result = await env.execute(
                f"python -c 'import {package}; print(\"{package}: \" + {package}.__version__)'"
            )
            return result.stdout.strip() if result.success else f"{package}: erreur"
    
    # Tester plusieurs packages en parallèle
    packages = ["flask", "django", "fastapi", "pyramid"]
    
    print(f"🚀 Test de {len(packages)} frameworks en parallèle...")
    
    # Lancer tous les tests en parallèle
    results = await asyncio.gather(*[test_package(pkg) for pkg in packages])
    
    print("✅ Résultats:")
    for result in results:
        print(f"   {result}")


async def example_storage_backends():
    """Comparaison des différents backends de stockage"""
    print("=== Backends de Stockage ===")
    
    import time
    
    backends = [
        (StorageBackend.DISK, "Disque standard"),
        (StorageBackend.TMPFS, "tmpfs (RAM)"),
        (StorageBackend.MEMORY, "Mémoire pure")
    ]
    
    for backend, description in backends:
        print(f"\n💾 Test avec {description}...")
        
        start_time = time.time()
        
        try:
            async with gestvenv.ephemeral(
                f"storage-{backend.value}",
                storage_backend=backend
            ) as env:
                creation_time = time.time() - start_time
                print(f"✅ Création en {creation_time:.3f}s")
                
                # Test d'écriture
                write_test = """
import time
start = time.time()
with open('test.txt', 'w') as f:
    for i in range(10000):
        f.write(f'Line {i}\\n')
print(f"Écriture: {time.time() - start:.3f}s")
"""
                result = await env.execute(f"python -c '{write_test}'")
                if result.success:
                    print(f"   {result.stdout.strip()}")
                    
        except Exception as e:
            print(f"❌ Erreur: {e}")


async def example_long_running_with_monitoring():
    """Exemple avec monitoring des ressources"""
    print("=== Monitoring Long Running ===")
    
    async def monitor_task(env_id: str):
        """Monitore un environnement en arrière-plan"""
        for i in range(5):
            await asyncio.sleep(2)
            
            # Récupérer les stats globales
            usage = await get_resource_usage()
            print(f"📊 [{i+1}/5] Environnements actifs: {usage['active_environments']}, "
                  f"Mémoire: {usage['total_memory_mb']:.1f}MB")
    
    async with gestvenv.ephemeral("monitored", ttl=30) as env:
        # Lancer le monitoring en arrière-plan
        monitor = asyncio.create_task(monitor_task(env.id))
        
        # Simulation de travail
        print("🔄 Simulation de travail...")
        await env.install(["requests", "beautifulsoup4"])
        
        for i in range(3):
            result = await env.execute(f"python -c 'import time; time.sleep(1); print(\"Étape {i+1}\")'")
            print(f"   {result.stdout.strip()}")
        
        monitor.cancel()
        try:
            await monitor
        except asyncio.CancelledError:
            pass


async def example_error_handling():
    """Gestion des erreurs et cas limites"""
    print("=== Gestion d'Erreurs ===")
    
    # 1. Package inexistant
    print("\n1️⃣ Test package inexistant...")
    async with gestvenv.ephemeral("error-test-1") as env:
        result = await env.install(["package-qui-nexiste-pas"])
        if not result.success:
            print(f"✅ Erreur attendue: {result.stderr.split('ERROR:')[1].strip()[:50]}...")
    
    # 2. Commande en erreur
    print("\n2️⃣ Test commande en erreur...")
    async with gestvenv.ephemeral("error-test-2") as env:
        result = await env.execute("python -c 'raise RuntimeError(\"Test error\")'")
        if not result.success:
            print(f"✅ Code retour: {result.returncode}")
            print(f"✅ Erreur capturée: {result.stderr.strip()}")
    
    # 3. Timeout
    print("\n3️⃣ Test timeout...")
    async with gestvenv.ephemeral("error-test-3") as env:
        result = await env.execute("python -c 'import time; time.sleep(10)'", timeout=2)
        if not result.success:
            print("✅ Timeout détecté")


async def example_ci_cd_pattern():
    """Pattern pour CI/CD"""
    print("=== Pattern CI/CD ===")
    
    # Simulation d'un pipeline CI/CD
    stages = [
        ("lint", ["flake8", "black", "isort"], "flake8 --version"),
        ("test", ["pytest", "pytest-cov"], "pytest --version"),
        ("build", ["build", "twine"], "python -m build --version")
    ]
    
    for stage_name, packages, check_cmd in stages:
        print(f"\n🔄 Stage: {stage_name}")
        
        async with gestvenv.ephemeral(
            f"ci-{stage_name}",
            backend=Backend.UV,  # Le plus rapide
            ttl=300  # 5 minutes max par stage
        ) as env:
            # Installation des outils
            print(f"   📦 Installation: {', '.join(packages)}")
            result = await env.install(packages)
            
            if result.success:
                # Vérification
                result = await env.execute(check_cmd)
                print(f"   ✅ {result.stdout.strip()}")
            else:
                print(f"   ❌ Échec installation")
                break


async def main():
    """Exécute tous les exemples"""
    examples = [
        example_basic,
        example_multiple_packages,
        example_isolation_levels,
        example_resource_limits,
        example_parallel_environments,
        example_storage_backends,
        example_long_running_with_monitoring,
        example_error_handling,
        example_ci_cd_pattern
    ]
    
    print("🚀 Exemples d'Environnements Éphémères GestVenv\n")
    
    # Afficher l'usage initial
    usage = await get_resource_usage()
    print(f"📊 État initial: {usage['active_environments']} environnements actifs\n")
    
    for example in examples:
        try:
            await example()
            print("\n" + "="*50 + "\n")
            
            # Pause entre les exemples
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Erreur dans {example.__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        # Vérifier qu'on nettoie bien
        envs = await list_active_environments()
        if envs:
            print(f"⚠️ {len(envs)} environnements encore actifs après {example.__name__}")
    
    # Vérifier l'état final
    final_usage = await get_resource_usage()
    print(f"\n📊 État final: {final_usage['active_environments']} environnements actifs")
    
    if final_usage['active_environments'] == 0:
        print("✅ Tous les environnements ont été nettoyés correctement!")
    else:
        print("⚠️ Certains environnements sont encore actifs")


if __name__ == "__main__":
    # Configuration du logging pour voir les détails
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Exécuter les exemples
    asyncio.run(main())