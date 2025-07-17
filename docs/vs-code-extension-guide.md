# Guide complet de l'extension VS Code GestVenv

## Vue d'ensemble

L'extension VS Code GestVenv offre une intégration native profonde avec l'éditeur, permettant une gestion transparente des environnements virtuels Python et une expérience de développement améliorée.

## Installation et démarrage rapide

### Prérequis

1. **VS Code** version 1.85.0 ou supérieure
2. **GestVenv CLI** installé : `pip install gestvenv`
3. **Python** 3.8+ installé sur le système
4. **API GestVenv** (optionnel, pour fonctionnalités avancées)

### Installation

#### Option 1 : Depuis le VS Code Marketplace (recommandé)
```bash
# Ouvrir VS Code
# Aller dans Extensions (Ctrl+Shift+X)
# Rechercher "GestVenv"
# Cliquer sur Install
```

#### Option 2 : Installation manuelle du VSIX
```bash
# Télécharger le fichier .vsix depuis les releases GitHub
code --install-extension gestvenv-vscode-0.1.0.vsix
```

#### Option 3 : Depuis le code source (développeurs)
```bash
cd extensions/vscode
npm install
npm run compile
# Appuyer sur F5 dans VS Code pour lancer en mode debug
```

### Configuration initiale

1. **Lancer l'API GestVenv** (pour IntelliSense avancé) :
   ```bash
   cd web
   python -m uvicorn api.main:app --reload
   ```

2. **Vérifier la détection automatique** :
   - Ouvrir un projet Python
   - La barre d'état devrait afficher l'environnement actif
   - Si non, utiliser la commande "GestVenv: Detect Environments"

## Fonctionnalités principales

### 1. Gestion des environnements

#### Création d'environnement
- **Commande** : `Ctrl+Shift+P` → "GestVenv: Create Environment"
- **Options disponibles** :
  - Backend : uv (recommandé), pip, pdm, poetry
  - Version Python : détection automatique ou sélection manuelle
  - Template : django, fastapi, data-science, etc.

#### Activation/Changement d'environnement
- **Clic sur la barre d'état** : Menu déroulant des environnements
- **Explorateur** : Double-clic sur un environnement
- **Commande** : "GestVenv: Activate Environment"

#### Suppression d'environnement
- **Explorateur** : Clic droit → "Delete"
- **Commande** : "GestVenv: Delete Environment"
- **Confirmation** : Toujours demandée avant suppression

### 2. Gestion des packages

#### Installation de packages

**Méthode 1 : Quick Fix sur import manquant**
```python
import requests  # Souligné en rouge
# Ctrl+. → "Install requests in current environment"
```

**Méthode 2 : Commande directe**
```
Ctrl+Shift+P → "GestVenv: Install Package"
→ Rechercher le package
→ Sélectionner la version (optionnel)
```

**Méthode 3 : Depuis l'explorateur**
- Clic droit sur environnement → "Install Package"
- Interface de recherche avec autocomplétion

#### Mise à jour de packages
- Explorateur → Badge sur package obsolète → Clic pour mettre à jour
- Commande : "GestVenv: Update Package"

#### Désinstallation
- Explorateur → Clic droit sur package → "Uninstall"
- Confirmation requise

### 3. IntelliSense amélioré

#### Auto-complétion contextuelle
```python
# Tapez "import " pour voir tous les packages installés
import |  # → requests, pandas, numpy, flask...

# Complétion des sous-modules
from flask import |  # → Flask, request, jsonify...

# Complétion des attributs
requests.|  # → get, post, Session...
```

#### Informations au survol
```python
import requests  # Survolez pour voir :
# requests v2.31.0
# HTTP library for Python
# ⬇️ 145M downloads/month
# 📦 Installed in: my-env
```

#### Signatures de fonctions
```python
requests.get(  # Affiche la signature complète
# get(url, params=None, **kwargs)
# → Response
```

### 4. Diagnostics et Quick Fixes

#### Détection d'imports manquants
```python
import missing_package  # Erreur : Package not found
# Quick Fix : Install missing_package
```

#### Vérification des versions
```python
# Warning si version incompatible détectée
import old_package  # ⚠️ Version 1.0 installed, 2.0 available
```

#### Résolution de conflits
- Détection automatique des conflits de dépendances
- Suggestions de résolution

### 5. Explorateur d'environnements

#### Structure de l'arbre
```
🏠 GestVenv
├── 📦 my-project (uv, Python 3.11) [Active]
│   ├── ℹ️ Details
│   │   ├── Backend: uv
│   │   ├── Python: 3.11.5
│   │   └── Path: /path/to/env
│   ├── 📚 Packages (25)
│   │   ├── django 4.2.8
│   │   ├── requests 2.31.0
│   │   └── ...
│   └── ⚡ Actions
│       ├── Install Package
│       ├── Update All
│       └── Export Requirements
├── 📦 test-env (pip, Python 3.10)
└── ➕ Create New Environment
```

#### Actions contextuelles
- **Sur environnement** : Activate, Delete, Rename, Clone
- **Sur package** : Update, Uninstall, Show Info
- **Global** : Refresh, Create, Import

### 6. Intégration avec le terminal

#### Activation automatique
- Nouveaux terminaux activent l'environnement sélectionné
- Indicateur visuel dans le prompt

#### Commandes intégrées
```bash
# Dans le terminal VS Code
gestvenv list  # Liste les environnements
gestvenv install package  # Installation directe
```

## Workflows avancés

### 1. Développement multi-environnement

```python
# Fichier : test_compatibility.py
# Tester avec différentes versions Python

# 1. Créer environnements de test
# GestVenv: Create Environment → Python 3.8
# GestVenv: Create Environment → Python 3.9
# GestVenv: Create Environment → Python 3.10

# 2. Basculer rapidement entre environnements
# Clic sur barre d'état → Sélectionner environnement

# 3. Exécuter tests dans chaque environnement
```

### 2. Migration de projets

```bash
# Importer depuis requirements.txt
GestVenv: Import from requirements.txt

# Importer depuis Pipfile
GestVenv: Import from Pipfile

# Exporter vers pyproject.toml
GestVenv: Export to pyproject.toml
```

### 3. Templates de projet

```python
# Créer projet Django complet
GestVenv: Create Environment
→ Template: django
→ Inclut : Django, DRF, Celery, Redis

# Créer projet Data Science
GestVenv: Create Environment
→ Template: data-science
→ Inclut : NumPy, Pandas, Jupyter, Matplotlib
```

### 4. Développement offline

```python
# Activer le cache local
Settings → gestvenv.cache.enable: true

# Pré-télécharger packages courants
GestVenv: Cache Popular Packages

# Travailler sans connexion
# Les packages en cache s'installent localement
```

## Configuration avancée

### settings.json complet

```json
{
  // Activation générale
  "gestvenv.enable": true,
  
  // Détection et activation
  "gestvenv.autoDetect": true,
  "gestvenv.autoActivate": true,
  "gestvenv.activateInTerminal": true,
  
  // Interface utilisateur
  "gestvenv.showStatusBar": true,
  "gestvenv.showExplorer": true,
  "gestvenv.compactMode": false,
  
  // IntelliSense
  "gestvenv.enableIntelliSense": true,
  "gestvenv.intelliSense.showStats": true,
  "gestvenv.intelliSense.showDocs": true,
  "gestvenv.intelliSense.includePrivate": false,
  
  // API et performance
  "gestvenv.apiEndpoint": "http://localhost:8000",
  "gestvenv.apiTimeout": 5000,
  
  // Cache
  "gestvenv.cache.enable": true,
  "gestvenv.cache.ttl": 300,
  "gestvenv.cache.maxSize": 100,
  
  // Diagnostics
  "gestvenv.diagnostics.enable": true,
  "gestvenv.diagnostics.showMissingImports": true,
  "gestvenv.diagnostics.showOutdated": true,
  "gestvenv.diagnostics.severity": "warning",
  
  // Packages
  "gestvenv.packages.autoUpdate": false,
  "gestvenv.packages.showPrerelease": false,
  
  // Backends préférés
  "gestvenv.preferredBackend": "uv",
  "gestvenv.backends.uv.path": "uv",
  "gestvenv.backends.pip.extraArgs": [],
  
  // Logging
  "gestvenv.logLevel": "info"
}
```

### Variables d'environnement

```bash
# Dans .env ou variables système
GESTVENV_API_ENDPOINT=http://localhost:8000
GESTVENV_CACHE_DIR=/custom/cache/path
GESTVENV_DEFAULT_BACKEND=uv
```

## Raccourcis clavier

| Action | Windows/Linux | macOS |
|--------|--------------|-------|
| Créer environnement | `Ctrl+Shift+G C` | `Cmd+Shift+G C` |
| Activer environnement | `Ctrl+Shift+G A` | `Cmd+Shift+G A` |
| Installer package | `Ctrl+Shift+G I` | `Cmd+Shift+G I` |
| Ouvrir explorateur | `Ctrl+Shift+G E` | `Cmd+Shift+G E` |
| Rafraîchir | `Ctrl+Shift+G R` | `Cmd+Shift+G R` |

## Troubleshooting

### L'extension ne se charge pas

1. **Vérifier les logs** :
   ```
   Affichage → Sortie → GestVenv
   ```

2. **Vérifier GestVenv CLI** :
   ```bash
   gestvenv --version
   # Doit afficher la version
   ```

3. **Recharger VS Code** :
   ```
   Ctrl+Shift+P → "Developer: Reload Window"
   ```

### IntelliSense ne fonctionne pas

1. **Vérifier l'API** :
   ```bash
   curl http://localhost:8000/api/health
   # Doit retourner {"status": "ok"}
   ```

2. **Vérifier l'environnement actif** :
   - Barre d'état doit montrer un environnement
   - Sinon, activer manuellement

3. **Effacer le cache** :
   ```
   Commande → "GestVenv: Clear Cache"
   ```

### Erreurs d'installation de packages

1. **Vérifier la connexion Internet**
2. **Vérifier les permissions** :
   ```bash
   # Linux/macOS
   ls -la ~/.local/share/gestvenv
   
   # Windows
   dir %LOCALAPPDATA%\gestvenv
   ```

3. **Essayer un backend différent** :
   ```
   Settings → gestvenv.preferredBackend → "pip"
   ```

### Performance lente

1. **Activer le cache** :
   ```json
   "gestvenv.cache.enable": true
   ```

2. **Réduire la fréquence de rafraîchissement** :
   ```json
   "gestvenv.refreshInterval": 60000
   ```

3. **Désactiver les fonctionnalités non utilisées** :
   ```json
   "gestvenv.diagnostics.enable": false
   ```

## Intégration avec d'autres extensions

### Python (Microsoft)
- Synchronisation automatique de l'interpréteur
- Partage des informations d'environnement

### Pylance
- IntelliSense enrichi combiné
- Type checking amélioré

### Jupyter
- Sélection de kernel automatique
- Packages data science pré-configurés

## Développement et contribution

### Structure du projet

```
extensions/vscode/
├── src/
│   ├── extension.ts      # Point d'entrée
│   ├── api/              # Client API
│   ├── providers/        # Providers VS Code
│   ├── views/            # UI components
│   ├── commands/         # Commandes
│   └── language/         # LSP
├── resources/            # Icônes et assets
├── test/                 # Tests
└── package.json          # Manifest
```

### Ajouter une nouvelle commande

```typescript
// src/commands/myCommand.ts
export async function myCommand(api: GestVenvAPI) {
    const result = await api.doSomething();
    vscode.window.showInformationMessage(`Result: ${result}`);
}

// src/extension.ts
commands.registerCommand('gestvenv.myCommand', 
    () => myCommand(api));
```

### Tests

```bash
# Tests unitaires
npm test

# Tests d'intégration
npm run test:integration

# Coverage
npm run test:coverage
```

## Prochaines fonctionnalités (Roadmap)

### Phase 3 : Temps réel et collaboration
- WebSocket pour synchronisation instantanée
- Notifications push des changements
- Partage d'environnements en équipe

### Phase 4 : Interface avancée
- Webview pour gestion visuelle des packages
- Graphique de dépendances interactif
- Statistiques d'utilisation

### Phase 5 : Intelligence artificielle
- Suggestions de packages basées sur le code
- Détection automatique des besoins
- Optimisation des dépendances

## Support et ressources

- **Documentation** : https://gestvenv.readthedocs.io
- **Issues** : https://github.com/gestvenv/gestvenv/issues
- **Discord** : https://discord.gg/gestvenv
- **Email** : support@gestvenv.io