# Changelog

Tous les changements notables apportés au projet GestVenv seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-18

### Ajouté

- Interface en ligne de commande complète pour la gestion des environnements virtuels
- Commande `create` pour créer des environnements avec différentes versions Python
- Commande `activate` et `deactivate` pour activer/désactiver des environnements
- Commande `list` pour afficher tous les environnements disponibles
- Commande `info` pour obtenir des informations détaillées sur un environnement
- Commande `install`, `update` et `remove` pour la gestion des packages
- Commande `export` pour exporter des configurations au format JSON et requirements.txt
- Commande `import` pour importer des configurations depuis JSON et requirements.txt
- Commande `clone` pour dupliquer des environnements existants
- Commande `run` pour exécuter des commandes dans un environnement spécifique
- Commande `check` pour vérifier les dépendances et les mises à jour disponibles
- Commande `pyversions` pour afficher les versions Python disponibles
- Documentation intégrée accessible via la commande `docs`
- Support complet pour Windows, macOS et Linux
- Validation des entrées utilisateur pour éviter les erreurs
- Messages d'aide contextuelle pour chaque commande
- Structure de configuration centralisée pour tous les environnements

### Optimisé

- Temps de création d'environnement réduit à moins de 10 secondes
- Temps de démarrage de l'application inférieur à 2 secondes
- Gestion efficace d'au moins 50 environnements virtuels

### Sécurité

- Vérification de l'intégrité des packages installés
- Pas de stockage d'informations sensibles dans les fichiers de configuration
- Respect des politiques de sécurité du système d'exploitation hôte

## [0.5.0] - 2025-04-01

### Ajouté

- Première version bêta avec fonctionnalités principales
- Structure de base du projet avec modules core et utils
- Tests unitaires pour les composants principaux
- Documentation préliminaire pour les utilisateurs et développeurs

### Amélioré

- Optimisation de la gestion des chemins de fichiers
- Amélioration de la compatibilité entre systèmes d'exploitation

### Corrigé

- Résolution des problèmes d'activation sur Windows
- Correction des erreurs de gestion des dépendances circulaires

## [0.2.0] - 2025-03-15

### Ajouté

- Prototype initial avec fonctionnalités de base
- Création et suppression d'environnements
- Installation simple de packages
- Configuration de base

## [0.1.0] - 2025-03-01

### Ajouté

- Initialisation du projet
- Structure des répertoires et fichiers
- Documentation de conception
- Définition des exigences et spécifications

[1.0.0]: https://github.com/votrenom/gestvenv/compare/v0.5.0...v1.0.0
[0.5.0]: https://github.com/votrenom/gestvenv/compare/v0.2.0...v0.5.0
[0.2.0]: https://github.com/votrenom/gestvenv/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/votrenom/gestvenv/releases/tag/v0.1.0
