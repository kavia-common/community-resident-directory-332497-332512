from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.models import Announcement
from src.api.schemas.schemas import AnnouncementCreateRequest, AnnouncementUpdateRequest


# PUBLIC_INTERFACE
async def create_announcement_flow(
    *,
    db: AsyncSession,
    actor_user_id: uuid.UUID,
    payload: AnnouncementCreateRequest,
) -> Announcement:
    """Create an announcement."""
    now = datetime.now(timezone.utc)
    ann = Announcement(
        created_by=actor_user_id,
        title=payload.title,
        body=payload.body,
        is_pinned=payload.is_pinned,
        visibility=payload.visibility,
        published_at=(now if payload.publish else None),
        created_at=now,
        updated_at=now,
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


# PUBLIC_INTERFACE
async def update_announcement_flow(
    *,
    db: AsyncSession,
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdateRequest,
) -> Announcement:
    """Update announcement fields."""
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    ann = result.scalar_one()
    now = datetime.now(timezone.utc)

    for f in ["title", "body", "is_pinned", "visibility"]:
        v = getattr(payload, f, None)
        if v is not None:
            setattr(ann, f, v)

    if payload.publish is True:
        ann.published_at = now
    elif payload.publish is False:
        ann.published_at = None

    ann.updated_at = now
    await db.commit()
    await db.refresh(ann)
    return ann


# PUBLIC_INTERFACE
async def list_announcements_flow(*, db: AsyncSession, limit: int, offset: int) -> list[Announcement]:
    """List announcements (newest first, pinned priority can be done client-side)."""
    stmt = select(Announcement).order_by(desc(Announcement.is_pinned), desc(Announcement.published_at), desc(Announcement.created_at))
    return (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()


# PUBLIC_INTERFACE
async def get_announcement_flow(*, db: AsyncSession, announcement_id: uuid.UUID) -> Announcement:
    """Get a single announcement by id."""
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    return result.scalar_one()
