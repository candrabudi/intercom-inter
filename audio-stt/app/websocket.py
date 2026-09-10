from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class WebSocketHub:
    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    def publish_from_thread(self, event: dict[str, Any]) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.broadcast(event), self._loop)

    async def broadcast(self, event: dict[str, Any]) -> None:
        for connection in list(self._connections):
            try:
                await connection.send_json(event)
            except Exception:
                self._connections.discard(connection)
