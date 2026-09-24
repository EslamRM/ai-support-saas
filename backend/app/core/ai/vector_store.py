"""
Responsibility: the ONLY place in the codebase that talks to Qdrant.

Every read/write method requires tenant_id AND knowledge_base_id as
mandatory keyword arguments and bakes them into the Qdrant filter itself
-- there is no method signature that allows a query without them. This
is the structural defense against "vector store leakage", the isolation
vulnerability class named in docs/architecture.md: a bug elsewhere might
forget to pass the right tenant_id, but it cannot construct a search that
skips the filter entirely, because the filter isn't optional here.
"""
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.core.reliability import retry_call

COLLECTION_NAME = "document_chunks"


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float


class VectorStore:
    def __init__(self, client: QdrantClient | None = None, vector_size: int = 1536):
        # Production: connects to the real Qdrant server at
        # settings.qdrant_url (docker-compose.yml's qdrant service).
        # Tests: inject an embedded QdrantClient(":memory:") instead, so
        # the ingestion + retrieval pipeline runs for real without a
        # running Qdrant container -- see tests/conftest.py.
        self._client = client or QdrantClient(url=settings.qdrant_url, timeout=settings.retrieval_timeout_seconds)
        self._vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if COLLECTION_NAME not in existing:
            self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=qmodels.VectorParams(size=self._vector_size, distance=qmodels.Distance.COSINE),
            )

    def upsert_chunks(
        self,
        *,
        tenant_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
        chunks: list[tuple[uuid.UUID, str, list[float]]],
    ) -> None:
        """chunks: list of (point_id, chunk_text, embedding_vector), one
        per chunk, already the same order/length as the chunk list the
        caller generated."""
        points = [
            qmodels.PointStruct(
                id=str(point_id),
                vector=vector,
                payload={
                    "tenant_id": str(tenant_id),
                    "knowledge_base_id": str(knowledge_base_id),
                    "document_id": str(document_id),
                    "content": text,
                },
            )
            for point_id, text, vector in chunks
        ]
        retry_call(
            "qdrant.upsert",
            lambda: self._client.upsert(collection_name=COLLECTION_NAME, points=points),
            max_attempts=settings.ai_max_attempts,
            base_delay=settings.ai_retry_base_delay_seconds,
            max_delay=settings.ai_retry_max_delay_seconds,
        )

    def search(
        self,
        *,
        tenant_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_vector: list[float],
        top_k: int,
        score_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(key="tenant_id", match=qmodels.MatchValue(value=str(tenant_id))),
                qmodels.FieldCondition(
                    key="knowledge_base_id", match=qmodels.MatchValue(value=str(knowledge_base_id))
                ),
            ]
        )
        result = retry_call(
            "qdrant.search",
            lambda: self._client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=score_threshold,
            ),
            max_attempts=settings.ai_max_attempts,
            base_delay=settings.ai_retry_base_delay_seconds,
            max_delay=settings.ai_retry_max_delay_seconds,
        )
        return [
            RetrievedChunk(
                chunk_id=uuid.UUID(str(point.id)),
                document_id=uuid.UUID(point.payload["document_id"]),
                content=point.payload["content"],
                score=point.score,
            )
            for point in result.points
        ]

    def delete_document_chunks(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        """Called when a document is deleted or re-processed, so stale
        vectors don't linger and get retrieved after the source document
        is gone."""
        self._client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="tenant_id", match=qmodels.MatchValue(value=str(tenant_id))),
                        qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=str(document_id))),
                    ]
                )
            ),
        )
