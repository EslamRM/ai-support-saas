# The AI Support Agent

This document explains what `backend/app/modules/agent/` actually implements. Conversation
persistence and multi-turn memory are Phase 6; the ticket-creation tool and human handoff
*execution* are Phase 7. This phase is the reasoning core those build on: given a tenant, a
knowledge base, and a single question, decide whether to look something up, generate a
grounded answer, and decide whether that answer is good enough to return.

## What "an agent" means here

An LLM call that always does the same fixed sequence of steps is a **chain**, not an agent —
useful, but it can't skip steps that don't apply or route around a failure. An agent adds
*decisions*: does this need a knowledge lookup at all? Is the resulting answer good enough to
show the customer, or should this go to a human instead? Those decisions are what LangGraph's
graph structure encodes explicitly, as nodes and conditional edges, rather than as an LLM
silently deciding everything inside one big prompt.

## Why LangGraph instead of a single prompt or a plain function chain

A single "do everything" prompt can't be unit-tested step by step, can't skip retrieval for
"hi", and makes it hard to reason about exactly what happened when something goes wrong — you
get one opaque LLM call with everything blended together. A plain Python function chain
(`step1(); step2(); step3()`) gets you explicit steps, but conditional branching becomes
nested if/else that's easy to tangle. LangGraph sits between them: **explicit typed state**
flowing through **named nodes** connected by **edges that can be conditional**, which is
exactly the shape of "sometimes skip retrieval, sometimes hand off" — while keeping each node
a plain, independently testable Python function.

## The Graph

```
START -> classify_intent -> (needs_retrieval?)
                               yes -> retrieve_knowledge -> generate_answer
                               no  -----------------------> generate_answer
         generate_answer -> quality_check -> END
```

Built in `graph.py: build_agent_graph()`. It's a **factory function**, not a module-level
compiled singleton — production calls it with no arguments and gets the real Qdrant- and
OpenAI-backed nodes; tests inject a fake `VectorStore`/`ChatModel` so the *entire compiled
graph* runs offline and deterministically via `.invoke()`, the same entrypoint production
code uses. This is why `tests/integration/test_agent_graph.py` can prove routing behavior
(small talk skips retrieval, an empty knowledge base routes to handoff, tenant isolation holds)
against the real graph, not a simplified stand-in.

## State (`state.py`)

A `TypedDict` (`AgentState`), not a bare dict. Every node's function signature says exactly
what it reads and what it's expected to write back — that's what makes each node reviewable
and unit-testable in isolation (see `tests/unit/test_agent_nodes.py`, which tests all four
nodes with zero graph, zero DB, zero vector store, except where a node's whole job *is*
talking to one). `tenant_id` and `knowledge_base_id` are stored as `str`, not `uuid.UUID` —
state needs to stay JSON-serializable for LangGraph's checkpointing (used starting Phase 6 for
multi-turn memory), and nodes convert to `UUID` locally where needed (see `nodes/retrieve.py`).

## Nodes

- **`classify_intent`** — deliberately a cheap deterministic heuristic (a small-talk word
  set), not an LLM call. See "When an agent is unnecessary" below.
- **`retrieve_knowledge`** — only runs when `classify_intent` set `needs_retrieval=True` (see
  the conditional edge). Embeds the question and searches through `VectorStore.search()`,
  which requires `tenant_id` + `knowledge_base_id` as mandatory arguments (Phase 4) — there is
  no path through this node that can search without them.
- **`generate_answer`** — always runs, with whatever context was retrieved (possibly none, for
  small talk or a failed retrieval). Calls the LLM through `ChatModel` (`llm.py`) and gets back
  a **structured** result: `answer`, `grounded` (bool), `confidence` (float). The system prompt
  explicitly instructs the model to answer *only* from provided context and say it doesn't know
  rather than invent information — see "Avoiding hallucination" below for why that instruction
  alone isn't a complete defense.
- **`quality_check`** — deterministic, no LLM call. Turns `(needs_retrieval, retrieved_chunks,
  grounded, confidence)` into a `route`: `"answered"` or `"handoff"`. This is the concrete
  implementation of "the agent should be deterministic where possible, and use the LLM only
  where reasoning is actually needed" — the LLM decides *what to say*, this function decides
  *whether that's good enough to show the customer*, from signals the LLM itself produced but
  didn't get to act on unilaterally.

## Conditional Routing

One conditional edge, after `classify_intent`: retrieval is skipped entirely for small talk
(`"hi"`, `"thanks"`, etc.), both to save an unnecessary vector search and — more importantly —
so `quality_check` doesn't wrongly route a greeting to human handoff just because there was no
knowledge-base content available to be "grounded" in.

## Structured Outputs

`generate_answer` doesn't just get back a string — `ChatModel.answer_from_context` returns an
`AgentAnswer(answer, grounded, confidence)`. The real provider (`OpenAIChatModel`) requests
`response_format={"type": "json_object"}` and the system prompt specifies the exact JSON shape.
This is what makes `quality_check` possible at all: it needs `grounded`/`confidence` as
*data*, not something re-derived by parsing free text after the fact.

## Tool Calling and Memory — deliberately not here yet

This graph has no tool-calling node and no conversation history. That's a phase-boundary
choice, not an oversight: Phase 5's brief is "answer a single question, using knowledge or
saying you don't know." Multi-turn context (Phase 6) changes what `generate_answer` needs to
see; the ticket-creation tool (Phase 7) needs somewhere to write a ticket to once `quality_check`
says `"handoff"`. Building either in here now would mean re-deciding the state shape twice.

## Avoiding Hallucination — and its limits

Two layers, neither sufficient alone:
1. **Prompt-level instruction** (`SYSTEM_PROMPT` in `llm.py`) — tells the model to answer only
   from context and say "I don't know" otherwise.
2. **Structural gate** (`quality_check`) — even if the model claims `grounded: true`, a
   `confidence` below `CONFIDENCE_HANDOFF_THRESHOLD` (0.4, an unvalidated starting guess — see
   Phase 12) routes to handoff instead of trusting the claim.

**What this does NOT do:** nothing here stops a model from ignoring the instruction and
answering from its own training data anyway while still self-reporting `grounded: true`. A
model can be wrong about its own groundedness. The honest limitation: `quality_check` catches
*low self-reported confidence*, not *incorrect self-reported confidence*. Actually measuring
whether answers are truly grounded (comparing the answer against the retrieved text, not just
trusting the model's own claim) is exactly what Phase 12's evaluation dataset is for — this
phase implements the mechanism, Phase 12 measures whether it works.

## Retry Strategy and Failure Handling

Not yet implemented in this graph — an LLM API error, a Qdrant timeout, or malformed JSON from
the model currently propagates as an unhandled exception out of `.invoke()`. This is an
intentional gap, called out here rather than hidden: Phase 10 (`docs/reliability.md`) is where
retry/timeout/circuit-breaker strategy gets designed deliberately, distinguishing retryable
failures (a transient API timeout) from non-retryable ones (malformed output that will fail
identically on retry) — bolting on ad-hoc `try/except` here would preempt that design.

## When an Agent Is Unnecessary

Worth stating plainly, since the temptation with LangGraph available is to route everything
through it: `classify_intent` and `quality_check` are **not** agentic — they're plain
deterministic functions, and correctly so. Only `generate_answer` genuinely needs an LLM
(producing a fluent, context-grounded natural-language answer is not something a heuristic can
do). If a future feature's entire job could be done with an `if` statement, it shouldn't get a
graph node that calls an LLM just because the infrastructure is already there.
