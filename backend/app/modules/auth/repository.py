"""
Module: auth
File responsibility (repository.py): all queries for the users table.

NOTE: get_by_email is intentionally NOT filtered by tenant_id, because
email is globally unique in v1 and login happens BEFORE tenant context
exists (see auth/models.py docstring for the design decision). Every
other lookup here IS tenant-scoped -- that asymmetry is deliberate, not
an oversight, and it's the only place in the codebase a users query
skips the tenant filter.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def get_by_id_for_tenant(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User | None:
        return self.db.scalar(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
