# maios/api/websocket.py
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: dict[str, Any], websocket: WebSocket):
        """Send a message to a specific connection."""
        await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast a message to all connections."""
        for connection in self.active_connections:
            await connection.send_json(message)


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint handler."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_message({"type": "pong"}, websocket)
            else:
                # Echo back for now (will be replaced with event routing)
                await manager.send_message(
                    {"type": "echo", "data": message},
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
