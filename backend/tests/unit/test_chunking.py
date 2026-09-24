"""Unit tests for text cleaning and chunking -- no DB, no HTTP."""
import pytest

from app.modules.documents.chunking import approximate_token_count, chunk_text, clean_text


def test_clean_text_collapses_whitespace():
    assert clean_text("Hello   world\t\tfoo") == "Hello world foo"


def test_clean_text_normalizes_line_endings_and_collapses_blank_lines():
    raw = "Line one\r\n\r\n\r\n\r\nLine two\rLine three"
    cleaned = clean_text(raw)
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned


def test_chunk_text_empty_string_returns_no_chunks():
    assert chunk_text("", chunk_size=100, overlap=10) == []


def test_chunk_text_short_text_returns_single_chunk():
    text = "This is a short document."
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long_text_produces_multiple_overlapping_chunks():
    words = [f"word{i}" for i in range(500)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    # Every chunk should be non-empty and shorter than the full text.
    assert all(chunks)
    assert all(len(c) < len(text) for c in chunks)

    # Prove actual overlap: words from the tail of the first chunk should
    # reappear somewhere in the second chunk (the whole point of overlap
    # -- a fact split across a boundary should still appear whole in one
    # chunk). Checking against the whole second chunk, not just its first
    # few words, since the overlap region doesn't necessarily land in an
    # arbitrarily-chosen small window at the very start.
    first_chunk_tail = set(chunks[0].split()[-10:])
    second_chunk_words = set(chunks[1].split())
    assert first_chunk_tail & second_chunk_words


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("some text here", chunk_size=100, overlap=100)  # overlap == chunk_size
    with pytest.raises(ValueError):
        chunk_text("some text here", chunk_size=100, overlap=-1)


def test_approximate_token_count_roughly_scales_with_word_count():
    short = approximate_token_count("one two three")
    long = approximate_token_count(" ".join(["word"] * 300))
    assert long > short * 10
