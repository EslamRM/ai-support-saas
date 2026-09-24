# ADR-002 PostgreSQL

## Context
The product needs transactional tenant/user/conversation/ticket data.

## Decision
Use PostgreSQL as the system of record.

## Alternatives
SQLite for production, MongoDB, separate databases per tenant.

## Trade-offs
Postgres adds operational infrastructure but gives strong transactions, mature indexing,
constraints and a clear path to replicas/partitioning.

## Consequences
Business data stays queryable and auditable in one relational store; vector search remains
a separate concern.
