"""Slug formatting primitives."""

from __future__ import annotations

import os
import re
import secrets
import string
import unicodedata

_BASE36_ALPHABET = string.digits + string.ascii_lowercase
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MULTI_DASH_RE = re.compile(r"-{2,}")
_MAX_SEMANTIC_BASE_LENGTH = 48


def normalize_semantic_base(filename: str) -> str:
    base_name = os.path.basename(str(filename))
    stem, _ = os.path.splitext(base_name)
    normalized = unicodedata.normalize("NFKD", stem)
    no_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = no_diacritics.lower()
    dashed = _NON_ALNUM_RE.sub("-", lowered)
    collapsed = _MULTI_DASH_RE.sub("-", dashed).strip("-")
    clipped = collapsed[:_MAX_SEMANTIC_BASE_LENGTH].strip("-")
    return clipped or "doc"


def generate_suffix(length: int = 5) -> str:
    if length < 1:
        raise ValueError("suffix length must be positive")
    return "".join(secrets.choice(_BASE36_ALPHABET) for _ in range(length))


def compose_slug(semantic_base: str, suffix: str) -> str:
    clean_semantic_base = str(semantic_base).strip()
    clean_suffix = str(suffix).strip()
    if not clean_semantic_base:
        raise ValueError("semantic_base must not be empty")
    if not clean_suffix:
        raise ValueError("suffix must not be empty")
    return f"{clean_semantic_base}-{clean_suffix}"
