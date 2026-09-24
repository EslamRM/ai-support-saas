"""
Module: documents
File responsibility (chunking.py): text cleaning + chunking with overlap.

TOKEN COUNTING SIMPLIFICATION: chunk_size/overlap are configured in
"approximate tokens" but this module counts them via a word-based
approximation (roughly 0.75 words per token for English text), not
tiktoken's exact BPE tokenization. This sandbox has no network access to
download tiktoken's encoding files, and more importantly, the exact
token count only has to be *close enough* to keep chunks under the
embedding model's context limit with headroom -- it doesn't need to be
exact. Production hardening: swap approximate_token_count() for
tiktoken.encoding_for_model(settings.embedding_model).encode() and count
len(tokens) directly. Isolated in one function specifically so that swap
is one function body, not a codebase-wide change.
"""
import re


def clean_text(text: str) -> str:
    """Collapses runs of whitespace, normalizes line endings. Deliberately
    conservative: doesn't strip punctuation/casing/stopwords, because
    that would also change what the embedding model sees, and RAG quality
    depends on embedding the same kind of text a real user question would
    be compared against."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def approximate_token_count(text: str) -> int:
    """See module docstring -- word-count-based approximation, not exact
    BPE tokenization. Roughly 0.75 words/token for English is the widely
    cited OpenAI estimate."""
    word_count = len(text.split())
    return max(1, round(word_count / 0.75))


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Splits text into overlapping chunks, each targeting ~chunk_size
    approximate tokens, with ~overlap tokens repeated at the start of the
    next chunk. Overlap exists so a sentence spanning a chunk boundary
    still appears whole in at least one chunk -- without it, a fact split
    exactly across the boundary can become unretrievable (neither chunk
    contains the complete sentence).

    Splits on whitespace (word boundaries), not sentences, for simplicity.
    A sentence-aware splitter (e.g. via a sentence tokenizer) would avoid
    ever cutting mid-sentence and is a documented improvement (see
    docs/rag.md limitations) -- not implemented in v1 to avoid adding an
    NLP dependency for a marginal quality gain at this stage.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and less than chunk_size")

    words = text.split()
    if not words:
        return []

    # Convert token-based sizes to approximate word-based sizes (inverse
    # of approximate_token_count's ratio) since we're splitting on words.
    words_per_chunk = max(1, round(chunk_size * 0.75))
    words_overlap = max(0, round(overlap * 0.75))
    step = max(1, words_per_chunk - words_overlap)

    chunks = []
    start = 0
    while start < len(words):
        chunk_words = words[start : start + words_per_chunk]
        chunks.append(" ".join(chunk_words))
        if start + words_per_chunk >= len(words):
            break
        start += step
    return chunks
