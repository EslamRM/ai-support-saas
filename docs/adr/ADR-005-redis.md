# ADR-005 Redis

## Context
Document ingestion should not block API requests.

## Decision
Use Redis as the Celery broker/backend.

## Alternatives
Synchronous processing, database polling, Kafka.

## Trade-offs
Redis is another service but is lightweight for the current workload.

## Consequences
Workers can scale independently from API replicas.
