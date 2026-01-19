# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.3] - 2026-01-19

### 🔧 Améliorations

#### Workflow Release
- **Sigstore v3** : Mise à jour vers `sigstore/gh-action-sigstore-python@v3.0.0` pour compatibilité avec GitHub Actions
- **Script notify-success** : Correction de l'erreur de syntaxe shell

---

## [2.0.2] - 2026-01-19

### 🐛 Corrections

#### CI/CD
- **Import Python manquant** : Ajout de `List` aux imports de typing dans `handlers.py`
- **Conflit de nommage WebSocket** : Renommage de `websocket.py` en `ws_manager.py` pour éviter le conflit avec le package `websocket/`
- **Serveur UI manquant** : Ajout de `npm run preview` dans le workflow CI pour servir l'UI avant les tests E2E
- **Viewport Cypress** : Configuration du viewport (1280x720) pour les tests E2E en mode headless
- **GitHub Actions dépréciées** : Mise à jour de `actions/upload-artifact` et `actions/cache` vers v4
- **Sigstore** : Mise à jour vers `sigstore/gh-action-sigstore-python@v3.0.0`

#### Corrections de code
- **Signature disconnect()** : Correction de l'appel `disconnect()` pour utiliser `client_id` au lieu de `websocket`
- **Erreur syntaxe workflow** : Correction du script shell dans le job `notify-success`

---

## [2.0.1] - 2026-01-19

### 🐛 Corrections

#### Interface Web
- **Fix CSS Tailwind** : Ajout de `postcss.config.js` manquant pour le rendu correct des styles
- **Installation plugins Tailwind** : Ajout des plugins `@tailwindcss/forms` et `@tailwindcss/typography`
- **Correction Packages.vue** : Remplacement des composants UI manquants (Input, Select, Button) par HTML natif
- **Correction PackageCard.vue** : Remplacement des composants Card, Badge, Button par classes CSS
- **Correction Cache.vue** : Remplacement des composants Label, Input, Checkbox par éléments natifs

#### Améliorations
- Meilleure compatibilité sans bibliothèque de composants externe
- Interface plus légère et rapide à charger
- Cohérence des styles avec Tailwind CSS natif

---

## [2.0.0] - 2025-07-17

### 🎉 Nouveautés Majeures

#### 🚀 Environnements Éphémères
- **API Python** avec context managers pour création/destruction automatique
- **4 niveaux d'isolation** : process, namespace, container, chroot
- **Monitoring temps réel** : suivi CPU, mémoire, disque
- **Storage optimisé** : tmpfs, memory, disk avec compression
- **CLI complète** : create, list, stats, cleanup
- **Cleanup automatique** garanti même en cas d'erreur

#### 🔌 Extension VS Code Native
- **IntelliSense** pour tous les packages Python installés
- **Auto-complétion** intelligente avec cache
- **Language Server Protocol** (LSP) complet
- **WebSocket** pour synchronisation temps réel
- **Code actions** : installation rapide, refactoring
- **Vue arborescente** des environnements et packages

#### 🌐 Interface Web Moderne
- **Dashboard Vue 3** avec Tailwind CSS
- **API REST** complète avec FastAPI
- **WebSocket** pour mises à jour temps réel
- **Gestion visuelle** : environnements, packages, cache
- **Monitoring** : statistiques et graphiques

#### ⚡ Alias de Commande
- Support de `gv` comme alias court de `gestvenv`
- Utilisable dans tous les contextes CLI

### ✨ Améliorations

#### Performance
- **Création d'environnement** : < 1s avec uv
- **Cache intelligent** : compression zstd, deduplication
- **Téléchargements parallèles** : 3x plus rapide
- **Lazy loading** : démarrage instantané

#### Architecture
- **Async/await** partout pour performance maximale
- **Plugin system** : backends extensibles
- **Service layer** : séparation claire des responsabilités
- **Error recovery** : mécanismes de récupération automatique

#### Developer Experience
- **Types complets** : TypeScript pour VS Code, Pydantic pour Python
- **Tests exhaustifs** : >90% de couverture
- **Documentation** : guides complets et API reference
- **CI/CD** : GitHub Actions pour tests et releases

### 🔧 Changements Techniques

#### Backend System
- Refactoring complet avec abstract base class
- Support unifié pip, uv, poetry, PDM
- Auto-détection intelligente du backend optimal

#### Configuration
- Support TOML pour tous les fichiers config
- Variables d'environnement `GESTVENV_*`
- Configuration en cascade : env → projet → global

#### API
- REST API v1 complète avec FastAPI
- WebSocket pour événements temps réel
- Authentication JWT (optionnelle)
- OpenAPI/Swagger documentation

### 🐛 Corrections

- Fix des problèmes de cache sur Windows
- Résolution des conflits de dépendances
- Correction des fuites mémoire dans le monitoring
- Fix de la détection Python sur macOS

### 📦 Dépendances

- Mise à jour vers Python 3.9+ minimum
- FastAPI 0.100+
- Vue 3.3+
- TypeScript 5.0+
- Pydantic 2.0+

### ⚠️ Breaking Changes

- Python 3.8 n'est plus supporté
- L'API v0 est dépréciée (utilisez v1)
- Format de cache changé (migration automatique)
- Configuration `.gestvenvrc` → `.gestvenv/config.toml`

### 🔄 Migration

Pour migrer depuis v1.x :
```bash
gv migrate --from-v1
```

## [1.1.0] - 2025-01-15

### ✨ Nouvelles fonctionnalités

- **Support pyproject.toml natif** : Conformité complète PEP 621
- **Backend uv** : Performance 10x supérieure avec fallback pip automatique
- **Architecture multi-backend** : Support extensible pip/uv/poetry/pdm
- **Cache intelligent** : Mode hors ligne avec compression et LRU
- **Service de diagnostic** : Détection automatique et réparation des problèmes
- **Templates de projets** : Templates intégrés (web, data science, CLI)
- **Migration automatique** : Transition transparente v1.0 → v1.1

### 🔧 Améliorations

- Interface CLI moderne avec sous-commandes intuitives
- Validation de sécurité renforcée
- Monitoring de performance intégré
- Messages d'erreur plus informatifs
- Support émojis dans l'interface

### 🐛 Corrections

- Gestion robuste des erreurs de réseau
- Correction des permissions sur Windows
- Amélioration de la détection des versions Python
- Fix de la gestion des dépendances circulaires

### 🔄 Migration

- Migration automatique des environnements v1.0
- Conversion assistée requirements.txt → pyproject.toml
- Préservation totale de la compatibilité ascendante

### ⚠️ Changements

- **AUCUN BREAKING CHANGE** : Compatibilité 100% avec v1.0
- Nouveau répertoire de configuration : `~/.gestvenv/` (migration auto)
- Cache reorganisé par backend pour optimisation

## [1.0.0] - 2024-10-01

### ✨ Version initiale

- Gestion d'environnements virtuels basique
- Support requirements.txt
- Backend pip uniquement
- Interface CLI simple
- Export/import JSON

---

**Note** : Les versions pre-1.0 sont considérées comme expérimentales et ne sont pas documentées ici.

Pour voir tous les changements entre les versions :
```bash
git log --oneline --decorate --graph v1.1.0..v2.0.0
```