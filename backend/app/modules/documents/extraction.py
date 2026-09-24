"""
Module: documents
File responsibility (extraction.py): turn raw uploaded bytes into plain
text, per content type. Kept separate from chunking.py because
extraction is format-specific (PDF vs. plain text) while chunking is
format-agnostic -- adding a new supported format (e.g. .docx) only
touches this file.
"""
import io

from app.core.exceptions import DomainError


class UnsupportedContentTypeError(DomainError):
    pass


class ExtractionFailedError(DomainError):
    pass


def extract_text(*, content_type: str, raw_content: bytes) -> str:
    if content_type in ("text/plain", "text/markdown"):
        return _extract_plain_text(raw_content)
    if content_type == "application/pdf":
        return _extract_pdf(raw_content)
    raise UnsupportedContentTypeError(f"Unsupported content type: {content_type}")


def _extract_plain_text(raw_content: bytes) -> str:
    try:
        return raw_content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionFailedError(f"File is not valid UTF-8 text: {exc}") from exc


def _extract_pdf(raw_content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency always present in requirements.txt
        raise ExtractionFailedError("PDF support requires the 'pypdf' package") from exc

    try:
        reader = PdfReader(io.BytesIO(raw_content))
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises several distinct exception types for malformed PDFs
        raise ExtractionFailedError(f"Failed to parse PDF: {exc}") from exc

    text = "\n\n".join(pages_text).strip()
    if not text:
        # A scanned/image-only PDF with no text layer extracts to an
        # empty string -- this is a real, common failure mode (not a bug)
        # that the pipeline must surface as a failed document rather than
        # silently indexing zero chunks. OCR is out of scope for v1 --
        # see docs/rag.md limitations.
        raise ExtractionFailedError(
            "No extractable text found in PDF (it may be a scanned/image-only document; OCR is not supported)"
        )
    return text
