from __future__ import annotations

from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()


class ConnectionManager:
    """Minimal WebSocket connection manager.

    Phase 1 仅提供基础连接和 echo 能力，用于打通前后端 WebSocket 通道。
    后续 Phase 可以在此基础上增加事件广播（position/update 等）。
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_json(self, message: dict) -> None:
        for connection in list(self.active_connections):
            await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """Basic WebSocket endpoint for future realtime events.

    当前实现：
    - 接入后发送一条欢迎消息
    - 回显客户端发送的文本消息
    - 在断开时安全移除连接
    """
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "system", "message": "connected"})
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "payload": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

