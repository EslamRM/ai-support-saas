"""
Module: documents
File responsibility (service.py): document upload orchestration.

upload_document() does the MINIMUM synchronous work: validate, persist
the Document row (status=pending) with raw bytes, commit, and enqueue
the background job. It deliberately does NOT extract/chunk/embed inline
-- that's workers/document_tasks.py's job, kept separate so the API
request returns immediately regardless of document size (see
docs/architecture.md background-processing flow).
"""
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DomainError
from app.modules.documents.models import Document, DocumentStatus
from app.modules.documents.repository import DocumentRepository
from app.modules.knowledge_base.service import KnowledgeBaseService


class FileTooLargeError(DomainError):
    pass


class UnsupportedFileTypeError(DomainError):
    pass


class DocumentNotFoundError(DomainError):
    pass


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DocumentRepository(db)
        self.kb_service = KnowledgeBaseService(db)

    def upload_document(
        self,
        *,
        tenant_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        filename: str,
        content_type: str,
        raw_content: bytes,
    ) -> Document:
        # Confirms the KB exists AND belongs to this tenant before
        # accepting the upload -- raises KnowledgeBaseNotFoundError
        # (a DomainError -> 404) otherwise. This is the IDOR check for
        # this endpoint: without it, a caller could upload a document
        # into ANY knowledge_base_id, including another tenant's.
        self.kb_service.get_or_404(knowledge_base_id, tenant_id)

        if content_type not in settings.allowed_upload_content_types:
            raise UnsupportedFileTypeError(f"Unsupported content type: {content_type}")
        if len(raw_content) > settings.max_upload_size_bytes:
            raise FileTooLargeError(
                f"File exceeds max upload size of {settings.max_upload_size_bytes} bytes"
            )

        document = Document(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            content_type=content_type,
            status=DocumentStatus.PENDING,
            raw_content=raw_content,
        )
        self.repo.create(document)
        self.db.commit()
        self.db.refresh(document)

        # Enqueue background processing. In production this hits Redis
        # and a separate worker process picks it up (docker-compose.yml's
        # `worker` service) -- the refresh below is then a no-op, since
        # the task genuinely hasn't run yet. In tests,
        # settings.celery_task_always_eager makes .delay() run
        # synchronously in-process (see workers/celery_app.py and
        # tests/conftest.py), so by the time .delay() returns the
        # document may already be indexed/failed -- refreshing avoids
        # returning a stale in-memory snapshot from before processing ran.
        from app.workers.document_tasks import process_document_task

        process_document_task.delay(str(document.id))
        self.db.refresh(document)

        return document

    def list_for_knowledge_base(self, kb_id: uuid.UUID, tenant_id: uuid.UUID) -> list[Document]:
        self.kb_service.get_or_404(kb_id, tenant_id)
        return self.repo.list_for_knowledge_base(kb_id, tenant_id)

    def get_or_404(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> Document:
        document = self.repo.get_by_id_for_tenant(document_id, tenant_id)
        if document is None:
            raise DocumentNotFoundError("Document not found")
        return document
