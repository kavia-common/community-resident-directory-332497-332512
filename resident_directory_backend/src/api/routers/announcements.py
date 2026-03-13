from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db_session
from src.api.deps.auth import get_current_user, require_admin
from src.api.models.models import AppUser
from src.api.realtime.ws_manager import announcement_ws_manager
from src.api.schemas.schemas import (
    AnnouncementCreateRequest,
    AnnouncementResponse,
    AnnouncementUpdateRequest,
)
from src.api.services.announcement_service import (
    create_announcement_flow,
    get_announcement_flow,
    list_announcements_flow,
    update_announcement_flow,
)
from src.api.services.audit_service import write_audit_log

router = APIRouter(prefix="/announcements", tags=["Announcements"])


def _to_response(a) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=a.id,
        created_by=a.created_by,
        title=a.title,
        body=a.body,
        is_pinned=a.is_pinned,
        visibility=a.visibility,
        published_at=a.published_at,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.get(
    "",
    response_model=list[AnnouncementResponse],
    summary="List announcements",
    description="List announcements (authenticated). Client can filter by visibility.",
)
async def list_announcements(
    limit: int = 50,
    offset: int = 0,
    _viewer: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[AnnouncementResponse]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    items = await list_announcements_flow(db=db, limit=limit, offset=offset)
    return [_to_response(a) for a in items]


@router.get(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    summary="Get announcement",
    description="Get one announcement by id.",
)
async def get_announcement(
    announcement_id: uuid.UUID,
    _viewer: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AnnouncementResponse:
    a = await get_announcement_flow(db=db, announcement_id=announcement_id)
    return _to_response(a)


@router.post(
    "",
    response_model=AnnouncementResponse,
    summary="Create announcement (admin)",
    description="Create an announcement and broadcast it to WebSocket subscribers.",
)
async def create_announcement(
    req: Request,
    payload: AnnouncementCreateRequest,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AnnouncementResponse:
    a = await create_announcement_flow(db=db, actor_user_id=admin.id, payload=payload)
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=admin.id,
        actor_email=admin.email,
        action="announcement.create",
        entity_type="announcement",
        entity_id=a.id,
        details={"title": a.title},
    )
    await announcement_ws_manager.broadcast({"type": "announcement.created", "announcement": _to_response(a).model_dump()})
    return _to_response(a)


@router.patch(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    summary="Update announcement (admin)",
    description="Update an announcement and broadcast the update to WebSocket subscribers.",
)
async def update_announcement(
    req: Request,
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdateRequest,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AnnouncementResponse:
    a = await update_announcement_flow(db=db, announcement_id=announcement_id, payload=payload)
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=admin.id,
        actor_email=admin.email,
        action="announcement.update",
        entity_type="announcement",
        entity_id=a.id,
        details={},
    )
    await announcement_ws_manager.broadcast({"type": "announcement.updated", "announcement": _to_response(a).model_dump()})
    return _to_response(a)
