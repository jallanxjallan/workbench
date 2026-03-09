"""Deterministic slug segment normalization."""

from __future__ import annotations

import re
import unicodedata

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_HYPHEN_RUN_RE = re.compile(r"-+")
_WHITESPACE_UNDERSCORE_RE = re.compile(r"[\s_]+")
_APOSTROPHE_RE = re.compile(r"[\'’]")


def normalize_segment(value: str) -> str:
    """Normalize one slug segment to canonical ASCII-hyphen form."""
    if not isinstance(value, str):
        raise ValueError("slug segment must be a string")

    lowered = value.strip().lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    without_apostrophes = _APOSTROPHE_RE.sub("", ascii_only)
    hyphenized_spacing = _WHITESPACE_UNDERSCORE_RE.sub("-", without_apostrophes)
    hyphenated = _NON_ALNUM_RE.sub("-", hyphenized_spacing)
    collapsed = _HYPHEN_RUN_RE.sub("-", hyphenated).strip("-")

    if not collapsed:
        raise ValueError("slug segment is empty after normalization")
    return collapsed
