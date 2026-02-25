"""Immutable slug identity generation."""

from __future__ import annotations

from pathlib import Path

from workbench.tools.markdown_document import Document

from workbench.interop.registry import find_vault_root, load_registry, resolve_project_code
from workbench.interop.slug import compose_slug, generate_suffix, normalize_semantic_base

_MAX_COLLISION_RETRIES = 1024


def create_slug(target_dir: Path, filename_hint: str) -> str:
    target = Path(target_dir).expanduser().resolve()
    vault_root = find_vault_root(target)
    registry = load_registry(vault_root)
    project_code = resolve_project_code(target, registry)
    semantic_base = normalize_semantic_base(filename_hint)

    for _ in range(_MAX_COLLISION_RETRIES):
        suffix = generate_suffix()
        slug = compose_slug(project_code, semantic_base, suffix)
        if not _slug_in_use(vault_root, slug):
            return slug

    raise RuntimeError("failed to generate unique slug after repeated collisions")


def _slug_in_use(vault_root: Path, candidate_slug: str) -> bool:
    for path in vault_root.rglob("*.md"):
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
