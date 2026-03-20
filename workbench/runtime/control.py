"""Generic Control note loading helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from workbench.runtime.scan import collect_slug_map


@lru_cache(maxsize=None)
def _control_slug_map(control_root: Path) -> dict[str, Path]:
    root = Path(control_root).expanduser().resolve()
    return collect_slug_map([root])


@lru_cache(maxsize=None)
def load_control_content(slug: str, control_root: Path) -> str:
    """Load raw content of a Control note by slug."""
    normalized_slug = str(slug).strip()
    root = Path(control_root).expanduser().resolve()
    slug_map = _control_slug_map(root)

    if normalized_slug not in slug_map:
        raise KeyError(f"Control slug not found: {normalized_slug}")

    path = slug_map[normalized_slug]
    text = path.read_text(encoding="utf-8")

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]

    return text.strip()


__all__ = ["load_control_content"]
