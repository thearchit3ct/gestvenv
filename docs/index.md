# Documentation GestVenv v1.1

Bienvenue dans la documentation de **GestVenv v1.1**, le gestionnaire d'environnements virtuels Python moderne et performant.

## Vue d'ensemble

GestVenv v1.1 révolutionne la gestion des environnements Python avec des performances jusqu'à 10x supérieures et un support complet des standards modernes.

### Fonctionnalités clés

- **Performance exceptionnelle** : Backend uv ultra-rapide
- **Standards modernes** : Support complet pyproject.toml (PEP 621)
- **Flexibilité** : Backends modulaires (pip, uv, poetry, pdm)
- **Efficacité** : Cache intelligent et mode hors ligne
- **Fiabilité** : Diagnostic automatique et réparation
- **Productivité** : Templates intégrés pour démarrage rapide

### Architecture

GestVenv s'appuie sur une architecture modulaire :

- **Core** : Gestionnaires d'environnements et configuration
- **Services** : Package, cache, migration, diagnostic, templates
- **Backends** : Abstraction pour pip, uv, poetry, pdm
- **Utils** : Utilitaires TOML, validation, sécurité

## Navigation

### 🚀 Démarrage
- [Installation](installation.md) - Installation et configuration
- [Démarrage rapide](quickstart.md) - Premiers pas avec GestVenv

### 📖 Guides
- [Guide utilisateur](user_guide/README.md) - Utilisation complète
- [Migration v1.0 → v1.1](user_guide/migration.md) - Mise à jour
- [Configuration](user_guide/configuration.md) - Personnalisation
- [Templates](user_guide/templates.md) - Utilisation des templates

### 🔧 Développement  
- [Architecture](development/architecture.md) - Design interne
- [Contribution](development/contributing.md) - Comment contribuer
- [Tests](development/testing.md) - Stratégie de tests

### 📚 Référence
- [API Reference](api/README.md) - Documentation API complète
- [CLI Reference](api/cli.md) - Commandes disponibles
- [Configuration](api/configuration.md) - Options de configuration

### 💡 Exemples
- [Projets types](examples/README.md) - Cas d'usage concrets
- [Workflows avancés](examples/advanced_workflows/) - Intégration CI/CD

## Support

- **Issues** : [GitHub Issues](https://github.com/gestvenv/gestvenv/issues)
- **Discussions** : [GitHub Discussions](https://github.com/gestvenv/gestvenv/discussions)
- **Email** : support@gestvenv.com

## Licence

GestVenv est distribué sous licence MIT. Voir [LICENSE](../LICENSE) pour les détails.
