from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.models import AuditLog


# PUBLIC_INTERFACE
async def write_audit_log(
    *,
    db: AsyncSession,
    request: Request,
    actor_user_id: uuid.UUID | None,
    actor_email: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Persist an audit log record.

    Contract:
    - Called by API boundary after auth decisions and before returning response.
    - Never raises on JSON serialization issues; falls back to string coercion to preserve debuggability.
    """
    safe_details: dict[str, Any] = details or {}
    try:
        json.dumps(safe_details)
    except TypeError:
        safe_details = {"_non_json_details": str(safe_details)}

    record = AuditLog(
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request.headers.get("x-request-id"),
        ip_address=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        details=safe_details,
    )
    db.add(record)
    await db.commit()
