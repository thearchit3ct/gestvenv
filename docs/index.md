# GestVenv - Gestionnaire d'Environnements Virtuels Python

Bienvenue dans la documentation de **GestVenv**, l'outil moderne pour gérer vos environnements virtuels Python avec simplicité et efficacité.

## 🚀 Qu'est-ce que GestVenv ?

GestVenv est un gestionnaire d'environnements virtuels Python qui simplifie et centralise la gestion de vos projets Python. Il offre une alternative unifiée aux outils existants comme `venv`, `virtualenv` et `pipenv`.

### ✨ Fonctionnalités principales

- **Gestion simplifiée** : Créez, activez et gérez vos environnements en quelques commandes
- **Support moderne** : Compatible avec `pyproject.toml` et les standards Python modernes
- **Performance optimisée** : Intégration avec `uv` pour des installations 10x plus rapides
- **Cache intelligent** : Mode hors ligne avec cache local des packages
- **Multi-plateforme** : Fonctionne sur Windows, macOS et Linux

## 🏁 Démarrage rapide

### Installation

```bash
pip install gestvenv
```

### Premiers pas

```bash
# Créer un nouvel environnement
gestvenv create mon_projet

# Activer l'environnement
gestvenv activate mon_projet

# Installer des packages
gestvenv install mon_projet "requests flask pytest"

# Lister vos environnements
gestvenv list
```

## 📚 Navigation de la documentation

- **[Installation](installation.md)** : Guide d'installation détaillé
- **[Guide Utilisateur](user-guide.md)** : Utilisation quotidienne de GestVenv
- **[Guide Développeur](developer-guide.md)** : Intégration et développement avancé
- **[Référence API](api/)** : Documentation technique complète
- **[Exemples](examples/)** : Cas d'usage pratiques

## 🆕 Nouveautés v1.1

GestVenv v1.1 apporte des fonctionnalités modernes :

- ✅ **Support pyproject.toml** : Compatible avec les standards Python modernes
- ✅ **Intégration uv** : Performances 10x supérieures pour l'installation de packages
- ✅ **Cache intelligent** : Mode hors ligne avec cache local
- ✅ **Détection automatique** : Reconnaissance automatique du type de projet

## 🤝 Communauté et Support

- **GitHub** : [thearchit3ct/gestvenv](https://github.com/thearchit3ct/gestvenv)
- **Issues** : [Signaler un bug](https://github.com/thearchit3ct/gestvenv/issues)
- **Discussions** : [Forum communautaire](https://github.com/thearchit3ct/gestvenv/discussions)

## 📄 License

GestVenv est distribué sous licence MIT. Voir le fichier [LICENSE](https://github.com/thearchit3ct/gestvenv/blob/main/LICENSE) pour plus de détails.