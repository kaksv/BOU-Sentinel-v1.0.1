"""
BOU Sentinel - WebSocket Connection Manager
Extracted as a standalone module so both main.py and regulatory_router.py
can import it without circular dependency.
"""
import asyncio
import logging
from typing import List
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("bou-sentinel.ws")


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages to all clients.
    Acts as the pub/sub bridge between Redis and connected frontends.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Send a message to all connected WebSocket clients."""
        async with self._lock:
            dead = []
            for conn in self.active_connections:
                try:
                    await conn.send_text(message)
                except (WebSocketDisconnect, Exception) as e:
                    logger.warning(f"⚠️ WS send error: {e}")
                    dead.append(conn)
            for conn in dead:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)

    @property
    def count(self) -> int:
        return len(self.active_connections)


# Singleton — import this everywhere
manager = ConnectionManager()