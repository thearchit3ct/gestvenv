"""Event types and factories for WebSocket communication."""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime


class EventType(Enum):
    """Types of events that can be broadcast."""
    
    # Environment events
    ENVIRONMENT_CREATED = "environment:created"
    ENVIRONMENT_UPDATED = "environment:updated"
    ENVIRONMENT_DELETED = "environment:deleted"
    ENVIRONMENT_ACTIVATED = "environment:activated"
    
    # Package events
    PACKAGE_INSTALLED = "package:installed"
    PACKAGE_UNINSTALLED = "package:uninstalled"
    PACKAGE_UPDATED = "package:updated"
    PACKAGE_LIST_CHANGED = "package:list_changed"
    
    # Operation events
    OPERATION_STARTED = "operation:started"
    OPERATION_PROGRESS = "operation:progress"
    OPERATION_COMPLETED = "operation:completed"
    OPERATION_FAILED = "operation:failed"
    
    # System events
    CACHE_UPDATED = "cache:updated"
    CONFIG_CHANGED = "config:changed"
    ERROR_OCCURRED = "error:occurred"
    
    # IDE events
    FILE_CHANGED = "file:changed"
    DIAGNOSTICS_UPDATED = "diagnostics:updated"
    REFACTORING_AVAILABLE = "refactoring:available"


def create_event(event_type: EventType, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a standardized event message."""
    return {
        "type": event_type.value,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }


def create_operation_event(
    operation_id: str,
    operation_type: str,
    status: str,
    progress: Optional[int] = None,
    message: Optional[str] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """Create an operation status event."""
    event_data = {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "status": status
    }
    
    if progress is not None:
        event_data["progress"] = progress
        
    if message:
        event_data["message"] = message
        
    if error:
        event_data["error"] = error
        
    if status == "started":
        event_type = EventType.OPERATION_STARTED
    elif status == "progress":
        event_type = EventType.OPERATION_PROGRESS
    elif status == "completed":
        event_type = EventType.OPERATION_COMPLETED
    elif status == "failed":
        event_type = EventType.OPERATION_FAILED
    else:
        raise ValueError(f"Invalid operation status: {status}")
        
    return create_event(event_type, event_data)


def create_diagnostic_event(
    file_path: str,
    diagnostics: List[Dict[str, Any]],
    environment_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a diagnostics update event."""
    return create_event(
        EventType.DIAGNOSTICS_UPDATED,
        {
            "file_path": file_path,
            "diagnostics": diagnostics,
            "environment_id": environment_id,
            "count": len(diagnostics)
        }
    )


def create_refactoring_event(
    file_path: str,
    line: int,
    column: int,
    refactoring_type: str,
    description: str
) -> Dict[str, Any]:
    """Create a refactoring available event."""
    return create_event(
        EventType.REFACTORING_AVAILABLE,
        {
            "file_path": file_path,
            "position": {"line": line, "column": column},
            "refactoring_type": refactoring_type,
            "description": description
        }
    )