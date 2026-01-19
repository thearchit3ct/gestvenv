"""
FastAPI application principale pour GestVenv Web Interface.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import logging
import os
from pathlib import Path

from api.routes import environments, packages, cache, system, templates, ide, websocket
from api.ws_manager import WebSocketManager
from api.core.config import settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(
    title="GestVenv Web API",
    description="Interface web pour la gestion d'environnements virtuels Python",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Manager pour les connexions temps réel
websocket_manager = WebSocketManager()

# Inclusion des routes API
app.include_router(environments.router, prefix="/api/v1", tags=["environments"])
app.include_router(packages.router, prefix="/api/v1", tags=["packages"])
app.include_router(cache.router, prefix="/api/v1", tags=["cache"])
app.include_router(system.router, prefix="/api/v1", tags=["system"])
app.include_router(templates.router, prefix="/api/v1", tags=["templates"])
app.include_router(ide.router, tags=["ide"])
app.include_router(websocket.router, tags=["websocket"])

# WebSocket endpoint pour les opérations en temps réel
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint pour les mises à jour en temps réel."""
    client_id = await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Traitement des messages WebSocket si nécessaire
            logger.info(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)

# Route de health check
@app.get("/api/health")
async def health_check():
    """Endpoint de vérification de santé de l'API."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "GestVenv Web API"
    }

# Servir les fichiers statiques du frontend en production
if settings.SERVE_STATIC_FILES:
    # Vérifier si le répertoire dist existe
    static_dir = Path(__file__).parent.parent / "web-ui" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    else:
        logger.warning(f"Static directory not found: {static_dir}")
        
        @app.get("/")
        async def root():
            return HTMLResponse("""
            <html>
                <head><title>GestVenv Web</title></head>
                <body>
                    <h1>GestVenv Web Interface</h1>
                    <p>Frontend not built yet. Please build the Vue.js application.</p>
                    <p>API Documentation: <a href="/api/docs">/api/docs</a></p>
                </body>
            </html>
            """)

# Événement de démarrage
@app.on_event("startup")
async def startup_event():
    """Événements exécutés au démarrage de l'application."""
    logger.info("Starting GestVenv Web API...")
    
    # Vérifier que GestVenv CLI est disponible
    from api.services.gestvenv_service import GestVenvService
    service = GestVenvService()
    try:
        result = await service.execute_command(["--version"])
        if result["returncode"] == 0:
            logger.info(f"GestVenv CLI available: {result['stdout'].strip()}")
        else:
            logger.error("GestVenv CLI not available or not working properly")
    except Exception as e:
        logger.error(f"Failed to check GestVenv CLI: {e}")

# Événement d'arrêt
@app.on_event("shutdown")
async def shutdown_event():
    """Événements exécutés à l'arrêt de l'application."""
    logger.info("Shutting down GestVenv Web API...")
    await websocket_manager.disconnect_all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )