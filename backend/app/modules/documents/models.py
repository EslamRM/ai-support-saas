"""
Module: documents
File responsibility (models.py): Document (one uploaded file) and
DocumentChunk (one chunk of that file, after processing).

DESIGN DECISION -- raw_content (the uploaded file's bytes) is stored
directly in Postgres (LargeBinary) rather than on local disk or S3.
This avoids needing extra infrastructure for a portfolio project; at
real scale this column would move to object storage (S3-compatible),
with `raw_content` replaced by a `storage_key` pointer -- see
docs/scaling.md (added later). raw_content is cleared (set to NULL)
once a document reaches INDEXED or FAILED status, specifically so the
table doesn't grow unbounded with binary blobs that are no longer
needed after their chunks are embedded.

DESIGN DECISION -- DocumentChunk stores the chunk's full text in
Postgres AS WELL AS in Qdrant's payload. This is deliberate duplication:
the dashboard can display/debug chunks without a Qdrant round-trip, and
chunk content survives even if Qdrant is temporarily unavailable. The
trade-off is storage duplication and a second place that could drift out
of sync -- acceptable at this data volume; revisit if documents get
large enough for this to matter (see docs/rag.md).
"""
import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TenantScopedBase


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(TenantScopedBase):
    __tablename__ = "documents"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), nullable=False, default=DocumentStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class DocumentChunk(TenantScopedBase):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalized from the parent document -- lets retrieval-adjacent
    # queries filter chunks by (tenant_id, knowledge_base_id) directly,
    # without a join through documents, matching the exact filter shape
    # VectorStore.search() uses in Qdrant. A deliberate denormalization,
    # not an oversight -- see docs/database.md query-pattern notes.
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # The point ID this chunk was upserted into Qdrant under -- lets us
    # delete/re-upsert the exact matching vector without a text-based
    # lookup, and lets debugging cross-reference a Postgres row to its
    # Qdrant point directly.
    qdrant_point_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
