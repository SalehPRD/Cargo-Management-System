from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[driver_id] = websocket

    def disconnect(self, driver_id: str):
        if driver_id in self.active_connections:
            del self.active_connections[driver_id]

    async def send_notification(self, driver_id: str, message: str):
        if driver_id in self.active_connections:
            try:
                await self.active_connections[driver_id].send_text(message)
                return True
            except:
                self.disconnect(driver_id)
        return False

manager = ConnectionManager()
