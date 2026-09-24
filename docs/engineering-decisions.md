# Engineering Decisions

The project intentionally prefers simple boundaries over premature microservices.

1. Modular monolith — one deployable backend, explicit module boundaries.
2. PostgreSQL — transactional system of record.
3. Qdrant — vector retrieval index with tenant filters.
4. LangGraph — explicit AI state/conditional workflow.
5. Redis + Celery — asynchronous document ingestion.
6. JWT + DB revalidation — stateless access token plus authoritative user state.
7. Deterministic handoff — the LLM does not control the security-sensitive side effect.
8. Structured outputs — parseable agent results instead of free-form control flow.
9. Provider abstractions — LLM and embeddings can be swapped without rewriting the graph.
10. Structured logging — runtime behavior is observable without leaking customer content.
