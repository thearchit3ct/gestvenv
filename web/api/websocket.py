"""
Gestionnaire WebSocket pour les communications temps réel.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from api.models.schemas import WSMessage, WSMessageType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gestionnaire des connexions WebSocket individuelles."""
    
    def __init__(self):
        self.websocket: WebSocket
        self.client_id: str
        self.subscriptions: set = set()
    
    async def send_message(self, message: WSMessage):
        """Envoie un message au client."""
        try:
            await self.websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to send message to {self.client_id}: {e}")
    
    def subscribe(self, event_type: str):
        """S'abonne à un type d'événement."""
        self.subscriptions.add(event_type)
    
    def unsubscribe(self, event_type: str):
        """Se désabonne d'un type d'événement."""
        self.subscriptions.discard(event_type)
    
    def is_subscribed(self, event_type: str) -> bool:
        """Vérifie si abonné à un type d'événement."""
        return event_type in self.subscriptions


class WebSocketManager:
    """Gestionnaire principal des connexions WebSocket."""
    
    def __init__(self):
        self.active_connections: Dict[str, ConnectionManager] = {}
        self.room_subscriptions: Dict[str, set] = {}  # room -> {client_ids}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """
        Accepte une nouvelle connexion WebSocket.
        
        Args:
            websocket: Instance WebSocket
            client_id: ID du client (généré si non fourni)
        """
        await websocket.accept()
        
        if not client_id:
            client_id = f"client_{len(self.active_connections)}"
        
        manager = ConnectionManager()
        manager.websocket = websocket
        manager.client_id = client_id
        
        self.active_connections[client_id] = manager
        
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
        # Envoyer message de bienvenue
        welcome_msg = WSMessage(
            type=WSMessageType.OPERATION_COMPLETED,
            data={
                "event": "connected",
                "client_id": client_id,
                "message": "Connexion WebSocket établie"
            }
        )
        await manager.send_message(welcome_msg)
        
        return client_id
    
    def disconnect(self, client_id: str):
        """
        Déconnecte un client.
        
        Args:
            client_id: ID du client à déconnecter
        """
        if client_id in self.active_connections:
            # Retirer de toutes les rooms
            for room_clients in self.room_subscriptions.values():
                room_clients.discard(client_id)
            
            # Supprimer la connexion
            del self.active_connections[client_id]
            
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def disconnect_all(self):
        """Déconnecte tous les clients."""
        for client_id in list(self.active_connections.keys()):
            self.disconnect(client_id)
        
        logger.info("All WebSocket clients disconnected")
    
    async def send_to_client(self, client_id: str, message: WSMessage):
        """
        Envoie un message à un client spécifique.
        
        Args:
            client_id: ID du client
            message: Message à envoyer
        """
        if client_id in self.active_connections:
            manager = self.active_connections[client_id]
            await manager.send_message(message)
    
    async def broadcast_to_all(self, message: WSMessage):
        """
        Diffuse un message à tous les clients connectés.
        
        Args:
            message: Message à diffuser
        """
        if not self.active_connections:
            return
        
        logger.info(f"Broadcasting message to {len(self.active_connections)} clients")
        
        # Envoyer en parallèle pour de meilleures performances
        tasks = [
            manager.send_message(message)
            for manager in self.active_connections.values()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_room(self, room: str, message: WSMessage):
        """
        Diffuse un message à tous les clients d'une room.
        
        Args:
            room: Nom de la room
            message: Message à diffuser
        """
        if room not in self.room_subscriptions:
            return
        
        client_ids = self.room_subscriptions[room]
        logger.info(f"Broadcasting to room '{room}' ({len(client_ids)} clients)")
        
        tasks = [
            self.send_to_client(client_id, message)
            for client_id in client_ids
            if client_id in self.active_connections
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_by_event_type(self, event_type: WSMessageType, message: WSMessage):
        """
        Diffuse un message à tous les clients abonnés à un type d'événement.
        
        Args:
            event_type: Type d'événement
            message: Message à diffuser
        """
        subscribers = [
            manager for manager in self.active_connections.values()
            if manager.is_subscribed(event_type.value)
        ]
        
        if not subscribers:
            return
        
        logger.info(f"Broadcasting '{event_type}' to {len(subscribers)} subscribers")
        
        tasks = [
            manager.send_message(message)
            for manager in subscribers
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def join_room(self, client_id: str, room: str):
        """
        Ajoute un client à une room.
        
        Args:
            client_id: ID du client
            room: Nom de la room
        """
        if client_id not in self.active_connections:
            return
        
        if room not in self.room_subscriptions:
            self.room_subscriptions[room] = set()
        
        self.room_subscriptions[room].add(client_id)
        logger.info(f"Client {client_id} joined room '{room}'")
    
    def leave_room(self, client_id: str, room: str):
        """
        Retire un client d'une room.
        
        Args:
            client_id: ID du client
            room: Nom de la room
        """
        if room in self.room_subscriptions:
            self.room_subscriptions[room].discard(client_id)
            
            # Supprimer la room si vide
            if not self.room_subscriptions[room]:
                del self.room_subscriptions[room]
            
            logger.info(f"Client {client_id} left room '{room}'")
    
    def subscribe_to_event(self, client_id: str, event_type: str):
        """
        Abonne un client à un type d'événement.
        
        Args:
            client_id: ID du client
            event_type: Type d'événement
        """
        if client_id in self.active_connections:
            self.active_connections[client_id].subscribe(event_type)
            logger.info(f"Client {client_id} subscribed to '{event_type}'")
    
    def unsubscribe_from_event(self, client_id: str, event_type: str):
        """
        Désabonne un client d'un type d'événement.
        
        Args:
            client_id: ID du client
            event_type: Type d'événement
        """
        if client_id in self.active_connections:
            self.active_connections[client_id].unsubscribe(event_type)
            logger.info(f"Client {client_id} unsubscribed from '{event_type}'")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques des connexions.
        
        Returns:
            Dictionnaire avec les statistiques
        """
        return {
            "total_connections": len(self.active_connections),
            "active_rooms": len(self.room_subscriptions),
            "clients_per_room": {
                room: len(clients) 
                for room, clients in self.room_subscriptions.items()
            },
            "connected_clients": list(self.active_connections.keys())
        }


# Instance globale du gestionnaire WebSocket
websocket_manager = WebSocketManager()


class WebSocketEventEmitter:
    """Émetteur d'événements pour WebSocket."""
    
    def __init__(self, manager: WebSocketManager):
        self.manager = manager
    
    async def emit_environment_created(self, environment_name: str, environment_data: Dict[str, Any]):
        """Émet un événement de création d'environnement."""
        message = WSMessage(
            type=WSMessageType.ENVIRONMENT_CREATED,
            data={
                "environment_name": environment_name,
                "environment": environment_data
            }
        )
        await self.manager.broadcast_to_all(message)
    
    async def emit_environment_deleted(self, environment_name: str):
        """Émet un événement de suppression d'environnement."""
        message = WSMessage(
            type=WSMessageType.ENVIRONMENT_DELETED,
            data={"environment_name": environment_name}
        )
        await self.manager.broadcast_to_all(message)
    
    async def emit_package_installed(self, environment_name: str, package_name: str, package_data: Dict[str, Any]):
        """Émet un événement d'installation de package."""
        message = WSMessage(
            type=WSMessageType.PACKAGE_INSTALLED,
            data={
                "environment_name": environment_name,
                "package_name": package_name,
                "package": package_data
            }
        )
        await self.manager.broadcast_to_room(f"env:{environment_name}", message)
    
    async def emit_operation_progress(self, operation_id: str, progress: float, message: str):
        """Émet un événement de progression d'opération."""
        ws_message = WSMessage(
            type=WSMessageType.OPERATION_PROGRESS,
            data={
                "operation_id": operation_id,
                "progress": progress,
                "message": message
            }
        )
        await self.manager.broadcast_to_room(f"operation:{operation_id}", ws_message)
    
    async def emit_cache_updated(self, cache_stats: Dict[str, Any]):
        """Émet un événement de mise à jour du cache."""
        message = WSMessage(
            type=WSMessageType.CACHE_UPDATED,
            data=cache_stats
        )
        await self.manager.broadcast_by_event_type(WSMessageType.CACHE_UPDATED, message)


# Instance globale de l'émetteur d'événements
event_emitter = WebSocketEventEmitter(websocket_manager)