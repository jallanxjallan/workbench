from __future__ import annotations

from pathlib import Path
from typing import Iterable

from workbench.scan.rg import rg_search


def rg_collect_unique_slugs(*, roots: Iterable[Path]) -> dict[str, Path]:
    """
    Discover all slugs across multiple roots and enforce global uniqueness.

    Returns:
        dict: {slug: path}

    Raises:
        RuntimeError: on duplicate slug
        RipgrepError: on rg failure
    """

    pattern = r"^slug:\s*([a-z0-9._-]+)\s*$"
    slug_index: dict[str, Path] = {}
    slug_lines: dict[str, int] = {}

    for root in roots:
        for record in rg_search(
            pattern=pattern,
            root=root,
            extensions=["md", "markdown"],
        ):
            groups = record.get("groups")
            if not groups:
                continue

            slug = groups[0].strip()
            path = record["path"]
            line = int(record["line"])

            if slug in slug_index:
                existing = slug_index[slug]
                existing_line = slug_lines[slug]
                raise RuntimeError(
                    "Duplicate slug detected:\n"
                    f"  slug: {slug}\n"
                    f"  first: {existing}:{existing_line}\n"
                    f"  second: {path}:{line}"
                )

            slug_index[slug] = path
            slug_lines[slug] = line

    return slug_index
