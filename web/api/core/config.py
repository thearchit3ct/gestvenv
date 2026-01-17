"""
Configuration de l'application GestVenv Web API.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
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
    
    # Configuration CORS - stored as string in env, parsed to list
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string to list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',') if origin.strip()]
    
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        # Ne pas essayer de parser automatiquement comme JSON
        env_parse_none_str="None"
    )


# Instance globale des settings
settings = Settings()


def get_settings() -> Settings:
    """Récupère l'instance des settings."""
    return settings