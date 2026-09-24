"""
Responsibility: SQLAlchemy declarative base + the tenant-scoping mixin.

TenantScopedBase is the structural enforcement of multi-tenancy: every
table that inherits it gets an indexed, non-nullable tenant_id column by
construction. A developer adding a new tenant-owned table has to actively
choose NOT to inherit this to create an isolation gap -- the safe path is
the default path.

id/tenant_id use SQLAlchemy's generic Uuid type (not the Postgres-specific
dialect type) so the same models work against SQLite in tests and
Postgres in production -- see backend/tests/conftest.py.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantScopedBase(Base):
    """Abstract base for every tenant-owned table (users, documents,
    conversations, tickets, etc). NOT used for the tenants table itself,
    which is the root of the hierarchy."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
