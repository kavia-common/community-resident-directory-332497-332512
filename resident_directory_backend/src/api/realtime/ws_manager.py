from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket


@dataclass
class WebSocketClient:
    websocket: WebSocket
    user_id: str
    is_admin: bool


class AnnouncementWSManager:
    """In-process WebSocket manager for broadcasting announcement events.

    Note: This is single-process only. If scaled horizontally, replace with Redis pub/sub.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._clients: set[WebSocketClient] = set()

    async def connect(self, websocket: WebSocket, *, user_id: str, is_admin: bool) -> WebSocketClient:
        await websocket.accept()
        client = WebSocketClient(websocket=websocket, user_id=user_id, is_admin=is_admin)
        async with self._lock:
            self._clients.add(client)
        return client

    async def disconnect(self, client: WebSocketClient) -> None:
        async with self._lock:
            self._clients.discard(client)

    async def broadcast(self, event: dict[str, Any]) -> None:
        message = json.dumps(event, default=str)
        async with self._lock:
            clients = list(self._clients)

        # Best-effort: drop failed sockets
        to_drop: list[WebSocketClient] = []
        for c in clients:
            try:
                await c.websocket.send_text(message)
            except Exception:  # noqa: BLE001 - realtime best effort
                to_drop.append(c)
        if to_drop:
            async with self._lock:
                for c in to_drop:
                    self._clients.discard(c)


announcement_ws_manager = AnnouncementWSManager()
