"""
Responsibility: shared FastAPI dependencies -- authentication and RBAC.

get_current_user is the ONE place a JWT is turned into an authenticated,
tenant-scoped User. Every protected route depends on it (directly or via
require_role). Read this file's docstring on get_current_user carefully --
it's the answer to "why re-validate against the DB instead of trusting
the token".
"""
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.core.tenancy import TenantContext, set_current_tenant
from app.db.session import get_db
from app.modules.auth.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Simple rank-based hierarchy: owner > admin > agent. See auth/models.py
# for why this is a plain enum rather than a Role/Permission table.
_ROLE_RANK: dict[UserRole, int] = {
    UserRole.AGENT: 0,
    UserRole.ADMIN: 1,
    UserRole.OWNER: 2,
}


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_error

    if payload.get("type") != "access":
        # Rejects a refresh token being used as an access token, and vice
        # versa -- the two must not be interchangeable.
        raise credentials_error

    raw_user_id = payload.get("sub")
    raw_tenant_id = payload.get("tenant_id")
    if raw_user_id is None or raw_tenant_id is None:
        raise credentials_error

    try:
        user_id = uuid.UUID(raw_user_id)
    except ValueError:
        raise credentials_error

    # CRITICAL: re-fetch the user from the database rather than trusting
    # the JWT's claims at face value. This is the same principle as the
    # Celery job tenant_id re-validation: a token is a claim, not a fact.
    # Re-fetching means:
    #  - a deactivated user (is_active=False) is rejected even with a
    #    still-valid, not-yet-expired token
    #  - the token's tenant_id claim is cross-checked against the DB row's
    #    OWN tenant_id, so a forged or stale tenant_id claim is caught
    #    here rather than silently trusted downstream
    user = db.get(User, user_id)
    if user is None or not user.is_active or str(user.tenant_id) != raw_tenant_id:
        raise credentials_error

    # Set for structured-logging enrichment ONLY -- see core/tenancy.py
    # docstring. Authorization already happened above using `user` itself.
    set_current_tenant(TenantContext(tenant_id=user.tenant_id, user_id=user.id, role=user.role.value))

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(minimum: UserRole):
    """Returns a FastAPI dependency that 403s unless the current user's
    role rank is >= the minimum required rank. Usage:

        @router.post("/documents", dependencies=[Depends(require_role(UserRole.ADMIN))])

    or, to also get the User object in the handler:

        def upload(user: Annotated[User, Depends(require_role(UserRole.ADMIN))]): ...
    """

    def _check(user: CurrentUser) -> User:
        if _ROLE_RANK[user.role] < _ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{minimum.value}' or higher",
            )
        return user

    return _check
