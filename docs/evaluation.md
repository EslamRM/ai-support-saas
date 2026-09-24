# Phase 12 — Evaluation

## Why unit tests are not enough

A unit test can prove that a function routes to `retrieve_knowledge`. It cannot prove that
retrieval returns the right evidence for paraphrased questions or that an LLM answer is
grounded.

LLM quality is probabilistic, so evaluation needs a small dataset and explicit dimensions.

## Dataset

`tests/evaluation/dataset.jsonl` contains cases for:

- answer clearly available
- partially available answer
- unavailable answer
- similar but incorrect information
- prompt injection
- multi-turn context

Each case has:
- `id`
- `question`
- `expected_behavior`
- `reference_keywords`
- `category`

## Metrics

### Retrieval relevance

For a question with known relevant documents:

`relevant_retrieved / retrieved`

A stronger version should use Recall@K and MRR against human-labeled relevant chunks.

### Answer correctness

Compare the response to an expected fact set, not an exact sentence.

### Groundedness

Every factual claim should be supported by retrieved context. For a first version,
human review can label each answer grounded / not grounded.

### Failure behavior

For unsupported questions, the expected behavior is an explicit uncertainty response
or a human handoff rather than fabricated information.

## Running the evaluation

Export one JSONL result per case with the fields described in `scripts/evaluate.py`, then run:

```bash
python scripts/evaluate.py results.jsonl
```

The evaluation dataset is deliberately provider-neutral. A production evaluation runner
should invoke the same graph used by the API with a real embedding/LLM provider and record
results as JSON.

Do not mix offline fake embeddings with real semantic retrieval quality scores: the fake
provider is deterministic plumbing, not a meaningful semantic model.

## Regression strategy

Keep a fixed "golden set" of representative support questions. Run it whenever:
- prompts change
- embedding models change
- retrieval thresholds change
- agent routing changes
- provider/model changes

Track quality, latency and token cost together because an improvement in one dimension
can regress another.
