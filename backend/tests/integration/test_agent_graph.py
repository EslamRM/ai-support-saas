"""
End-to-end tests for the compiled LangGraph agent, run with .invoke() --
the same entrypoint production code uses. Retrieval runs against a real
embedded Qdrant instance (no server, no mocking of VectorStore's
behavior); only the chat model is the offline FakeChatModel (see its
docstring in modules/agent/llm.py for why a real semantic evaluation
needs the real provider instead).
"""
import uuid

from app.modules.agent.graph import build_agent_graph
from app.modules.agent.llm import FakeChatModel


def _index_chunk(vector_store, *, tenant_id, kb_id, text):
    """Bypasses the full document-upload pipeline and writes one chunk
    directly to the vector store -- these tests are about the AGENT
    graph's behavior given retrieval results, not re-proving document
    ingestion (that's covered in test_document_ingestion.py)."""
    from app.core.ai.embeddings import get_embedding_provider

    vector = get_embedding_provider().embed_texts([text])[0]
    vector_store.upsert_chunks(
        tenant_id=tenant_id,
        knowledge_base_id=kb_id,
        document_id=uuid.uuid4(),
        chunks=[(uuid.uuid4(), text, vector)],
    )


def test_small_talk_never_triggers_retrieval_or_handoff(vector_store):
    tenant_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    graph = build_agent_graph(vector_store=vector_store, chat_model=FakeChatModel())

    result = graph.invoke({"tenant_id": str(tenant_id), "knowledge_base_id": str(kb_id), "question": "hi"})

    assert result["needs_retrieval"] is False
    assert result["route"] == "answered"
    assert "retrieved_chunks" not in result or result["retrieved_chunks"] == []


def test_real_question_with_relevant_knowledge_is_answered(vector_store, monkeypatch):
    # FakeEmbeddingProvider (see modules/agent/llm.py / core/ai/embeddings.py
    # docstrings) produces deterministic but NOT semantically meaningful
    # vectors -- the default retrieval_similarity_threshold (0.7) is tuned
    # for a real embedding model and would filter out even the one
    # obviously-relevant chunk here. Lowering it for this test only; the
    # threshold itself is exercised against real embeddings in
    # docs/evaluation.md's dataset (Phase 12), not here.
    monkeypatch.setattr("app.core.config.settings.retrieval_similarity_threshold", None)

    tenant_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    _index_chunk(
        vector_store,
        tenant_id=tenant_id,
        kb_id=kb_id,
        text="Our refund policy allows returns within 30 days of purchase with a valid receipt.",
    )

    graph = build_agent_graph(vector_store=vector_store, chat_model=FakeChatModel())
    result = graph.invoke(
        {
            "tenant_id": str(tenant_id),
            "knowledge_base_id": str(kb_id),
            "question": "What is your refund policy?",
        }
    )

    assert result["needs_retrieval"] is True
    assert len(result["retrieved_chunks"]) > 0
    assert result["route"] == "answered"
    assert "refund" in result["answer"].lower()


def test_question_with_no_matching_knowledge_routes_to_handoff(vector_store):
    tenant_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    # Knowledge base is empty -- nothing indexed for this tenant/KB at all.

    graph = build_agent_graph(vector_store=vector_store, chat_model=FakeChatModel())
    result = graph.invoke(
        {
            "tenant_id": str(tenant_id),
            "knowledge_base_id": str(kb_id),
            "question": "Can I get a refund for a damaged item?",
        }
    )

    assert result["needs_retrieval"] is True
    assert result["retrieved_chunks"] == []
    assert result["route"] == "handoff"


def test_retrieval_in_the_agent_graph_never_crosses_tenant_boundaries(vector_store):
    """The agent-level version of the tenant isolation guarantee already
    proven at the VectorStore level (Phase 4) -- proves the GRAPH, as a
    whole, never leaks another tenant's indexed content into an answer."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    kb_a = uuid.uuid4()
    kb_b = uuid.uuid4()

    _index_chunk(
        vector_store,
        tenant_id=tenant_b,
        kb_id=kb_b,
        text="CONFIDENTIAL: Tenant B's internal escalation contact is Jane at extension 4471.",
    )
    # Tenant A's knowledge base is empty.

    graph = build_agent_graph(vector_store=vector_store, chat_model=FakeChatModel())
    result = graph.invoke(
        {
            "tenant_id": str(tenant_a),
            "knowledge_base_id": str(kb_a),
            "question": "What is the internal escalation contact?",
        }
    )

    assert result["retrieved_chunks"] == []
    assert "Jane" not in result["answer"]
    assert "4471" not in result["answer"]
    assert result["route"] == "handoff"
