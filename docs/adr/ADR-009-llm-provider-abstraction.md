# ADR-009 LLM Provider Abstraction

## Context
The project should not be permanently coupled to one LLM vendor.

## Decision
Use `ChatModel` and `EmbeddingProvider` interfaces with OpenAI and deterministic fake
implementations.

## Alternatives
Call the SDK directly throughout the application.

## Trade-offs
A small abstraction layer adds indirection but makes tests deterministic and provider
swaps localized.

## Consequences
Provider-specific options belong in the adapter, not business modules.
