"""
Module: tenants
File responsibility (service.py): tenant lifecycle business logic.
Currently just slug generation + creation, called from
modules/auth/service.py during signup. Tenant settings/plan/limits are
added when billing/usage limits are implemented (out of v1 scope --
see docs/architecture.md system boundaries).
"""
import re
import uuid

from sqlalchemy.orm import Session

from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


class TenantService:
    def __init__(self, db: Session):
        self.repo = TenantRepository(db)

    def create_tenant(self, name: str) -> Tenant:
        base_slug = _slugify(name)
        slug = base_slug
        suffix = 1
        # Handle slug collisions (e.g. two tenants both named "Acme").
        # Fine at current scale; if signups become high-volume this
        # should move to a DB-level retry-on-conflict instead of a
        # check-then-insert loop (a TOCTOU race is possible under
        # concurrent signups with the same name).
        while self.repo.get_by_slug(slug) is not None:
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        tenant = Tenant(name=name, slug=slug)
        return self.repo.create(tenant)
