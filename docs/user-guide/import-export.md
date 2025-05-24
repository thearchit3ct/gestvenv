# Import et Export d'Environnements

## Introduction

L'import et l'export d'environnements virtuels sont des fonctionnalités essentielles de GestVenv qui facilitent la collaboration entre développeurs et la reproductibilité des environnements de développement. Cette section vous guidera à travers le processus de partage et de réplication d'environnements virtuels.

## Export d'environnements

### Export au format JSON

Le format JSON est le format natif de GestVenv pour l'export d'environnements. Il préserve toutes les métadonnées et configurations :

```bash
gestvenv export mon_projet
```

Par défaut, cette commande crée un fichier `mon_projet.json` dans le répertoire courant. Vous pouvez spécifier un chemin de sortie :

```bash
gestvenv export mon_projet --output /chemin/vers/mon_projet_config.json
```

### Export au format requirements.txt

Pour la compatibilité avec d'autres outils, vous pouvez exporter au format `requirements.txt` :

```bash
gestvenv export mon_projet --format requirements
```

Cette commande crée un fichier `requirements.txt` standard contenant la liste des packages et leurs versions.

### Export avec métadonnées supplémentaires

Vous pouvez enrichir l'export avec des métadonnées supplémentaires :

```bash
gestvenv export mon_projet --add-metadata "description:Environnement pour application web Flask,auteur:Jean Dupont"
```

### Exemple de fichier d'export JSON

```json
{
  "name": "mon_projet",
  "python_version": "3.9.6",
  "packages": [
    "flask==2.0.1",
    "pytest==6.2.5",
    "gunicorn==20.1.0"
  ],
  "metadata": {
    "created_by": "username",
    "exported_at": "2025-05-18T15:45:00",
    "description": "Environnement pour application web Flask",
    "auteur": "Jean Dupont"
  }
}
```

## Import d'environnements

### Import depuis un fichier JSON

Pour créer un nouvel environnement à partir d'un fichier d'export JSON :

```bash
gestvenv import mon_projet_config.json
```

Par défaut, l'environnement importé aura le même nom que celui défini dans le fichier. Vous pouvez spécifier un nom différent :

```bash
gestvenv import mon_projet_config.json --name nouveau_projet
```

### Import depuis un fichier requirements.txt

Pour créer un environnement à partir d'un fichier `requirements.txt` :

```bash
gestvenv import requirements.txt --name nouveau_projet
```

Comme le fichier `requirements.txt` ne contient pas d'informations sur la version Python, vous devrez peut-être la spécifier :

```bash
gestvenv import requirements.txt --name nouveau_projet --python python3.9
```

### Import avec modifications

Vous pouvez modifier certains paramètres lors de l'import :

```bash
# Importer en excluant certains packages
gestvenv import mon_projet_config.json --exclude "pytest,gunicorn"

# Importer en ajoutant des packages supplémentaires
gestvenv import mon_projet_config.json --add "django,celery"

# Importer en spécifiant un chemin personnalisé
gestvenv import mon_projet_config.json --path "/chemin/personnalise"
```

## Partage d'environnements entre développeurs

Le workflow typique pour partager un environnement entre développeurs est le suivant :

1. **Développeur 1** : Exporte l'environnement
   ```bash
   gestvenv export mon_projet --add-metadata "description:Projet API Flask"
   ```

2. **Développeur 1** : Partage le fichier `mon_projet.json` (via Git, email, etc.)

3. **Développeur 2** : Importe l'environnement
   ```bash
   gestvenv import mon_projet.json
   ```

4. **Développeur 2** : Active l'environnement importé
   ```bash
   gestvenv activate mon_projet
   ```

## Mise à jour d'environnements partagés

Lorsqu'un environnement partagé est modifié (ajout/suppression de packages), vous pouvez mettre à jour le fichier d'export :

```bash
# Après avoir installé de nouveaux packages
gestvenv install "redis,celery"

# Mettre à jour le fichier d'export
gestvenv export mon_projet --output mon_projet.json --overwrite
```

## Conversion entre formats

### De JSON vers requirements.txt

```bash
gestvenv convert mon_projet.json --format requirements --output requirements.txt
```

### De requirements.txt vers JSON

```bash
gestvenv convert requirements.txt --format json --output mon_projet.json --name mon_projet --python python3.9
```

## Compatibilité avec les outils existants

GestVenv est conçu pour s'intégrer avec les outils Python existants :

### Intégration avec pip

```bash
# Export pour pip
gestvenv export mon_projet --format requirements
pip install -r requirements.txt

# Import depuis pip
pip freeze > requirements.txt
gestvenv import requirements.txt --name mon_projet
```

### Intégration avec virtualenv/venv

```bash
# Créer un environnement GestVenv à partir d'un virtualenv existant
virtualenv -p python3.9 mon_env
source mon_env/bin/activate
pip install flask pytest
pip freeze > requirements.txt
gestvenv import requirements.txt --name mon_projet
```

## Bonnes pratiques

1. **Versionnez les fichiers d'export** dans votre système de contrôle de version (Git).
2. **Utilisez le format JSON** pour préserver toutes les métadonnées.
3. **Ajoutez des descriptions** détaillées lors de l'export pour faciliter la compréhension.
4. **Vérifiez la compatibilité des versions Python** entre les systèmes lors du partage.
5. **Mettez à jour régulièrement** les fichiers d'export après des modifications importantes.

## Dépannage

- Si vous rencontrez des erreurs lors de l'import, vérifiez que la version Python spécifiée est disponible sur votre système.
- Pour résoudre les problèmes de dépendances lors de l'import, utilisez l'option `--verbose` pour plus d'informations.
- Si certains packages ne s'installent pas correctement, essayez de les exclure avec `--exclude` puis de les installer manuellement.