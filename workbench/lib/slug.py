"""Slug validation helpers."""

from __future__ import annotations

import re

_BATCH_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_batch_slug(value: str) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if not normalized or normalized != value:
        return False
    return _BATCH_SLUG_RE.fullmatch(normalized) is not None
