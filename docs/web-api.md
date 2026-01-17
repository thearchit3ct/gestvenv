# API Web GestVenv

L'API Web GestVenv fournit une interface REST complète et WebSocket pour gérer les environnements virtuels Python à distance ou via des interfaces web.

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Installation et démarrage](#installation-et-démarrage)
3. [API REST](#api-rest)
4. [WebSocket](#websocket)
5. [Authentication](#authentication)
6. [Interface Web](#interface-web)
7. [Architecture](#architecture)
8. [Développement](#développement)

## Vue d'ensemble

### Fonctionnalités principales

- **API REST complète** : CRUD pour environnements, packages, cache
- **WebSocket temps réel** : Notifications et synchronisation
- **Interface Vue 3** : Dashboard moderne avec Tailwind CSS
- **OpenAPI/Swagger** : Documentation interactive
- **CORS configuré** : Pour intégrations cross-origin
- **Async/await** : Performance optimale avec FastAPI

### Stack technique

- **Backend** : FastAPI, Pydantic, SQLAlchemy
- **Frontend** : Vue 3, TypeScript, Tailwind CSS, Vite
- **WebSocket** : Native FastAPI WebSocket
- **Documentation** : OpenAPI 3.0, Swagger UI

## Installation et démarrage

### Prérequis

- Python 3.9+
- Node.js 16+ (pour l'interface web)
- GestVenv 2.0+ installé

### Installation

```bash
# Backend API
cd web/api
pip install -r requirements.txt

# Frontend (optionnel)
cd web/web-ui
npm install
```

### Démarrage

```bash
# Mode développement avec auto-reload
cd web
./start-dev.sh

# Ou manuellement
# Terminal 1 - API
cd web/api
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd web/web-ui
npm run dev
```

### Configuration

```python
# web/api/core/config.py
class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "GestVenv API"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    
    # WebSocket
    WS_MESSAGE_QUEUE_SIZE: int = 1000
    WS_HEARTBEAT_INTERVAL: int = 30
    
    # Performance
    MAX_CONCURRENT_OPERATIONS: int = 50
    CACHE_TTL: int = 3600
```

## API REST

### Base URL

```
http://localhost:8000/api/v1
```

### Endpoints principaux

#### Environnements

```http
# Lister tous les environnements
GET /environments

# Créer un environnement
POST /environments
{
    "name": "my-project",
    "python_version": "3.11",
    "backend": "uv",
    "packages": ["django", "requests"]
}

# Détails d'un environnement
GET /environments/{env_id}

# Mettre à jour
PUT /environments/{env_id}

# Supprimer
DELETE /environments/{env_id}

# Activer un environnement
POST /environments/{env_id}/activate
```

#### Packages

```http
# Lister les packages d'un environnement
GET /environments/{env_id}/packages

# Installer des packages
POST /environments/{env_id}/packages
{
    "packages": ["pandas", "numpy"],
    "upgrade": false
}

# Désinstaller un package
DELETE /environments/{env_id}/packages/{package_name}

# Mettre à jour des packages
PUT /environments/{env_id}/packages
{
    "packages": ["django"],
    "to_version": "4.2.0"
}
```

#### Cache

```http
# Informations du cache
GET /cache

# Nettoyer le cache
DELETE /cache

# Ajouter au cache
POST /cache/packages
{
    "packages": ["requests", "django"],
    "python_version": "3.11"
}

# Exporter le cache
GET /cache/export?format=tar.gz

# Importer un cache
POST /cache/import
```

#### Environnements éphémères

```http
# Créer un environnement éphémère
POST /ephemeral/environments
{
    "name": "test-env",
    "ttl": 3600,
    "packages": ["pytest"],
    "isolation_level": "process"
}

# Lister les environnements éphémères
GET /ephemeral/environments

# Statistiques
GET /ephemeral/stats

# Cleanup
DELETE /ephemeral/environments/{env_id}
DELETE /ephemeral/cleanup-all
```

#### Opérations

```http
# Lister les opérations en cours
GET /operations

# Détails d'une opération
GET /operations/{operation_id}

# Annuler une opération
DELETE /operations/{operation_id}
```

#### Système

```http
# Santé de l'API
GET /health

# Informations système
GET /system/info

# Diagnostics
GET /system/diagnostics

# Backends disponibles
GET /system/backends
```

### Exemples d'utilisation

#### cURL

```bash
# Créer un environnement
curl -X POST http://localhost:8000/api/v1/environments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-api-project",
    "python_version": "3.11",
    "backend": "uv"
  }'

# Installer des packages
curl -X POST http://localhost:8000/api/v1/environments/my-api-project/packages \
  -H "Content-Type: application/json" \
  -d '{
    "packages": ["fastapi", "uvicorn", "sqlalchemy"]
  }'

# Streaming des logs d'installation
curl -N http://localhost:8000/api/v1/operations/abc123/stream
```

#### Python

```python
import requests
import json

# Client API simple
class GestVenvAPI:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def create_environment(self, name, python_version="3.11", backend="uv"):
        response = self.session.post(
            f"{self.base_url}/environments",
            json={
                "name": name,
                "python_version": python_version,
                "backend": backend
            }
        )
        return response.json()
    
    def install_packages(self, env_id, packages):
        response = self.session.post(
            f"{self.base_url}/environments/{env_id}/packages",
            json={"packages": packages}
        )
        return response.json()

# Utilisation
api = GestVenvAPI()
env = api.create_environment("test-project")
result = api.install_packages(env["id"], ["requests", "pandas"])
```

#### JavaScript/TypeScript

```typescript
// Client TypeScript avec types
interface Environment {
    id: string;
    name: string;
    python_version: string;
    backend: string;
    created_at: string;
    packages: Package[];
}

interface Package {
    name: string;
    version: string;
    installed_at: string;
}

class GestVenvClient {
    private baseUrl: string = 'http://localhost:8000/api/v1';
    
    async createEnvironment(config: {
        name: string;
        python_version?: string;
        backend?: string;
    }): Promise<Environment> {
        const response = await fetch(`${this.baseUrl}/environments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        return response.json();
    }
    
    async installPackages(
        envId: string, 
        packages: string[]
    ): Promise<Operation> {
        const response = await fetch(
            `${this.baseUrl}/environments/${envId}/packages`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ packages })
            }
        );
        return response.json();
    }
}
```

## WebSocket

### Connexion

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    console.log('Connected to GestVenv WebSocket');
    
    // S'abonner à un environnement
    ws.send(JSON.stringify({
        type: 'subscribe',
        environment_id: 'my-project'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Event:', data.type, data);
};
```

### Types de messages

#### Messages sortants (client → serveur)

```typescript
// Abonnement
{
    type: 'subscribe',
    environment_id: string
}

// Désabonnement
{
    type: 'unsubscribe',
    environment_id: string
}

// Ping
{
    type: 'ping'
}

// Commandes
{
    type: 'environment:refresh',
    environment_id: string
}

{
    type: 'package:install',
    environment_id: string,
    package_name: string,
    version?: string
}
```

#### Messages entrants (serveur → client)

```typescript
// Événements d'environnement
{
    type: 'environment:created',
    data: {
        environment: Environment
    }
}

{
    type: 'environment:updated',
    data: {
        environment: Environment,
        changes: string[]
    }
}

{
    type: 'environment:deleted',
    data: {
        environment_id: string
    }
}

// Événements de packages
{
    type: 'package:installed',
    data: {
        environment_id: string,
        package: Package
    }
}

{
    type: 'package:uninstalled',
    data: {
        environment_id: string,
        package_name: string
    }
}

// Événements d'opération
{
    type: 'operation:started',
    data: {
        operation_id: string,
        type: string,
        environment_id: string
    }
}

{
    type: 'operation:progress',
    data: {
        operation_id: string,
        progress: number,
        message: string
    }
}

{
    type: 'operation:completed',
    data: {
        operation_id: string,
        result: any,
        duration: number
    }
}

{
    type: 'operation:failed',
    data: {
        operation_id: string,
        error: string
    }
}
```

### Exemple complet

```javascript
class GestVenvWebSocket {
    constructor(url = 'ws://localhost:8000/ws') {
        this.url = url;
        this.ws = null;
        this.handlers = new Map();
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectDelay = 1000;
            this.emit('connected');
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.emit(message.type, message.data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.emit('disconnected');
            this.reconnect();
        };
    }
    
    reconnect() {
        setTimeout(() => {
            console.log('Reconnecting...');
            this.connect();
            this.reconnectDelay = Math.min(
                this.reconnectDelay * 2, 
                this.maxReconnectDelay
            );
        }, this.reconnectDelay);
    }
    
    send(message) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }
    
    on(event, handler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, []);
        }
        this.handlers.get(event).push(handler);
    }
    
    emit(event, data) {
        const handlers = this.handlers.get(event) || [];
        handlers.forEach(handler => handler(data));
    }
    
    subscribe(environmentId) {
        this.send({
            type: 'subscribe',
            environment_id: environmentId
        });
    }
}

// Utilisation
const ws = new GestVenvWebSocket();
ws.connect();

ws.on('connected', () => {
    ws.subscribe('my-project');
});

ws.on('package:installed', (data) => {
    console.log(`Package ${data.package.name} installed!`);
});
```

## Authentication

### Configuration

```python
# Activer l'authentification (optionnel)
ENABLE_AUTH: bool = False
SECRET_KEY: str = "your-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
```

### JWT Token

```http
# Login
POST /auth/login
{
    "username": "admin",
    "password": "secret"
}

Response:
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer"
}

# Utilisation du token
GET /api/v1/environments
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## Interface Web

### Dashboard

L'interface web Vue 3 est disponible sur `http://localhost:5173` et offre :

- **Vue d'ensemble** : Statistiques et métriques
- **Gestion des environnements** : Création, suppression, activation
- **Gestion des packages** : Installation, mise à jour, recherche
- **Cache** : Visualisation et gestion
- **Opérations** : Suivi en temps réel
- **Système** : Diagnostics et informations

### Components principaux

```vue
<!-- EnvironmentCard.vue -->
<template>
  <div class="card">
    <div class="card-header">
      <h3>{{ environment.name }}</h3>
      <span class="badge">{{ environment.backend }}</span>
    </div>
    <div class="card-body">
      <p>Python {{ environment.python_version }}</p>
      <p>{{ environment.packages.length }} packages</p>
    </div>
    <div class="card-footer">
      <button @click="activate">Activer</button>
      <button @click="openDetails">Détails</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'
import type { Environment } from '@/types'

const props = defineProps<{
  environment: Environment
}>()

const activate = () => {
  // Activation logic
}

const openDetails = () => {
  // Navigation logic
}
</script>
```

## Architecture

### Structure backend

```
web/api/
├── main.py                 # Application FastAPI
├── core/
│   ├── config.py          # Configuration
│   └── exceptions.py      # Exceptions personnalisées
├── models/
│   ├── schemas.py         # Schémas Pydantic
│   └── database.py        # Modèles SQLAlchemy
├── routes/
│   ├── environments.py    # Routes environnements
│   ├── packages.py        # Routes packages
│   ├── cache.py          # Routes cache
│   └── system.py         # Routes système
├── services/
│   ├── gestvenv_service.py  # Interface avec GestVenv
│   └── operation_service.py  # Gestion des opérations
└── websocket/
    ├── manager.py         # Gestionnaire WebSocket
    └── handlers.py        # Handlers de messages
```

### Structure frontend

```
web/web-ui/
├── src/
│   ├── App.vue           # Composant racine
│   ├── router/           # Vue Router
│   ├── stores/           # Pinia stores
│   ├── views/            # Pages
│   ├── components/       # Composants réutilisables
│   ├── composables/      # Composition API
│   ├── api/             # Client API
│   └── types/           # Types TypeScript
├── public/              # Assets statiques
└── index.html          # Point d'entrée
```

### Flow de données

```mermaid
graph TD
    A[Client Web] --> B[API REST]
    A --> C[WebSocket]
    B --> D[FastAPI]
    C --> D
    D --> E[GestVenv Core]
    E --> F[File System]
    E --> G[Backends]
    D --> H[Cache Redis/Memory]
    D --> I[Database SQLite]
```

## Développement

### Setup développement

```bash
# Backend
cd web/api
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements-dev.txt

# Frontend
cd web/web-ui
npm install
```

### Tests

```bash
# Backend tests
cd web/api
pytest
pytest --cov=.

# Frontend tests
cd web/web-ui
npm run test
npm run test:e2e
```

### Linting

```bash
# Backend
black .
isort .
flake8
mypy .

# Frontend
npm run lint
npm run type-check
```

### Build production

```bash
# Backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
npm run build
# Servir dist/ avec nginx ou autre
```

### Docker

```dockerfile
# Dockerfile backend
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# Dockerfile frontend
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: ./web/api
    ports:
      - "8000:8000"
    environment:
      - GESTVENV_HOME=/data/gestvenv
    volumes:
      - gestvenv-data:/data/gestvenv
      
  web:
    build: ./web/web-ui
    ports:
      - "80:80"
    depends_on:
      - api
      
volumes:
  gestvenv-data:
```

## Sécurité

### CORS

```python
# Configuration CORS stricte
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/environments")
@limiter.limit("10/minute")
async def create_environment(request: Request):
    # ...
```

### Validation

```python
# Validation stricte avec Pydantic
class EnvironmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, regex="^[a-zA-Z0-9_-]+$")
    python_version: str = Field(..., regex="^3\.(9|10|11|12)$")
    backend: Literal["pip", "uv", "poetry", "pdm"]
    packages: List[str] = Field(default_factory=list, max_items=1000)
```

## Monitoring

### Métriques Prometheus

```python
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('gestvenv_api_requests_total', 'Total requests')
request_duration = Histogram('gestvenv_api_request_duration_seconds', 'Request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Logging structuré

```python
import structlog

logger = structlog.get_logger()

@app.post("/api/v1/environments/{env_id}/packages")
async def install_packages(env_id: str, packages: List[str]):
    logger.info(
        "package_installation_started",
        environment_id=env_id,
        packages=packages,
        user_id=current_user.id
    )
    # ...
```

## Changelog

### v2.0.0 (2024-07-17)
- API REST complète avec FastAPI
- WebSocket pour événements temps réel
- Interface web Vue 3 moderne
- Support des environnements éphémères
- Documentation OpenAPI/Swagger

### Roadmap v2.1
- GraphQL API
- Webhooks configurables
- Multi-tenancy
- Métriques avancées
- Export Terraform/Ansible