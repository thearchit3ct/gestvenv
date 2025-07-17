#!/bin/bash

# Script de démarrage pour GestVenv Web Interface en mode développement
# Usage: ./start-dev.sh [backend|frontend|both]

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage avec couleur
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    print_status "Vérification des prérequis..."
    
    # Vérifier Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 n'est pas installé"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "Python version: $PYTHON_VERSION"
    
    # Vérifier Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js n'est pas installé"
        exit 1
    fi
    
    NODE_VERSION=$(node --version)
    print_status "Node.js version: $NODE_VERSION"
    
    # Vérifier NPM
    if ! command -v npm &> /dev/null; then
        print_error "NPM n'est pas installé"
        exit 1
    fi
    
    NPM_VERSION=$(npm --version)
    print_status "NPM version: $NPM_VERSION"
    
    # Vérifier GestVenv CLI
    if ! command -v gestvenv &> /dev/null; then
        print_warning "GestVenv CLI n'est pas dans le PATH. Installation depuis le répertoire parent..."
        cd ..
        pip install -e .
        cd web
    fi
    
    GESTVENV_VERSION=$(gestvenv --version 2>/dev/null || echo "dev")
    print_success "GestVenv CLI version: $GESTVENV_VERSION"
}

# Setup du backend
setup_backend() {
    print_status "Configuration du backend FastAPI..."
    
    # Créer un environnement virtuel pour le backend si nécessaire
    if [ ! -d "venv" ]; then
        print_status "Création de l'environnement virtuel..."
        python3 -m venv venv
    fi
    
    # Activer l'environnement virtuel
    source venv/bin/activate
    
    # Installer les dépendances
    print_status "Installation des dépendances Python..."
    pip install -r requirements.txt
    
    # Créer les répertoires nécessaires
    mkdir -p data logs
    
    # Copier le fichier .env s'il n'existe pas
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Fichier .env créé depuis .env.example"
        else
            print_warning "Fichier .env.example non trouvé"
        fi
    fi
    
    print_success "Backend configuré avec succès"
}

# Setup du frontend
setup_frontend() {
    print_status "Configuration du frontend Vue.js..."
    
    cd web-ui
    
    # Installer les dépendances
    if [ ! -d "node_modules" ]; then
        print_status "Installation des dépendances Node.js..."
        npm install
    else
        print_status "Mise à jour des dépendances Node.js..."
        npm update
    fi
    
    cd ..
    print_success "Frontend configuré avec succès"
}

# Démarrage du backend
start_backend() {
    print_status "Démarrage du backend FastAPI..."
    
    # Activer l'environnement virtuel
    source venv/bin/activate
    
    # Variables d'environnement pour le développement
    export DEBUG=true
    export RELOAD=true
    export LOG_LEVEL=DEBUG
    
    print_success "Backend démarré sur http://localhost:8000"
    print_status "API Documentation: http://localhost:8000/api/docs"
    print_status "WebSocket: ws://localhost:8000/ws"
    
    # Démarrer avec hot-reload
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
}

# Démarrage du frontend
start_frontend() {
    print_status "Démarrage du frontend Vue.js..."
    
    cd web-ui
    
    print_success "Frontend démarré sur http://localhost:3001"
    print_status "Le serveur de développement supporte le hot-reload"
    
    # Démarrer le serveur de développement Vite
    npm run dev
}

# Démarrage des deux services
start_both() {
    print_status "Démarrage du backend et du frontend..."
    
    # Obtenir le répertoire actuel
    CURRENT_DIR=$(pwd)
    
    # Créer un script temporaire pour le backend
    cat > /tmp/start-backend.sh << EOF
#!/bin/bash
cd "$CURRENT_DIR"
source venv/bin/activate
export DEBUG=true
export RELOAD=true
export LOG_LEVEL=DEBUG
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
EOF
    chmod +x /tmp/start-backend.sh
    
    # Créer un script temporaire pour le frontend
    cat > /tmp/start-frontend.sh << EOF
#!/bin/bash
cd "$CURRENT_DIR/web-ui"
npm run dev
EOF
    chmod +x /tmp/start-frontend.sh
    
    print_success "Services configurés"
    print_status "Backend: http://localhost:8000"
    print_status "Frontend: http://localhost:3001"
    print_status "API Docs: http://localhost:8000/api/docs"
    print_warning "Appuyez sur Ctrl+C pour arrêter les services"
    
    # Démarrer les deux services en parallèle
    /tmp/start-backend.sh &
    BACKEND_PID=$!
    
    sleep 3  # Attendre que le backend démarre
    
    /tmp/start-frontend.sh &
    FRONTEND_PID=$!
    
    # Fonction de nettoyage
    cleanup() {
        print_status "Arrêt des services..."
        kill $BACKEND_PID 2>/dev/null || true
        kill $FRONTEND_PID 2>/dev/null || true
        rm -f /tmp/start-backend.sh /tmp/start-frontend.sh
        print_success "Services arrêtés"
    }
    
    # Capturer Ctrl+C
    trap cleanup EXIT INT TERM
    
    # Attendre que les processus se terminent
    wait
}

# Menu principal
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  setup     - Configurer l'environnement de développement"
    echo "  backend   - Démarrer uniquement le backend FastAPI"
    echo "  frontend  - Démarrer uniquement le frontend Vue.js"
    echo "  both      - Démarrer backend et frontend (défaut)"
    echo "  check     - Vérifier les prérequis"
    echo "  help      - Afficher cette aide"
    echo ""
    echo "Examples:"
    echo "  $0 setup     # Configuration initiale"
    echo "  $0 both      # Démarrage complet"
    echo "  $0 backend   # Backend seulement"
    echo "  $0 frontend  # Frontend seulement"
}

# Script principal
main() {
    local command=${1:-both}
    
    case $command in
        "check")
            check_prerequisites
            ;;
        "setup")
            check_prerequisites
            setup_backend
            setup_frontend
            print_success "Configuration terminée! Exécutez '$0 both' pour démarrer."
            ;;
        "backend")
            check_prerequisites
            start_backend
            ;;
        "frontend")
            check_prerequisites
            start_frontend
            ;;
        "both")
            check_prerequisites
            # Auto-setup si nécessaire
            if [ ! -d "venv" ]; then
                print_warning "Environnement virtuel non trouvé. Exécution du setup automatique..."
                setup_backend
            fi
            if [ ! -d "web-ui/node_modules" ]; then
                print_warning "Dépendances frontend non trouvées. Exécution du setup automatique..."
                setup_frontend
            fi
            start_both
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Commande inconnue: $command"
            show_help
            exit 1
            ;;
    esac
}

# Point d'entrée
main "$@"