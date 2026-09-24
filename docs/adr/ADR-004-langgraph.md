# ADR-004 LangGraph

## Context
The support agent has explicit state and conditional retrieval/handoff behavior.

## Decision
Use LangGraph to model the workflow as nodes and edges.

## Alternatives
A single LLM call, a custom state machine, a generic chain abstraction.

## Trade-offs
LangGraph adds a framework dependency, but the graph is easier to inspect and test than
hidden orchestration inside one function.

## Consequences
Agent state is typed and graph routing is explicit.
