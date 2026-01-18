# Guide de Contribution - GestVenv

Merci de votre intérêt pour contribuer à GestVenv ! Ce document décrit les lignes directrices pour contribuer au projet.

## Table des Matières

- [Code de Conduite](#code-de-conduite)
- [Comment Contribuer](#comment-contribuer)
- [Configuration de l'Environnement de Développement](#configuration-de-lenvironnement-de-développement)
- [Standards de Code](#standards-de-code)
- [Processus de Pull Request](#processus-de-pull-request)
- [Rapport de Bugs](#rapport-de-bugs)
- [Demande de Fonctionnalités](#demande-de-fonctionnalités)

## Code de Conduite

Ce projet adhère à un code de conduite. En participant, vous vous engagez à respecter ce code. Les comportements inacceptables peuvent être signalés à contact@gestvenv.dev.

### Nos Standards

- Utiliser un langage accueillant et inclusif
- Respecter les différents points de vue et expériences
- Accepter gracieusement les critiques constructives
- Se concentrer sur ce qui est le mieux pour la communauté
- Faire preuve d'empathie envers les autres membres de la communauté

## Comment Contribuer

### Types de Contributions

1. **Corrections de bugs** - Identifier et corriger les problèmes
2. **Nouvelles fonctionnalités** - Ajouter de nouvelles capacités
3. **Documentation** - Améliorer ou ajouter de la documentation
4. **Tests** - Ajouter ou améliorer la couverture de tests
5. **Revue de code** - Examiner les pull requests des autres

### Premiers Pas

1. Forkez le dépôt
2. Créez une branche pour votre contribution
3. Effectuez vos modifications
4. Soumettez une pull request

## Configuration de l'Environnement de Développement

### Prérequis

- Python 3.9 ou supérieur
- Git
- pip ou uv (recommandé)

### Installation

```bash
# Cloner votre fork
git clone https://github.com/VOTRE_USERNAME/gestvenv.git
cd gestvenv

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate  # Windows

# Installer en mode développement
pip install -e ".[dev]"

# Installer les hooks pre-commit
pre-commit install
```

### Lancer les Tests

```bash
# Tests unitaires
pytest tests/unit/

# Tests d'intégration
pytest tests/integration/

# Tous les tests avec couverture
pytest --cov=gestvenv --cov-report=html

# Tests de performance
pytest tests/performance/
```

### Linting et Formatage

```bash
# Vérifier le formatage
black --check gestvenv/
isort --check-only gestvenv/

# Appliquer le formatage
black gestvenv/
isort gestvenv/

# Linting
flake8 gestvenv/
mypy gestvenv/

# Exécuter tous les checks pre-commit
pre-commit run --all-files
```

## Standards de Code

### Style Python

- Suivre [PEP 8](https://peps.python.org/pep-0008/)
- Utiliser [Black](https://black.readthedocs.io/) pour le formatage (ligne max: 88)
- Utiliser [isort](https://pycqa.github.io/isort/) pour trier les imports
- Documenter avec des docstrings (style Google)

### Exemple de Docstring

```python
def create_environment(name: str, python_version: str = None) -> Environment:
    """Crée un nouvel environnement virtuel.

    Args:
        name: Nom de l'environnement à créer.
        python_version: Version Python à utiliser (optionnel).

    Returns:
        L'objet Environment créé.

    Raises:
        EnvironmentExistsError: Si l'environnement existe déjà.
        PythonNotFoundError: Si la version Python n'est pas trouvée.

    Example:
        >>> env = create_environment("myapp", "3.11")
        >>> print(env.name)
        myapp
    """
```

### Conventions de Nommage

| Élément | Convention | Exemple |
|---------|------------|---------|
| Modules | snake_case | `environment_manager.py` |
| Classes | PascalCase | `EnvironmentManager` |
| Fonctions | snake_case | `create_environment()` |
| Constantes | SCREAMING_SNAKE_CASE | `DEFAULT_PYTHON_VERSION` |
| Variables | snake_case | `env_path` |

### Messages de Commit

Utilisez le format [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>(<scope>): <description>

[body optionnel]

[footer optionnel]
```

**Types:**
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation uniquement
- `style`: Formatage (pas de changement de code)
- `refactor`: Refactoring du code
- `test`: Ajout ou modification de tests
- `chore`: Maintenance (CI, dépendances, etc.)

**Exemples:**
```
feat(cli): add migrate command for v1.x to v2.0 migration
fix(cache): resolve path traversal vulnerability in tarfile extraction
docs(readme): update installation instructions
test(backends): add unit tests for uv backend
```

## Processus de Pull Request

### Avant de Soumettre

1. Assurez-vous que tous les tests passent
2. Ajoutez des tests pour les nouvelles fonctionnalités
3. Mettez à jour la documentation si nécessaire
4. Exécutez `pre-commit run --all-files`
5. Vérifiez que votre branche est à jour avec `develop`

### Soumettre une PR

1. Créez une branche depuis `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/ma-fonctionnalite
   ```

2. Faites vos modifications et committez:
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

3. Poussez et créez la PR:
   ```bash
   git push origin feature/ma-fonctionnalite
   ```

4. Remplissez le template de PR avec:
   - Description des changements
   - Lien vers l'issue (si applicable)
   - Type de changement
   - Checklist de vérification

### Revue de Code

- Un mainteneur examinera votre PR
- Des modifications peuvent être demandées
- Une fois approuvée, la PR sera mergée

## Rapport de Bugs

### Avant de Signaler

1. Vérifiez les [issues existantes](https://github.com/gestvenv/gestvenv/issues)
2. Assurez-vous d'utiliser la dernière version
3. Vérifiez que ce n'est pas une erreur de configuration

### Créer un Rapport

Utilisez le [template de bug report](.github/ISSUE_TEMPLATE/bug_report.md) et incluez:

- Version de GestVenv (`gestvenv --version`)
- Version de Python
- Système d'exploitation
- Étapes pour reproduire
- Comportement attendu vs observé
- Logs ou messages d'erreur

## Demande de Fonctionnalités

### Avant de Demander

1. Vérifiez que la fonctionnalité n'existe pas déjà
2. Vérifiez les issues existantes
3. Considérez si la fonctionnalité correspond à la vision du projet

### Créer une Demande

Utilisez le [template de feature request](.github/ISSUE_TEMPLATE/feature_request.md) et incluez:

- Description claire de la fonctionnalité
- Cas d'utilisation
- Comportement attendu
- Alternatives considérées

## Structure du Projet

```
gestvenv/
├── gestvenv/              # Code source principal
│   ├── backends/          # Implémentations des backends (pip, uv, etc.)
│   ├── core/              # Logique métier centrale
│   ├── services/          # Services (cache, migration, etc.)
│   ├── templates/         # Templates de projets
│   └── utils/             # Utilitaires
├── tests/                 # Tests
│   ├── unit/              # Tests unitaires
│   ├── integration/       # Tests d'intégration
│   └── performance/       # Tests de performance
├── docs/                  # Documentation
├── extensions/            # Extensions (VS Code)
└── web/                   # Interface web
```

## Questions ?

- Ouvrez une [discussion](https://github.com/gestvenv/gestvenv/discussions)
- Consultez la [documentation](https://gestvenv.readthedocs.io)
- Contactez-nous: contact@gestvenv.dev

---

Merci de contribuer à GestVenv !
