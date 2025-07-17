# WebSocket module for real-time communication
from .manager import manager as websocket_manager
from .events import EventType, create_event

# Legacy compatibility
event_emitter = websocket_manager

__all__ = ['websocket_manager', 'event_emitter', 'EventType', 'create_event']