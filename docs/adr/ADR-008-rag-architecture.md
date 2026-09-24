# ADR-008 RAG Architecture

## Context
Support answers must be grounded in company documents.

## Decision
Extract -> clean -> chunk -> embed -> Qdrant; retrieve top-K tenant-filtered chunks;
pass only retrieved context to the answer model.

## Alternatives
Long prompt with all documents, fine-tuning.

## Trade-offs
RAG introduces retrieval quality as a new failure mode, but document updates become
available without retraining a model.

## Consequences
Retrieval relevance must be evaluated separately from answer quality.
