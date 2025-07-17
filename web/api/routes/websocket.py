"""WebSocket routes for real-time IDE communication."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import uuid
import logging

from ..websocket.manager import manager
from ..websocket.handlers import WebSocketHandler
from ..services.environment_service import EnvironmentService
from ..services.package_service import PackageService
from ..core.dependencies import get_environment_service, get_package_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/ide/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    env_service: EnvironmentService = Depends(get_environment_service),
    pkg_service: PackageService = Depends(get_package_service)
):
    """
    WebSocket endpoint for IDE real-time communication.
    
    Client ID should be unique per VS Code instance.
    """
    # Extract metadata from query params
    metadata = {
        "user_agent": websocket.headers.get("user-agent", ""),
        "vscode_version": websocket.query_params.get("vscode_version"),
        "extension_version": websocket.query_params.get("extension_version"),
        "workspace": websocket.query_params.get("workspace")
    }
    
    # Connect client
    await manager.connect(websocket, client_id, metadata)
    
    # Create handler
    handler = WebSocketHandler(env_service, pkg_service)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            logger.debug(f"Received message from {client_id}: {data}")
            
            # Handle message
            await handler.handle_message(client_id, data)
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket server status."""
    return {
        "connected_clients": manager.get_client_count(),
        "clients": list(manager.active_connections.keys()),
        "environment_subscriptions": {
            client_id: list(envs)
            for client_id, envs in manager.client_environments.items()
        }
    }