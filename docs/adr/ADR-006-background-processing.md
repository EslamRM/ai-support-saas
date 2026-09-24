# ADR-006 Background Processing

## Context
PDF extraction, chunking and embedding can be slow and failure-prone.

## Decision
Persist document metadata first, then process asynchronously with Celery.

## Alternatives
Do everything inside the HTTP request.

## Trade-offs
The UI must expose eventual document status.

## Consequences
Interactive API latency is not tied to document size.
