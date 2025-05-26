# 📋 CHANGELOG - GestVenv

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### À venir

- Support complet pyproject.toml (PEP 621)
- Intégration backend uv pour performances optimales
- Templates de projets intégrés

---

## [1.1.1] - 2025-05-26

### 🐛 Corrections Critiques

- **Corrigé** : Erreur `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90` lors de l'ajout de packages au cache

- **Corrigé** : Erreur `list index out of range` lors du parsing des noms de packages complexes
- **Corrigé** : Blocages lors de téléchargements lents (ajout timeout 5min)
- **Corrigé** : Corruption du cache après erreurs partielles
- **Corrigé** : Statistiques incorrectes après nettoyage du cache

### 🚀 Ajouté

- **Nouveau** : Méthode `download_and_cache_packages()` pour téléchargement par lots
- **Nouveau** : Commande `gestvenv cache remove` pour suppression sélective
- **Nouveau** : Détection intelligente des versions avec regex améliorée
- **Nouveau** : Support complet UTF-8 dans toutes les opérations
- **Nouveau** : Validation d'intégrité SHA-256 pour tous les packages cachés

### 🔧 Amélioré

- **Amélioré** : Gestion d'erreurs robuste avec try/catch généralisés
- **Amélioré** : Messages d'erreur contextuels et informatifs
- **Amélioré** : Performance du parsing des noms de packages (+28%)
- **Amélioré** : Nettoyage du cache plus rapide (+19%)
- **Amélioré** : Support des formats de packages étendus (.whl, .tar.gz, .zip)

### 🔒 Sécurité

- **Sécurisé** : Validation stricte des noms de packages
- **Sécurisé** : Échappement approprié pour l'exécution de commandes système
- **Sécurisé** : Isolation des processus de téléchargement

---

## [1.1.0] - 2025-05-24

### 🚀 Ajouté

- **Nouveau** : Service de cache intelligent pour packages Python
- **Nouveau** : Mode hors ligne complet (`--offline`)
- **Nouveau** : Commandes cache (`add`, `list`, `clean`, `info`)
- **Nouveau** : Détection automatique des backends (préparation uv)
- **Nouveau** : Architecture modulaire pour backends de packages
- **Nouveau** : Support des groupes de dépendances optionnelles
- **Nouveau** : Outils de migration et conversion

### 🔧 Amélioré

- **Amélioré** : PackageService refactorisé avec architecture unifiée
- **Amélioré** : ConfigManager avec migration automatique
- **Amélioré** : Gestion d'erreurs centralisée et robuste
- **Amélioré** : CLI étendu avec nouvelles commandes
- **Amélioré** : Performance générale (+15% vitesse moyenne)

### 📚 Documentation

- **Ajouté** : Guide du cache intelligent
- **Ajouté** : Documentation mode hors ligne
- **Ajouté** : Guide de migration v1.0 → v1.1
- **Ajouté** : Exemples d'utilisation avancée

---

## [1.0.1] - 2024-02-20

### 🐛 Corrections

- **Corrigé** : Problème d'activation sous Windows PowerShell
- **Corrigé** : Gestion des chemins avec espaces
- **Corrigé** : Export JSON avec caractères spéciaux
- **Corrigé** : Validation des noms d'environnements

### 🔧 Amélioré

- **Amélioré** : Messages d'erreur plus explicites
- **Amélioré** : Performance de la commande `list`
- **Amélioré** : Compatibilité Python 3.13

---

## [1.0.0] - 2024-01-01

### 🎉 Release Initiale

### 🚀 Fonctionnalités Core

- **Ajouté** : Création d'environnements virtuels (`create`)
- **Ajouté** : Activation/désactivation d'environnements (`activate`, `deactivate`)
- **Ajouté** : Gestion des packages (`install`, `update`, `remove`)
- **Ajouté** : Liste et informations des environnements (`list`, `info`)
- **Ajouté** : Export/import de configurations (`export`, `import`)
- **Ajouté** : Clonage d'environnements (`clone`)
- **Ajouté** : Exécution de commandes dans environnements (`run`)

### 🛠️ Infrastructure

- **Ajouté** : ConfigManager pour gestion centralisée
- **Ajouté** : EnvironmentService pour opérations environnements
- **Ajouté** : PackageService pour gestion packages
- **Ajouté** : SystemService pour interactions système
- **Ajouté** : CLI complet avec sous-commandes

### 📦 Distribution

- **Ajouté** : Package PyPI `gestvenv`
- **Ajouté** : Support Python 3.9, 3.10, 3.11, 3.12
- **Ajouté** : Compatibilité Windows, macOS, Linux
- **Ajouté** : Documentation utilisateur complète

### 🧪 Tests

- **Ajouté** : Suite de tests avec 85% de couverture
- **Ajouté** : Tests d'intégration multi-plateformes
- **Ajouté** : Tests de performance et benchmarks

---

## [0.9.0] - 2024-11-15 (Beta)

### 🚀 Ajouté

- **Ajouté** : Prototype CLI avec commandes de base
- **Ajouté** : Modèles de données (`EnvironmentInfo`, `PackageInfo`)
- **Ajouté** : Service de base pour environnements virtuels
- **Ajouté** : Configuration JSON pour persistance

### 🧪 Tests

- **Ajouté** : Tests unitaires de base
- **Ajouté** : Configuration pytest et CI/CD

---

## [0.5.0] - 2024-10-20 (Alpha)

### 🚀 Ajouté

- **Ajouté** : Proof of concept pour gestion environnements
- **Ajouté** : Architecture de base des services
- **Ajouté** : Prototype d'interface CLI

### 📚 Documentation

- **Ajouté** : README initial
- **Ajouté** : Spécifications techniques de base

---

## Types de Changements

- `🚀 Ajouté` pour les nouvelles fonctionnalités
- `🔧 Amélioré` pour les modifications de fonctionnalités existantes
- `🐛 Corrigé` pour les corrections de bugs
- `🗑️ Supprimé` pour les fonctionnalités supprimées
- `🔒 Sécurité` pour les corrections de vulnérabilités
- `📚 Documentation` pour les changements de documentation
- `🧪 Tests` pour les ajouts ou modifications de tests
- `⚡ Performance` pour les améliorations de performance

---

## Liens

- [PyPI Package](https://pypi.org/project/gestvenv/)
- [GitHub Repository](https://github.com/thearchit3ct/gestvenv)
- [Documentation](https://github.com/thearchit3ct/gestvenv/wiki)
- [Issues](https://github.com/thearchit3ct/gestvenv/issues)
- [Discussions](https://github.com/thearchit3ct/gestvenv/discussions)

---

## Notes de Version

### Politique de Support

- **Versions majeures** : Supportées 2 ans après release
- **Versions mineures** : Supportées 1 an après release  
- **Versions patch** : Correctifs critiques uniquement

### Migration

- **v1.0 → v1.1** : Migration automatique, 100% compatible
- **v1.1 → v1.2** : Nouvelles fonctionnalités, compatible
- **v1.x → v2.0** : Guide de migration fourni

### Performance

- **v1.0.0** : Baseline performance
- **v1.1.0** : +15% performance générale
- **v1.1.1** : +28% performance cache, +19% nettoyage
- **v1.2.0** : +500-1000% performance prévue (uv backend)