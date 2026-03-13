from __future__ import annotations

from src.api.models.models import AppUser, ResidentPrivacySettings, ResidentProfile
from src.api.schemas.schemas import ResidentProfileResponse, ResidentPrivacySettings as PrivacySchema


def _privacy_to_schema(p: ResidentPrivacySettings | None) -> PrivacySchema:
    if p is None:
        return PrivacySchema()
    return PrivacySchema(
        show_phone=p.show_phone,
        show_email=p.show_email,
        show_address=p.show_address,
        show_photo=p.show_photo,
        allow_messages_from_residents=p.allow_messages_from_residents,
        allow_messages_from_admins=p.allow_messages_from_admins,
    )


# PUBLIC_INTERFACE
def to_privacy_filtered_resident_response(
    *,
    resident: ResidentProfile,
    viewer: AppUser,
) -> ResidentProfileResponse:
    """Convert a ResidentProfile ORM object into a privacy-filtered API response.

    Invariants:
    - Admins see all fields.
    - Residents see their own full record.
    - Others see only fields enabled by resident_privacy_settings.
    """
    privacy = resident.privacy
    is_self = resident.user_id is not None and resident.user_id == viewer.id
    can_view_all = viewer.is_admin or is_self

    show_address = True if can_view_all else bool(privacy.show_address if privacy else False)
    show_phone = True if can_view_all else bool(privacy.show_phone if privacy else False)
    show_email = True if can_view_all else bool(privacy.show_email if privacy else False)
    show_photo = True if can_view_all else bool(privacy.show_photo if privacy else True)

    return ResidentProfileResponse(
        id=resident.id,
        user_id=resident.user_id,
        full_name=resident.full_name,
        unit=resident.unit,
        address_line1=resident.address_line1 if show_address else None,
        address_line2=resident.address_line2 if show_address else None,
        city=resident.city if show_address else None,
        state=resident.state if show_address else None,
        postal_code=resident.postal_code if show_address else None,
        phone=resident.phone if show_phone else None,
        email_public=resident.email_public if show_email else None,
        bio=resident.bio,
        photo_object_key=resident.photo_object_key if show_photo else None,
        privacy=_privacy_to_schema(privacy),
        created_at=resident.created_at,
        updated_at=resident.updated_at,
    )
