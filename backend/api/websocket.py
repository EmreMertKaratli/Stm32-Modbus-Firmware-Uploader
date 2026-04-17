from fastapi import WebSocket
from typing import List
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_progress(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                self.active_connections.remove(connection)

    async def send_log(self, message: str, level: str = "INFO"):
        await self.send_progress({
            "type": "log",
            "message": message,
            "level": level
        })

    async def send_error(self, message: str):
        await self.send_log(message, "ERROR")


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                await manager.send_progress({"type": "echo", "data": msg})
            except:
                pass
    except:
        manager.disconnect(websocket)