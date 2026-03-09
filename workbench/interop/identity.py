"""Slug generation without registry-bound context."""

from __future__ import annotations

import os
from pathlib import Path
import re
import unicodedata

from workbench.lib.identity import slug as identity_slug

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


def create_slug(target_dir: Path, filename_hint: str) -> str:
    del target_dir  # retained for backwards-compatible call signatures
    base_name = os.path.basename(str(filename_hint))
    stem, _ = os.path.splitext(base_name)
    return identity_slug(stem or filename_hint)
