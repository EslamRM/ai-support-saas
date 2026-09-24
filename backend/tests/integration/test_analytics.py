"""End-to-end tests for GET /analytics, through the real HTTP API and
the real conversation/ticket flow (not hand-inserted rows), proving both
correctness and tenant isolation."""
from tests.conftest import auth_headers_for


def _create_kb(client, headers) -> str:
    return client.post("/knowledge-bases", json={"name": "Docs"}, headers=headers).json()["id"]


def _start_conversation(client, headers, kb_id: str) -> str:
    return client.post(
        "/conversations",
        json={"knowledge_base_id": kb_id, "customer_identifier": "c@example.com"},
        headers=headers,
    ).json()["id"]


def test_analytics_summary_is_zeroed_for_a_fresh_tenant(client, tenant_a):
    _, user = tenant_a
    resp = client.get("/analytics", headers=auth_headers_for(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_count"] == 0
    assert body["message_count"] == 0
    assert body["ticket_count"] == 0
    assert body["handoff_rate"] is None
    assert body["average_confidence"] is None


def test_analytics_reflects_real_conversation_and_ticket_activity(client, tenant_a, patch_agent_graph):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)
    conversation_id = _start_conversation(client, headers, kb_id)

    # One small-talk turn (answered, no ticket) and one unanswerable turn
    # (handoff, creates a ticket) -- empty KB guarantees the second one
    # can't be grounded.
    client.post(f"/conversations/{conversation_id}/messages", json={"content": "hi"}, headers=headers)
    client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "I was charged twice, please help"},
        headers=headers,
    )

    resp = client.get("/analytics", headers=headers)
    body = resp.json()

    assert body["conversation_count"] == 1
    assert body["message_count"] == 4  # 2 user + 2 assistant
    assert body["ticket_count"] == 1
    assert body["tickets_by_status"]["open"] == 1
    assert body["handoff_rate"] == 0.5  # 1 of 2 assistant messages handed off


def test_analytics_never_crosses_tenant_boundaries(client, tenant_a, tenant_b, patch_agent_graph):
    _, user_a = tenant_a
    _, user_b = tenant_b
    kb_id = _create_kb(client, auth_headers_for(user_a))
    conversation_id = _start_conversation(client, auth_headers_for(user_a), kb_id)
    client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "hi"}, headers=auth_headers_for(user_a)
    )

    resp = client.get("/analytics", headers=auth_headers_for(user_b))
    body = resp.json()
    assert body["conversation_count"] == 0
    assert body["message_count"] == 0
