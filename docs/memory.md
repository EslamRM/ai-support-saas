# Conversation Memory

This document explains what `backend/app/modules/conversations/` implements, and how it
connects to the agent graph from Phase 5.

## Short-term vs. long-term memory — and what "memory" means here

- **Short-term memory** = the current conversation's recent turns, sent to the LLM on every
  request so it has continuity within one conversation (`context.py: build_bounded_history`).
  This is what's implemented.
- **Long-term memory** = knowledge that persists and is retrieved *across* conversations —
  e.g. "this customer mentioned last week they're on the Enterprise plan." **Not implemented
  in v1.** There's no cross-conversation customer profile; each conversation's context is
  scoped to that conversation alone. Building this would mean either a separate
  `CustomerProfile`-style store or treating past conversation summaries as retrievable
  documents — a real design decision, deferred until there's a product requirement driving it
  rather than built speculatively.

## What "conversation history" actually is here

`Conversation` (one thread with one customer, scoped to one knowledge base) and `Message`
(one turn, `role` = `user`/`assistant`, plus `agent_metadata` — the `route`/`grounded`/
`confidence` the agent produced for that turn, stored so the dashboard, Phase 8, can show *why*
a message was routed to handoff without re-running the agent).

## The context window problem

Sending the entire conversation transcript to the LLM on every turn has two failure modes, both
easy to miss in short test conversations and ugly in production:
1. **Cost scales without bound** — a 50-turn conversation costs roughly 50x what turn 1 cost,
   on every subsequent turn, because the whole history is retransmitted every time.
2. **It eventually exceeds the model's context window outright** — a long-running support
   thread would simply break.

## The implemented strategy: two-layer bounding

1. **DB-level row cap** (`repository.py: MessageRepository.list_recent_for_conversation`,
   `MAX_MESSAGES_LOADED_FOR_CONTEXT = 50`) — bounds what's even loaded into memory from
   Postgres, regardless of how long the full conversation actually is.
2. **Token-budget trim** (`context.py: build_bounded_history`,
   `DEFAULT_MAX_HISTORY_TOKENS = 2000`) — walks the loaded messages newest-to-oldest,
   accumulating until the approximate token budget would be exceeded, then returns the
   surviving subset oldest-first. "50 short messages" and "50 very long messages" cost very
   differently — the row cap alone doesn't account for that, which is why there are two layers,
   not one.

Both use the same **word-count token approximation** as `documents/chunking.py`
(`approximate_token_count`) for the same reason: no network access to download `tiktoken`'s
encoding files in this environment, and the count only needs to be close enough to keep
requests under the model's actual context limit with headroom — not exact.

**Edge case handled explicitly:** if a single message alone exceeds the token budget, it's
still returned alone rather than producing an empty history — an over-budget-but-present last
turn is more useful than silently dropping the customer's most recent message entirely (see
`test_a_single_oversized_message_is_still_returned_alone`).

## When to retrieve previous information

"Retrieval" here (Phase 4/5's Qdrant search) only ever searches the **current question's**
text — conversation history is *not* currently folded into the retrieval query. This is a
real, named limitation: a follow-up like "what about for a damaged item?" (referring back to
"what's your refund policy?" from two turns ago) won't retrieve refund-policy chunks, because
the retrieval query is just "what about for a damaged item?" in isolation. The system prompt
(`modules/agent/llm.py`) does give the model the conversation history for *understanding what
the user means*, but that doesn't help retrieval find the right chunks if the current turn's
text alone doesn't carry enough signal. The correct fix — query rewriting, where a cheap step
reformulates the current question using conversation context before embedding it for search —
is a natural Phase 12-informed improvement once evaluation data shows this actually hurts
retrieval quality in practice, rather than guessed at now.

## Summarization — not implemented, and why

Once messages age out of the bounded window, they are **dropped**, not summarized. A detail
mentioned 20 turns ago (an order number, a prior troubleshooting step) is silently forgotten
rather than carried forward compressed. The natural extension: when messages fall outside the
window, run them through a cheap summarization LLM call and prepend the result as a synthetic
leading turn ahead of the recent window. Not built in v1 — it's another LLM call (cost,
latency, another failure mode) for a product whose first-version support conversations are
mostly short. Worth adding once real usage data (not a guess) shows long conversations are
common enough to matter — see `docs/scaling.md`, added later.

## Token cost, concretely

Every turn's LLM call cost now has two components: the (bounded) history + the new question +
the retrieved context. `docs/cost.md` (added in a later phase) will tie this to actual
per-conversation dollar estimates; for now, the practical implication is that
`DEFAULT_MAX_HISTORY_TOKENS` is a direct cost lever — halving it roughly halves the
history-driven portion of per-turn token cost, at the expense of the model "remembering" less
of the conversation.

## Testing note

`tests/integration/test_conversations.py` exercises the full loop — create conversation, send
multiple messages, read back the transcript, prove tenant isolation — through the real HTTP
API with the real agent graph (`patch_agent_graph` fixture wires in the same embedded Qdrant +
offline `FakeChatModel` used in Phase 4/5). `tests/unit/test_conversation_context.py` tests
`build_bounded_history` in isolation, including the single-oversized-message edge case.
