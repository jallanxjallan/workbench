"""Slug ensure/write operations for markdown files."""

from __future__ import annotations

from pathlib import Path

from workbench.interop.document import Document
from workbench.lib.rg import RipgrepError, find_files_with_slug
from workbench.slug.builder import build_slug
from workbench.slug.validator import validate_slug

MARKDOWN_SUFFIXES = (".md", ".markdown")


def _is_within_root(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def write_slug_to_document(
    *,
    filepath: Path,
    document: Document,
    slug: str,
    require_placeholder: bool = True,
) -> str:
    path = Path(filepath).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError(f"target file does not exist: {path}")
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise ValueError(f"target file is not markdown: {path}")
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("slug must be a non-empty string")

    validate_slug(slug)

    metadata = dict(document.metadata or {})
    existing = metadata.get("slug")
    if require_placeholder:
        if not isinstance(existing, str) or existing.strip() != "__SLUG__":
            raise ValueError("slug sentinel '__SLUG__' not found")

    metadata["slug"] = slug
    Document(content=document.content, metadata=metadata).write_file(
        path, overwrite=True
    )
    return slug


def write_slug(filepath: Path, slug: str, *, require_placeholder: bool = True) -> str:
    path = Path(filepath).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError(f"target file does not exist: {path}")
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise ValueError(f"target file is not markdown: {path}")
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("slug must be a non-empty string")

    validate_slug(slug)

    doc = Document.read_file(path)
    return write_slug_to_document(
        filepath=path,
        document=doc,
        slug=slug,
        require_placeholder=require_placeholder,
    )


def ensure_slug(
    filepath: Path,
    *,
    namespace: str | None = None,
    slug_owner_index: dict[str, set[Path]] | None = None,
) -> str:
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
                if slug_owner_index is not None:
                    slug_owner_index.setdefault(existing_text, set()).add(path)
                return existing
        else:
            raise ValueError("existing slug must be a string")

    class_raw = metadata.get("class")
    if not isinstance(class_raw, str) or not class_raw.strip():
        raise ValueError("missing class in frontmatter")

    context_raw = metadata.get("context")
    context = (
        context_raw if isinstance(context_raw, str) and context_raw.strip() else None
    )

    seed = path.stem
    slug = build_slug(
        namespace=namespace,
        class_name=class_raw,
        seed=seed,
        context=context,
    )

    if slug_owner_index is not None:
        owners = {
            owner
            for owner in slug_owner_index.get(slug, set())
            if _is_within_root(owner, path.parent)
        }
    else:
        try:
            owners = set(find_files_with_slug(slug, root=path.parent))
        except RipgrepError as exc:
            raise ValueError(str(exc)) from exc
    if any(owner != path for owner in owners):
        raise ValueError(f"slug collision detected: {slug}")

    metadata["slug"] = slug
    Document(content=doc.content, metadata=metadata).write_file(path, overwrite=True)
    if slug_owner_index is not None:
        slug_owner_index.setdefault(slug, set()).add(path)
    return slug
