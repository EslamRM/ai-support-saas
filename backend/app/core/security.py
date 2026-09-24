"""
Responsibility: password hashing (bcrypt) and JWT encode/decode.

This module knows HOW to create/verify tokens and hash/verify passwords.
It does NOT know about users, tenants, or the database -- that belongs in
modules/auth/service.py. Keeping this generic makes it independently
testable and reusable if the auth strategy changes later (e.g. SSO).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def _create_token(
    subject: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta,
    token_type: Literal["access", "refresh"],
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        # jti gives every token a unique id -- useful later if we add a
        # revocation/blocklist for refresh tokens (not implemented in v1;
        # see docs/security.md "known limitations").
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    return _create_token(
        user_id, tenant_id, role,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def create_refresh_token(user_id: str, tenant_id: str, role: str) -> str:
    return _create_token(
        user_id, tenant_id, role,
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def decode_token(token: str) -> dict[str, Any]:
    """Raises jose.JWTError on invalid/expired/tampered tokens. The caller
    (core/dependencies.py) is responsible for mapping that to a 401 --
    this module stays HTTP-agnostic."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
