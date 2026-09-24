"""
Module: knowledge_base
File responsibility (repository.py): all queries for the knowledge_bases
table. Every method takes tenant_id and filters by it -- there is no
"get by id" that skips the tenant check.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.knowledge_base.models import KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, kb: KnowledgeBase) -> KnowledgeBase:
        self.db.add(kb)
        self.db.flush()
        return kb

    def get_by_id_for_tenant(self, kb_id: uuid.UUID, tenant_id: uuid.UUID) -> KnowledgeBase | None:
        return self.db.scalar(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id)
        )

    def list_for_tenant(self, tenant_id: uuid.UUID) -> list[KnowledgeBase]:
        return list(
            self.db.scalars(
                select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant_id).order_by(KnowledgeBase.created_at)
            )
        )
