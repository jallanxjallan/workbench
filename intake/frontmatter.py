from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class FrontmatterError(RuntimeError):
    pass


def read_frontmatter(path: Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")

    if not text.startswith("---\n"):
        return {}

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise FrontmatterError(f"Unterminated frontmatter: {path}")

    raw = parts[1].strip()
    if not raw:
        return {}

    data = yaml.safe_load(raw)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise FrontmatterError(f"Frontmatter must be a mapping: {path}")

    return data