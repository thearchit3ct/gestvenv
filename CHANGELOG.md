
# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-01-27

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

## [1.0.0] - 2024-12-15

### ✨ Version initiale

- Gestion d'environnements virtuels basique
- Support requirements.txt
- Backend pip uniquement
- Interface CLI simple
- Export/import JSON

---

**Note** : Les versions pre-1.0 sont considérées comme expérimentales et ne sont pas documentées ici.