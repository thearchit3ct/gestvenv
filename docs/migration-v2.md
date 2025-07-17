# Guide de Migration vers GestVenv v2.0

Ce guide détaille les étapes pour migrer de GestVenv v1.x vers v2.0, incluant les nouvelles fonctionnalités et les changements majeurs.

## Table des matières

1. [Vue d'ensemble des changements](#vue-densemble-des-changements)
2. [Migration automatique](#migration-automatique)
3. [Changements breaking](#changements-breaking)
4. [Nouvelles fonctionnalités](#nouvelles-fonctionnalités)
5. [Migration manuelle](#migration-manuelle)
6. [Troubleshooting](#troubleshooting)

## Vue d'ensemble des changements

### Nouveautés majeures v2.0

- 🚀 **Environnements éphémères** avec cleanup automatique
- 🔌 **Extension VS Code** native avec IntelliSense
- 🌐 **API Web REST/WebSocket** complète
- ⚡ **Alias `gv`** pour tous les commandes
- 📦 **Architecture async** pour performance maximale

### Améliorations

- Performance 30-60% supérieure
- Monitoring temps réel
- Cache intelligent avec compression zstd
- Meilleure gestion des erreurs

### Changements

- Python 3.8 n'est plus supporté (minimum 3.9)
- Format de cache modifié
- Configuration `.gestvenvrc` → `.gestvenv/config.toml`
- API v0 dépréciée

## Migration automatique

### Commande de migration

```bash
# Installation de v2.0
pip install --upgrade gestvenv

# Lancer la migration automatique
gv migrate --from-v1

# Ou avec l'ancienne commande
gestvenv migrate --from-v1
```

### Ce que fait la migration automatique

1. **Sauvegarde** : Création d'un backup dans `~/.gestvenv-backup-v1/`
2. **Environnements** : Migration de tous les environnements existants
3. **Cache** : Conversion au nouveau format avec compression
4. **Configuration** : Migration des settings vers TOML
5. **Historique** : Préservation de l'historique des commandes

### Output de migration

```
🔄 Migration GestVenv v1.x → v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Backup créé: ~/.gestvenv-backup-v1/
✅ 12 environnements migrés
✅ Cache converti (2.3GB → 768MB avec compression)
✅ Configuration migrée vers TOML
✅ Historique préservé

🎉 Migration terminée avec succès!

💡 Nouvelles commandes disponibles:
  - Utilisez 'gv' au lieu de 'gestvenv'
  - Essayez 'gv ephemeral create test' pour les environnements temporaires
  - Installez l'extension VS Code depuis extensions/vscode/
```

## Changements breaking

### 1. Python 3.8 déprécié

```bash
# Vérifier votre version Python
python --version

# Si Python < 3.9, mettre à jour d'abord
# macOS avec Homebrew
brew upgrade python@3.11

# Ubuntu/Debian
sudo apt update && sudo apt install python3.11

# Windows avec winget
winget install Python.Python.3.11
```

### 2. Format de cache

L'ancien format de cache n'est plus compatible :

```bash
# Ancien format (v1.x)
~/.gestvenv/cache/
├── pip/
│   └── packages/
└── metadata.json

# Nouveau format (v2.0)
~/.gestvenv/cache/
├── packages/
│   ├── pip/
│   ├── uv/
│   └── poetry/
├── metadata.db  # SQLite au lieu de JSON
└── compressed/  # Cache compressé zstd
```

### 3. Configuration

```bash
# Ancienne configuration (v1.x)
~/.gestvenvrc

# Nouvelle configuration (v2.0)
~/.config/gestvenv/config.toml
```

Exemple de nouvelle configuration :

```toml
[general]
preferred_backend = "uv"
default_python = "3.11"
auto_cleanup = true

[cache]
enabled = true
size_mb = 2000
compression = "zstd"

[ephemeral]
default_ttl = 3600
default_isolation = "process"

[api]
enabled = false
port = 8000
```

### 4. API Changes

```python
# v1.x - API synchrone
from gestvenv import Environment

env = Environment.create("myproject")
env.install_package("django")

# v2.0 - API async par défaut
import asyncio
from gestvenv import Environment

async def main():
    env = await Environment.create("myproject")
    await env.install_package("django")

asyncio.run(main())

# Alternative synchrone toujours disponible
from gestvenv.sync import Environment

env = Environment.create("myproject")
env.install_package("django")
```

## Nouvelles fonctionnalités

### Environnements éphémères

```python
# Création automatique avec cleanup garanti
from gestvenv import ephemeral

async with ephemeral("test-env") as env:
    await env.install(["pytest", "mypy"])
    result = await env.execute("pytest tests/")
    print(result.stdout)
# Cleanup automatique ici
```

### Extension VS Code

```bash
# Installation
cd extensions/vscode
npm install
npm run package
code --install-extension gestvenv-vscode-2.0.0.vsix

# Utilisation
# 1. Ouvrir un projet Python
# 2. Ctrl/Cmd+Shift+P → "GestVenv: Create Environment"
# 3. IntelliSense automatique pour tous les packages
```

### API Web

```bash
# Démarrer l'API
cd web
./start-dev.sh

# Utiliser l'API
curl http://localhost:8000/api/v1/environments

# Interface web
open http://localhost:5173
```

### Alias court `gv`

```bash
# Toutes les commandes disponibles avec 'gv'
gv create myproject
gv install django
gv list
gv ephemeral create test
```

## Migration manuelle

Si la migration automatique échoue ou pour des cas spéciaux :

### 1. Backup manuel

```bash
# Sauvegarder l'ancienne installation
cp -r ~/.gestvenv ~/.gestvenv-backup-manual
cp ~/.gestvenvrc ~/.gestvenvrc-backup
```

### 2. Export des environnements

```bash
# Avec v1.x, exporter chaque environnement
gestvenv export myproject > myproject-env.json
gestvenv export another-project > another-env.json
```

### 3. Installation propre v2.0

```bash
# Désinstaller v1.x
pip uninstall gestvenv

# Nettoyer les anciens fichiers
rm -rf ~/.gestvenv

# Installer v2.0
pip install gestvenv==2.0.0
```

### 4. Réimporter les environnements

```bash
# Avec v2.0
gv import myproject-env.json --name myproject
gv import another-env.json --name another-project
```

### 5. Reconfigurer

```bash
# Créer la nouvelle configuration
gv config init

# Éditer selon vos besoins
gv config edit
```

## Troubleshooting

### Erreur : "Python 3.8 is not supported"

```bash
# Solution : Mettre à jour Python
pyenv install 3.11.0
pyenv global 3.11.0

# Ou avec conda
conda create -n py311 python=3.11
conda activate py311
```

### Erreur : "Cache format incompatible"

```bash
# Solution : Nettoyer et reconstruire le cache
gv cache clear --all
gv cache rebuild
```

### Erreur : "Configuration file not found"

```bash
# Solution : Initialiser la configuration
gv config init
gv config set preferred_backend uv
gv config set cache_enabled true
```

### Extension VS Code ne fonctionne pas

```bash
# Vérifier que GestVenv est dans le PATH
which gv  # Doit retourner le chemin

# Vérifier la version
gv --version  # Doit être 2.0.0+

# Recharger VS Code
# Ctrl/Cmd+Shift+P → "Developer: Reload Window"
```

### Performance dégradée après migration

```bash
# Optimiser le cache
gv cache optimize

# Activer le backend uv (plus rapide)
gv config set preferred_backend uv

# Nettoyer les environnements inutilisés
gv cleanup --unused --older-than 30d
```

## Rollback si nécessaire

Si vous devez revenir à v1.x :

```bash
# Désinstaller v2.0
pip uninstall gestvenv

# Restaurer le backup
rm -rf ~/.gestvenv
mv ~/.gestvenv-backup-v1 ~/.gestvenv
mv ~/.gestvenvrc-backup ~/.gestvenvrc

# Réinstaller v1.x
pip install gestvenv==1.1.0
```

## Support

### Documentation

- [Guide utilisateur v2.0](https://gestvenv.readthedocs.io)
- [Changelog complet](CHANGELOG.md)
- [API Reference](docs/api/)

### Communauté

- GitHub Issues : https://github.com/gestvenv/gestvenv/issues
- Discussions : https://github.com/gestvenv/gestvenv/discussions
- Discord : https://discord.gg/gestvenv

### Migration assistée

Pour les cas complexes, utilisez le mode verbose :

```bash
gv migrate --from-v1 --verbose --dry-run
```

Cela affichera toutes les actions sans les exécuter.