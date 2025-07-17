# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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