"""Slug generation without registry-bound context."""

from __future__ import annotations

from pathlib import Path

from workbench.interop.document import Document

from workbench.interop.slug import compose_slug, generate_suffix, normalize_semantic_base

_MAX_COLLISION_RETRIES = 1024


def create_slug(target_dir: Path, filename_hint: str) -> str:
    target = Path(target_dir).expanduser().resolve()
    semantic_base = normalize_semantic_base(filename_hint)

    for _ in range(_MAX_COLLISION_RETRIES):
        suffix = generate_suffix()
        slug = compose_slug(semantic_base, suffix)
        if not _slug_in_use(target, slug):
            return slug

    raise RuntimeError("failed to generate unique slug after repeated collisions")


def _slug_in_use(search_root: Path, candidate_slug: str) -> bool:
    scan_root = search_root if search_root.is_dir() else search_root.parent
    if not scan_root.exists():
        return False
    for path in scan_root.rglob("*.md"):
        if path.stem == candidate_slug:
            return True

        existing_slug = _read_frontmatter_slug(path)
        if existing_slug == candidate_slug:
            return True

    return False


def _read_frontmatter_slug(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    inspected = Document.inspect_text(text)
    if inspected.error:
        return None

    metadata = inspected.metadata or {}
    slug = metadata.get("slug")
    if isinstance(slug, str) and slug.strip():
        return slug.strip()
    return None
