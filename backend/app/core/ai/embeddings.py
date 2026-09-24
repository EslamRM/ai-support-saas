"""
Responsibility: abstraction over the embedding provider, so the rest of
the codebase calls embed_texts() without knowing whether it's OpenAI, a
local model, or (in tests / local dev without an API key) a deterministic
offline fake.

This mirrors modules/agent/llm.py's role for the chat model -- both exist
so provider-swapping is a one-file change (see docs/adr/ADR-009, added
later) rather than a grep-and-replace, and so the test suite never needs
a real API key or network access.
"""
import hashlib
from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.reliability import retry_call

# Matches OpenAI's text-embedding-3-small. If EMBEDDING_MODEL changes to a
# model with a different dimensionality, this must change too -- and the
# Qdrant collection would need to be recreated (see docs/rag.md,
# "changing the embedding model" for why this isn't a live migration).
EMBEDDING_DIM = 1536


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Returns one EMBEDDING_DIM-length vector per input text, same order."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Production provider. Kept deliberately thin -- a single API call,
    no branching logic -- so there's as little as possible hiding behind
    the one part of this class the test suite can't exercise (this
    sandbox has no network access to api.openai.com)."""

    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return retry_call(
            "llm.embeddings",
            lambda: [
                item.embedding
                for item in self._client.embeddings.create(
                    model=settings.embedding_model,
                    input=texts,
                    timeout=settings.llm_timeout_seconds,
                ).data
            ],
            max_attempts=settings.ai_max_attempts,
            base_delay=settings.ai_retry_base_delay_seconds,
            max_delay=settings.ai_retry_max_delay_seconds,
        )


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic, fully offline embedding: same text always produces
    the same vector, and it's a real unit vector so cosine similarity math
    behaves sanely -- but it is NOT semantically meaningful. Unlike a real
    embedding model, two sentences with similar meaning but different
    words will NOT land near each other here. This is only good enough to
    prove the pipeline's plumbing (chunk -> vector -> Qdrant -> filtered
    retrieval) end-to-end, not to evaluate retrieval quality -- that
    needs a real embedding model (see docs/evaluation.md, later phase).
    """

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        repeats = EMBEDDING_DIM // len(digest) + 1
        raw = (digest * repeats)[:EMBEDDING_DIM]
        vector = [(b / 127.5) - 1.0 for b in raw]
        norm = sum(v * v for v in vector) ** 0.5
        return [v / norm for v in vector] if norm > 0 else vector


def get_embedding_provider() -> EmbeddingProvider:
    """Real provider whenever an API key is configured, offline fake
    otherwise -- so `pytest` works with zero setup and a real deployment
    just needs OPENAI_API_KEY set, no code change."""
    if settings.openai_api_key:
        return OpenAIEmbeddingProvider()
    return FakeEmbeddingProvider()
