# ADR-003 Qdrant

## Context
RAG requires nearest-neighbor vector search with metadata filtering.

## Decision
Use Qdrant for document chunk vectors.

## Alternatives
pgvector, Elasticsearch, an in-memory index.

## Trade-offs
A separate service adds one operational dependency but keeps vector retrieval explicit and
allows independent scaling.

## Consequences
Every query must carry tenant and knowledge-base filters.
