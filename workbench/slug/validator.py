"""Canonical slug validation."""

from __future__ import annotations

import re

SEGMENT_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
SLUG_PATTERN = re.compile(
    rf"^{SEGMENT_PATTERN}\.{SEGMENT_PATTERN}\.(?:{SEGMENT_PATTERN}\.)?{SEGMENT_PATTERN}$"
)


def validate_slug(slug: str) -> None:
    """Raise ValueError when slug violates frozen grammar/structure."""
    if not isinstance(slug, str) or not slug:
        raise ValueError("slug must be a non-empty string")

    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug does not match canonical pattern")

    parts = slug.split(".")
    if len(parts) not in (3, 4):
        raise ValueError("slug must contain 3 or 4 dot-separated segments")
