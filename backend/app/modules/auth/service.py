"""
Module: auth
File responsibility (service.py): authentication business logic --
signup, login, token refresh. Framework-agnostic (no FastAPI imports),
so every method here is unit-tested directly against a DB session
without going through HTTP (see tests/unit/test_auth_service.py).
"""
import uuid

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import UserRepository
from app.modules.tenants.service import TenantService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tenants = TenantService(db)

    def signup_tenant(
        self, tenant_name: str, email: str, password: str, full_name: str | None
    ) -> tuple[User, str, str]:
        if self.users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(f"Email '{email}' is already registered")

        tenant = self.tenants.create_tenant(tenant_name)
        user = User(
            tenant_id=tenant.id,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.OWNER,  # the signer-upper always becomes the owner
        )
        self.users.create(user)
        self.db.commit()
        self.db.refresh(user)

        access = create_access_token(str(user.id), str(user.tenant_id), user.role.value)
        refresh = create_refresh_token(str(user.id), str(user.tenant_id), user.role.value)
        return user, access, refresh

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = self.users.get_by_email(email)
        # Deliberately identical error for "no such email" and "wrong
        # password" -- distinguishing them lets an attacker enumerate
        # which emails are registered. See docs/security.md.
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InvalidCredentialsError("Invalid email or password")

        access = create_access_token(str(user.id), str(user.tenant_id), user.role.value)
        refresh = create_refresh_token(str(user.id), str(user.tenant_id), user.role.value)
        return user, access, refresh

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise InvalidCredentialsError("Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise InvalidCredentialsError("Invalid or expired refresh token")

        try:
            user_id = uuid.UUID(payload["sub"])
            tenant_id = uuid.UUID(payload["tenant_id"])
        except (KeyError, ValueError):
            raise InvalidCredentialsError("Invalid or expired refresh token")

        # Re-derive the user from the DB rather than trusting the refresh
        # token's embedded role/tenant claims -- same principle as
        # get_current_user. A role change or deactivation since the
        # refresh token was issued must take effect immediately.
        user = self.users.get_by_id_for_tenant(user_id, tenant_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Invalid or expired refresh token")

        access = create_access_token(str(user.id), str(user.tenant_id), user.role.value)
        new_refresh = create_refresh_token(str(user.id), str(user.tenant_id), user.role.value)
        return access, new_refresh
