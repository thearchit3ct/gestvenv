# Gestion des Packages

## Introduction

La gestion efficace des packages Python est essentielle pour maintenir des environnements de développement cohérents et fonctionnels. GestVenv simplifie ce processus en offrant une interface unifiée pour l'installation, la mise à jour et la suppression des packages dans vos environnements virtuels.

## Installation de packages

### Installation dans l'environnement actif

Pour installer un ou plusieurs packages dans l'environnement actuellement actif :

```bash
gestvenv install "pandas,matplotlib"
```

Vous pouvez également spécifier des versions précises :

```bash
gestvenv install "pandas==1.4.2,matplotlib==3.5.1"
```

### Installation dans un environnement spécifique

Pour installer des packages dans un environnement spécifique sans l'activer au préalable :

```bash
gestvenv install "requests,beautifulsoup4" --env mon_projet
```

### Installation depuis différentes sources

GestVenv prend en charge l'installation de packages depuis diverses sources :

```bash
# Depuis PyPI (par défaut)
gestvenv install "numpy,scipy"

# Depuis un dépôt Git
gestvenv install "git+https://github.com/user/repo.git"

# Depuis un fichier local
gestvenv install "./chemin/vers/package_local"

# Depuis un fichier requirements.txt
gestvenv install --requirements chemin/vers/requirements.txt
```

## Mise à jour des packages

### Vérification des mises à jour disponibles

Pour vérifier quels packages peuvent être mis à jour :

```bash
gestvenv check
```

Exemple de sortie :

```
Packages pouvant être mis à jour dans l'environnement 'mon_projet' :
  - pandas (1.3.5 → 1.4.2)
  - matplotlib (3.4.3 → 3.5.1)
```

### Mise à jour des packages

Pour mettre à jour un ou plusieurs packages spécifiques :

```bash
gestvenv update "pandas,matplotlib"
```

Pour mettre à jour tous les packages dans l'environnement actif :

```bash
gestvenv update --all
```

Pour mettre à jour les packages dans un environnement spécifique :

```bash
gestvenv update --all --env mon_projet
```

## Suppression de packages

Pour supprimer un ou plusieurs packages :

```bash
gestvenv uninstall "pandas,matplotlib"
```

Pour supprimer des packages d'un environnement spécifique :

```bash
gestvenv uninstall "requests,beautifulsoup4" --env mon_projet
```

GestVenv vérifiera les dépendances avant la suppression et vous avertira si d'autres packages dépendent de ceux que vous souhaitez supprimer.

## Liste des packages installés

Pour afficher tous les packages installés dans l'environnement actif :

```bash
gestvenv list-packages
```

Pour afficher les packages dans un environnement spécifique :

```bash
gestvenv list-packages --env mon_projet
```

Exemple de sortie :

```
Packages installés dans l'environnement 'mon_projet' :
  - flask==2.0.1
  - pytest==6.2.5
  - gunicorn==20.1.0
  - werkzeug==2.0.2 (dépendance de flask)
  - jinja2==3.0.3 (dépendance de flask)
```

## Gestion des dépendances

### Vérification des conflits

Pour vérifier les conflits potentiels entre les packages installés :

```bash
gestvenv check-conflicts
```

### Analyse de dépendances

Pour afficher l'arbre de dépendances d'un package :

```bash
gestvenv deps flask
```

Exemple de sortie :

```
flask==2.0.1
├── Werkzeug>=2.0
│   └── ...
├── Jinja2>=3.0
│   ├── MarkupSafe>=2.0
│   └── ...
├── itsdangerous>=2.0
└── click>=7.1.2
```

## Recherche de packages

Pour rechercher des packages disponibles sur PyPI :

```bash
gestvenv search "machine learning"
```

## Bonnes pratiques

1. **Spécifiez les versions** des packages clés pour garantir la reproductibilité.
2. **Vérifiez régulièrement** les mises à jour de sécurité avec `gestvenv check`.
3. **Documentez les dépendances** en exportant régulièrement la configuration de l'environnement.
4. **Limitez le nombre de dépendances** directes pour réduire les risques de conflits.
5. **Testez les mises à jour** dans un environnement de développement avant de les appliquer en production.

## Dépannage

Si vous rencontrez des problèmes lors de l'installation ou de la mise à jour des packages :

- Utilisez l'option `--verbose` pour obtenir plus d'informations sur le processus.
- Vérifiez la connectivité réseau si vous ne pouvez pas accéder à PyPI.
- Essayez de mettre à jour pip avec `gestvenv run [env] pip install --upgrade pip`.
- Pour les packages qui ne s'installent pas correctement, vérifiez s'ils nécessitent des dépendances système supplémentaires.