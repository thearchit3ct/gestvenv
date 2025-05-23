# Commandes de base

Ce guide vous présente les commandes essentielles de GestVenv pour commencer rapidement.

## Vue d'ensemble

GestVenv utilise une interface en ligne de commande simple avec la syntaxe :

```bash
gestvenv <commande> [options] [arguments]
```

## Commandes essentielles

### 📋 Lister les environnements

```bash
# Lister tous les environnements
gestvenv list

# Affichage détaillé
gestvenv list --verbose
```

### 🆕 Créer un environnement

```bash
# Création simple
gestvenv create mon_projet

# Avec version Python spécifique
gestvenv create mon_projet --python python3.9

# Avec packages initiaux
gestvenv create mon_projet --packages "flask,pytest,requests"
```

### ⚡ Activer un environnement

```bash
gestvenv activate mon_projet
```

!!! note "Important"
    GestVenv affiche la commande à exécuter pour activer l'environnement. Vous devez copier-coller cette commande dans votre terminal.

### 📦 Installer des packages

```bash
# Dans l'environnement actif
gestvenv install "pandas,matplotlib"

# Dans un environnement spécifique
gestvenv install "numpy" --env mon_projet
```

### ℹ️ Informations sur un environnement

```bash
gestvenv info mon_projet
```

### 🔄 Mettre à jour des packages

```bash
# Vérifier les mises à jour disponibles
gestvenv check mon_projet

# Mettre à jour tous les packages
gestvenv update --all --env mon_projet
```

### 🗑️ Supprimer un environnement

```bash
# Avec confirmation
gestvenv delete mon_projet

# Sans confirmation
gestvenv delete mon_projet --force
```

## Aide et documentation

### Aide générale

```bash
gestvenv --help
```

### Aide sur une commande spécifique

```bash
gestvenv create --help
gestvenv install --help
```

### Versions Python disponibles

```bash
gestvenv pyversions
```

### Documentation intégrée

```bash
gestvenv docs
```

## Workflow typique

Voici un exemple de workflow complet :

```bash
# 1. Créer un environnement pour un nouveau projet
gestvenv create api_project --python python3.10

# 2. Activer l'environnement
gestvenv activate api_project
# Suivre les instructions affichées

# 3. Installer les dépendances
gestvenv install "fastapi,uvicorn,pytest"

# 4. Vérifier l'installation
gestvenv info api_project

# 5. Développer votre projet...

# 6. Exporter la configuration pour l'équipe
gestvenv export api_project --output api_config.json
```

## Options globales

### Affichage de la version

```bash
gestvenv --version
```

### Mode debug

```bash
gestvenv --debug <commande>
```

### Format de sortie JSON

```bash
gestvenv list --json
gestvenv info mon_projet --json
```

## Conseils pratiques

### 🎯 Nommage des environnements

- Utilisez des noms descriptifs : `web_app`, `data_analysis`, `ml_project`
- Évitez les espaces et caractères spéciaux
- Préférez les underscores aux tirets : `my_project` plutôt que `my-project`

### 🔍 Vérification rapide

```bash
# Status de tous les environnements
gestvenv list --verbose

# Environnement actif
gestvenv list | grep "●"
```

### 🚀 Raccourcis utiles

```bash
# Créer et activer en une fois
gestvenv create mon_projet && gestvenv activate mon_projet

# Installer depuis requirements.txt
gestvenv import requirements.txt --name mon_projet
```

## Prochaines étapes

Maintenant que vous maîtrisez les commandes de base, explorez :

- [Gestion des environnements](../user-guide/environment-management.md) - Fonctionnalités avancées
- [Gestion des packages](../user-guide/package-management.md) - Installation et mise à jour
- [Import/Export](../user-guide/import-export.md) - Partage de configurations