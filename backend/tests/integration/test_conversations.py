"""
End-to-end tests for conversation persistence + the agent integration,
through the real HTTP API. patch_agent_graph wires the same embedded
Qdrant + FakeChatModel providers used in Phase 4/5's tests into
ConversationService's default graph factory -- see conftest.py.
"""
from tests.conftest import auth_headers_for


def _create_kb(client, headers) -> str:
    resp = client.post("/knowledge-bases", json={"name": "Product Docs"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def _index_chunk(vector_store, *, tenant_id, kb_id, text):
    import uuid

    from app.core.ai.embeddings import get_embedding_provider

    vector = get_embedding_provider().embed_texts([text])[0]
    vector_store.upsert_chunks(
        tenant_id=tenant_id, knowledge_base_id=kb_id, document_id=uuid.uuid4(), chunks=[(uuid.uuid4(), text, vector)]
    )


def test_start_conversation_and_send_message(client, tenant_a, patch_agent_graph):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)

    conv_resp = client.post(
        "/conversations",
        json={"knowledge_base_id": kb_id, "customer_identifier": "customer@example.com"},
        headers=headers,
    )
    assert conv_resp.status_code == 201
    conversation_id = conv_resp.json()["id"]

    msg_resp = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "hi"},
        headers=headers,
    )
    assert msg_resp.status_code == 201
    body = msg_resp.json()
    assert body["role"] == "assistant"
    assert body["agent_metadata"]["route"] == "answered"
    assert body["agent_metadata"]["needs_retrieval"] is False


def test_conversation_transcript_includes_both_user_and_assistant_messages(client, tenant_a, patch_agent_graph):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)
    conversation_id = client.post(
        "/conversations",
        json={"knowledge_base_id": kb_id, "customer_identifier": "c@example.com"},
        headers=headers,
    ).json()["id"]

    client.post(f"/conversations/{conversation_id}/messages", json={"content": "hi"}, headers=headers)
    client.post(f"/conversations/{conversation_id}/messages", json={"content": "thanks"}, headers=headers)

    transcript = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert transcript.status_code == 200
    messages = transcript.json()["messages"]
    assert len(messages) == 4  # 2 user + 2 assistant
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]


def test_question_answerable_from_knowledge_base_is_grounded(client, tenant_a, patch_agent_graph, monkeypatch):
    # See Phase 4/5 notes on FakeEmbeddingProvider: its cosine scores
    # aren't semantically meaningful, so the default (real-model-tuned)
    # retrieval_similarity_threshold would filter out even an obviously
    # relevant chunk here.
    monkeypatch.setattr("app.core.config.settings.retrieval_similarity_threshold", None)

    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)
    _index_chunk(
        patch_agent_graph,
        tenant_id=user.tenant_id,
        kb_id=__import__("uuid").UUID(kb_id),
        text="Our support hours are 9am to 5pm Monday through Friday.",
    )

    conversation_id = client.post(
        "/conversations",
        json={"knowledge_base_id": kb_id, "customer_identifier": "c@example.com"},
        headers=headers,
    ).json()["id"]

    resp = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "What are your support hours?"},
        headers=headers,
    )

    assert resp.status_code == 201
    assert resp.json()["agent_metadata"]["route"] == "answered"
    assert resp.json()["agent_metadata"]["retrieved_chunk_count"] > 0


def test_question_with_no_matching_knowledge_routes_to_handoff(client, tenant_a, patch_agent_graph):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)
    # Empty knowledge base -- nothing indexed.

    conversation_id = client.post(
        "/conversations",
        json={"knowledge_base_id": kb_id, "customer_identifier": "c@example.com"},
        headers=headers,
    ).json()["id"]

    resp = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Can I get a refund for a damaged item?"},
        headers=headers,
    )

    assert resp.status_code == 201
    assert resp.json()["agent_metadata"]["route"] == "handoff"


def test_conversation_is_tenant_isolated(client, tenant_a, tenant_b, patch_agent_graph):
    _, user_a = tenant_a
    _, user_b = tenant_b
    kb_id = _create_kb(client, auth_headers_for(user_a))
    conversation_id = client.post(
        "/conversations",
        json={"knowledge_base_id": kb_id, "customer_identifier": "c@example.com"},
        headers=auth_headers_for(user_a),
    ).json()["id"]

    # tenant B tries to read tenant A's conversation.
    resp = client.get(f"/conversations/{conversation_id}", headers=auth_headers_for(user_b))
    assert resp.status_code == 404

    # tenant B tries to send a message into tenant A's conversation.
    resp2 = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "sneaky"},
        headers=auth_headers_for(user_b),
    )
    assert resp2.status_code == 404
