# Multi-stage Dockerfile pour GestVenv Web Interface

# Stage 1: Build du frontend Vue.js
FROM node:18-alpine as frontend-builder

WORKDIR /app/web-ui

# Copier les fichiers de configuration
COPY web-ui/package*.json ./
COPY web-ui/tsconfig.json ./
COPY web-ui/vite.config.ts ./
COPY web-ui/tailwind.config.js ./

# Installer les dépendances
RUN npm ci --only=production

# Copier le code source
COPY web-ui/src ./src
COPY web-ui/public ./public
COPY web-ui/index.html ./
COPY web-ui/env.d.ts ./

# Build de production
RUN npm run build

# Stage 2: Setup Python et FastAPI
FROM python:3.11-slim as backend

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN groupadd -r gestvenv && useradd -r -g gestvenv gestvenv

# Créer les répertoires de travail
RUN mkdir -p /app /app/logs /home/gestvenv && \
    chown -R gestvenv:gestvenv /app /home/gestvenv

WORKDIR /app

# Copier les requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'API
COPY api ./api

# Copier le frontend buildé depuis le stage précédent
COPY --from=frontend-builder /app/web-ui/dist ./web-ui/dist

# Créer les répertoires nécessaires
RUN mkdir -p /app/data /app/logs

# Changer vers l'utilisateur non-root
USER gestvenv

# Exposer le port
EXPOSE 8000

# Variables d'environnement par défaut
ENV HOST=0.0.0.0 \
    PORT=8000 \
    DEBUG=false \
    SERVE_STATIC_FILES=true

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Commande de démarrage
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]