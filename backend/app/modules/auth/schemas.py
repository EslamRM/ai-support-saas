"""
Module: auth
File responsibility (schemas.py): API request/response models.
"""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.auth.models import UserRole


class TenantSignupRequest(BaseModel):
    """Creates a brand-new tenant AND its first user (the owner) in one
    call. This is the only way to create a user without already being
    authenticated -- every subsequent user is invited by an
    owner/admin within an authenticated, tenant-scoped request (added
    when the dashboard needs a "team members" page)."""

    tenant_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
