# Senior/Staff Interview Questions — Actual Project

This document is intentionally tied to the implementation rather than a generic AI course.

## Product Questions

### Q: What business problem does this solve?
**Short answer:** Companies can let an AI answer support questions from their own knowledge
base and hand uncertain cases to humans.

**Deep:** The value comes from reducing repetitive support work while preserving a human
path for cases the system cannot ground.

**Project:** RAG + deterministic handoff.

**Trade-offs:** More automation increases the cost of incorrect automation.

**Common mistake:** Claiming the agent should answer every question.

**Follow-ups:** How would you measure deflection without rewarding hallucinations?

## Architecture Questions

### Q: Why a modular monolith?
**Short:** The product needs strong module boundaries but does not yet need distributed
deployment complexity.

**Deep:** Each bounded context owns routers/services/repositories. AI orchestration is
isolated in `agent/`. Extraction runs in a worker.

**Project:** FastAPI is one deployable; Redis/Celery and Qdrant are infrastructure
dependencies.

**Trade-offs:** A monolith shares a failure domain, but is easier to debug.

**Mistake:** Splitting every module into a service immediately.

**Follow-ups:** What signal would justify extraction?

## Backend Questions

### Q: Where is the transaction boundary for a conversation turn?
**Short:** The customer message is persisted before inference; the AI-created ticket and
assistant message share a final commit.

**Deep:** Provider calls are outside the database transaction. Holding a DB transaction
open across a 20-second LLM call would be harmful.

**Project:** This is why the user message is durable even on provider failure.

**Trade-off:** The turn is not fully atomic across the external LLM call.

**Follow-up:** How would you make retries idempotent?

## Database Questions

### Q: Why is Postgres the source of truth while Qdrant is an index?
**Short:** Business entities need transactions and relational integrity; vector search is
an optimized retrieval index.

**Project:** Documents and chunks exist in Postgres; Qdrant stores searchable vectors.

**Follow-up:** What happens if Qdrant loses data?

## RAG Questions

### Q: Why chunk documents?
**Short:** Sending whole documents wastes context and makes retrieval less precise.

**Deep:** Chunking converts large documents into retrievable units. Chunk size and overlap
trade context completeness against retrieval noise and token cost.

**Project:** `chunk_size` and `chunk_overlap` are configuration values.

**Follow-up:** How would you tune chunking?

## Embedding Questions

### Q: What does an embedding represent?
**Short:** A text-to-vector mapping intended to place semantically related text near each
other in vector space.

**Project:** The embedding adapter hides the provider.

**Trade-off:** Better embeddings can improve retrieval but cost more and require re-indexing
when dimensionality/model semantics change.

## Vector Database Questions

### Q: How do you prevent cross-tenant retrieval?
**Short:** Tenant and knowledge-base IDs are mandatory inputs to `VectorStore.search()` and
are embedded in the Qdrant filter.

**Project:** There is no public search method without those filters.

**Follow-up:** Would you add a second defense? PostgreSQL RLS cannot directly protect Qdrant,
so application-level filtering and tenant-scoped collections are alternatives.

## LangGraph Questions

### Q: Why LangGraph instead of one prompt?
**Short:** The workflow has explicit state and conditional routing.

**Project:** classify -> retrieve -> generate -> quality check.

**Trade-off:** A framework is unnecessary for a single deterministic LLM call.

**Follow-up:** When would you remove LangGraph?

## Agentic AI Questions

### Q: Is this truly autonomous?
**Short:** It is intentionally bounded. The graph controls retrieval and handoff; the LLM
does not control security-sensitive side effects.

**Project:** Ticket creation is invoked by application code after deterministic quality
checking.

**Follow-up:** What would you allow an autonomous agent to do later?

## LLM Questions

### Q: What happens when the model returns malformed JSON?
**Short:** Parsing fails and the request does not execute a side effect.

**Project:** Structured JSON is parsed into explicit fields.

**Follow-up:** Would you retry malformed output? Only with a bounded structured-output
repair strategy; never blindly.

## Prompt Engineering Questions

### Q: How do you reduce hallucination?
**Short:** Restrict factual answers to retrieved context, request groundedness/confidence,
and route uncertain retrieval cases to human handoff.

**Trade-off:** Conservative behavior can increase handoffs.

## Memory Questions

### Q: Why not send the full transcript?
**Short:** Context windows and token costs grow with conversation length.

**Project:** Recent history is bounded before entering graph state.

**Follow-up:** When would you summarize older turns?

## Tool Calling Questions

### Q: Why isn't ticket creation an LLM-selected function call?
**Short:** Because whether a ticket should exist is a business/security decision. The model
can help write the summary, but trusted application code decides the side effect.

## AI Security Questions

### Q: What is the LLM security boundary?
**Short:** The LLM is untrusted. It can propose text but cannot authorize access or execute
arbitrary commands.

## Prompt Injection Questions

### Q: What if a document says "ignore system instructions"?
**Short:** Retrieved document text is data, not authority. The system prompt defines behavior
and the application enforces tenant scope and tools.

**Follow-up:** What about indirect prompt injection that manipulates an LLM into producing
a malicious ticket? Validate tool inputs and constrain tool capabilities.

## Multi-Tenancy Questions

### Q: How do you prove tenant isolation?
**Short:** Tests create two tenants and verify that IDs from tenant B return not-found/empty
results to tenant A.

**Project:** SQL repositories and Qdrant filters are tenant-scoped.

## Authentication/RBAC Questions

### Q: Why re-read the user from the database if JWT is signed?
**Short:** A signed token proves integrity, not that the user is still active or that its
tenant claim matches current DB state.

## Redis Questions

### Q: What is Redis doing?
**Short:** Celery uses it as the broker/backend. A future shared rate limiter can also use it.

## Async Processing Questions

### Q: What belongs in Celery?
**Short:** Document extraction/chunking/embedding/indexing.

**Why:** It is slow and eventually consistent.

## Performance Questions

### Q: Where is latency spent?
**Short:** Usually retrieval/provider calls dominate; the system logs HTTP, retrieval,
LLM and total agent latency separately.

## Scalability Questions

### Q: What changes at 100x?
**Short:** Scale API and workers independently, move analytics to aggregates, use shared
rate limiting and observability, then extract services only if measurements justify it.

## Reliability Questions

### Q: What do you retry?
**Short:** Timeouts, connection failures, 429 and upstream 5xx, with bounded exponential
backoff and jitter.

## Observability Questions

### Q: What would you investigate for a slow customer response?
**Short:** Start with `X-Request-ID`, compare total request latency with agent, retrieval and
LLM latency, then inspect token usage and upstream failures.

## Testing Questions

### Q: How do you test an LLM system?
**Short:** Unit-test deterministic logic and evaluate model behavior with datasets and
quality dimensions rather than exact generated strings.

## Evaluation Questions

### Q: What is retrieval relevance?
**Short:** Whether the retrieved chunks actually contain evidence needed for the question.

## Docker/Deployment Questions

### Q: Why separate the worker?
**Short:** Ingestion workload has different scaling and failure characteristics from the
interactive API.

## Cost Optimization Questions

### Q: How do you control LLM cost?
**Short:** Bound context, avoid unnecessary retrieval/LLM calls for small talk, record token
usage, and use model/provider routing when quality allows.

## System Design Questions

### Q: What would you change for 1M conversations/month?
**Short:** Keep the domain boundaries but scale API/workers independently, optimize Postgres
message storage and analytics, control LLM cost, add durable job delivery, and introduce
distributed tracing.

The important Staff-level skill is explaining why each change is justified by a measured
bottleneck rather than adding infrastructure because it is fashionable.
