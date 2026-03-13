from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db_session
from src.api.core.security import decode_access_token
from src.api.models.models import AppUser

bearer_scheme = HTTPBearer(auto_error=False)


# PUBLIC_INTERFACE
async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> AppUser:
    """Resolve current user from Authorization: Bearer <token>.

    Errors:
    - 401 if missing/invalid token
    - 403 if user inactive
    """
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_access_token(creds.credentials)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e

    sub = payload.get("sub")
    try:
        user_id = uuid.UUID(str(sub))
    except Exception as e:  # noqa: BLE001 - boundary parsing
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from e

    result = await db.execute(select(AppUser).where(AppUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive or not found")
    request.state.auth_payload = payload
    return user


# PUBLIC_INTERFACE
def require_admin(user: AppUser = Depends(get_current_user)) -> AppUser:
    """Enforce admin privileges (is_admin)."""
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user
