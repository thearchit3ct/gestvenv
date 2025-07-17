"""
Configuration de l'application GestVenv Web API.
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Configuration de l'application."""
    
    # Configuration de base
    APP_NAME: str = "GestVenv Web API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Configuration serveur
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Configuration CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # Dev frontend
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # Configuration base de données
    DATABASE_URL: str = "sqlite:///./gestvenv_web.db"
    
    # Configuration Redis (optionnel pour cache/sessions)
    REDIS_URL: str = "redis://localhost:6379"
    USE_REDIS: bool = False
    
    # Configuration JWT (pour authentification future)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Configuration GestVenv
    GESTVENV_CLI_PATH: str = "gestvenv"  # Chemin vers l'exécutable GestVenv
    
    # Configuration fichiers statiques
    SERVE_STATIC_FILES: bool = True
    
    # Configuration logging
    LOG_LEVEL: str = "INFO"
    
    # Configuration WebSocket
    WS_MAX_CONNECTIONS: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instance globale des settings
settings = Settings()


def get_settings() -> Settings:
    """Récupère l'instance des settings."""
    return settings