"""
Module: tenants
Purpose: the root entity of the multi-tenancy hierarchy.

Every other tenant-owned table has a tenant_id FK pointing here, with
ON DELETE CASCADE -- deleting a tenant cleanly removes all its data
rather than leaving orphaned rows (see docs/database.md, added later,
for why cascade-delete is acceptable here vs. soft-delete elsewhere).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # slug: URL/routing-safe identifier, unique platform-wide. Not currently
    # used for tenant resolution (auth is email-based in v1 -- see
    # modules/auth/models.py docstring) but reserved for a future
    # subdomain-per-tenant or /t/{slug}/ routing scheme.
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
