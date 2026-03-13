from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db_session
from src.api.deps.auth import require_admin
from src.api.models.models import AppUser
from src.api.schemas.schemas import InvitationCreateRequest, InvitationResponse, SignupRequest, TokenResponse
from src.api.core.security import create_access_token
from src.api.services.audit_service import write_audit_log
from src.api.services.invitation_service import accept_invitation_and_signup_flow, create_invitation_flow, revoke_invitation_flow

router = APIRouter(prefix="/invitations", tags=["Invitations"])


@router.post(
    "",
    response_model=InvitationResponse,
    summary="Create invitation (admin)",
    description="Create an invitation for an email address. Returns the raw token only once.",
)
async def create_invitation(
    req: Request,
    payload: InvitationCreateRequest,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> InvitationResponse:
    inv, raw_token = await create_invitation_flow(
        db=db,
        invited_by_user_id=admin.id,
        email=str(payload.email),
        expires_in_hours=payload.expires_in_hours,
    )
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=admin.id,
        actor_email=admin.email,
        action="invitation.create",
        entity_type="invitation",
        entity_id=inv.id,
        details={"email": inv.email},
    )
    return InvitationResponse(
        id=inv.id,
        email=inv.email,
        expires_at=inv.expires_at,
        accepted_at=inv.accepted_at,
        revoked_at=inv.revoked_at,
        created_at=inv.created_at,
        token=raw_token,
    )


@router.post(
    "/{invitation_id}/revoke",
    response_model=InvitationResponse,
    summary="Revoke invitation (admin)",
    description="Revoke an invitation so it cannot be accepted.",
)
async def revoke_invitation(
    req: Request,
    invitation_id: uuid.UUID,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> InvitationResponse:
    inv = await revoke_invitation_flow(db=db, invitation_id=invitation_id)
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=admin.id,
        actor_email=admin.email,
        action="invitation.revoke",
        entity_type="invitation",
        entity_id=inv.id,
        details={},
    )
    return InvitationResponse(
        id=inv.id,
        email=inv.email,
        expires_at=inv.expires_at,
        accepted_at=inv.accepted_at,
        revoked_at=inv.revoked_at,
        created_at=inv.created_at,
        token=None,
    )


@router.post(
    "/accept",
    response_model=TokenResponse,
    summary="Accept invitation and signup",
    description="Accept an invitation using the raw token and create a local user. Returns a JWT.",
)
async def accept_invitation(
    req: Request,
    payload: SignupRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    try:
        user = await accept_invitation_and_signup_flow(
            db=db,
            raw_token=payload.token,
            email=str(payload.email),
            password=payload.password,
            display_name=payload.display_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    token = create_access_token(str(user.id), extra_claims={"is_admin": user.is_admin})
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=user.id,
        actor_email=user.email,
        action="invitation.accept",
        entity_type="invitation",
        entity_id=None,
        details={},
    )
    return TokenResponse(access_token=token)
