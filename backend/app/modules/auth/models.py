"""
Module: auth
Purpose: the User model and role definition.

DESIGN DECISION -- email is globally unique across the whole platform,
NOT scoped per-tenant. This means one person/email can belong to exactly
ONE tenant in v1. The alternative (email scoped per-tenant, like Slack
workspaces where you pick a workspace before logging in) would let one
person belong to multiple tenants, but requires a tenant-selection step
before authentication and a separate membership table. That's real
complexity with no current requirement driving it -- see
docs/adr/ADR-007-multi-tenancy.md for the full trade-off writeup.
Consequence: login is just (email, password) -- no tenant slug needed.

DESIGN DECISION -- role is a plain enum column on User, not a full
Role/Permission table. Three fixed roles (owner/admin/agent) with a
simple rank-based hierarchy (see core/dependencies.require_role) covers
every RBAC need this product currently has. A full Role/Permission schema
is the right call when permissions become tenant-configurable (e.g. a
tenant admin defining custom roles) -- premature now. This is the
"do not blindly normalize everything" trade-off called out in Phase 1.
"""
import enum

from sqlalchemy import Boolean, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TenantScopedBase


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    AGENT = "agent"


class User(TenantScopedBase):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True), nullable=False, default=UserRole.AGENT
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
