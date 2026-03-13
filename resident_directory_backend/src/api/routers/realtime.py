from __future__ import annotations

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from src.api.core.security import decode_access_token
from src.api.core.db import AsyncSessionLocal
from src.api.models.models import AppUser
from src.api.realtime.ws_manager import announcement_ws_manager

router = APIRouter(prefix="/realtime", tags=["Realtime"])


@router.websocket(
    "/announcements",
)
async def announcements_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token, passed as query param: ?token=..."),
) -> None:
    """WebSocket: live announcement events.

    Usage:
    - Connect to ws(s)://<host>/realtime/announcements?token=<JWT>
    - Server sends JSON events:
        { "type": "announcement.created", "announcement": { ... } }
        { "type": "announcement.updated", "announcement": { ... } }
    """
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Load user (avoid Depends in WS route)
    sub = payload.get("sub")
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(AppUser).where(AppUser.id == sub))).scalar_one_or_none()  # type: ignore[arg-type]
    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    client = await announcement_ws_manager.connect(websocket, user_id=str(user.id), is_admin=user.is_admin)
    try:
        while True:
            # Keep connection alive; ignore client messages for now.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await announcement_ws_manager.disconnect(client)
