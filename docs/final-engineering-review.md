# Final Staff Engineer Review

This review is based on the implementation in the repository after Phase 15.

## Critical

### C1 — Public customer-chat authentication is not implemented

The current conversation API uses tenant staff JWTs. A real embedded customer widget needs
a separate short-lived, knowledge-base-scoped credential. Without that boundary, exposing
the current conversation endpoints directly to end customers would grant more access than
the product intends.

**Action:** implement an embed-token flow:
`widget -> short-lived token scoped to knowledge_base_id -> chat endpoint`.

### C2 — Document upload MIME validation is not content inspection

The API validates the declared content type and size. MIME types can be spoofed.

**Action:** validate file signatures/magic bytes, virus-scan uploads, and isolate parsers
before public production use.

## High

### H1 — Rate limiting is process-local

The current limiter protects local development and single-instance deployments, but two API
replicas have independent counters.

**Action:** move the limiter to Redis or an API gateway before horizontal scaling.

### H2 — Document job delivery is not transactional with the database

The document row is committed before Celery enqueueing. If Redis is unavailable after the
commit, the document can remain pending.

**Action:** add an outbox/job table or a durable queue with retryable delivery.

### H3 — Refresh-token revocation is not persisted

Tokens contain a `jti`, but there is no revocation store.

**Action:** persist refresh-token/session state in Redis or PostgreSQL and revoke on logout,
credential changes and suspected compromise.

### H4 — Analytics are request-time aggregates

The dashboard currently computes some agent metadata by loading assistant messages.

**Action:** maintain denormalized counters or an asynchronous analytics pipeline when volume
makes this expensive.

## Medium

### M1 — Qdrant is an external index without a full reconciliation job

Postgres is the source of truth, but there is no scheduled job that detects missing/orphaned
vectors.

**Action:** add an index reconciliation command that compares indexed document chunks with
Qdrant payloads and repairs drift.

### M2 — Provider failover is not implemented

The abstraction makes provider swapping possible, but runtime failover between providers is
not yet automatic.

**Action:** add an explicit provider policy only when reliability requirements justify it.

### M3 — Conversation turn idempotency

A client retry can potentially submit the same customer message twice.

**Action:** add an idempotency key per customer turn and persist the result keyed by
`(tenant_id, idempotency_key)`.

### M4 — Observability is log-centric

The request ID and structured events provide useful correlation, but there is no distributed
trace backend.

**Action:** add OpenTelemetry when multiple services/workers make cross-process debugging
difficult.

## Low

### L1 — Configuration could be validated more aggressively

Production startup should reject development JWT secrets and unsafe CORS configuration.

### L2 — Cost pricing is not calculated

Token counts are recorded, but dollar cost depends on the provider/model price at the time.

**Action:** add a versioned model-price table if customer billing is introduced.

### L3 — Evaluation runner is dataset-first

The dataset exists, but a complete automated LLM-as-judge or human-labeling workflow is not
part of this phase.

**Action:** build the evaluation harness before changing prompts/models frequently.

## Architectural strengths

- Tenant scoping is explicit in SQL and Qdrant APIs.
- LLM and embedding providers are behind small interfaces.
- Agent state is explicit and inspectable.
- Ticket side effects are controlled by application code.
- Document ingestion is asynchronous.
- Retry policy is centralized and bounded.
- Request/AI events are structured and correlated.
- Tests use deterministic providers instead of spending API credits.

## What I would change first for a real production launch

1. Customer embed-token boundary.
2. Shared/distributed rate limiting.
3. Durable document-job delivery.
4. Upload magic-byte validation + malware scanning.
5. Idempotency for chat turns.
6. Token/session revocation.
7. Automated RAG/answer evaluation in CI.

The key Staff-level conclusion is not "add more services." The current modular monolith has
clear enough boundaries that these improvements can be introduced without rewriting the
domain model.
