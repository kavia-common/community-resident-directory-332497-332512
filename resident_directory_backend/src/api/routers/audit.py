from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db_session
from src.api.deps.auth import require_admin
from src.api.models.models import AuditLog, AppUser

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get(
    "",
    summary="List audit logs (admin)",
    description="List audit logs (admin-only) in reverse chronological order.",
)
async def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    _admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    items = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": i.id,
            "actor_user_id": i.actor_user_id,
            "actor_email": i.actor_email,
            "action": i.action,
            "entity_type": i.entity_type,
            "entity_id": i.entity_id,
            "request_id": i.request_id,
            "ip_address": i.ip_address,
            "user_agent": i.user_agent,
            "details": i.details,
            "created_at": i.created_at,
        }
        for i in items
    ]
