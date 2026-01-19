# Guide d'Installation - Interface Web GestVenv

Ce guide détaille l'installation et la configuration de l'interface web de GestVenv.

## Prérequis

### Backend (API)
- Python 3.9+
- pip ou uv
- GestVenv installé

### Frontend (Web UI)
- Node.js 18+
- npm ou pnpm

### Production (optionnel)
- Docker et Docker Compose
- PostgreSQL (recommandé)
- Nginx (reverse proxy)

---

## Installation Rapide (Développement)

### 1. Cloner le projet

```bash
git clone https://github.com/gestvenv/gestvenv.git
cd gestvenv
```

### 2. Installer les dépendances Python

```bash
# Avec pip
pip install -e .[full]

# Avec uv (recommandé)
uv pip install -e .[full]
```

### 3. Installer les dépendances Frontend

```bash
cd web/web-ui
npm install
```

### 4. Démarrer les serveurs

```bash
# Terminal 1 - Backend API
cd web/api
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd web/web-ui
npm run dev
```

### 5. Accéder à l'interface

Ouvrir http://localhost:3001 (ou le port affiché dans le terminal)

---

## Configuration

### Backend (API)

Créer un fichier `.env` dans `web/api/` :

```env
# Base de données
DATABASE_URL=sqlite:///./gestvenv.db
# ou PostgreSQL pour production
# DATABASE_URL=postgresql://user:password@localhost:5432/gestvenv

# Sécurité
SECRET_KEY=your-secret-key-here
JWT_ENABLED=false
CORS_ORIGINS=http://localhost:3001,http://localhost:5173

# GestVenv
GESTVENV_BASE_PATH=~/.gestvenv
CACHE_ENABLED=true

# WebSocket
WS_ENABLED=true
```

### Frontend (Web UI)

Le frontend utilise Vite avec proxy automatique vers le backend.

Configuration dans `web/web-ui/vite.config.ts` :

```typescript
export default defineConfig({
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

---

## Structure du Projet Web

```
web/
├── api/                    # Backend FastAPI
│   ├── main.py            # Point d'entrée
│   ├── routes/            # Endpoints API
│   │   ├── environments.py
│   │   ├── packages.py
│   │   ├── cache.py
│   │   ├── system.py
│   │   └── templates.py
│   ├── services/          # Logique métier
│   ├── models/            # Schémas Pydantic
│   └── websocket.py       # Gestion WebSocket
│
└── web-ui/                # Frontend Vue 3
    ├── src/
    │   ├── components/    # Composants Vue
    │   │   ├── PackageCard.vue
    │   │   ├── EnvironmentCard.vue
    │   │   └── ...
    │   ├── views/         # Pages
    │   │   ├── Dashboard.vue
    │   │   ├── Environments.vue
    │   │   ├── Packages.vue
    │   │   ├── Cache.vue
    │   │   ├── System.vue
    │   │   ├── Templates.vue
    │   │   ├── Operations.vue
    │   │   └── Settings.vue
    │   ├── stores/        # Pinia stores
    │   │   ├── environments.ts
    │   │   ├── packages.ts
    │   │   └── system.ts
    │   ├── services/      # API clients
    │   │   ├── api.ts
    │   │   └── websocket.ts
    │   ├── router/        # Vue Router
    │   ├── style.css      # Styles Tailwind
    │   └── main.ts        # Bootstrap
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── vite.config.ts
    └── package.json
```

---

## Déploiement Production

### Option 1 : Docker Compose (Recommandé)

#### docker-compose.yml

```yaml
version: '3.8'

services:
  # Base de données PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: gestvenv
      POSTGRES_USER: gestvenv
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gestvenv"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend API
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      DATABASE_URL: postgresql://gestvenv:${DB_PASSWORD}@postgres:5432/gestvenv
      SECRET_KEY: ${SECRET_KEY}
      CORS_ORIGINS: ${CORS_ORIGINS}
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"

  # Frontend (build statique servi par Nginx)
  frontend:
    build:
      context: ./web/web-ui
      dockerfile: Dockerfile
    depends_on:
      - api

  # Reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
      - frontend

volumes:
  postgres_data:
```

#### Dockerfile.api

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY web/api/ .
COPY gestvenv/ /app/gestvenv/

# Utilisateur non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### web/web-ui/Dockerfile

```dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### Déploiement

```bash
# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# Construire et démarrer
docker-compose up -d --build

# Vérifier les logs
docker-compose logs -f

# Arrêter
docker-compose down
```

### Option 2 : Déploiement Manuel

#### Backend

```bash
# Installation des dépendances
pip install gestvenv[full] uvicorn gunicorn

# Démarrage avec Gunicorn
cd web/api
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

#### Frontend

```bash
# Build de production
cd web/web-ui
npm run build

# Les fichiers statiques sont dans dist/
# Servir avec Nginx, Apache, ou un CDN
```

#### Nginx Configuration

```nginx
server {
    listen 80;
    server_name gestvenv.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name gestvenv.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Frontend statique
    location / {
        root /var/www/gestvenv;
        try_files $uri $uri/ /index.html;
    }

    # API Backend
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Troubleshooting

### Problèmes Courants

#### 1. Styles CSS non appliqués

**Symptôme** : Interface sans styles, éléments mal positionnés

**Solution** :
```bash
cd web/web-ui

# Vérifier que postcss.config.js existe
cat postcss.config.js

# Si manquant, créer :
echo 'export default { plugins: { tailwindcss: {}, autoprefixer: {} } }' > postcss.config.js

# Installer les plugins Tailwind
npm install -D @tailwindcss/forms @tailwindcss/typography

# Redémarrer le serveur
npm run dev
```

#### 2. Erreur de connexion API

**Symptôme** : Erreurs 500 ou "Failed to fetch"

**Solution** :
- Vérifier que le backend est démarré sur le port 8000
- Vérifier la configuration proxy dans vite.config.ts
- Vérifier les logs du backend

#### 3. WebSocket ne se connecte pas

**Symptôme** : Message "Reconnexion..." permanent

**Solution** :
- Le WebSocket nécessite le backend actif
- En mode développement, c'est normal si le backend n'est pas lancé
- L'interface fonctionne en mode dégradé sans WebSocket

#### 4. Erreur "Component not found"

**Symptôme** : Warnings Vue "[Vue warn]: Failed to resolve component"

**Solution** :
- Les composants utilisent des classes CSS natives
- Pas besoin de bibliothèque de composants externe
- Vérifier les imports dans le fichier concerné

---

## Commandes Utiles

```bash
# Développement
npm run dev          # Serveur de développement
npm run build        # Build production
npm run preview      # Prévisualiser le build

# Qualité
npm run lint         # Linting ESLint
npm run type-check   # Vérification TypeScript
npm run format       # Formatage Prettier

# Tests
npm run test:unit    # Tests unitaires Vitest
npm run test:e2e     # Tests E2E Cypress
```

---

## Ressources

- [Vue 3 Documentation](https://vuejs.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vite](https://vitejs.dev/)
- [Pinia](https://pinia.vuejs.org/)
