"""Slug ensure/write operations for markdown files."""

from __future__ import annotations

from pathlib import Path

from workbench.interop.document import Document
from workbench.slug.builder import build_slug
from workbench.slug.normalize import normalize_segment
from workbench.slug.validator import validate_slug

MARKDOWN_SUFFIXES = (".md", ".markdown")


def ensure_slug(filepath: Path, *, namespace: str | None = None) -> str:
    """
    Ensure a file has a valid slug.

    If slug exists, it is validated and returned unchanged.
    If missing, a deterministic slug is built and written.
    """
    path = Path(filepath).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError(f"target file does not exist: {path}")
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise ValueError(f"target file is not markdown: {path}")

    inspected = Document.inspect_file(path)
    if inspected.error:
        raise ValueError(f"failed to parse markdown: {inspected.error}")
    if not inspected.has_frontmatter:
        raise ValueError("missing frontmatter block")
    doc = Document.read_file(path)

    metadata = dict(doc.metadata or {})

    if "slug" in metadata:
        existing = metadata["slug"]
        if existing is None:
            del metadata["slug"]
        elif isinstance(existing, str):
            existing_text = existing.strip()
            if not existing_text or existing_text.lower() == "__slug__":
                del metadata["slug"]
            else:
                validate_slug(existing)
                return existing
        else:
            raise ValueError("existing slug must be a string")

    class_raw = metadata.get("class")
    if not isinstance(class_raw, str) or not class_raw.strip():
        raise ValueError("missing class in frontmatter")

    context: str | None = None
    if normalize_segment(class_raw) == "instruction":
        context_raw = metadata.get("context")
        if not isinstance(context_raw, str) or not context_raw.strip():
            raise ValueError("missing context for instruction class")
        context = context_raw

    seed = path.stem
    slug = build_slug(
        namespace=namespace,
        class_name=class_raw,
        seed=seed,
        context=context,
    )

    sibling_slugs = _collect_sibling_slugs(path)
    if slug in sibling_slugs:
        raise ValueError(f"slug collision detected: {slug}")

    metadata["slug"] = slug
    Document(content=doc.content, metadata=metadata).write_file(path, overwrite=True)
    return slug


def _collect_sibling_slugs(filepath: Path) -> set[str]:
    slugs: set[str] = set()
    target = filepath.resolve()

    for path in target.parent.rglob("*"):
        if path.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        resolved = path.resolve()
        if resolved == target:
            continue

        try:
            doc = Document.read_file(resolved)
        except ValueError as exc:
            raise ValueError(f"failed to parse sibling markdown: {resolved}: {exc}") from exc

        data = dict(doc.metadata or {})
        value = data.get("slug")
        if not isinstance(value, str):
            continue

        value_text = value.strip()
        if not value_text or value_text.lower() in {"__slug__", "null", "~"}:
            continue

        validate_slug(value_text)
        slugs.add(value_text)

    return slugs
