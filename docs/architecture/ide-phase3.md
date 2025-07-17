# Phase 3 : Fonctionnalités avancées IDE VS Code

## Vue d'ensemble

La phase 3 de l'intégration IDE VS Code apporte des fonctionnalités avancées pour une expérience de développement améliorée avec synchronisation temps réel, refactoring assisté et code actions intelligentes.

## Fonctionnalités implémentées

### 1. WebSocket pour synchronisation temps réel

#### Architecture WebSocket

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│  VS Code Client │ ◄─────────────────────────► │  FastAPI Server │
└─────────────────┘                             └─────────────────┘
        │                                                │
        ├── Subscribe to environments                    ├── Broadcast changes
        ├── Receive real-time updates                    ├── Manage connections
        └── Execute async operations                     └── Handle operations
```

#### Composants implémentés

1. **WebSocket Manager (Backend)**
   - Gestion des connexions multiples
   - Système de souscription par environnement
   - Broadcasting ciblé ou global
   - Gestion automatique des déconnexions

2. **WebSocket Client (VS Code)**
   - Reconnexion automatique
   - File d'attente des messages
   - Gestion des événements typés
   - Heartbeat pour maintenir la connexion

3. **Types d'événements supportés**
   - `environment:*` - Changements d'environnements
   - `package:*` - Installation/désinstallation de packages
   - `operation:*` - Progression des opérations longues
   - `diagnostics:updated` - Mise à jour des diagnostics
   - `refactoring:available` - Suggestions de refactoring

### 2. Code Actions avancées

#### Types de code actions

1. **Quick Fixes**
   - Installation automatique de packages manquants
   - Mise à jour de packages obsolètes
   - Correction d'imports incorrects

2. **Refactoring Actions**
   - Extract Variable
   - Extract Function
   - Inline Variable
   - Organize Imports
   - Convert to F-String

3. **Source Actions**
   - Organize Imports
   - Sort Imports
   - Remove Unused Imports

#### Implémentation

```typescript
// Exemple de code action pour installer un package manquant
const action = new vscode.CodeAction(
    `Install '${packageName}'`,
    vscode.CodeActionKind.QuickFix
);
action.command = {
    command: 'gestvenv.installPackage',
    arguments: [environment, packageName]
};
```

### 3. Refactoring assisté

#### Extract Variable

Permet d'extraire une expression sélectionnée dans une variable :

```python
# Avant
result = calculate_price(items) * tax_rate * (1 - discount)

# Après extraction
price = calculate_price(items)
discounted_price = price * (1 - discount)
result = discounted_price * tax_rate
```

#### Extract Function

Extrait du code sélectionné dans une nouvelle fonction :

```python
# Avant
# Code sélectionné
total = 0
for item in items:
    total += item.price * item.quantity

# Après extraction
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    return total

total = calculate_total(items)
```

#### Organize Imports

Organise automatiquement les imports selon PEP 8 :

```python
# Avant
from mymodule import func
import sys
from django.db import models
import os

# Après
import os
import sys

from django.db import models

from mymodule import func
```

## Communication temps réel

### Flux de messages WebSocket

1. **Connexion initiale**
   ```json
   {
     "type": "connection",
     "client_id": "vscode_xxx",
     "metadata": {
       "vscode_version": "1.85.0",
       "extension_version": "0.1.0"
     }
   }
   ```

2. **Souscription à un environnement**
   ```json
   {
     "type": "subscribe",
     "environment_id": "env_123"
   }
   ```

3. **Notification de changement**
   ```json
   {
     "type": "package:installed",
     "timestamp": "2024-01-17T10:30:00Z",
     "data": {
       "environment_id": "env_123",
       "package": "requests",
       "version": "2.31.0"
     }
   }
   ```

### Gestion des opérations asynchrones

Les opérations longues (installation de packages, etc.) utilisent un système de tâches :

```typescript
// Lancement d'une installation
webSocketClient.send({
    type: 'package:install',
    data: {
        environment_id: envId,
        package_name: 'numpy'
    }
});

// Réception des mises à jour
webSocketClient.on('task:progress', (message) => {
    updateProgressBar(message.data.progress);
});
```

## Intégration avec l'extension

### Configuration ajoutée

```json
{
  "gestvenv.enableWebSocket": true,
  "gestvenv.refactoring.extractVariable": true,
  "gestvenv.refactoring.extractFunction": true,
  "gestvenv.refactoring.organizeImports": true
}
```

### Commandes ajoutées

- `gestvenv.extractVariable` - Extraire la sélection dans une variable
- `gestvenv.extractFunction` - Extraire la sélection dans une fonction
- `gestvenv.organizeImports` - Organiser les imports
- `gestvenv.addMissingImport` - Ajouter un import manquant
- `gestvenv.inlineVariable` - Inliner une variable
- `gestvenv.convertToFString` - Convertir en f-string

## Performance et optimisations

### WebSocket

- Reconnexion automatique avec backoff exponentiel
- File d'attente pour les messages hors ligne
- Compression des messages volumineux
- Heartbeat toutes les 30 secondes

### Code Actions

- Cache des suggestions d'import
- Analyse incrémentale du code
- Debouncing des requêtes d'analyse

## Sécurité

- Validation de tous les messages WebSocket
- Authentification par client ID unique
- Timeout sur les opérations longues
- Sanitization des entrées utilisateur

## Prochaines étapes (Phases 4-5)

### Phase 4 : Interface utilisateur avancée
- Webview pour gestion visuelle des packages
- Graphique de dépendances interactif
- Terminal intégré avec environnement activé

### Phase 5 : Intelligence et performance
- Suggestions ML de packages basées sur le code
- Pré-chargement intelligent des métadonnées
- Workers pour opérations CPU-intensives