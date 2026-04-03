from fastapi import WebSocket

class AgentStatusManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.last_cycle_status: dict = {}  # persist last known state for late joiners

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # immediately send current status to new connection
        if self.last_cycle_status:
            await websocket.send_json(self.last_cycle_status)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        self.last_cycle_status = data
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        
        for d in disconnected:
            self.disconnect(d)

agent_status_manager = AgentStatusManager()
