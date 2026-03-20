"""Generic runtime slug scanning helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from workbench.interop.document import Document

_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_SKIP_DIR_NAMES = frozenset({
    ".git",
    ".obsidian",
    "__pycache__",
    "_compiled",
    "_control",
    "_staging",
    "archive",
    "node_modules",
    "venv",
    ".venv",
})


def _iter_markdown_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in _SKIP_DIR_NAMES)
        current_path = Path(current_root)
        for filename in sorted(filenames):
            candidate = current_path / filename
            if candidate.suffix.lower() not in _MARKDOWN_SUFFIXES:
                continue
            paths.append(candidate.resolve())
    return paths


def collect_slug_map(roots: Iterable[Path]) -> dict[str, Path]:
    slug_map: dict[str, Path] = {}
    for root in roots:
        root_path = Path(root).expanduser().resolve()
        if not root_path.exists() or not root_path.is_dir():
            continue
        for path in _iter_markdown_files(root_path):
            inspected = Document.inspect_file(path)
            if inspected.error is not None:
                continue
            if not inspected.has_frontmatter or not isinstance(inspected.metadata, dict):
                continue
            raw_slug = inspected.metadata.get("slug")
            if not isinstance(raw_slug, str) or not raw_slug.strip():
                continue
            slug = raw_slug.strip()
            if slug in slug_map:
                existing = slug_map[slug]
                raise RuntimeError(
                    "Duplicate slug detected:\n"
                    f"  slug: {slug}\n"
                    f"  first: {existing}\n"
                    f"  second: {path.resolve()}"
                )
            slug_map[slug] = path.resolve()
    return slug_map


__all__ = ["collect_slug_map"]
