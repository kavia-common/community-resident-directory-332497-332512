from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.security import hash_password
from src.api.models.models import AppUser, Invitation, OnboardingEvent


def _hash_token(raw_token: str) -> str:
    # Store only the hash to avoid leaking raw tokens if DB is compromised.
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# PUBLIC_INTERFACE
async def create_invitation_flow(
    *,
    db: AsyncSession,
    invited_by_user_id: uuid.UUID,
    email: str,
    expires_in_hours: int,
) -> tuple[Invitation, str]:
    """Create an invitation and return (invitation_row, raw_token)."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    inv = Invitation(
        email=email,
        invited_by_user_id=invited_by_user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
    )
    db.add(inv)
    await db.flush()

    db.add(
        OnboardingEvent(
            invitation_id=inv.id,
            user_id=None,
            event_type="invited",
            event_data={"email": email},
        )
    )
    await db.commit()
    await db.refresh(inv)
    return inv, raw_token


# PUBLIC_INTERFACE
async def revoke_invitation_flow(*, db: AsyncSession, invitation_id: uuid.UUID) -> Invitation:
    """Revoke an invitation by setting revoked_at."""
    result = await db.execute(select(Invitation).where(Invitation.id == invitation_id))
    inv = result.scalar_one()
    inv.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(inv)
    db.add(
        OnboardingEvent(
            invitation_id=inv.id,
            user_id=None,
            event_type="revoked",
            event_data={},
        )
    )
    await db.commit()
    return inv


# PUBLIC_INTERFACE
async def accept_invitation_and_signup_flow(
    *,
    db: AsyncSession,
    raw_token: str,
    email: str,
    password: str,
    display_name: str | None,
) -> AppUser:
    """Accept invitation and create a local user account.

    Errors raised:
    - ValueError for invalid token/email/expired/revoked/already accepted
    """
    token_hash = _hash_token(raw_token)
    result = await db.execute(select(Invitation).where(Invitation.token_hash == token_hash))
    inv = result.scalar_one_or_none()
    if not inv:
        raise ValueError("Invalid invitation token")
    if inv.email.lower() != email.lower():
        raise ValueError("Invitation email mismatch")
    now = datetime.now(timezone.utc)
    if inv.expires_at < now:
        raise ValueError("Invitation expired")
    if inv.revoked_at is not None:
        raise ValueError("Invitation revoked")
    if inv.accepted_at is not None:
        raise ValueError("Invitation already accepted")

    # Create user
    user = AppUser(
        email=email,
        password_hash=hash_password(password),
        auth_provider="local",
        is_active=True,
        is_admin=False,
        display_name=display_name,
    )
    db.add(user)
    await db.flush()

    inv.accepted_at = now
    db.add(
        OnboardingEvent(
            invitation_id=inv.id,
            user_id=user.id,
            event_type="accepted",
            event_data={},
        )
    )
    await db.commit()
    await db.refresh(user)
    return user
