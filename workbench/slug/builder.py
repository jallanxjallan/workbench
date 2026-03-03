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
    """Build canonical slug for content or instruction objects."""
    normalized_class = normalize_segment(class_name)
    normalized_seed = normalize_segment(seed)

    normalized_namespace: str | None = None
    if namespace is not None and str(namespace).strip():
        normalized_namespace = normalize_segment(namespace)

    normalized_context: str | None = None
    if context is not None:
        normalized_context = normalize_segment(context)

    if normalized_class == "instruction":
        if normalized_context is None:
            raise ValueError("context is required when class_name is 'instruction'")

        if normalized_namespace is None:
            slug = f"gbl.instruction.{normalized_context}.{normalized_seed}"
        else:
            if normalized_namespace == "gbl":
                raise ValueError(
                    "namespace must be omitted for global instruction slugs"
                )
            slug = (
                f"{normalized_namespace}.instruction."
                f"{normalized_context}.{normalized_seed}"
            )
    else:
        if normalized_context is not None:
            raise ValueError("context is only valid for class_name='instruction'")
        if normalized_namespace is None:
            raise ValueError("namespace is required for non-instruction slugs")
        if normalized_namespace == "gbl":
            raise ValueError("namespace 'gbl' is reserved for global instructions")

        slug = f"{normalized_namespace}.{normalized_class}.{normalized_seed}"

    validate_slug(slug)
    return slug

