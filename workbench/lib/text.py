"""Text normalization helpers."""

from __future__ import annotations

import re


def snake_case(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value)
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"[\s\-]+", "_", cleaned)
    return cleaned or "chunk"


def kebab_case(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value)
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"[\s_]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned.strip("-") or "item"


def strip_utf8_bom(text: str) -> str:
    return text[1:] if text.startswith("\ufeff") else text
