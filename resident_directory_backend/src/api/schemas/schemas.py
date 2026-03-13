from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type (always 'bearer')")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")


class SignupRequest(BaseModel):
    token: str = Field(..., description="Raw invitation token")
    email: EmailStr = Field(..., description="Invited email (must match invitation)")
    password: str = Field(..., min_length=8, description="New password")
    display_name: str | None = Field(None, description="Optional display name")


class MeResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_admin: bool
    roles: list[str] = []
    display_name: str | None = None


class ResidentPrivacySettings(BaseModel):
    show_phone: bool = False
    show_email: bool = False
    show_address: bool = False
    show_photo: bool = True
    allow_messages_from_residents: bool = True
    allow_messages_from_admins: bool = True


class ResidentProfileBase(BaseModel):
    full_name: str = Field(..., min_length=1, description="Resident full name")
    unit: str | None = Field(None, description="Unit/apartment identifier")
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    email_public: EmailStr | None = Field(None, description="Optional public contact email")
    bio: str | None = None


class ResidentProfileCreate(ResidentProfileBase):
    user_id: uuid.UUID | None = Field(None, description="Link to an existing app user (admin only)")


class ResidentProfileUpdate(BaseModel):
    full_name: str | None = None
    unit: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    email_public: EmailStr | None = None
    bio: str | None = None
    privacy: ResidentPrivacySettings | None = None


class ResidentProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    full_name: str
    unit: str | None

    # privacy-filtered fields (may be None even if stored)
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    email_public: EmailStr | None = None

    bio: str | None = None
    photo_object_key: str | None = None

    privacy: ResidentPrivacySettings
    created_at: datetime
    updated_at: datetime


class InvitationCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Email to invite")
    expires_in_hours: int = Field(72, ge=1, le=720, description="Invitation expiry window in hours")


class InvitationResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    # Only returned on create for admins
    token: str | None = Field(None, description="Raw invitation token (only returned once)")


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Announcement title")
    body: str = Field(..., min_length=1, description="Announcement body")
    is_pinned: bool = Field(False, description="Whether announcement is pinned")
    visibility: Literal["all", "residents", "admins"] = Field("all", description="Visibility segment")
    publish: bool = Field(True, description="If true, sets published_at to now")


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    is_pinned: bool | None = None
    visibility: Literal["all", "residents", "admins"] | None = None
    publish: bool | None = None  # True -> publish now, False -> unpublish


class AnnouncementResponse(BaseModel):
    id: uuid.UUID
    created_by: uuid.UUID | None
    title: str
    body: str
    is_pinned: bool
    visibility: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DirectorySearchResponse(BaseModel):
    items: list[ResidentProfileResponse]
    total: int
