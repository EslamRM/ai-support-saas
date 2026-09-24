"""Unit tests for document text extraction, including a REAL generated
PDF (via reportlab, a test-only dependency -- see requirements-dev.txt)
so pypdf's extraction path is genuinely exercised, not mocked."""
import io

import pytest

from app.modules.documents.extraction import (
    ExtractionFailedError,
    UnsupportedContentTypeError,
    extract_text,
)


def test_extract_plain_text():
    result = extract_text(content_type="text/plain", raw_content=b"Hello, world!")
    assert result == "Hello, world!"


def test_extract_markdown_treated_as_plain_text():
    result = extract_text(content_type="text/markdown", raw_content=b"# Heading\n\nSome body text.")
    assert "Heading" in result


def test_extract_plain_text_rejects_invalid_utf8():
    with pytest.raises(ExtractionFailedError):
        extract_text(content_type="text/plain", raw_content=b"\xff\xfe\x00invalid")


def test_extract_unsupported_content_type():
    with pytest.raises(UnsupportedContentTypeError):
        extract_text(content_type="application/zip", raw_content=b"whatever")


def test_extract_real_pdf():
    reportlab = pytest.importorskip("reportlab", reason="test-only dependency, see requirements-dev.txt")
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Refunds are processed within 5 business days.")
    c.save()
    raw_pdf = buf.getvalue()

    result = extract_text(content_type="application/pdf", raw_content=raw_pdf)

    assert "Refunds are processed within 5 business days" in result


def test_extract_pdf_with_no_text_layer_raises_extraction_failed():
    reportlab = pytest.importorskip("reportlab", reason="test-only dependency, see requirements-dev.txt")
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()  # blank page, no text drawn -- simulates a scanned/image-only PDF
    c.save()
    raw_pdf = buf.getvalue()

    with pytest.raises(ExtractionFailedError):
        extract_text(content_type="application/pdf", raw_content=raw_pdf)


def test_extract_malformed_pdf_raises_extraction_failed():
    with pytest.raises(ExtractionFailedError):
        extract_text(content_type="application/pdf", raw_content=b"this is not a real pdf file")
