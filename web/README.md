# 🌐 GestVenv Interface Web

Interface web moderne pour la gestion d'environnements virtuels Python via GestVenv.

## ✨ Fonctionnalités

- **🖥️ Interface utilisateur intuitive** - Dashboard Vue.js 3 avec Tailwind CSS
- **⚡ Opérations temps réel** - WebSocket pour mises à jour en direct
- **📊 Monitoring avancé** - Suivi des opérations et santé du système
- **🔧 Gestion complète** - Environnements, packages, cache, templates
- **🐳 Déploiement containerisé** - Docker et Docker Compose inclus
- **🚀 Performance optimisée** - API asynchrone FastAPI + frontend build optimisé

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Frontend      │    │   Backend API    │    │   Core GestVenv     │
│   (Vue.js 3)    │◄──►│   (FastAPI)      │◄──►│   (CLI Interface)   │
│   + Tailwind    │    │   + WebSocket    │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

### Stack Technologique

**Backend :**
- FastAPI (API REST + WebSocket)
- SQLAlchemy (ORM)
- Pydantic (Validation)
- Uvicorn (Serveur ASGI)

**Frontend :**
- Vue.js 3 (Composition API)
- TypeScript
- Tailwind CSS
- Pinia (State Management)
- Vite (Build Tool)

## 🚀 Installation et Démarrage

### Méthode 1 : Développement local (Recommandé)

#### Démarrage rapide avec script automatique

```bash
# Aller dans le répertoire web
cd gestvenv/web

# Configuration initiale (première fois seulement)
./start-dev.sh setup

# Démarrer les services
./start-dev.sh both

# L'interface sera disponible sur :
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
# - API Docs: http://localhost:8000/api/docs
```

### Méthode 2 : Installation manuelle

#### Backend

```bash
# Installer les dépendances Python
cd web
pip install -r requirements.txt

# Lancer le serveur de développement
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
# Installer les dépendances Node.js
cd web-ui
npm install

# Démarrage en mode développement
npm run dev

# Build de production
npm run build
```

### Méthode 3 : Docker (Alternative pour production)

```bash
# Cloner et aller dans le répertoire web
cd gestvenv/web

# Copier la configuration d'exemple
cp .env.example .env

# Démarrer l'interface web
docker-compose up -d

# L'interface sera disponible sur http://localhost:8000
```

## ⚙️ Configuration

### Variables d'environnement

Copiez `.env.example` vers `.env` et ajustez les valeurs :

```bash
# Configuration de base
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Sécurité
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Base de données
DATABASE_URL=sqlite:///./data/gestvenv_web.db

# GestVenv
GESTVENV_CLI_PATH=gestvenv
```

### Configuration Docker (Production)

#### Développement local avec Docker

```bash
# Démarrage avec hot-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

#### Production avec PostgreSQL et Redis

```bash
# Avec services additionnels
docker-compose --profile postgres --profile redis up -d
```

#### Production avec Nginx

```bash
# Avec reverse proxy SSL
docker-compose --profile nginx up -d
```

## 📱 Utilisation

### Dashboard Principal

- **Vue d'ensemble** des environnements et statistiques
- **Santé du système** et diagnostic rapide
- **Opérations en cours** avec progression temps réel
- **Actions rapides** pour créer et gérer les environnements

### Gestion des Environnements

- **Création avancée** avec templates et backends multiples
- **Activation/désactivation** en un clic
- **Synchronisation** automatique avec pyproject.toml
- **Filtrage et recherche** par nom, backend, statut

### Gestion des Packages

- **Installation par groupes** (dev, test, etc.)
- **Mise à jour intelligente** avec détection des packages obsolètes
- **Désinstallation sécurisée** avec gestion des dépendances
- **Recherche et filtrage** avancés

### Cache et Performance

- **Monitoring du cache** avec statistiques détaillées
- **Export/import** pour sauvegarde et partage
- **Nettoyage intelligent** par âge et taille
- **Mode hors ligne** complet

### Templates

- **6 templates intégrés** : Basic, CLI, Web, FastAPI, Django, Data Science
- **Création personnalisée** avec variables et configuration
- **Structure optimisée** suivant les meilleures pratiques

## 🔌 API REST

### Endpoints principaux

```bash
# Environnements
GET    /api/v1/environments          # Liste des environnements
POST   /api/v1/environments          # Créer un environnement
GET    /api/v1/environments/{name}   # Détails d'un environnement
DELETE /api/v1/environments/{name}   # Supprimer un environnement

# Packages
GET    /api/v1/environments/{name}/packages  # Packages d'un environnement
POST   /api/v1/packages/install              # Installer un package
DELETE /api/v1/packages/{name}               # Désinstaller un package

# Système
GET    /api/v1/system/info           # Informations système
GET    /api/v1/system/health         # Santé du système
POST   /api/v1/system/doctor         # Diagnostic
GET    /api/v1/system/operations     # Liste des opérations

# Cache
GET    /api/v1/cache/info           # Informations du cache
POST   /api/v1/cache/clean          # Nettoyer le cache
POST   /api/v1/cache/export         # Exporter le cache

# Templates
GET    /api/v1/templates            # Liste des templates
POST   /api/v1/templates/create     # Créer depuis template
```

### WebSocket

Connexion WebSocket pour les mises à jour temps réel :

```javascript
const ws = new WebSocket('ws://localhost:8000/ws')

// Événements supportés :
// - environment_created
// - environment_deleted
// - package_installed
// - operation_progress
// - cache_updated
```

## 🐳 Déploiement Production

### Option 1 : Serveurs locaux (Recommandé pour développement/test)

```bash
# Backend sur un serveur
cd web
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Frontend buildé et servi par Nginx
cd web-ui
npm run build
# Copier dist/ vers serveur web
```

### Option 2 : Docker Simple

```bash
# Build de l'image
docker build -t gestvenv-web .

# Démarrage
docker run -d \
  --name gestvenv-web \
  -p 8000:8000 \
  -v ~/.gestvenv:/home/gestvenv/.gestvenv \
  gestvenv-web
```

### Option 3 : Docker Compose Production

```bash
# Configuration complète avec PostgreSQL, Redis, Nginx
docker-compose --profile postgres --profile redis --profile nginx up -d
```

### Variables importantes pour production

```bash
# Sécurité
SECRET_KEY=production-secret-key-very-long-and-random
DEBUG=false
ALLOWED_ORIGINS=https://yourdomain.com

# Base de données
DATABASE_URL=postgresql://user:password@postgres:5432/gestvenv_web

# SSL/TLS (avec Nginx)
SSL_CERTIFICATE=/etc/ssl/certs/server.crt
SSL_PRIVATE_KEY=/etc/ssl/certs/server.key
```

## 🔧 Développement

### Structure du projet

```
web/
├── api/                    # Backend FastAPI
│   ├── main.py            # Point d'entrée
│   ├── routes/            # Endpoints API
│   ├── services/          # Services métier
│   ├── models/            # Schémas Pydantic
│   └── websocket.py       # Gestion WebSocket
├── web-ui/                # Frontend Vue.js
│   ├── src/
│   │   ├── components/    # Composants Vue
│   │   ├── views/         # Pages principales
│   │   ├── stores/        # Stores Pinia
│   │   ├── services/      # Services API
│   │   └── types/         # Types TypeScript
│   └── dist/              # Build de production
├── Dockerfile             # Image Docker
├── docker-compose.yml     # Configuration Docker Compose
└── nginx.conf             # Configuration Nginx
```

### Scripts de développement

```bash
# Backend
cd web
pip install -r requirements.txt
uvicorn api.main:app --reload

# Frontend
cd web-ui
npm install
npm run dev

# Tests
npm run test
pytest api/tests/

# Linting
npm run lint
black api/
isort api/
```

## 📊 Monitoring

### Métriques disponibles

- **Performance** : Temps de réponse API, utilisation mémoire
- **Utilisation** : Nombre d'environnements, packages installés
- **Système** : État des backends, espace disque
- **WebSocket** : Connexions actives, messages échangés

### Health Checks

```bash
# API Health
curl http://localhost:8000/api/health

# Application complète
curl http://localhost:8000/api/v1/system/health
```

## 🔐 Sécurité

### Bonnes pratiques implémentées

- **CORS** configuré restrictif
- **Rate limiting** sur les endpoints sensibles
- **Headers de sécurité** (CSP, HSTS, etc.)
- **Validation des entrées** avec Pydantic
- **Logs de sécurité** pour audit

### Configuration SSL/TLS

```bash
# Générer un certificat auto-signé pour développement
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir [LICENSE](../LICENSE) pour plus de détails.

## 🆘 Support

- **Documentation** : Consultez les guides dans `/docs`
- **Issues** : Rapportez les bugs sur GitHub
- **Discussions** : Posez vos questions dans les discussions GitHub

---

**GestVenv Web Interface** - Interface moderne pour la gestion d'environnements virtuels Python 🐍✨