"""Ripgrep-backed Studio query helpers."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any


class RipgrepError(RuntimeError):
    pass


_SLUG_LINE_PATTERN = re.compile(r"^slug:\s*(\S+)")


def build_slug_index(studio_root: Path) -> dict[str, Path]:
    root = Path(studio_root).expanduser().resolve()
    if not root.exists():
        raise RipgrepError(f"studio root does not exist: {root}")

    args = [
        "rg",
        "--json",
        "--pcre2",
        "--glob",
        "*.md",
        r"^slug:\s*(\S+)",
        str(root),
    ]

    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RipgrepError("ripgrep executable not found: rg") from exc
    except OSError as exc:
        raise RipgrepError(f"failed to run ripgrep: {exc}") from exc

    if proc.returncode not in {0, 1}:
        detail = proc.stderr.strip() or proc.stdout.strip() or "ripgrep failed"
        raise RipgrepError(detail)

    index: dict[str, Path] = {}
    for line in proc.stdout.splitlines():
        event = _parse_event(line)
        if event.get("type") != "match":
            continue

        data = event.get("data")
        if not isinstance(data, dict):
            continue

        slug = _extract_slug(data)
        if slug is None:
            continue

        matched_path = _extract_path(data)
        if matched_path is None:
            continue

        absolute_path = _resolve_match_path(root=root, matched_path=matched_path)
        if absolute_path.suffix.lower() != ".md":
            continue
        if slug in index:
            raise RipgrepError("duplicate slug detected")
        index[slug] = absolute_path

    return index


def _parse_event(line: str) -> dict[str, Any]:
    try:
        event = json.loads(line)
    except json.JSONDecodeError as exc:
        raise RipgrepError(f"invalid ripgrep JSON event: {exc}") from exc
    if not isinstance(event, dict):
        raise RipgrepError("invalid ripgrep JSON event: event must be an object")
    return event


def _extract_slug(data: dict[str, Any]) -> str | None:
    lines = data.get("lines")
    if not isinstance(lines, dict):
        return None
    text = lines.get("text")
    if not isinstance(text, str):
        return None
    match = _SLUG_LINE_PATTERN.search(text.strip())
    if match is None:
        return None
    return match.group(1).strip()


def _extract_path(data: dict[str, Any]) -> Path | None:
    path_data = data.get("path")
    if not isinstance(path_data, dict):
        return None
    path_text = path_data.get("text")
    if not isinstance(path_text, str) or not path_text.strip():
        return None
    return Path(path_text.strip())


def _resolve_match_path(*, root: Path, matched_path: Path) -> Path:
    if matched_path.is_absolute():
        return matched_path.resolve()
    return (root / matched_path).resolve()
