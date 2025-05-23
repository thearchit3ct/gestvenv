# Architecture de GestVenv

Ce document présente l'architecture générale de GestVenv et explique comment les différents composants interagissent entre eux.

## Vue d'ensemble

GestVenv est conçu selon une architecture modulaire qui sépare l'interface utilisateur (CLI) de la logique métier. Cette séparation permet une maintenance plus facile, un test plus simple et une évolution flexible du projet.

L'architecture suit globalement le modèle MVC (Modèle-Vue-Contrôleur) adapté aux applications en ligne de commande :

- **Modèle** : Les classes de gestion (managers) qui manipulent les données et l'état des environnements
- **Vue** : L'interface en ligne de commande qui présente les informations à l'utilisateur
- **Contrôleur** : Les commandes CLI qui reçoivent les entrées utilisateur et coordonnent les actions

## Diagramme d'architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                          Interface CLI                              │
│                             cli.py                                  │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                        Gestionnaires Core                          │
│                                                                    │
│   ┌──────────────────┐    ┌───────────────────┐    ┌─────────────┐ │
│   │  env_manager.py  │◄──►│  package_manager.py│◄──►│config_manager│ │
│   └──────────────────┘    └───────────────────┘    └─────────────┘ │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                          Utilitaires                               │
│                                                                    │
│   ┌──────────────────┐    ┌───────────────────┐    ┌─────────────┐ │
│   │  path_handler.py │    │ system_commands.py │    │ validators.py│ │
│   └──────────────────┘    └───────────────────┘    └─────────────┘ │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                      Système & Librairies                          │
│                                                                    │
│   ┌──────────────────┐    ┌───────────────────┐    ┌─────────────┐ │
│   │      venv        │    │       pip         │    │  Système OS  │ │
│   └──────────────────┘    └───────────────────┘    └─────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## Composants principaux

### Interface CLI (cli.py)

Ce composant est le point d'entrée de l'application. Il est responsable de :
- Analyser les arguments de ligne de commande
- Valider les entrées utilisateur
- Distribuer les commandes aux gestionnaires appropriés
- Formater et afficher les résultats

L'interface CLI utilise le module `argparse` pour définir les commandes, sous-commandes et options disponibles. Les commandes sont organisées hiérarchiquement pour une interface utilisateur cohérente.

### Gestionnaires Core

#### Gestionnaire d'environnements (env_manager.py)

Ce composant encapsule toute la logique liée à la gestion des environnements virtuels :
- Création et suppression d'environnements
- Activation et désactivation
- Listage et interrogation des environnements existants

Il interagit directement avec les modules `venv` ou `virtualenv` et maintient l'état des environnements dans la configuration.

#### Gestionnaire de packages (package_manager.py)

Ce composant gère tout ce qui concerne les packages Python :
- Installation et désinstallation de packages
- Mise à jour de packages
- Résolution de dépendances
- Vérification des conflits

Il utilise principalement `pip` comme backend pour les opérations sur les packages.

#### Gestionnaire de configuration (config_manager.py)

Ce composant est responsable de :
- Chargement et sauvegarde des configurations
- Gestion des paramètres par défaut
- Import et export de configurations d'environnement
- Validation des configurations

Les configurations sont stockées au format JSON pour une compatibilité et une lisibilité maximales.

### Utilitaires

#### Gestionnaire de chemins (path_handler.py)

Ce module fournit des fonctionnalités pour :
- Déterminer les chemins des environnements virtuels
- Résoudre les chemins relatifs et absolus
- Gérer les chemins spécifiques au système d'exploitation

Il utilise principalement le module `pathlib` pour une manipulation portable des chemins.

#### Commandes système (system_commands.py)

Ce module encapsule :
- L'exécution de commandes système
- La détection du système d'exploitation
- L'interaction avec le shell
- La gestion des erreurs liées au système

#### Validateurs (validators.py)

Ce module contient des fonctions pour :
- Valider les noms d'environnements
- Vérifier les versions de Python
- Valider les noms et versions de packages
- Vérifier les entrées utilisateur

## Flux de données

1. L'utilisateur exécute une commande GestVenv via le terminal
2. Le module CLI analyse les arguments et détermine l'action à effectuer
3. La commande est transmise au gestionnaire approprié (environnement, package, etc.)
4. Le gestionnaire effectue les opérations nécessaires, souvent en utilisant les modules utilitaires
5. Les résultats sont renvoyés au module CLI
6. Le module CLI formate et affiche les résultats à l'utilisateur

## Gestion de l'état

GestVenv utilise un fichier de configuration central (au format JSON) pour maintenir l'état de tous les environnements virtuels gérés. Ce fichier contient :

- La liste des environnements virtuels avec leurs métadonnées
- L'environnement actuellement actif
- Les paramètres de configuration par défaut
- Les préférences utilisateur

Le fichier de configuration est stocké dans un emplacement spécifique au système d'exploitation :
- Windows : `%APPDATA%\GestVenv\config.json`
- macOS : `~/Library/Application Support/GestVenv/config.json`
- Linux : `~/.config/gestvenv/config.json`

## Principes de conception

### Isolation

Chaque composant a une responsabilité unique et bien définie, minimisant les dépendances entre modules.

### Extensibilité

L'architecture permet d'ajouter facilement de nouvelles fonctionnalités sans modifier le code existant, en suivant le principe ouvert/fermé.

### Portabilité

GestVenv est conçu pour fonctionner de manière cohérente sur différents systèmes d'exploitation, en abstrayant les différences spécifiques au système.

### Robustesse

Le système gère correctement les erreurs à tous les niveaux, fournissant des messages utiles et évitant les défaillances catastrophiques.

## Dépendances externes

GestVenv s'appuie sur plusieurs bibliothèques et outils Python standard :

- **venv/virtualenv** : Pour la création d'environnements virtuels
- **pip** : Pour la gestion des packages
- **argparse** : Pour l'analyse des arguments de ligne de commande
- **json** : Pour la gestion des fichiers de configuration
- **pathlib** : Pour la manipulation des chemins de fichiers
- **subprocess** : Pour l'exécution de commandes système

Ces dépendances sont soit des modules standard Python, soit des outils largement utilisés dans l'écosystème Python, minimisant ainsi les problèmes de compatibilité.

## Considérations de performance

GestVenv est conçu pour être efficace, même avec un grand nombre d'environnements virtuels. Les principales optimisations incluent :

- Chargement paresseux des modules pour réduire le temps de démarrage
- Mise en cache des informations fréquemment utilisées
- Exécution asynchrone de certaines opérations longues
- Limitation des appels système au minimum nécessaire

Ces optimisations permettent à GestVenv de rester réactif, même lors de la gestion de nombreux environnements avec de multiples packages.
