# RAG (Retrieval-Augmented Generation)

This document explains what `backend/app/modules/documents/` and `backend/app/core/ai/`
actually implement, why, and where it will fall short. Retrieval is used by the agent
starting Phase 5 — this document covers the ingestion side and the retrieval mechanism itself.

## Why RAG at all

An LLM's training data doesn't contain a tenant's private product documentation. RAG closes
that gap: instead of asking the model to answer from memory, we find the most relevant pieces
of the tenant's *own* documents and put them directly in the prompt, so the model answers from
text it can actually see. **"Vector search" alone is not "good RAG"** — the encoding, chunking,
filtering, and context-construction choices below determine whether retrieval actually
surfaces the right text, and a wrong or missing chunk produces a wrong or evasive answer no
matter how good the LLM is.

## Pipeline

```
Upload (sync)          Background job (async, Celery)
─────────────          ────────────────────────────────────────────────
raw bytes           →  extract text (extraction.py)
→ Document row          → clean text (chunking.py: clean_text)
  (status=pending)      → chunk with overlap (chunking.py: chunk_text)
→ enqueue job            → embed each chunk (core/ai/embeddings.py)
                          → upsert vectors to Qdrant (core/ai/vector_store.py)
                          → persist DocumentChunk rows in Postgres
                          → mark Document status=indexed (or failed)
```

The upload endpoint (`documents/router.py`) does only the synchronous, fast part: validate,
persist the raw bytes, commit, enqueue. Everything CPU/IO-heavy (parsing, embedding API calls)
happens in `workers/document_tasks.py`, off the request thread — a large PDF doesn't block the
HTTP response. See `docs/architecture.md`'s background-processing section for why this matters.

## Extraction (`extraction.py`)

Supported formats in v1: `text/plain`, `text/markdown` (decoded as UTF-8 directly), and
`application/pdf` (via `pypdf`). A PDF with no extractable text layer — a scanned/image-only
document — raises `ExtractionFailedError` rather than silently indexing zero chunks; that's a
real, common failure mode (not a bug) and the document correctly ends up `failed` with a clear
error message rather than looking like an empty-but-successful upload. **OCR is out of scope
for v1** — a scanned PDF needs an OCR step before this pipeline can use it.

## Cleaning (`chunking.py: clean_text`)

Deliberately conservative: collapses whitespace and normalizes line endings, nothing more. It
does **not** strip punctuation, lowercase text, or remove stopwords, because that would change
what the embedding model actually sees — and RAG quality depends on embedding text that looks
like the kind of thing a real question would be compared against, not a stripped-down bag of
words.

## Chunking (`chunking.py: chunk_text`)

- **Chunk size / overlap**, configured in `CHUNK_SIZE` (default 800) and `CHUNK_OVERLAP`
  (default 150), are in **approximate tokens**, not exact BPE tokens — see the "token counting
  simplification" note in `chunking.py`'s module docstring for why (this environment has no
  network access to download `tiktoken`'s encoding files, and the exact count only needs to be
  close enough to stay under the embedding model's context limit with headroom). Production
  hardening: swap `approximate_token_count()` for real `tiktoken` counting — isolated to one
  function specifically so that's a contained change.
- **Why overlap at all:** without it, a fact that happens to fall exactly across a chunk
  boundary can become unretrievable — neither the chunk before nor after contains the complete
  sentence. Overlap re-includes the tail of one chunk at the head of the next so boundary-
  spanning content still appears whole somewhere.
- **Splitting on words, not sentences:** simpler, no extra NLP dependency, but it means a chunk
  can end mid-sentence. A sentence-aware splitter is a documented, not-yet-implemented
  improvement (see Limitations below).

## Metadata

Every chunk stored in Qdrant carries `tenant_id`, `knowledge_base_id`, and `document_id` in its
payload (`core/ai/vector_store.py: upsert_chunks`). Every `DocumentChunk` row in Postgres
carries the same, plus `chunk_index` and `token_count`. This metadata is what makes filtered
retrieval possible — and mandatory, see Tenant Filtering below.

## Embeddings (`core/ai/embeddings.py`)

Abstracted behind an `EmbeddingProvider` interface with two implementations:
- `OpenAIEmbeddingProvider` — production, calls the real embeddings API
  (`text-embedding-3-small`, 1536 dimensions).
- `FakeEmbeddingProvider` — a deterministic, offline, hash-based embedding used automatically
  whenever `OPENAI_API_KEY` is unset (local dev without a key, and the entire test suite).
  **It is not semantically meaningful** — unlike a real model, two sentences with similar
  meaning but different words will not land near each other. It only proves the pipeline's
  plumbing works end-to-end (chunk → vector → Qdrant → filtered retrieval), not that retrieval
  quality is good. Retrieval *quality* evaluation (Phase 12, `docs/evaluation.md`) requires the
  real provider.

## Vector similarity and Qdrant (`core/ai/vector_store.py`)

Cosine similarity, over a single `document_chunks` collection shared by all tenants — isolation
is enforced by payload filtering, not by separate collections per tenant (see Tenant Filtering).

**Why one shared collection instead of one per tenant:** a collection per tenant would give
stronger physical isolation but means provisioning a new collection on every tenant signup,
and Qdrant's per-collection overhead doesn't amortize well across a large number of
low-document tenants. Filtered search in a shared collection is the standard pattern at this
scale; revisit if a single tenant's data volume or an even stricter isolation requirement
justifies dedicated collections later.

## Top-K and similarity threshold

Configured via `RETRIEVAL_TOP_K` (default 5) and `RETRIEVAL_SIMILARITY_THRESHOLD` (default
0.7). Top-K bounds how much text enters the LLM context (cost and latency both scale with
it — see docs/cost, added later). The similarity threshold is a cutoff below which a "match"
is probably not actually relevant and would just add noise (or invite the model to talk about
something it wasn't really asked about). **Both are tuned against a real embedding model** —
the defaults are reasonable starting points, not values validated against this specific
product's documents; that tuning is exactly what Phase 12's evaluation dataset is for.

## Tenant Filtering — the structural guarantee

`VectorStore.search()` takes `tenant_id` and `knowledge_base_id` as **mandatory** keyword
arguments and bakes them into the Qdrant query filter itself — there is no method signature
that allows a search without them. This is the direct implementation of the "vector store
leakage" isolation risk named in `docs/architecture.md`: a bug elsewhere might pass the wrong
`tenant_id`, but the *code shape* makes it impossible to construct a query that skips the
filter entirely.

`tests/integration/test_document_ingestion.py::test_retrieval_never_crosses_tenant_boundaries`
proves this directly — it uploads **near-identical content** into two different tenants' KBs
and asserts that searching as tenant A never returns tenant B's chunks, even though both were
embedded from essentially the same text.

## Context Construction

Not yet implemented — this is Phase 5's job (the LangGraph agent assembles retrieved chunks
into the prompt context). Documented here as the next link in the chain: retrieval produces
`RetrievedChunk` objects (chunk text + score + source document id); Phase 5 defines how those
become part of what the LLM sees, and how the agent is instructed to ground its answer in that
context and say when it doesn't know.

## RAG Limitations (known now, honestly)

- **Word-based chunking**, not sentence-aware — a chunk can end mid-sentence.
- **Word-based token approximation**, not exact — chunks could occasionally run larger or
  smaller than intended relative to the embedding model's real tokenizer.
- **No OCR** — scanned/image-only PDFs fail extraction outright.
- **No re-ranking step** — results are returned in raw vector-similarity order; a
  cross-encoder re-ranker (common in production RAG systems) would likely improve precision
  but adds latency and another model call, deferred until evaluation data shows it's needed.
- **No deduplication across near-identical chunks** — if a tenant uploads the same document
  twice, both get indexed and both can appear in results.
- **Hallucination is not eliminated by RAG** — it's *reduced*, because the model has real text
  to ground in, but nothing here stops a model from ignoring the provided context and answering
  from its own training data anyway. That's an agent-level concern (instructing the model to
  only use provided context, and detecting when it hasn't) — addressed in Phase 5's agent
  design and measured in Phase 12's evaluation (`docs/evaluation.md`).
