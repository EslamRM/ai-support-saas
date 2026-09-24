# ADR-007 Multi-Tenancy

## Context
Multiple companies share one application.

## Decision
Shared PostgreSQL schema with explicit `tenant_id` scoping and Qdrant metadata filters.

## Alternatives
Database-per-tenant, schema-per-tenant.

## Trade-offs
Shared schema is operationally simple but requires disciplined application isolation.

## Consequences
Tenant IDs are mandatory in repository and vector-store APIs, and isolation is covered
by security tests.
