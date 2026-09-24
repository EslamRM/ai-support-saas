"""
Module: documents
File responsibility (repository.py): all queries for documents and
document_chunks. Every method is tenant-scoped.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.documents.models import Document, DocumentChunk, DocumentStatus


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def get_by_id_for_tenant(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> Document | None:
        return self.db.scalar(
            select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
        )

    def get_for_processing(self, document_id: uuid.UUID) -> Document | None:
        """Deliberately NOT tenant-scoped by a caller-supplied tenant_id --
        this is called from the background worker, which has only a
        document_id (see workers/document_tasks.py). The row's own
        tenant_id IS the source of truth here; there's nothing to compare
        it against except itself. This is the document-processing
        instance of the "re-derive from the DB, don't trust the payload"
        pattern discussed in docs/architecture.md background-processing
        section."""
        return self.db.get(Document, document_id)

    def list_for_knowledge_base(self, kb_id: uuid.UUID, tenant_id: uuid.UUID) -> list[Document]:
        return list(
            self.db.scalars(
                select(Document)
                .where(Document.knowledge_base_id == kb_id, Document.tenant_id == tenant_id)
                .order_by(Document.created_at.desc())
            )
        )

    def update_status(
        self,
        document: Document,
        *,
        status: DocumentStatus,
        error_message: str | None = None,
        chunk_count: int | None = None,
        clear_raw_content: bool = False,
    ) -> Document:
        document.status = status
        document.error_message = error_message
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if clear_raw_content:
            document.raw_content = None
        self.db.add(document)
        self.db.flush()
        return document

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        self.db.add_all(chunks)
        self.db.flush()

    def delete_chunks_for_document(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        chunks = self.db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document_id, DocumentChunk.tenant_id == tenant_id
            )
        )
        for chunk in chunks:
            self.db.delete(chunk)
        self.db.flush()
