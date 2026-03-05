"""Public API for Workbench slug identity utilities."""

from workbench.slug.builder import build_slug
from workbench.slug.normalize import normalize_segment
from workbench.slug.validator import validate_slug
from workbench.slug.writer import ensure_slug, write_slug

__all__ = [
    "build_slug",
    "ensure_slug",
    "normalize_segment",
    "validate_slug",
    "write_slug",
]
