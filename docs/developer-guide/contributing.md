# Guide de contribution

Merci de votre intérêt pour contribuer à GestVenv ! Ce document explique comment vous pouvez participer au développement du projet.

## Prérequis

Avant de commencer, assurez-vous d'avoir installé :

- Python 3.7 ou supérieur
- Git
- pip
- Un éditeur de code (VS Code, PyCharm, etc.)

## Configurer l'environnement de développement

1. **Forker le dépôt** sur GitHub

2. **Cloner votre fork** :
   ```bash
   git clone https://github.com/votre-username/gestvenv.git
   cd gestvenv
   ```

3. **Configurer le dépôt upstream** :
   ```bash
   git remote add upstream https://github.com/original-owner/gestvenv.git
   ```

4. **Créer un environnement virtuel** :
   ```bash
   python -m venv venv
   # Sur Windows
   venv\Scripts\activate
   # Sur Unix/macOS
   source venv/bin/activate
   ```

5. **Installer les dépendances de développement** :
   ```bash
   pip install -e ".[dev]"
   ```

6. **Vérifier l'installation** :
   ```bash
   python -m pytest
   ```

## Workflow de développement

### 1. Choisir une tâche

- Consultez les [issues ouvertes](https://github.com/original-owner/gestvenv/issues) sur GitHub
- Vérifiez les [projets](https://github.com/original-owner/gestvenv/projects) pour voir les fonctionnalités planifiées
- Créez une nouvelle issue si vous avez identifié un bug ou une amélioration

### 2. Créer une branche

Créez une branche dédiée à votre contribution :

```bash
git checkout -b type/description-courte
```

Où `type` peut être :
- `feature` : pour les nouvelles fonctionnalités
- `bugfix` : pour les corrections de bugs
- `docs` : pour les améliorations de documentation
- `test` : pour les ajouts ou améliorations de tests
- `refactor` : pour les refactorisations de code

Exemple : `feature/export-json-format` ou `bugfix/activation-windows`

### 3. Développer

Pendant le développement, suivez ces bonnes pratiques :

- **Respectez les conventions de code** décrites dans le document [code-structure.md](./code-structure.md)
- **Écrivez des tests** pour toutes les nouvelles fonctionnalités
- **Documentez** votre code avec des docstrings
- **Vérifiez régulièrement** votre code avec les outils d'analyse statique

```bash
# Lancer les tests
pytest

# Vérifier le style de code
flake8 gestvenv

# Vérifier le typage
mypy gestvenv
```

### 4. Committer les changements

Écrivez des messages de commit clairs et descriptifs :

```bash
git commit -m "Type: description courte

Description plus détaillée des changements et de leur motivation.
Fait référence à l'issue #42."
```

Où `Type` peut être :
- `Feat` : nouvelle fonctionnalité
- `Fix` : correction de bug
- `Docs` : documentation
- `Test` : ajout ou modification de tests
- `Refactor` : refactorisation
- `Chore` : maintenance générale

### 5. Soumettre une Pull Request

1. Assurez-vous que votre branche est à jour avec la branche principale :
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Poussez vos changements sur votre fork :
   ```bash
   git push origin votre-branche
   ```

3. Créez une Pull Request sur GitHub
   - Utilisez un titre clair
   - Décrivez les changements apportés
   - Faites référence aux issues concernées
   - Remplissez le template de PR

4. Attendez la revue de code et répondez aux commentaires

## Standards de qualité

### Tests

Toutes les nouvelles fonctionnalités doivent être accompagnées de tests :

- **Tests unitaires** pour les fonctions et classes individuelles
- **Tests d'intégration** pour les interactions entre composants
- **Tests système** pour les flux de travail complets

Reportez-vous à [testing.md](./testing.md) pour plus de détails.

### Documentation

Documentez toujours votre code :

- **Docstrings** pour tous les modules, classes, méthodes et fonctions
- **Commentaires** pour les sections complexes
- **Mise à jour de la documentation utilisateur** si nécessaire

Exemple de docstring (format Google) :

```python
def create_environment(name, python_version=None, packages=None):
    """Crée un nouvel environnement virtuel.
    
    Args:
        name (str): Nom de l'environnement à créer.
        python_version (str, optional): Version Python à utiliser.
            Exemple: "3.9" ou "python3.8". Par défaut None (utilise la version système).
        packages (list, optional): Liste de packages à installer initialement.
            Exemple: ["flask", "pytest"]. Par défaut None.
            
    Returns:
        bool: True si l'environnement a été créé avec succès, False sinon.
        
    Raises:
        EnvExistsError: Si l'environnement existe déjà.
        InvalidNameError: Si le nom d'environnement est invalide.
    """
    # Implémentation...
```

### Style de code

Nous suivons les conventions PEP 8 pour le style de code. Utilisez les outils suivants pour vérifier votre code :

- **flake8** pour le style général
- **black** pour le formatage automatique
- **isort** pour trier les imports

Un fichier de configuration pour chaque outil est fourni dans le dépôt.

## Processus de revue

Chaque Pull Request est soumise à un processus de revue :

1. **Vérification automatique** : les tests et analyses de code sont exécutés automatiquement
2. **Revue de code** : un ou plusieurs mainteneurs examinent le code
3. **Demandes de modifications** : des modifications peuvent être demandées
4. **Approbation** : une fois approuvée, la PR peut être fusionnée

Soyez patient pendant ce processus et n'hésitez pas à demander des clarifications.

## Publier une nouvelle version

Si vous êtes un mainteneur, voici comment publier une nouvelle version :

1. **Mettre à jour la version** dans `gestvenv/__init__.py`
2. **Mettre à jour le CHANGELOG.md**
3. **Créer un tag** avec la nouvelle version
   ```bash
   git tag -a v1.0.1 -m "Version 1.0.1"
   git push origin v1.0.1
   ```
4. **Construire et publier** le package sur PyPI
   ```bash
   python -m build
   python -m twine upload dist/*
   ```

## Communication

Pour communiquer avec l'équipe de développement :

- **Issues GitHub** pour les bugs et fonctionnalités
- **Discussions GitHub** pour les questions générales
- **Discord/Slack** pour les discussions en temps réel (lien disponible dans le README)

## Reconnaissance des contributions

Toutes les contributions sont reconnues et appréciées :

- Les contributeurs sont listés dans le fichier CONTRIBUTORS.md
- Les contributions importantes sont mentionnées dans les notes de version

## Code de conduite

Nous adhérons au [Contributor Covenant](https://www.contributor-covenant.org/). En bref :

- Soyez respectueux et inclusif
- Acceptez les critiques constructives
- Concentrez-vous sur ce qui est le mieux pour la communauté
- Faites preuve d'empathie envers les autres membres

## Questions fréquentes

### Comment débuter si je suis nouveau ?

Commencez par les issues marquées "good first issue" qui sont généralement plus simples à aborder.

### Comment suggérer une nouvelle fonctionnalité ?

Créez une nouvelle issue en utilisant le template "Feature Request" et décrivez en détail la fonctionnalité souhaitée.

### Comment signaler un bug ?

Créez une nouvelle issue en utilisant le template "Bug Report", en incluant les étapes pour reproduire le bug, le comportement attendu et le comportement observé.

### Comment obtenir de l'aide ?

Si vous rencontrez des difficultés pendant le développement, n'hésitez pas à :
- Poser une question dans les discussions GitHub
- Demander de l'aide dans le canal Discord/Slack
- Commenter sur l'issue sur laquelle vous travaillez

## Ressources supplémentaires

- [Documentation Python](https://docs.python.org/)
- [Guide Git](https://git-scm.com/book/en/v2)
- [Documentation venv](https://docs.python.org/fr/3/library/venv.html)
- [Documentation pip](https://pip.pypa.io/en/stable/)
- [Guide de distribution Python](https://packaging.python.org/guides/distributing-packages-using-setuptools/)

---

Merci encore pour votre intérêt à contribuer à GestVenv. Votre aide est précieuse pour améliorer cet outil et le rendre plus utile pour la communauté Python !
