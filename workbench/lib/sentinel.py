"""Batch sentinel helpers for pipeline-level metadata markers."""

from __future__ import annotations

import re
from pathlib import Path

BATCH_SENTINEL_PATTERN = re.compile(r"^--- ASC BATCH: ([a-z0-9._-]+) ---$")


def _first_non_empty_line(lines: list[str]) -> tuple[int, str] | None:
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            return index, stripped
    return None


def read_batch_sentinel(path: Path | str) -> str | None:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            found = BATCH_SENTINEL_PATTERN.fullmatch(stripped)
            if not found:
                return None
            return found.group(1)
    return None


def strip_batch_sentinel(text: str) -> str:
    lines = text.splitlines(keepends=True)
    first = _first_non_empty_line(lines)
    if first is None:
        return text

    line_index, stripped = first
    if BATCH_SENTINEL_PATTERN.fullmatch(stripped) is None:
        return text

    return "".join(lines[:line_index] + lines[line_index + 1 :])


def insert_batch_sentinel(text: str, slug: str) -> str:
    raw_slug = str(slug).strip()
    if BATCH_SENTINEL_PATTERN.fullmatch(f"--- ASC BATCH: {raw_slug} ---") is None:
        raise ValueError(f"invalid batch slug for sentinel: {slug!r}")

    stripped = strip_batch_sentinel(text)
    sentinel_line = f"--- ASC BATCH: {raw_slug} ---"
    return f"{sentinel_line}\n{stripped}"


__all__ = [
    "BATCH_SENTINEL_PATTERN",
    "insert_batch_sentinel",
    "read_batch_sentinel",
    "strip_batch_sentinel",
]
