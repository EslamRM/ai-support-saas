"""
Node: retrieve_knowledge

Embeds the question and searches the tenant's knowledge base through
VectorStore.search(), which requires tenant_id + knowledge_base_id as
mandatory arguments (see core/ai/vector_store.py) -- there is no code
path through this node that can search without them. Only runs when
classify_intent set needs_retrieval=True (see graph.py's conditional
routing).
"""
import time
import uuid

import structlog

from app.core.ai.embeddings import get_embedding_provider
from app.core.ai.vector_store import VectorStore
from app.core.config import settings
from app.modules.agent.state import AgentState

logger = structlog.get_logger(__name__)


def make_retrieve_knowledge(vector_store: VectorStore | None = None):
    """Factory, not a bare function: production code calls
    make_retrieve_knowledge() with no arguments and gets the real Qdrant-
    backed store; tests inject an embedded VectorStore instance so
    retrieval is exercised for real without a running Qdrant server."""

    def retrieve_knowledge(state: AgentState) -> dict:
        started = time.perf_counter()
        store = vector_store or VectorStore()
        embedder = get_embedding_provider()
        query_vector = embedder.embed_texts([state["question"]])[0]

        results = store.search(
            tenant_id=uuid.UUID(state["tenant_id"]),
            knowledge_base_id=uuid.UUID(state["knowledge_base_id"]),
            query_vector=query_vector,
            top_k=settings.retrieval_top_k,
            score_threshold=settings.retrieval_similarity_threshold,
        )

        logger.info(
            "rag.retrieval.completed",
            top_k=settings.retrieval_top_k,
            result_count=len(results),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return {
            "retrieved_chunks": [
                {
                    "chunk_id": str(r.chunk_id),
                    "document_id": str(r.document_id),
                    "content": r.content,
                    "score": r.score,
                }
                for r in results
            ]
        }

    return retrieve_knowledge
