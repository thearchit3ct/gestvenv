# Extension VS Code GestVenv

## Vue d'ensemble

L'extension VS Code GestVenv offre une intégration native complète avec IntelliSense amélioré, gestion visuelle des environnements, et diagnostics intelligents.

## Installation et Configuration

### Prérequis

1. **VS Code** version 1.85.0 ou supérieure
2. **GestVenv CLI** installé et accessible dans le PATH
3. **Python** 3.8 ou supérieur
4. **Node.js** 18+ (pour le développement uniquement)

### Installation de l'extension

#### Depuis le code source (développement)

```bash
# Cloner le repo
cd extensions/vscode

# Installer les dépendances
npm install

# Compiler l'extension
npm run compile

# Lancer VS Code en mode développement
code --extensionDevelopmentPath=.
```

#### Build pour distribution

```bash
# Installer vsce (VS Code Extension manager)
npm install -g @vscode/vsce

# Créer le package VSIX
cd extensions/vscode
vsce package

# Installer localement
code --install-extension gestvenv-vscode-0.1.0.vsix
```

### Configuration de l'API

L'extension nécessite l'API GestVenv pour les fonctionnalités avancées :

```bash
# Lancer l'API GestVenv
cd web
python -m uvicorn api.main:app --reload
```

### Paramètres de l'extension

Configurez l'extension dans VS Code (`settings.json`) :

```json
{
  // Activation générale
  "gestvenv.enable": true,
  
  // Détection automatique des environnements
  "gestvenv.autoDetect": true,
  
  // Affichage dans la barre d'état
  "gestvenv.showStatusBar": true,
  
  // IntelliSense amélioré
  "gestvenv.enableIntelliSense": true,
  
  // Endpoint de l'API
  "gestvenv.apiEndpoint": "http://localhost:8000",
  
  // Cache
  "gestvenv.cache.enable": true,
  "gestvenv.cache.ttl": 300,
  
  // Diagnostics
  "gestvenv.diagnostics.enable": true,
  "gestvenv.diagnostics.showMissingImports": true,
  
  // Complétion
  "gestvenv.completion.showPackageStats": true
}
```

## Fonctionnalités Implémentées

### Phase 1 : Foundation ✅

#### 1. Structure de base
- Extension TypeScript complète avec architecture modulaire
- Système de commandes extensible
- Configuration flexible

#### 2. API REST étendue
- Routes `/api/v1/ide/*` pour l'intégration
- Endpoints spécialisés pour packages, complétion, analyse
- Support des métadonnées complètes

#### 3. Détection et activation
- Détection automatique au démarrage
- Changement d'environnement depuis la barre d'état
- Support multi-workspace

#### 4. Vue arborescente
- Explorateur d'environnements dans la barre latérale
- Vue hiérarchique : Environnements → Détails/Packages/Actions
- Actions contextuelles sur chaque nœud

### Phase 2 : IntelliSense Core ✅

#### 1. Language Server Protocol
- Serveur LSP complet avec diagnostics
- Communication bidirectionnelle avec l'API
- Support des actions de code

#### 2. Provider de complétion
- Auto-complétion pour imports Python
- Suggestions contextuelles basées sur l'environnement actif
- Métadonnées enrichies (version, description, stats)

#### 3. Hover Provider
- Information au survol pour les packages
- Documentation inline
- Statistiques de téléchargement PyPI

#### 4. Cache intelligent
- Cache en mémoire avec TTL configurable
- Invalidation automatique sur changements
- Performance optimisée

## Utilisation

### Création d'environnement

1. **Palette de commandes** : `Ctrl+Shift+P` → "GestVenv: Create Environment"
2. **Explorateur** : Clic sur l'icône + dans la vue GestVenv
3. **Options** :
   - Nom de l'environnement
   - Backend (uv, pip, pdm, poetry)
   - Template optionnel (django, fastapi, etc.)

### Installation de packages

#### Méthode 1 : Commande
1. `Ctrl+Shift+P` → "GestVenv: Install Package"
2. Entrer le nom du package
3. Choisir les options (version, editable, etc.)

#### Méthode 2 : Quick Fix
1. Écrire `import requests` dans un fichier Python
2. VS Code souligne l'import manquant
3. `Ctrl+.` → "Install requests"

#### Méthode 3 : Explorateur
1. Clic droit sur un environnement
2. "Install Package"
3. Recherche et sélection

### IntelliSense amélioré

#### Auto-complétion des imports
```python
# Tapez "import " et VS Code suggère tous les packages installés
import |  # ← suggestions: requests, pandas, flask...

# Ou avec from
from flask import |  # ← suggestions: Flask, render_template...
```

#### Hover pour informations
```python
import requests  # ← Survolez pour voir version et description
```

### Barre d'état

La barre d'état affiche :
- Nom de l'environnement actif
- Version Python
- Nombre de packages
- Clic pour changer d'environnement

### Diagnostics

L'extension détecte automatiquement :
- Imports manquants avec quick fix
- Packages obsolètes
- Problèmes de dépendances

## Architecture Technique

### Structure des fichiers

```
extensions/vscode/
├── src/
│   ├── extension.ts          # Point d'entrée
│   ├── api/
│   │   └── gestvenvClient.ts # Client API REST
│   ├── providers/
│   │   ├── pythonProvider.ts # Complétion & Hover
│   │   ├── environmentProvider.ts
│   │   └── diagnosticProvider.ts
│   ├── views/
│   │   ├── environmentExplorer.ts
│   │   └── statusBar.ts
│   ├── commands/
│   │   └── index.ts         # Toutes les commandes
│   ├── language/
│   │   ├── client.ts        # Client LSP
│   │   └── server.ts        # Serveur LSP
│   └── cache/
│       └── completionCache.ts
├── package.json             # Manifest
├── tsconfig.json           # Config TypeScript
└── README.md
```

### Communication avec l'API

```typescript
// Exemple d'appel API
const packages = await api.getPackagesWithModules(envId);

// WebSocket pour temps réel (Phase 3)
const ws = new WebSocket('ws://localhost:8000/ws/ide/CLIENT_ID');
```

### Cache et Performance

- Cache LRU en mémoire pour les complétions
- TTL configurable (défaut 5 minutes)
- Invalidation sur changements d'environnement
- Requêtes parallèles pour les métadonnées

## Développement

### Ajout d'une nouvelle commande

```typescript
// src/commands/myCommand.ts
export async function myCommand(api: GestVenvAPI) {
    // Implémentation
}

// src/commands/index.ts
context.subscriptions.push(
    vscode.commands.registerCommand('gestvenv.myCommand', () => {
        myCommand(api);
    })
);
```

### Ajout d'un provider

```typescript
// src/providers/myProvider.ts
export class MyProvider implements vscode.SomeProvider {
    // Implémentation
}

// src/extension.ts
const provider = new MyProvider(api);
context.subscriptions.push(
    vscode.languages.registerSomeProvider(selector, provider)
);
```

### Tests

```bash
# Tests unitaires
npm test

# Tests d'intégration
npm run test:integration

# Lancer en mode debug
F5 dans VS Code
```

## Troubleshooting

### L'extension ne détecte pas les environnements

1. Vérifier que GestVenv CLI est installé :
   ```bash
   gestvenv --version
   ```

2. Vérifier l'API est accessible :
   ```bash
   curl http://localhost:8000/api/health
   ```

3. Recharger la fenêtre VS Code :
   `Ctrl+Shift+P` → "Developer: Reload Window"

### IntelliSense ne fonctionne pas

1. Vérifier les paramètres :
   ```json
   "gestvenv.enableIntelliSense": true
   ```

2. Vérifier qu'un environnement est actif (barre d'état)

3. Voir les logs :
   `Ctrl+Shift+U` → "Output" → "GestVenv"

### Erreurs de l'API

1. Vérifier que l'API est lancée
2. Vérifier l'endpoint dans les paramètres
3. Voir les logs de l'API pour plus de détails

## Prochaines étapes (Phases 3-5)

### Phase 3 : Features avancées
- WebSocket pour synchronisation temps réel
- Code actions avancées
- Refactoring assisté

### Phase 4 : UI/UX
- Vue webview pour gestion des packages
- Graphiques de dépendances
- Terminal intégré

### Phase 5 : Performance
- Workers pour opérations lourdes
- Streaming des résultats
- Pré-chargement intelligent