# ADR-001: Modular Monolith over Microservices

## Context

We're building a multi-tenant AI support SaaS with distinct bounded contexts: tenancy/auth,
knowledge base, document processing, conversations, the AI agent, tickets, and analytics. A
microservices split along these lines is possible from day one.

## Decision

Start as a single deployable FastAPI service plus Celery workers, with the bounded contexts
enforced as internal modules (`app/modules/*`) that only communicate through each other's
service-layer interfaces — never by reaching into another module's ORM models directly.

## Alternatives Considered

- **Microservices per bounded context** (separate deploy for tenancy, documents, agent, etc.)
- **Single unstructured FastAPI app** (no internal module boundaries at all)

## Trade-offs

| | Modular Monolith (chosen) | Microservices |
|---|---|---|
| Operational overhead | One deploy, one process type to monitor | N deploys, service discovery, N sets of infra |
| Latency | In-process calls | Network hop per cross-service call — costly next to LLM latency |
| Data consistency | Single DB transaction across modules when needed | Distributed transactions / eventual consistency |
| Independent scaling | Scale the whole monolith (or split API vs. worker) | Scale each service independently |
| Team scaling | Fine for a small team/solo project | Justified once teams own separate services |
| Refactor cost later | Extraction requires respecting the module boundary we set now | N/A — already split |

A single unstructured app was rejected because without enforced module boundaries, the
"modular" part erodes within a few features and tenant-isolation bugs become much easier to
introduce (a documents-module function reaching straight into the conversations module's
tables, bypassing tenant checks that live in that module's repository layer).

## Consequences

- Every module must expose a service-layer interface for anything another module needs — no
  shared direct ORM access across module boundaries. This is checked informally in code review
  and could be enforced later with import-linting if the team grows.
- The two extraction candidates if/when scale demands it are **document processing** (CPU/IO
  heavy, independently scalable) and the **agent/RAG layer** (may want isolated deploy cadence
  for LLM-call performance). See `docs/scaling.md` (added in a later phase) for the concrete
  trigger conditions.
- We accept slower theoretical ceiling on independent scaling in exchange for much lower
  operational cost and complexity at the current stage (zero production tenants).
