# Phase 9 — Observability

## Goal

The application now treats observability as part of the runtime contract rather than
debugging after the fact. The three layers are:

1. **Structured logs** — every HTTP request and important AI event is JSON.
2. **Metrics** — dashboard aggregates plus per-turn latency/token metadata.
3. **Tracing concept** — request ID and conversation ID provide a lightweight correlation
   model that can later be upgraded to OpenTelemetry without changing business logic.

## What is logged

Important events include:

- `http.request.started`
- `http.request.completed`
- `http.request.failed`
- `rag.retrieval.completed`
- `ai.llm.call.completed`
- `agent.execution.started`
- `agent.execution.completed`
- `agent.execution.failed`
- `agent.ticket_created`
- `ticket.created`

Every request gets an `X-Request-ID`. Tenant/user context comes from the authenticated
request context and is used only for log enrichment.

## What is deliberately not logged

Never put these values in logs:

- passwords
- access/refresh JWTs
- API keys
- document contents
- full customer messages
- raw LLM prompts/responses
- uploaded binary data

AI logs contain metadata such as model, latency, token counts, retrieval count and route.

## AI-specific observability

An assistant message stores:

- route (`answered` / `handoff`)
- grounded flag
- confidence
- retrieval count
- total agent latency
- LLM latency when available
- prompt/completion/total token counts when the provider returns usage

This makes a support turn inspectable without storing a second copy of the customer's text.

## Cost tracking

Token usage is the most provider-independent first approximation of LLM cost.
The current implementation records usage but does not hard-code a dollar price because
provider/model prices change. A production billing layer should map `(provider, model,
input_tokens, output_tokens)` to a versioned price table.

## Failure tracking

Failures are logged with operation name and latency. The application distinguishes:
- retryable upstream failures
- validation/client failures
- application bugs

See `docs/reliability.md`.

## Scaling the observability layer

At 10x traffic, JSON stdout logs can be shipped by the container platform to a centralized
log system. At larger scale, add OpenTelemetry traces and a metrics backend. The business
modules should not depend directly on a vendor SDK.
