"""Slug generation without registry-bound context."""

from __future__ import annotations

import os
from pathlib import Path
import re
import secrets
import string
import unicodedata

from workbench.interop.document import Document

_MAX_COLLISION_RETRIES = 1024
_BASE36_ALPHABET = string.digits + string.ascii_lowercase
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MULTI_DASH_RE = re.compile(r"-{2,}")
_MAX_SEMANTIC_BASE_LENGTH = 48


def normalize_semantic_base(filename: str) -> str:
    base_name = os.path.basename(str(filename))
    stem, _ = os.path.splitext(base_name)
    normalized = unicodedata.normalize("NFKD", stem)
    no_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = no_diacritics.lower()
    dashed = _NON_ALNUM_RE.sub("-", lowered)
    collapsed = _MULTI_DASH_RE.sub("-", dashed).strip("-")
    clipped = collapsed[:_MAX_SEMANTIC_BASE_LENGTH].strip("-")
    return clipped or "doc"


def generate_suffix(length: int = 5) -> str:
    if length < 1:
        raise ValueError("suffix length must be positive")
    return "".join(secrets.choice(_BASE36_ALPHABET) for _ in range(length))


def compose_slug(semantic_base: str, suffix: str) -> str:
    clean_semantic_base = str(semantic_base).strip()
    clean_suffix = str(suffix).strip()
    if not clean_semantic_base:
        raise ValueError("semantic_base must not be empty")
    if not clean_suffix:
        raise ValueError("suffix must not be empty")
    return f"{clean_semantic_base}-{clean_suffix}"


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
