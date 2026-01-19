# Documentation GestVenv v2.0

Bienvenue dans la documentation de **GestVenv v2.0**, le gestionnaire d'environnements virtuels Python moderne et performant.

## Nouveautés v2.0

Cette version majeure introduit trois fonctionnalités révolutionnaires :

- **Environnements Éphémères** : Environnements temporaires avec nettoyage automatique
- **Extension VS Code Native** : Intégration IDE profonde avec IntelliSense
- **Interface Web Moderne** : Dashboard complet Vue 3 + FastAPI

Voir les [Release Notes v2.0](../RELEASE_NOTES_v2.0.md) pour tous les détails.

## Vue d'ensemble

GestVenv v2.0 révolutionne la gestion des environnements Python avec des performances jusqu'à 10x supérieures et un écosystème complet d'outils.

### Fonctionnalités clés

- **Performance exceptionnelle** : Backend uv ultra-rapide (< 1s création)
- **Environnements éphémères** : Création/destruction automatique avec isolation
- **Extension VS Code** : IntelliSense et synchronisation temps réel
- **Interface Web** : Gestion visuelle complète avec API REST/WebSocket
- **Standards modernes** : Support complet pyproject.toml (PEP 621)
- **Flexibilité** : Backends modulaires (pip, uv, poetry, pdm)
- **Efficacité** : Cache intelligent et mode hors ligne
- **Fiabilité** : Diagnostic automatique et réparation
- **Productivité** : Templates intégrés pour démarrage rapide

### Architecture

GestVenv s'appuie sur une architecture modulaire :

```
gestvenv/
├── core/           # Gestionnaires d'environnements et configuration
├── services/       # Package, cache, migration, diagnostic, templates
├── backends/       # Abstraction pour pip, uv, poetry, pdm
├── cli/            # Interface ligne de commande
├── core/ephemeral/ # Environnements éphémères
├── web/            # API REST et interface web
└── extensions/     # Extension VS Code
```

## Navigation

### 🚀 Démarrage
- [Installation](installation.md) - Installation et configuration
- [Démarrage rapide](quickstart.md) - Premiers pas avec GestVenv
- [Migration v1.x → v2.0](migration-v2.md) - Guide de migration

### 📖 Guides Utilisateur
- [Guide utilisateur](user_guide/README.md) - Utilisation complète
- [Configuration](user_guide/configuration.md) - Personnalisation
- [Templates](user_guide/templates.md) - Utilisation des templates

### 🚀 Environnements Éphémères
- [Guide complet](ephemeral-environments.md) - Création et utilisation
- [Migration vers éphémères](migration-to-ephemeral.md) - Adoption progressive

### 🔌 Extension VS Code
- [Guide VS Code](vscode-extension.md) - Installation et configuration
- [Fonctionnalités](vs-code-extension-guide.md) - Tour des fonctionnalités

### 🌐 Interface Web
- [Installation Web UI](web-ui-installation.md) - Déploiement de l'interface
- [API REST](web-api.md) - Documentation complète de l'API
- [WebSocket Events](web-api.md#websocket) - Événements temps réel

### 🔧 Référence
- [Référence CLI complète](cli-reference-complete.md) - Toutes les commandes
- [Structure du projet](gestvenv_project_structure.md) - Organisation du code

### 🏗️ Développement
- [Architecture](architecture/) - Design interne
- [ADRs](adr/) - Décisions d'architecture
- [Contribution](development/) - Comment contribuer
- [Troubleshooting](troubleshooting/) - Résolution de problèmes

### 💡 Exemples
- [Projets types](examples/) - Cas d'usage concrets

## Commandes Rapides

```bash
# Alias : utilisez 'gv' ou 'gestvenv'

# Création d'environnement
gv create monapp
gv create-from-template fastapi mon-api

# Gestion des packages
gv install requests flask --env monapp
gv list-packages --env monapp

# Environnements éphémères
gv ephemeral create test --interactive

# Cache et offline
gv cache add -r requirements.txt
gv --offline install numpy --env monapp

# Diagnostic
gv doctor --full --auto-fix

# Interface web
cd web && ./start-dev.sh
```

## Support

- **Issues** : [GitHub Issues](https://github.com/gestvenv/gestvenv/issues)
- **Discussions** : [GitHub Discussions](https://github.com/gestvenv/gestvenv/discussions)
- **Email** : contact@gestvenv.dev

## Changelog

Voir le [CHANGELOG](../CHANGELOG.md) pour l'historique complet des versions.

## Licence

GestVenv est distribué sous licence MIT. Voir [LICENSE](../LICENSE) pour les détails.

---

<div align="center">
  <strong>GestVenv v2.0 - L'avenir de la gestion d'environnements Python</strong>
</div>
