"""Schema-driven slug construction."""

from __future__ import annotations

from workbench.slug.normalize import normalize_segment
from workbench.slug.validator import validate_slug


def build_slug(
    *,
    namespace: str | None,
    class_name: str,
    seed: str,
    context: str | None = None,
) -> str:
    """Build canonical slug with optional context for any class."""
    if namespace is None or not str(namespace).strip():
        raise ValueError("namespace is required")

    normalized_namespace = normalize_segment(namespace)
    normalized_class = normalize_segment(class_name)
    normalized_seed = normalize_segment(seed)
    normalized_context = normalize_segment(context) if context is not None else None

    if normalized_context is None:
        slug = f"{normalized_namespace}.{normalized_class}.{normalized_seed}"
    else:
        slug = (
            f"{normalized_namespace}.{normalized_class}."
            f"{normalized_context}.{normalized_seed}"
        )

    validate_slug(slug)
    return slug
