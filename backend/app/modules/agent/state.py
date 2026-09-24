"""
Module: agent
File responsibility (state.py): the typed LangGraph state threaded
through every node.

Explicit typed state (TypedDict, not a bare dict) is what makes the
graph reviewable and testable node-by-node -- each node's signature says
exactly what it reads and returns, rather than every node needing to
know the shape of an untyped grab-bag.

total=False: each node only returns the keys IT sets (LangGraph merges
partial updates into state -- a node returning {"answer": "..."} doesn't
need to also echo back tenant_id, question, etc). See graph.py for how
nodes are wired together.
"""
from typing import TypedDict


class RetrievedChunkDict(TypedDict):
    chunk_id: str
    document_id: str
    content: str
    score: float


class AgentState(TypedDict, total=False):
    # --- input, set by the caller before invoking the graph ---
    tenant_id: str
    knowledge_base_id: str
    question: str
    # Prior turns of this conversation, oldest-first, as plain
    # {"role": "user"|"assistant", "content": str} dicts -- already
    # bounded by modules/conversations/context.py before being placed
    # here. Empty/absent for a single-turn call (e.g. Phase 5's tests) or
    # the first message of a new conversation.
    history: list[dict]

    # --- set by classify_intent ---
    needs_retrieval: bool

    # --- set by retrieve_knowledge (only runs if needs_retrieval) ---
    retrieved_chunks: list[RetrievedChunkDict]

    # --- set by generate_answer ---
    answer: str
    grounded: bool
    confidence: float
    llm_latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    # --- set by quality_check ---
    route: str  # "answered" | "handoff"
