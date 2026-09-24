"""
Module: conversations
File responsibility (context.py): the conversation context strategy --
which prior messages actually get sent to the LLM on a given turn.

STRATEGY (v1): a recency-bounded window, capped by an approximate token
budget (DEFAULT_MAX_HISTORY_TOKENS), on top of a row-count cap already
applied at the DB query level (see repository.py:
list_recent_for_conversation). Two layers, deliberately: the DB-level
LIMIT bounds how much ever gets loaded into memory at all; this
function's token budget bounds what actually gets sent to the model,
since "50 short messages" and "50 very long messages" cost very
differently.

WHY THIS MATTERS: sending the entire conversation history on every turn
means the per-message cost grows without bound as a conversation gets
longer, and eventually the history alone exceeds the model's context
window -- a failure that's easy to miss in testing (short test
conversations never hit it) and ugly in production (a long-running
support thread suddenly breaks).

WHAT'S NOT IMPLEMENTED (named, not hidden): summarization-based long-term
memory. Once messages fall outside the window, they are DROPPED, not
summarized -- a detail the customer mentioned 20 turns ago (an order
number, a prior troubleshooting step) is silently forgotten rather than
carried forward as compressed context. The natural extension: when
messages age out of the window, run them through a cheap summarization
LLM call and prepend the result as a synthetic leading turn ahead of the
recent window. Not built in v1 because it's another LLM call (cost +
latency + another failure mode) for a product whose first-version
support conversations are mostly short; worth adding once real usage
data shows long conversations are common (see docs/scaling.md, added
later) rather than guessing the need upfront.
"""
from app.modules.conversations.models import Message
from app.modules.documents.chunking import approximate_token_count

DEFAULT_MAX_HISTORY_TOKENS = 2000


def build_bounded_history(messages: list[Message], *, max_tokens: int = DEFAULT_MAX_HISTORY_TOKENS) -> list[dict]:
    """messages must be ordered OLDEST-FIRST. Returns the most recent
    subset that fits under max_tokens (approximate -- same word-count
    approximation as chunking.approximate_token_count, and the same
    reasoning for why exact tiktoken counting isn't used here), still
    oldest-first, as plain {"role", "content"} dicts -- an LLM-provider-
    agnostic shape, not the ORM model itself (modules/agent/llm.py
    shouldn't need to know about SQLAlchemy)."""
    selected: list[Message] = []
    total_tokens = 0

    for message in reversed(messages):  # walk newest -> oldest
        message_tokens = approximate_token_count(message.content)
        # Always keep at least the single most recent message, even if it
        # alone exceeds max_tokens -- an empty history because the last
        # turn was long is worse than a slightly-over-budget one.
        if selected and total_tokens + message_tokens > max_tokens:
            break
        selected.append(message)
        total_tokens += message_tokens

    selected.reverse()  # back to oldest-first
    return [{"role": m.role.value, "content": m.content} for m in selected]
