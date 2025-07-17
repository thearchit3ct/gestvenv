# Guide de Migration vers les Environnements Éphémères

## Pourquoi migrer ?

Les environnements éphémères offrent plusieurs avantages par rapport aux environnements virtuels traditionnels :

- ✅ **Nettoyage automatique** : Plus de répertoires orphelins
- ⚡ **Performance** : Création en < 1 seconde avec uv
- 🔒 **Isolation** : Sécurité renforcée avec plusieurs niveaux
- 📊 **Monitoring** : Suivi des ressources en temps réel
- 💾 **Optimisation** : Stockage en RAM pour les tests courts

## Cas d'usage recommandés

### ✅ Parfait pour :
- Tests automatisés et CI/CD
- Scripts d'automatisation
- Expérimentation de packages
- Environnements de développement temporaires
- Exécution isolée de code non fiable

### ❌ Non recommandé pour :
- Environnements de production permanents
- Développement long terme (> 24h)
- Projets nécessitant des données persistantes

## Migration depuis virtualenv/venv

### Avant (virtualenv traditionnel)

```bash
# Création manuelle
python -m venv myenv
source myenv/bin/activate
pip install requests pandas

# Utilisation
python script.py

# Nettoyage manuel (souvent oublié)
deactivate
rm -rf myenv
```

### Après (environnement éphémère)

```python
import asyncio
import gestvenv

async def main():
    async with gestvenv.ephemeral("myenv") as env:
        await env.install(["requests", "pandas"])
        result = await env.execute("python script.py")
        print(result.stdout)
    # Nettoyage automatique

asyncio.run(main())
```

## Migration depuis subprocess

### Avant

```python
import subprocess
import tempfile
import shutil
import os

# Création complexe
temp_dir = tempfile.mkdtemp()
venv_path = os.path.join(temp_dir, "venv")

try:
    # Créer venv
    subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
    
    # Installer packages
    pip_path = os.path.join(venv_path, "bin", "pip")
    subprocess.run([pip_path, "install", "requests"], check=True)
    
    # Exécuter script
    python_path = os.path.join(venv_path, "bin", "python")
    result = subprocess.run([python_path, "script.py"], capture_output=True)
    print(result.stdout.decode())
    
finally:
    # Nettoyage manuel
    shutil.rmtree(temp_dir)
```

### Après

```python
import gestvenv

async with gestvenv.ephemeral() as env:
    await env.install(["requests"])
    result = await env.execute("python script.py")
    print(result.stdout)
```

## Migration des tests pytest

### Avant

```python
# conftest.py
import pytest
import venv
import tempfile
import shutil

@pytest.fixture(scope="function")
def test_venv():
    # Création manuelle
    temp_dir = tempfile.mkdtemp()
    venv_path = os.path.join(temp_dir, "venv")
    
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(venv_path)
    
    yield venv_path
    
    # Nettoyage
    shutil.rmtree(temp_dir)

# test_mycode.py
def test_package_install(test_venv):
    pip = os.path.join(test_venv, "bin", "pip")
    subprocess.run([pip, "install", "mypackage"])
    # Tests...
```

### Après

```python
# conftest.py
import pytest
import gestvenv

@pytest.fixture
async def test_env():
    """Environnement de test isolé avec nettoyage automatique"""
    async with gestvenv.ephemeral("pytest") as env:
        yield env

# test_mycode.py
async def test_package_install(test_env):
    await test_env.install(["mypackage"])
    result = await test_env.execute("python -c 'import mypackage; print(mypackage.__version__)'")
    assert result.success
```

## Migration des scripts CI/CD

### GitHub Actions - Avant

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Create virtualenv
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          source venv/bin/activate
          pytest tests/
      
      - name: Cleanup
        if: always()
        run: rm -rf venv
```

### GitHub Actions - Après

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install GestVenv
        run: pip install gestvenv[performance]
      
      - name: Run tests in ephemeral env
        run: |
          gestvenv ephemeral create ci-test \
            --requirements requirements.txt \
            --ttl 600
          
          gestvenv run --env ci-test pytest tests/
          
          # Nettoyage automatique après TTL
```

## Migration depuis Docker pour les tests

### Avant (Dockerfile pour tests)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["pytest"]
```

```bash
# Exécution
docker build -t test-env .
docker run --rm test-env
```

### Après

```python
import gestvenv
from gestvenv.core.ephemeral import IsolationLevel

async with gestvenv.ephemeral(
    "test",
    isolation_level=IsolationLevel.CONTAINER,
    python_version="3.11"
) as env:
    await env.install(["-r", "requirements.txt"])
    result = await env.execute("pytest")
    print(result.stdout)
```

## Patterns de migration

### 1. Pattern Context Manager

Remplacez toute création/suppression manuelle par un context manager :

```python
# ❌ Ancien pattern
env_path = create_virtualenv()
try:
    run_in_env(env_path, command)
finally:
    cleanup_env(env_path)

# ✅ Nouveau pattern
async with gestvenv.ephemeral() as env:
    await env.execute(command)
```

### 2. Pattern Fixture de Test

Pour les tests, utilisez des fixtures async :

```python
# Fixture réutilisable
@pytest.fixture
async def isolated_env():
    async with gestvenv.ephemeral(
        isolation_level=IsolationLevel.NAMESPACE
    ) as env:
        yield env

# Tests
async def test_feature(isolated_env):
    await isolated_env.install(["mylib"])
    # Tests...
```

### 3. Pattern Pool pour Performance

Pour de nombreuses créations, utilisez un pool :

```python
# Créer plusieurs environnements en parallèle
async def run_parallel_tests(test_files):
    tasks = []
    
    for test_file in test_files:
        task = run_in_ephemeral(test_file)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results

async def run_in_ephemeral(test_file):
    async with gestvenv.ephemeral() as env:
        await env.install(["pytest"])
        return await env.execute(f"pytest {test_file}")
```

### 4. Pattern Monitoring

Ajoutez du monitoring pour les usages intensifs :

```python
import asyncio
from gestvenv import ephemeral, get_resource_usage

async def monitored_execution():
    # Vérifier les ressources avant
    usage_before = await get_resource_usage()
    
    if usage_before['active_environments'] > 40:
        print("⚠️ Attente de libération de ressources...")
        await asyncio.sleep(10)
    
    async with ephemeral("monitored") as env:
        # Exécution
        await env.install(["heavy-package"])
        
        # Vérifier pendant
        usage_during = await get_resource_usage()
        print(f"Mémoire utilisée: {usage_during['total_memory_mb']}MB")
```

## Configuration recommandée

### Développement local

```toml
# ~/.config/gestvenv/config.toml
[ephemeral]
default_ttl = 3600              # 1 heure
storage_backend = "tmpfs"       # Rapide
max_concurrent = 20             # Limite raisonnable
default_isolation_level = "process"
```

### CI/CD

```toml
[ephemeral]
default_ttl = 600               # 10 minutes
storage_backend = "memory"      # Ultra-rapide
max_concurrent = 10             # Limite stricte
default_isolation_level = "namespace"  # Isolation renforcée
force_cleanup_after = 1200      # 20 minutes max
```

### Tests de sécurité

```toml
[ephemeral]
default_ttl = 300               # 5 minutes
storage_backend = "memory"
max_concurrent = 5
default_isolation_level = "container"  # Isolation maximale
default_security_mode = "sandboxed"
```

## Checklist de migration

- [ ] Identifier les cas d'usage éphémères vs permanents
- [ ] Remplacer les créations manuelles par des context managers
- [ ] Migrer les tests vers des fixtures async
- [ ] Configurer les limites de ressources appropriées
- [ ] Ajouter du monitoring si nécessaire
- [ ] Tester les performances (devrait être plus rapide)
- [ ] Vérifier que le nettoyage automatique fonctionne
- [ ] Adapter la CI/CD pour utiliser les environnements éphémères
- [ ] Former l'équipe sur la nouvelle API

## Problèmes courants et solutions

### "Trop d'environnements actifs"

```python
# Problème
ResourceExhaustedException: Maximum concurrent environments reached

# Solution 1: Attendre
await asyncio.sleep(30)

# Solution 2: Forcer le nettoyage
from gestvenv.core.ephemeral import list_active_environments, cleanup_environment

envs = await list_active_environments()
old_envs = [e for e in envs if e.age_seconds > 3600]
for env in old_envs:
    await cleanup_environment(env.id, force=True)

# Solution 3: Augmenter la limite
config.max_concurrent = 100
```

### "Isolation non disponible"

```python
# Le système fallback automatiquement
async with ephemeral(isolation_level=IsolationLevel.CONTAINER) as env:
    # Si Docker n'est pas disponible, fallback vers PROCESS
    print(f"Isolation utilisée: {env.isolation_level}")
```

### "Performance de création"

```python
# Utiliser uv pour la meilleure performance
async with ephemeral(backend=Backend.UV) as env:
    # Création en < 1 seconde
    pass

# Pré-allocation pour usage intensif
config = EphemeralConfig(
    enable_preallocation=True,
    pool_size=10
)
```

## Support et aide

- Documentation complète : [ephemeral-environments.md](./ephemeral-environments.md)
- API référence : [api/ephemeral.md](./api/ephemeral.md)
- Issues GitHub : https://github.com/gestvenv/gestvenv/issues
- Tag : `ephemeral-environments`