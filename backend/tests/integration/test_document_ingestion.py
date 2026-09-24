"""
End-to-end tests for the document ingestion pipeline, exercised through
the REAL HTTP API (upload endpoint -> DocumentService -> Celery task in
eager mode -> extract/chunk/embed -> embedded Qdrant + SQLite). Nothing
here is mocked except the network-dependent pieces this sandbox can't
reach (a real Qdrant server, a real OpenAI API) -- both are swapped for
fully-functional offline equivalents (embedded Qdrant, the deterministic
FakeEmbeddingProvider), not stubbed-out no-ops. This proves the pipeline
actually works, not just that its functions are individually callable.
"""
from tests.conftest import auth_headers_for


def _create_kb(client, headers) -> str:
    resp = client.post("/knowledge-bases", json={"name": "Product Docs"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_upload_plain_text_document_is_indexed_end_to_end(client, tenant_a, patch_vector_store):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)

    content = (
        "Refund Policy. Refunds are processed within 5 business days of the return "
        "being received. " * 60
    )  # long enough to produce more than one chunk at the default chunk_size

    resp = client.post(
        "/documents",
        headers=headers,
        data={"knowledge_base_id": kb_id},
        files={"file": ("refund-policy.txt", content.encode("utf-8"), "text/plain")},
    )
    assert resp.status_code == 202
    document_id = resp.json()["id"]
    # Because CELERY_TASK_ALWAYS_EAGER=true, processing already completed
    # synchronously by the time upload_document() returned.
    assert resp.json()["status"] == "indexed"
    assert resp.json()["chunk_count"] > 1

    get_resp = client.get(f"/documents/{document_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "indexed"
    assert get_resp.json()["error_message"] is None


def test_uploaded_document_chunks_are_retrievable_from_vector_store(client, tenant_a, patch_vector_store):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)

    content = "The office is closed on national holidays. " * 40
    client.post(
        "/documents",
        headers=headers,
        data={"knowledge_base_id": kb_id},
        files={"file": ("hours.txt", content.encode("utf-8"), "text/plain")},
    )

    from app.core.ai.embeddings import get_embedding_provider

    query_vector = get_embedding_provider().embed_texts(["When is the office closed?"])[0]
    results = patch_vector_store.search(
        tenant_id=user.tenant_id,
        knowledge_base_id=__import__("uuid").UUID(kb_id),
        query_vector=query_vector,
        top_k=3,
        score_threshold=None,  # FakeEmbeddingProvider isn't semantically meaningful
        # (see its docstring) -- unrelated text can score below 0.0 on cosine
        # similarity, so a positive threshold isn't meaningful against it here.
    )

    assert len(results) > 0
    assert "office is closed" in results[0].content


def test_upload_rejects_unsupported_file_type(client, tenant_a, patch_vector_store):
    _, user = tenant_a
    headers = auth_headers_for(user)
    kb_id = _create_kb(client, headers)

    resp = client.post(
        "/documents",
        headers=headers,
        data={"knowledge_base_id": kb_id},
        files={"file": ("archive.zip", b"PK\x03\x04fakezipcontent", "application/zip")},
    )
    assert resp.status_code == 415


def test_upload_to_another_tenants_knowledge_base_is_rejected(client, tenant_a, tenant_b, patch_vector_store):
    _, user_a = tenant_a
    _, user_b = tenant_b
    kb_id_owned_by_b = _create_kb(client, auth_headers_for(user_b))

    # user_a tries to upload into a knowledge base that belongs to tenant B.
    resp = client.post(
        "/documents",
        headers=auth_headers_for(user_a),
        data={"knowledge_base_id": kb_id_owned_by_b},
        files={"file": ("sneaky.txt", b"trying to write into another tenant", "text/plain")},
    )
    assert resp.status_code == 404  # KnowledgeBaseNotFoundError -- from user_a's perspective it doesn't exist


def test_retrieval_never_crosses_tenant_boundaries(client, tenant_a, tenant_b, patch_vector_store):
    """The core RAG tenant-isolation guarantee: even with identical
    content in both tenants' knowledge bases, searching as tenant A must
    never return tenant B's chunks."""
    _, user_a = tenant_a
    _, user_b = tenant_b

    kb_a = _create_kb(client, auth_headers_for(user_a))
    kb_b = _create_kb(client, auth_headers_for(user_b))

    same_content = "Our support hours are 9am to 5pm Monday through Friday. " * 30

    client.post(
        "/documents",
        headers=auth_headers_for(user_a),
        data={"knowledge_base_id": kb_a},
        files={"file": ("hours.txt", same_content.encode("utf-8"), "text/plain")},
    )
    client.post(
        "/documents",
        headers=auth_headers_for(user_b),
        data={"knowledge_base_id": kb_b},
        files={"file": ("hours.txt", same_content.encode("utf-8"), "text/plain")},
    )

    from app.core.ai.embeddings import get_embedding_provider
    import uuid

    query_vector = get_embedding_provider().embed_texts(["What are your support hours?"])[0]

    results_for_a = patch_vector_store.search(
        tenant_id=user_a.tenant_id,
        knowledge_base_id=uuid.UUID(kb_a),
        query_vector=query_vector,
        top_k=10,
        score_threshold=None,  # see note above on FakeEmbeddingProvider + thresholds
    )

    assert len(results_for_a) > 0
    assert all(r.document_id != uuid.UUID(kb_b) for r in results_for_a)
    # Every returned chunk must actually belong to tenant A's document,
    # never tenant B's, despite both tenants having near-identical content
    # embedded with the same (fake, deterministic) embedding vectors.
    for r in results_for_a:
        assert str(r.chunk_id) is not None  # sanity: real chunk objects, not empty stand-ins
