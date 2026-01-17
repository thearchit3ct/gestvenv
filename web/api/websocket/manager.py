"""WebSocket connection manager for real-time IDE synchronization."""

from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for IDE clients."""
    
    def __init__(self):
        # Store active connections by client ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Track which environments each client is watching
        self.client_environments: Dict[str, Set[str]] = {}
        # Track client metadata
        self.client_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str, metadata: Optional[Dict] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_environments[client_id] = set()
        self.client_metadata[client_id] = metadata or {}
        
        logger.info(f"Client {client_id} connected")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        }, client_id)
        
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.client_environments[client_id]
            del self.client_metadata[client_id]
            logger.info(f"Client {client_id} disconnected")
            
    async def send_personal_message(self, message: Dict, client_id: str):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
                
    async def broadcast_to_environment(self, message: Dict, environment_id: str):
        """Broadcast a message to all clients watching an environment."""
        disconnected_clients = []
        
        for client_id, environments in self.client_environments.items():
            if environment_id in environments:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)
                    
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
    async def broadcast_to_all(self, message: Dict):
        """Broadcast a message to all connected clients."""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
                
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
    def subscribe_to_environment(self, client_id: str, environment_id: str):
        """Subscribe a client to environment updates."""
        if client_id in self.client_environments:
            self.client_environments[client_id].add(environment_id)
            logger.info(f"Client {client_id} subscribed to environment {environment_id}")
            
    def unsubscribe_from_environment(self, client_id: str, environment_id: str):
        """Unsubscribe a client from environment updates."""
        if client_id in self.client_environments:
            self.client_environments[client_id].discard(environment_id)
            logger.info(f"Client {client_id} unsubscribed from environment {environment_id}")
            
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self.active_connections)
        
    def get_environment_subscribers(self, environment_id: str) -> List[str]:
        """Get list of clients subscribed to an environment."""
        subscribers = []
        for client_id, environments in self.client_environments.items():
            if environment_id in environments:
                subscribers.append(client_id)
        return subscribers


# Global connection manager instance
manager = ConnectionManager()