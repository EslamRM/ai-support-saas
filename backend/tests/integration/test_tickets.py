"""
End-to-end tests: an unanswerable question, through the real HTTP
conversation API, actually creates a ticket -- and that ticket is
tenant-isolated like everything else. patch_agent_graph (same fixture as
Phase 6's tests) wires in embedded Qdrant + the offline FakeChatModel.
"""
from tests.conftest import auth_headers_for


def _create_kb(client, headers) -> str:
    resp = client.post("/knowledge-bases", json={"name": "Product Docs"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def _start_conversation(client, headers, kb_id: str) -> str:
    resp = client.post(
        "/conversations",
        json={"knowledge_base_id": kb_id, "customer_identifier": "customer@example.com"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_unanswerable_question_creates_a_ticket(client, tenant_a, patch_agent_graph):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)
    conversation_id = _start_conversation(client, headers, kb_id)
    # Knowledge base is empty -- nothing indexed, guaranteeing a handoff.

    msg_resp = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "I was charged twice for my last order, can you fix this?"},
        headers=headers,
    )
    assert msg_resp.status_code == 201
    metadata = msg_resp.json()["agent_metadata"]
    assert metadata["route"] == "handoff"
    assert "ticket_id" in metadata

    ticket_resp = client.get(f"/tickets/{metadata['ticket_id']}", headers=headers)
    assert ticket_resp.status_code == 200
    ticket = ticket_resp.json()
    assert ticket["conversation_id"] == conversation_id
    assert ticket["status"] == "open"
    assert ticket["priority"] == "medium"
    assert "charged twice" in ticket["title"].lower() or "charged twice" in ticket["description"].lower()


def test_answered_question_does_not_create_a_ticket(client, tenant_a, patch_agent_graph):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)
    conversation_id = _start_conversation(client, headers, kb_id)

    resp = client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "hi"}, headers=headers
    )
    assert resp.status_code == 201
    assert "ticket_id" not in resp.json()["agent_metadata"]

    tickets_resp = client.get("/tickets", headers=headers)
    assert tickets_resp.json() == []


def test_manual_ticket_creation_by_staff(client, tenant_a, patch_agent_graph):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)
    conversation_id = _start_conversation(client, headers, kb_id)

    resp = client.post(
        "/tickets",
        json={
            "conversation_id": conversation_id,
            "customer_identifier": "customer@example.com",
            "title": "Escalated by staff",
            "description": "Customer called in directly, filing manually.",
            "priority": "high",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["priority"] == "high"


def test_ticket_status_update_requires_admin_role(client, tenant_a, patch_agent_graph):
    _, owner = tenant_a  # signup always creates an OWNER (see auth/service.py)
    headers = auth_headers_for(owner)
    kb_id = _create_kb(client, headers)
    conversation_id = _start_conversation(client, headers, kb_id)
    ticket_id = client.post(
        "/tickets",
        json={
            "conversation_id": conversation_id,
            "customer_identifier": "c@example.com",
            "title": "x",
            "description": "y",
        },
        headers=headers,
    ).json()["id"]

    # Owner outranks admin (see core/dependencies._ROLE_RANK) so this
    # should succeed.
    resp = client.patch(f"/tickets/{ticket_id}/status", json={"status": "resolved"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


def test_tickets_are_tenant_isolated(client, tenant_a, tenant_b, patch_agent_graph):
    _, user_a = tenant_a
    _, user_b = tenant_b
    kb_id = _create_kb(client, auth_headers_for(user_a))
    conversation_id = _start_conversation(client, auth_headers_for(user_a), kb_id)
    ticket_id = client.post(
        "/tickets",
        json={
            "conversation_id": conversation_id,
            "customer_identifier": "c@example.com",
            "title": "Tenant A's ticket",
            "description": "should not be visible to tenant B",
        },
        headers=auth_headers_for(user_a),
    ).json()["id"]

    resp = client.get(f"/tickets/{ticket_id}", headers=auth_headers_for(user_b))
    assert resp.status_code == 404

    list_resp = client.get("/tickets", headers=auth_headers_for(user_b))
    assert list_resp.json() == []


def test_ticket_creation_rejects_another_tenants_conversation_id(client, tenant_a, tenant_b, patch_agent_graph):
    _, user_a = tenant_a
    _, user_b = tenant_b
    kb_id = _create_kb(client, auth_headers_for(user_a))
    conversation_id_owned_by_a = _start_conversation(client, auth_headers_for(user_a), kb_id)

    resp = client.post(
        "/tickets",
        json={
            "conversation_id": conversation_id_owned_by_a,
            "customer_identifier": "sneaky@example.com",
            "title": "IDOR attempt",
            "description": "trying to attach a ticket to another tenant's conversation",
        },
        headers=auth_headers_for(user_b),
    )
    assert resp.status_code == 404
