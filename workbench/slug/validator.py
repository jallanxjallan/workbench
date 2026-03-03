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

    namespace, class_name = parts[0], parts[1]

    if class_name == "instruction":
        if len(parts) != 4:
            raise ValueError("instruction slug must include context segment")
    else:
        if len(parts) != 3:
            raise ValueError("non-instruction slug must not include context segment")
        if namespace == "gbl":
            raise ValueError("namespace 'gbl' is reserved for global instructions")

