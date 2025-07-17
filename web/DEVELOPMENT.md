# 🛠️ Guide de Développement GestVenv Web Interface

## 🚀 Démarrage Rapide - Développement Local

### Option 1 : Script automatique (Recommandé)

```bash
# 1. Aller dans le répertoire web
cd gestvenv/web

# 2. Configuration initiale (première fois seulement)
./start-dev.sh setup

# 3. Démarrer les services
./start-dev.sh both

# L'interface sera disponible sur :
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
# - API Docs: http://localhost:8000/api/docs
```

### Option 2 : Démarrage manuel

#### Backend FastAPI

```bash
# 1. Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Créer les répertoires
mkdir -p data logs

# 4. Démarrer le backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Vue.js (dans un autre terminal)

```bash
# 1. Aller dans le répertoire frontend
cd web-ui

# 2. Installer les dépendances
npm install

# 3. Démarrer le serveur de développement
npm run dev
```

## 📋 Commandes Utiles

### Script de développement

```bash
# Vérifier les prérequis
./start-dev.sh check

# Configuration complète
./start-dev.sh setup

# Démarrer backend seulement
./start-dev.sh backend

# Démarrer frontend seulement
./start-dev.sh frontend

# Démarrer les deux services
./start-dev.sh both

# Aide
./start-dev.sh help
```

### Backend

```bash
# Dans le répertoire web/
source venv/bin/activate

# Démarrage avec auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Avec logs debug
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Tests
pytest api/tests/

# Linting
black api/
isort api/
mypy api/
```

### Frontend

```bash
# Dans le répertoire web-ui/

# Développement avec hot-reload
npm run dev

# Build de production
npm run build

# Aperçu du build
npm run preview

# Type checking
npm run type-check

# Linting
npm run lint

# Formatage
npm run format
```

## 🔧 Configuration

### Variables d'environnement

Le fichier `.env` a été créé automatiquement avec les valeurs de développement :

```bash
DEBUG=true
HOST=0.0.0.0
PORT=8000
GESTVENV_CLI_PATH=gestvenv
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
DATABASE_URL=sqlite:///./data/gestvenv_web.db
```

### Configuration frontend (vite.config.ts)

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    },
    '/ws': {
      target: 'ws://localhost:8000',
      ws: true,
      changeOrigin: true
    }
  }
}
```

## 🐛 Debugging

### Backend

1. **Logs détaillés** : Définir `LOG_LEVEL=DEBUG` dans `.env`
2. **Debugger Python** : Ajouter des breakpoints avec `import pdb; pdb.set_trace()`
3. **API Interactive** : Utiliser http://localhost:8000/api/docs

### Frontend

1. **Vue DevTools** : Installer l'extension navigateur
2. **Console navigateur** : Logs automatiques des erreurs API/WebSocket
3. **Network tab** : Vérifier les appels API

### WebSocket

```javascript
// Test de connexion WebSocket dans la console
const ws = new WebSocket('ws://localhost:8000/ws')
ws.onopen = () => console.log('WebSocket connecté')
ws.onmessage = (event) => console.log('Message reçu:', event.data)
```

## 📁 Structure de Développement

```
web/
├── api/                    # Backend FastAPI
│   ├── main.py            # Point d'entrée
│   ├── core/
│   │   └── config.py      # Configuration
│   ├── routes/            # Endpoints REST
│   ├── services/          # Services métier
│   ├── models/            # Schémas Pydantic
│   └── websocket.py       # WebSocket
├── web-ui/                # Frontend Vue.js
│   ├── src/
│   │   ├── components/    # Composants Vue
│   │   ├── views/         # Pages
│   │   ├── stores/        # State Pinia
│   │   ├── services/      # API client
│   │   └── types/         # Types TypeScript
│   ├── package.json
│   └── vite.config.ts
├── data/                  # Base de données SQLite
├── logs/                  # Logs de l'application
├── venv/                  # Environnement virtuel Python
├── .env                   # Configuration locale
└── start-dev.sh          # Script de démarrage
```

## 🔄 Workflow de Développement

### 1. Ajouter une nouvelle fonctionnalité

#### Backend
```bash
# 1. Ajouter le modèle Pydantic dans api/models/schemas.py
# 2. Créer le service dans api/services/
# 3. Ajouter les routes dans api/routes/
# 4. Tester avec http://localhost:8000/api/docs
```

#### Frontend
```bash
# 1. Ajouter les types dans src/types/index.ts
# 2. Mettre à jour le service API dans src/services/api.ts
# 3. Créer/modifier les composants dans src/components/
# 4. Mettre à jour les stores Pinia si nécessaire
```

### 2. Hot Reload

- **Backend** : uvicorn avec `--reload` recharge automatiquement
- **Frontend** : Vite avec hot-reload intégré
- **Styles** : Tailwind recompile automatiquement

### 3. Tests

```bash
# Backend
pytest api/tests/ -v

# Frontend
npm run test

# E2E (si configuré)
npm run test:e2e
```

## 🚨 Problèmes Courants

### 1. Backend ne démarre pas

```bash
# Vérifier que GestVenv CLI est installé
gestvenv --version

# Réinstaller si nécessaire
cd ..
pip install -e .
cd web
```

### 2. Frontend ne trouve pas l'API

```bash
# Vérifier que le backend est démarré sur le port 8000
curl http://localhost:8000/api/health

# Vérifier la configuration proxy dans vite.config.ts
```

### 3. WebSocket ne se connecte pas

```bash
# Vérifier la connexion WebSocket
curl -H "Upgrade: websocket" -H "Connection: Upgrade" http://localhost:8000/ws
```

### 4. Erreurs de dépendances

```bash
# Backend
pip install -r requirements.txt --upgrade

# Frontend
rm -rf node_modules package-lock.json
npm install
```

## 📊 Monitoring en Développement

### Logs en temps réel

```bash
# Backend logs
tail -f logs/app.log

# Frontend logs (dans le navigateur)
# Ouvrir les DevTools > Console
```

### Métriques

- **API Performance** : http://localhost:8000/api/docs (temps de réponse)
- **WebSocket** : Compteur de connexions dans les logs
- **Frontend** : Vue DevTools pour les stores et composants

## 🔧 Outils Recommandés

### Éditeurs
- **VSCode** avec extensions Vue.js, Python, Tailwind CSS
- **PyCharm** pour développement Python avancé

### Extensions VSCode
- Vue Language Features (Volar)
- Python
- Tailwind CSS IntelliSense
- Thunder Client (test API)

### Outils CLI
```bash
# Installation globale d'outils utiles
npm install -g @vue/cli vue-tsc typescript
pip install black isort mypy pytest httpx
```

Avec cette configuration, vous avez un environnement de développement complet pour GestVenv Web Interface ! 🚀

## 🐳 Docker pour Production

Docker est disponible comme alternative pour le déploiement en production :

```bash
# Build et déploiement Docker
docker-compose up -d

# Avec services additionnels (PostgreSQL, Redis, Nginx)
docker-compose --profile postgres --profile redis --profile nginx up -d
```

### Avantages du développement local :
- ✅ Hot-reload plus rapide
- ✅ Debugging plus facile
- ✅ Accès direct aux logs
- ✅ Pas de overhead de container
- ✅ Configuration plus flexible

### Avantages de Docker :
- ✅ Environnement isolé
- ✅ Déploiement reproductible
- ✅ Gestion des dépendances simplifiée
- ✅ Idéal pour production