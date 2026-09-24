"""
Module: tenants
File responsibility (repository.py): all queries for the tenants table.
Note tenants is the ROOT of the hierarchy -- it has no tenant_id of its
own to filter by, unlike every other repository in this codebase.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tenants.models import Tenant


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_slug(self, slug: str) -> Tenant | None:
        return self.db.scalar(select(Tenant).where(Tenant.slug == slug))

    def get_by_id(self, tenant_id) -> Tenant | None:
        return self.db.get(Tenant, tenant_id)

    def create(self, tenant: Tenant) -> Tenant:
        self.db.add(tenant)
        self.db.flush()
        return tenant
