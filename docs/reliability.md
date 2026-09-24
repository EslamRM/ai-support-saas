# Phase 10 — Reliability

## Failure policy

The application does not retry everything.

### Retryable

- network connection failures
- timeouts
- HTTP 429/rate limiting from an upstream provider
- upstream HTTP 5xx errors

### Non-retryable

- invalid request data
- unsupported document format
- malformed LLM JSON
- authentication/authorization failures
- 4xx provider errors other than 429
- programming errors

The shared `app.core.reliability.retry_call()` implements bounded exponential backoff
with jitter and a maximum attempt count.

## LLM failures

The OpenAI client is configured with a timeout. Calls are retried up to the configured
attempt limit. The provider wrapper remains the only place that knows the SDK.

A future production implementation should add a circuit breaker when sustained provider
failure would otherwise waste latency and money.

## Qdrant failures

Qdrant reads/writes use the same retry policy. If retrieval still fails, the request
should fail explicitly rather than silently pretending that the knowledge base was empty.
That distinction matters: "no relevant knowledge exists" is different from "the retrieval
system is unavailable."

## Redis failures

Redis is the Celery broker/backend. Document ingestion therefore cannot be guaranteed
to run when Redis is down. The document row is persisted before enqueueing, so an operator
can identify pending work and requeue it after recovery.

At scale, use a durable queue and an outbox pattern if enqueue-vs-database atomicity
becomes a business requirement.

## Database failures

The request-scoped SQLAlchemy session is closed after every request. Business services
should rollback failed transactions before reusing a session.

## Transaction boundary for AI handoff

The AI-generated ticket is inserted with `commit=False` during a conversation turn.
The ticket and assistant message are committed together. This avoids the Phase 8 failure
mode where a ticket could be committed while the assistant message was lost.

The user message is persisted before graph execution. This is intentional: even if the
provider fails, the customer message remains part of the conversation audit trail.

## Timeouts, retries and backoff

A timeout bounds latency. A retry attempts recovery. Backoff prevents synchronized retry
storms. These are different controls and should not be treated as synonyms.

## Graceful degradation

The safest degradation is explicit:
- if retrieval is unavailable, do not claim there is no knowledge;
- if the LLM is unavailable, return a service error and preserve the customer message;
- if an LLM output is malformed, do not execute a tool based on it;
- if document ingestion fails, mark the document `FAILED` with an operator-visible error.

## Known next step

A production-grade queue should add an outbox/retryable job record for document ingestion.
A circuit breaker and provider failover policy are also candidates for the next scale stage.
