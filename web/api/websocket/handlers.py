"""WebSocket message handlers for IDE integration."""

from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
import logging

from ..services.environment_service import EnvironmentService
from ..services.package_service import PackageService
from .manager import manager
from .events import EventType, create_event

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Handles incoming WebSocket messages from IDE clients."""
    
    def __init__(self, env_service: EnvironmentService, pkg_service: PackageService):
        self.env_service = env_service
        self.pkg_service = pkg_service
        
    async def handle_message(self, client_id: str, message: Dict[str, Any]):
        """Route and handle incoming WebSocket messages."""
        msg_type = message.get("type")
        
        if not msg_type:
            await manager.send_personal_message({
                "type": "error",
                "message": "Message type is required"
            }, client_id)
            return
            
        # Route to appropriate handler
        handlers = {
            "subscribe": self.handle_subscribe,
            "unsubscribe": self.handle_unsubscribe,
            "environment:refresh": self.handle_environment_refresh,
            "package:install": self.handle_package_install,
            "package:uninstall": self.handle_package_uninstall,
            "package:update": self.handle_package_update,
            "code:analyze": self.handle_code_analyze,
            "refactor:suggest": self.handle_refactor_suggest,
            "ping": self.handle_ping
        }
        
        handler = handlers.get(msg_type)
        if handler:
            try:
                await handler(client_id, message)
            except Exception as e:
                logger.error(f"Error handling message {msg_type}: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Error handling {msg_type}: {str(e)}"
                }, client_id)
        else:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }, client_id)
            
    async def handle_subscribe(self, client_id: str, message: Dict):
        """Handle environment subscription."""
        env_id = message.get("environment_id")
        if not env_id:
            await manager.send_personal_message({
                "type": "error",
                "message": "environment_id is required"
            }, client_id)
            return
            
        manager.subscribe_to_environment(client_id, env_id)
        
        # Send current environment state
        try:
            env = await self.env_service.get_environment(env_id)
            packages = await self.pkg_service.list_packages(env_id)
            
            await manager.send_personal_message({
                "type": "subscription:confirmed",
                "environment_id": env_id,
                "environment": env.dict() if env else None,
                "packages": [pkg.dict() for pkg in packages]
            }, client_id)
        except Exception as e:
            logger.error(f"Error getting environment state: {e}")
            
    async def handle_unsubscribe(self, client_id: str, message: Dict):
        """Handle environment unsubscription."""
        env_id = message.get("environment_id")
        if env_id:
            manager.unsubscribe_from_environment(client_id, env_id)
            await manager.send_personal_message({
                "type": "unsubscription:confirmed",
                "environment_id": env_id
            }, client_id)
            
    async def handle_environment_refresh(self, client_id: str, message: Dict):
        """Handle environment refresh request."""
        env_id = message.get("environment_id")
        if not env_id:
            return
            
        # Trigger refresh
        await self.env_service.refresh_environment(env_id)
        
        # Broadcast update to all subscribers
        event = create_event(
            EventType.ENVIRONMENT_UPDATED,
            {"environment_id": env_id, "refreshed": True}
        )
        await manager.broadcast_to_environment(event, env_id)
        
    async def handle_package_install(self, client_id: str, message: Dict):
        """Handle package installation request."""
        env_id = message.get("environment_id")
        package_name = message.get("package_name")
        version = message.get("version")
        
        if not env_id or not package_name:
            return
            
        # Start installation
        task_id = f"install_{package_name}_{datetime.utcnow().timestamp()}"
        
        # Send progress update
        await manager.send_personal_message({
            "type": "task:started",
            "task_id": task_id,
            "task_type": "package:install",
            "package_name": package_name
        }, client_id)
        
        try:
            # Perform installation
            result = await self.pkg_service.install_package(
                env_id, package_name, version
            )
            
            # Send completion
            await manager.send_personal_message({
                "type": "task:completed",
                "task_id": task_id,
                "result": result
            }, client_id)
            
            # Broadcast package added event
            event = create_event(
                EventType.PACKAGE_INSTALLED,
                {
                    "environment_id": env_id,
                    "package": package_name,
                    "version": version or "latest"
                }
            )
            await manager.broadcast_to_environment(event, env_id)
            
        except Exception as e:
            await manager.send_personal_message({
                "type": "task:failed",
                "task_id": task_id,
                "error": str(e)
            }, client_id)
            
    async def handle_package_uninstall(self, client_id: str, message: Dict):
        """Handle package uninstallation request."""
        env_id = message.get("environment_id")
        package_name = message.get("package_name")
        
        if not env_id or not package_name:
            return
            
        task_id = f"uninstall_{package_name}_{datetime.utcnow().timestamp()}"
        
        await manager.send_personal_message({
            "type": "task:started",
            "task_id": task_id,
            "task_type": "package:uninstall",
            "package_name": package_name
        }, client_id)
        
        try:
            result = await self.pkg_service.uninstall_package(env_id, package_name)
            
            await manager.send_personal_message({
                "type": "task:completed",
                "task_id": task_id,
                "result": result
            }, client_id)
            
            event = create_event(
                EventType.PACKAGE_UNINSTALLED,
                {
                    "environment_id": env_id,
                    "package": package_name
                }
            )
            await manager.broadcast_to_environment(event, env_id)
            
        except Exception as e:
            await manager.send_personal_message({
                "type": "task:failed",
                "task_id": task_id,
                "error": str(e)
            }, client_id)
            
    async def handle_package_update(self, client_id: str, message: Dict):
        """Handle package update request."""
        env_id = message.get("environment_id")
        package_name = message.get("package_name")
        version = message.get("version")
        
        if not env_id or not package_name:
            return
            
        task_id = f"update_{package_name}_{datetime.utcnow().timestamp()}"
        
        await manager.send_personal_message({
            "type": "task:started",
            "task_id": task_id,
            "task_type": "package:update",
            "package_name": package_name
        }, client_id)
        
        try:
            result = await self.pkg_service.update_package(
                env_id, package_name, version
            )
            
            await manager.send_personal_message({
                "type": "task:completed",
                "task_id": task_id,
                "result": result
            }, client_id)
            
            event = create_event(
                EventType.PACKAGE_UPDATED,
                {
                    "environment_id": env_id,
                    "package": package_name,
                    "version": version or "latest"
                }
            )
            await manager.broadcast_to_environment(event, env_id)
            
        except Exception as e:
            await manager.send_personal_message({
                "type": "task:failed",
                "task_id": task_id,
                "error": str(e)
            }, client_id)
            
    async def handle_code_analyze(self, client_id: str, message: Dict):
        """Handle code analysis request."""
        code = message.get("code", "")
        file_path = message.get("file_path", "")
        env_id = message.get("environment_id")
        
        # Perform analysis
        analysis = await self.analyze_code(code, file_path, env_id)
        
        await manager.send_personal_message({
            "type": "code:analysis",
            "analysis": analysis
        }, client_id)
        
    async def handle_refactor_suggest(self, client_id: str, message: Dict):
        """Handle refactoring suggestion request."""
        code = message.get("code", "")
        selection = message.get("selection", {})
        refactor_type = message.get("refactor_type", "extract_function")
        
        suggestions = await self.suggest_refactoring(code, selection, refactor_type)
        
        await manager.send_personal_message({
            "type": "refactor:suggestions",
            "suggestions": suggestions
        }, client_id)
        
    async def handle_ping(self, client_id: str, message: Dict):
        """Handle ping message."""
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }, client_id)
        
    async def analyze_code(self, code: str, file_path: str, env_id: Optional[str]) -> Dict:
        """Analyze code for issues and suggestions."""
        # TODO: Implement actual code analysis
        return {
            "issues": [],
            "suggestions": [],
            "metrics": {
                "complexity": 0,
                "lines": len(code.splitlines()),
                "functions": 0,
                "classes": 0
            }
        }
        
    async def suggest_refactoring(self, code: str, selection: Dict, refactor_type: str) -> List[Dict]:
        """Suggest refactoring options."""
        # TODO: Implement actual refactoring suggestions
        return [{
            "type": refactor_type,
            "description": f"Extract {refactor_type}",
            "preview": code,
            "actions": []
        }]