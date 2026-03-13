"""Text normalization helpers."""

from __future__ import annotations

def strip_utf8_bom(text: str) -> str:
    return text[1:] if text.startswith("\ufeff") else text
