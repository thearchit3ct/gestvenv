# Tests de Performance GestVenv v2.0

Ce dossier contient les tests de performance pour GestVenv v2.0.

## Structure des Tests

- `test_backend_performance.py` : Tests de performance des backends (pip, uv, etc.)
- `test_cache_performance.py` : Tests de performance du système de cache
- `test_ephemeral_performance.py` : Tests de performance des environnements éphémères
- `test_parsing_performance.py` : Tests de performance du parsing de fichiers

## Exécution des Tests

### Tous les tests de performance

```bash
pytest tests/performance/ -v -m benchmark
```

### Tests spécifiques

```bash
# Backend uniquement
pytest tests/performance/test_backend_performance.py -v

# Cache uniquement
pytest tests/performance/test_cache_performance.py -v

# Avec rapport de temps
pytest tests/performance/ -v --durations=10
```

### Génération de rapport

```bash
# Avec pytest-benchmark (si installé)
pytest tests/performance/ --benchmark-only --benchmark-json=benchmark.json

# Avec coverage
pytest tests/performance/ --cov=gestvenv --cov-report=html
```

## Seuils de Performance

Les tests vérifient que les opérations respectent ces seuils :

- **Création d'environnement** : < 30s (pip), < 5s (uv)
- **Installation de packages** : < 60s pour packages larges
- **Opérations cache** : < 0.1s pour lookup
- **Parsing** : < 0.1s pour fichiers standards

## Notes

- Les tests marqués `@pytest.mark.benchmark` sont des tests de performance
- Certains tests nécessitent `uv` installé pour les comparaisons
- Les tests d'environnements éphémères peuvent être skippés si le module n'est pas disponible
- Les temps peuvent varier selon la machine et la connexion réseau

## Développement

Pour ajouter un nouveau test de performance :

1. Créer le test dans le fichier approprié
2. Utiliser le décorateur `@pytest.mark.benchmark`
3. Mesurer le temps avec `time.perf_counter()`
4. Vérifier contre un seuil raisonnable

Exemple :

```python
@pytest.mark.benchmark
def test_my_performance(self):
    start = time.perf_counter()
    # Code à tester
    duration = time.perf_counter() - start
    assert duration < 1.0, f"Trop lent: {duration}s"
```