from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db_session
from src.api.deps.auth import get_current_user, require_admin
from src.api.models.models import AppUser, ResidentProfile
from src.api.schemas.schemas import (
    DirectorySearchResponse,
    ResidentProfileCreate,
    ResidentProfileResponse,
    ResidentProfileUpdate,
)
from src.api.services.audit_service import write_audit_log
from src.api.services.privacy_service import to_privacy_filtered_resident_response
from src.api.services.resident_service import (
    create_resident_profile_flow,
    delete_resident_profile_flow,
    search_directory_flow,
    update_resident_profile_flow,
)

router = APIRouter(prefix="/residents", tags=["Residents"])


@router.get(
    "/directory",
    response_model=DirectorySearchResponse,
    summary="Directory search",
    description="Search and filter resident directory. Privacy is enforced per resident settings.",
)
async def directory_search(
    q: str | None = None,
    unit: str | None = None,
    limit: int = 20,
    offset: int = 0,
    viewer: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DirectorySearchResponse:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    residents, total = await search_directory_flow(db=db, query=q, unit=unit, limit=limit, offset=offset)
    return DirectorySearchResponse(
        items=[to_privacy_filtered_resident_response(resident=r, viewer=viewer) for r in residents],
        total=total,
    )


@router.post(
    "",
    response_model=ResidentProfileResponse,
    summary="Create resident profile (admin)",
    description="Create a resident profile. Admin-only. Privacy defaults are created automatically.",
)
async def create_resident(
    req: Request,
    payload: ResidentProfileCreate,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResidentProfileResponse:
    resident = await create_resident_profile_flow(db=db, payload=payload)
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=admin.id,
        actor_email=admin.email,
        action="resident.create",
        entity_type="resident_profile",
        entity_id=resident.id,
        details={"full_name": resident.full_name},
    )
    return to_privacy_filtered_resident_response(resident=resident, viewer=admin)


@router.get(
    "/{resident_id}",
    response_model=ResidentProfileResponse,
    summary="Get resident profile",
    description="Get a resident profile by id, with privacy enforcement for the viewer.",
)
async def get_resident(
    resident_id: uuid.UUID,
    viewer: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ResidentProfileResponse:
    result = await db.execute(select(ResidentProfile).where(ResidentProfile.id == resident_id))
    resident = result.scalar_one_or_none()
    if not resident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    return to_privacy_filtered_resident_response(resident=resident, viewer=viewer)


@router.patch(
    "/{resident_id}",
    response_model=ResidentProfileResponse,
    summary="Update resident profile",
    description="Update a resident profile. Admins can update any profile; residents can update their own.",
)
async def update_resident(
    req: Request,
    resident_id: uuid.UUID,
    payload: ResidentProfileUpdate,
    viewer: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ResidentProfileResponse:
    result = await db.execute(select(ResidentProfile).where(ResidentProfile.id == resident_id))
    resident = result.scalar_one_or_none()
    if not resident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    is_self = resident.user_id is not None and resident.user_id == viewer.id
    if not (viewer.is_admin or is_self):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    resident = await update_resident_profile_flow(db=db, resident_id=resident_id, payload=payload)
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=viewer.id,
        actor_email=viewer.email,
        action="resident.update",
        entity_type="resident_profile",
        entity_id=resident.id,
        details={},
    )
    return to_privacy_filtered_resident_response(resident=resident, viewer=viewer)


@router.delete(
    "/{resident_id}",
    status_code=204,
    summary="Delete resident profile (admin)",
    description="Delete a resident profile (admin-only).",
)
async def delete_resident(
    req: Request,
    resident_id: uuid.UUID,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    await delete_resident_profile_flow(db=db, resident_id=resident_id)
    await write_audit_log(
        db=db,
        request=req,
        actor_user_id=admin.id,
        actor_email=admin.email,
        action="resident.delete",
        entity_type="resident_profile",
        entity_id=resident_id,
        details={},
    )
    return None
