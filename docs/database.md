# Database Design

## PostgreSQL is the system of record

Postgres stores:
- tenants
- users and roles
- knowledge bases
- document metadata and chunks
- conversations
- messages
- tickets

Qdrant is an index, not the business source of truth.

## Tenant isolation

Every tenant-owned row includes `tenant_id`. Repository methods require the tenant ID
explicitly. The service layer performs object ownership checks before creating relationships.

This is application-enforced isolation in v1. At higher assurance requirements, PostgreSQL
Row-Level Security is a possible second defense.

## Transactions

The main transaction boundaries are:
- registration: tenant + owner user
- document upload: document metadata + enqueue after commit
- conversation turn: user message + AI ticket + assistant message
- ticket update: status change

The current architecture intentionally persists the customer message before calling the
LLM so a provider outage does not erase the user's input.

## Indexing

Tenant-scoped queries should index `(tenant_id, ...)` together with common lookup columns.
As message volume grows, add indexes based on real query plans rather than speculative indexes.

## Analytics

The Phase 8 dashboard currently performs simple aggregate queries and computes some JSON
metadata in Python. This is acceptable at portfolio scale. At high volume, maintain
denormalized counters or an analytics pipeline.

## Migration strategy

Alembic owns schema changes. Every schema change should have:
- migration
- forward/backward consideration
- test coverage
- deployment note if data transformation is required
