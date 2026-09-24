"""
Module: knowledge_base
File responsibility (service.py): knowledge base business logic.
Thin for now (plain CRUD) -- this module's real complexity is in
modules/documents (the ingestion pipeline that populates a KB).
"""
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.modules.knowledge_base.models import KnowledgeBase
from app.modules.knowledge_base.repository import KnowledgeBaseRepository


class KnowledgeBaseNotFoundError(DomainError):
    pass


class KnowledgeBaseService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = KnowledgeBaseRepository(db)

    def create(self, tenant_id: uuid.UUID, name: str, description: str | None) -> KnowledgeBase:
        kb = KnowledgeBase(tenant_id=tenant_id, name=name, description=description)
        self.repo.create(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def list_for_tenant(self, tenant_id: uuid.UUID) -> list[KnowledgeBase]:
        return self.repo.list_for_tenant(tenant_id)

    def get_or_404(self, kb_id: uuid.UUID, tenant_id: uuid.UUID) -> KnowledgeBase:
        kb = self.repo.get_by_id_for_tenant(kb_id, tenant_id)
        if kb is None:
            raise KnowledgeBaseNotFoundError("Knowledge base not found")
        return kb
