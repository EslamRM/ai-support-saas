# Scaling

The current architecture is a modular monolith. That is deliberate: scale the bottleneck,
not the diagram.

## 10x traffic

Keep the API codebase together and:
- run multiple FastAPI replicas;
- put a load balancer in front;
- move rate limiting to Redis/gateway;
- run multiple Celery workers;
- tune Postgres connection pools;
- keep Qdrant independently sized;
- cache low-risk read-heavy tenant configuration.

The application modules remain the same.

## 100x traffic

Introduce operational separation where bottlenecks appear:
- separate ingestion workers from interactive API workers;
- add a durable job/outbox table;
- partition or archive high-volume message data;
- move analytics aggregation away from request-time JSON scanning;
- add Redis caching for hot knowledge-base metadata;
- add Qdrant collection/shard strategy based on tenant scale;
- add OpenTelemetry and centralized metrics.

Only then consider extracting a service if independent scaling or deployment is valuable.

## 1M conversations/month

At this volume, the critical path is:
API -> Postgres conversation persistence -> retrieval -> LLM.

Priorities:
1. control LLM spend with model routing, token budgets and caching where safe;
2. bound conversation context;
3. avoid synchronous analytics scans;
4. scale workers independently;
5. use connection pooling and read replicas if DB reads become dominant;
6. retain raw conversation data according to a clear retention policy;
7. isolate large tenants if noisy-neighbor behavior appears.

## What should become asynchronous

Good async candidates:
- document extraction/indexing
- analytics aggregation
- evaluation runs
- exports
- notifications

Keep synchronous:
- authentication
- conversation message acceptance
- retrieval + answer generation for interactive chat
- ticket creation when the customer must immediately know a ticket was created.

## Eventual consistency

Document indexing is eventually consistent: upload creates the document immediately,
then a worker makes it searchable. The UI exposes document status.

Analytics can also become eventually consistent at scale.

## What should remain one module

Authentication, tenancy checks and business invariants should stay close to the API/domain
until independent scaling or ownership justifies separation.

## Main bottlenecks

- LLM latency/cost
- embedding throughput during ingestion
- Qdrant retrieval latency
- Postgres message volume
- synchronous analytics aggregation

Measure these before adding infrastructure.
