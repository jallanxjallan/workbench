"""PDF text extraction utility."""

from __future__ import annotations

from pathlib import Path


class PdfExtractTextError(RuntimeError):
    """Raised when text extraction fails."""


def extract_text(source_path: Path) -> str:
    """Extract text from PDF using pypdf when available."""
    try:
        from pypdf import PdfReader
    except Exception as exc:  # noqa: BLE001
        raise PdfExtractTextError(
            "pypdf is not installed; install pypdf to enable pdf-extract-text"
        ) from exc

    try:
        reader = PdfReader(str(source_path))
        chunks = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # noqa: BLE001
        raise PdfExtractTextError(f"failed to extract text from {source_path}: {exc}") from exc

    return "\n".join(chunks)
