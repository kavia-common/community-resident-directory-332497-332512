from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db_session
from src.api.core.security import create_access_token, verify_password
from src.api.deps.auth import get_current_user
from src.api.models.models import AppUser
from src.api.schemas.schemas import LoginRequest, MeResponse, TokenResponse
from src.api.services.audit_service import write_audit_log

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login (local auth)",
    description="Authenticate a local user by email/password and return a JWT access token.",
)
async def login(req: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    result = await db.execute(select(AppUser).where(AppUser.email == str(payload.email).lower()))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")

    token = create_access_token(str(user.id), extra_claims={"is_admin": user.is_admin})
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=user.id,
        actor_email=user.email,
        action="auth.login",
        entity_type="app_user",
        entity_id=user.id,
        details={},
    )
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user",
    description="Return the current authenticated user identity and roles.",
)
async def me(user: AppUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        roles=[r.name for r in (user.roles or [])],
        display_name=user.display_name,
    )
