"""
Responsibility: the background job that turns an uploaded document into
searchable, tenant-isolated vectors in Qdrant.

Pipeline: extract -> clean -> chunk -> embed -> upsert to Qdrant ->
persist DocumentChunk rows -> mark the Document indexed (or failed).

_process_document() is a plain function, separate from the @celery_app.task
wrapper, so tests can call it directly without going through Celery's
task-dispatch machinery at all if they want to (most tests instead call
process_document_task.delay() with CELERY_TASK_ALWAYS_EAGER=true, which
exercises the real task wrapper too -- see tests/conftest.py).
"""
import uuid

from app.core.ai.embeddings import get_embedding_provider
from app.core.ai.vector_store import VectorStore
from app.db.session import SessionLocal
from app.modules.documents.chunking import chunk_text, clean_text, approximate_token_count
from app.modules.documents.extraction import extract_text
from app.modules.documents.models import Document, DocumentChunk, DocumentStatus
from app.modules.documents.repository import DocumentRepository
from app.core.config import settings
from app.workers.celery_app import celery_app


def _process_document(document_id: uuid.UUID, *, vector_store: VectorStore | None = None) -> None:
    """vector_store is injectable so tests can pass an embedded
    QdrantClient(":memory:")-backed instance instead of connecting to a
    real Qdrant server. Production (the real Celery task below) always
    uses the default, which connects to settings.qdrant_url."""
    db = SessionLocal()
    repo = DocumentRepository(db)
    store = vector_store or VectorStore()

    try:
        # Re-fetch from the DB by id -- the row's own tenant_id is the
        # only tenant_id this function trusts. See the docstring on
        # DocumentRepository.get_for_processing.
        document = repo.get_for_processing(document_id)
        if document is None:
            # Document was deleted between enqueue and processing.
            # Nothing to do -- not an error, just a no-op.
            return

        repo.update_status(document, status=DocumentStatus.PROCESSING)
        db.commit()

        try:
            raw_text = extract_text(content_type=document.content_type, raw_content=document.raw_content)
            cleaned = clean_text(raw_text)
            chunks = chunk_text(cleaned, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)

            if not chunks:
                raise ValueError("Document produced zero chunks after cleaning (empty or whitespace-only content)")

            embedder = get_embedding_provider()
            vectors = embedder.embed_texts(chunks)

            # Any previous chunks/vectors for this document are cleared
            # first, so re-processing a document (e.g. a future
            # "reprocess" admin action) doesn't leave stale duplicates
            # behind in either Postgres or Qdrant.
            repo.delete_chunks_for_document(document.id, document.tenant_id)
            store.delete_document_chunks(tenant_id=document.tenant_id, document_id=document.id)

            point_ids = [uuid.uuid4() for _ in chunks]
            store.upsert_chunks(
                tenant_id=document.tenant_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                chunks=list(zip(point_ids, chunks, vectors)),
            )

            chunk_rows = [
                DocumentChunk(
                    tenant_id=document.tenant_id,
                    knowledge_base_id=document.knowledge_base_id,
                    document_id=document.id,
                    chunk_index=i,
                    content=chunk_content,
                    token_count=approximate_token_count(chunk_content),
                    qdrant_point_id=point_id,
                )
                for i, (chunk_content, point_id) in enumerate(zip(chunks, point_ids))
            ]
            repo.add_chunks(chunk_rows)

            repo.update_status(
                document,
                status=DocumentStatus.INDEXED,
                chunk_count=len(chunks),
                clear_raw_content=True,
            )
            db.commit()

        except Exception as exc:  # noqa: BLE001 - worker boundary
            # If Qdrant accepted vectors but a later DB write failed, remove
            # the vectors as compensation. This is not a distributed
            # transaction; it is a best-effort cleanup that prevents stale
            # failed-document vectors from becoming retrievable.
            try:
                store.delete_document_chunks(
                    tenant_id=document.tenant_id,
                    document_id=document.id,
                )
            except Exception:
                # Preserve the original processing failure. An operator can
                # reconcile Qdrant later; see docs/final-engineering-review.md.
                pass
            db.rollback()
            document = repo.get_for_processing(document_id)
            if document is not None:
                repo.update_status(
                    document,
                    status=DocumentStatus.FAILED,
                    error_message=str(exc),
                    clear_raw_content=True,
                )
                db.commit()
    finally:
        db.close()


@celery_app.task(name="documents.process_document")
def process_document_task(document_id: str) -> None:
    _process_document(uuid.UUID(document_id))
