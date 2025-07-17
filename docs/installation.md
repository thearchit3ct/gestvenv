# Installation GestVenv v1.1

Guide complet d'installation et de configuration de GestVenv v1.1.

## Prérequis

- **Python** : 3.8 ou supérieur
- **Système** : Windows, macOS, Linux
- **Espace disque** : 50 MB minimum (cache recommandé : 1-2 GB)

## Installation standard

### Via pip (recommandé)

```bash
pip install gestvenv
```

### Variantes d'installation

#### Installation avec optimisations performance
```bash
pip install gestvenv[performance]
```
Inclut les dépendances pour performances maximales (uv, cache optimisé).

#### Installation complète
```bash
pip install gestvenv[full]
```
Inclut tous les backends optionnels et outils de développement.

#### Installation développement
```bash
pip install gestvenv[dev]
```
Inclut les outils de test, linting et documentation.

### Depuis les sources

```bash
git clone https://github.com/gestvenv/gestvenv.git
cd gestvenv
pip install -e .
```

## Configuration initiale

### Vérification de l'installation

```bash
gestvenv --version
gestvenv doctor
```

La commande `doctor` diagnostique votre installation et suggère des optimisations.

### Configuration des backends

#### Détection automatique
```bash
gestvenv config set-backend auto
```
Recommandé : sélection automatique du backend optimal.

#### Configuration manuelle
```bash
# Backend uv (performance maximale)
gestvenv config set-backend uv

# Backend pip (compatibilité universelle)  
gestvenv config set-backend pip

# Backend poetry (projets poetry existants)
gestvenv config set-backend poetry
```

### Configuration du cache

```bash
# Activer le cache (recommandé)
gestvenv config set cache-enabled true

# Taille du cache
gestvenv config set cache-size 2GB

# Répertoire de cache personnalisé
gestvenv config set cache-dir /custom/path/cache
```

## Installation des backends

### Backend uv (recommandé)

```bash
pip install uv
```

Avantages :
- 10x plus rapide que pip
- Résolution de dépendances optimisée
- Support natif pyproject.toml
- Cache unifié

### Backend poetry

```bash
pip install poetry
```

Avantages :
- Gestion complète de projets
- Lock files détaillés
- Publication PyPI intégrée

### Backend pdm

```bash
pip install pdm
```

Avantages :
- Support PEP 582 (sans venv)
- Performance élevée
- Standards modernes

## Configuration système

### Variables d'environnement

```bash
# Répertoire racine GestVenv
export GESTVENV_HOME=/custom/gestvenv

# Mode hors ligne par défaut
export GESTVENV_OFFLINE=true

# Backend par défaut
export GESTVENV_BACKEND=uv

# Niveau de logs
export GESTVENV_LOG_LEVEL=INFO
```

### Fichier de configuration global

Créez `~/.gestvenv/config.toml` :

```toml
[general]
backend = "auto"
cache_enabled = true
cache_size = "2GB"
auto_cleanup = true

[performance]
parallel_downloads = 4
cache_compression = true
prefer_binary = true

[security]
verify_ssl = true
trusted_hosts = []
```

## Intégration IDE

### VS Code

Ajoutez dans `.vscode/settings.json` :

```json
{
    "python.terminal.activateEnvironment": true,
    "python.pythonPath": ".gestvenv/environments/default/bin/python"
}
```

### PyCharm

Configurez l'interpréteur Python vers `.gestvenv/environments/*/bin/python`.

## Vérification avancée

### Test de performance

```bash
gestvenv benchmark create
gestvenv benchmark install numpy pandas
gestvenv benchmark results
```

### Test de compatibilité

```bash
gestvenv test-compatibility
```

Vérifie la compatibilité avec votre environnement système.

## Désinstallation

```bash
# Nettoyage des environnements
gestvenv cleanup --all

# Désinstallation du package
pip uninstall gestvenv

# Suppression des données (optionnel)
rm -rf ~/.gestvenv
```

## Résolution des problèmes

### Problèmes courants

#### "Command not found"
```bash
# Vérifiez l'installation
pip show gestvenv

# Rechargez le PATH
source ~/.bashrc
```

#### "Backend not available"
```bash
# Installez le backend manquant
pip install uv  # ou poetry, pdm

# Reconfigurez
gestvenv config set-backend auto
```

#### Problèmes de permissions
```bash
# Installation utilisateur
pip install --user gestvenv

# Ou avec sudo (non recommandé)
sudo pip install gestvenv
```

### Diagnostic avancé

```bash
# Diagnostic complet
gestvenv doctor --verbose

# Test de l'environnement
gestvenv debug environment

# Vérification de la configuration
gestvenv debug config
```

## Migration depuis v1.0

Voir le [guide de migration](user_guide/migration.md) pour une mise à jour en douceur.

## Support

Pour l'aide à l'installation :
- [Issues GitHub](https://github.com/gestvenv/gestvenv/issues)
- [Guide de dépannage](troubleshooting.md)
- Email : support@gestvenv.com
