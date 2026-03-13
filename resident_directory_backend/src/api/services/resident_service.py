from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.models import ResidentPrivacySettings, ResidentProfile
from src.api.schemas.schemas import ResidentProfileCreate, ResidentProfileUpdate


# PUBLIC_INTERFACE
async def ensure_privacy_settings_flow(*, db: AsyncSession, resident_id: uuid.UUID) -> ResidentPrivacySettings:
    """Ensure resident has a privacy settings row (creates defaults if missing)."""
    result = await db.execute(select(ResidentPrivacySettings).where(ResidentPrivacySettings.resident_id == resident_id))
    privacy = result.scalar_one_or_none()
    if privacy:
        return privacy
    privacy = ResidentPrivacySettings(resident_id=resident_id)
    db.add(privacy)
    await db.commit()
    await db.refresh(privacy)
    return privacy


# PUBLIC_INTERFACE
async def create_resident_profile_flow(*, db: AsyncSession, payload: ResidentProfileCreate) -> ResidentProfile:
    """Create a resident profile and default privacy settings."""
    resident = ResidentProfile(
        user_id=payload.user_id,
        full_name=payload.full_name,
        unit=payload.unit,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        phone=payload.phone,
        email_public=str(payload.email_public) if payload.email_public else None,
        bio=payload.bio,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(resident)
    await db.flush()
    db.add(ResidentPrivacySettings(resident_id=resident.id))
    await db.commit()
    await db.refresh(resident)
    return resident


# PUBLIC_INTERFACE
async def update_resident_profile_flow(
    *,
    db: AsyncSession,
    resident_id: uuid.UUID,
    payload: ResidentProfileUpdate,
) -> ResidentProfile:
    """Update resident profile fields and optional privacy settings."""
    result = await db.execute(select(ResidentProfile).where(ResidentProfile.id == resident_id))
    resident = result.scalar_one()

    for field in [
        "full_name",
        "unit",
        "address_line1",
        "address_line2",
        "city",
        "state",
        "postal_code",
        "phone",
        "email_public",
        "bio",
    ]:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(resident, field, str(value) if field == "email_public" else value)

    resident.updated_at = datetime.now(timezone.utc)

    if payload.privacy is not None:
        privacy = await ensure_privacy_settings_flow(db=db, resident_id=resident.id)
        privacy.show_phone = payload.privacy.show_phone
        privacy.show_email = payload.privacy.show_email
        privacy.show_address = payload.privacy.show_address
        privacy.show_photo = payload.privacy.show_photo
        privacy.allow_messages_from_residents = payload.privacy.allow_messages_from_residents
        privacy.allow_messages_from_admins = payload.privacy.allow_messages_from_admins
        privacy.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(resident)
    return resident


# PUBLIC_INTERFACE
async def delete_resident_profile_flow(*, db: AsyncSession, resident_id: uuid.UUID) -> None:
    """Delete a resident profile (privacy settings cascade)."""
    result = await db.execute(select(ResidentProfile).where(ResidentProfile.id == resident_id))
    resident = result.scalar_one()
    await db.delete(resident)
    await db.commit()


# PUBLIC_INTERFACE
async def search_directory_flow(
    *,
    db: AsyncSession,
    query: str | None,
    unit: str | None,
    limit: int,
    offset: int,
) -> tuple[list[ResidentProfile], int]:
    """Search/filter resident directory by name or unit with pagination."""
    stmt = select(ResidentProfile).order_by(ResidentProfile.full_name.asc())
    count_stmt = select(func.count()).select_from(ResidentProfile)

    filters = []
    if query:
        q = f"%{query.strip()}%"
        filters.append(or_(ResidentProfile.full_name.ilike(q), ResidentProfile.email_public.ilike(q)))
    if unit:
        filters.append(ResidentProfile.unit == unit)

    if filters:
        for f in filters:
            stmt = stmt.where(f)
            count_stmt = count_stmt.where(f)

    total = (await db.execute(count_stmt)).scalar_one()
    items = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()
    return items, int(total)
