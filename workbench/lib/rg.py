"""Ripgrep-backed Studio query helpers."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any


class RipgrepError(RuntimeError):
    pass


def _ensure_pcre2_available() -> None:
    """
    Verify that ripgrep supports PCRE2.
    Studio scanning depends on PCRE2 features such as lookahead.
    """
    try:
        proc = subprocess.run(
            ["rg", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RipgrepError("ripgrep executable not found: rg") from exc
    except OSError as exc:
        raise RipgrepError(f"failed to run ripgrep: {exc}") from exc

    version_output = proc.stdout or ""
    if proc.returncode != 0 or "+pcre2" not in version_output:
        raise RipgrepError(
            "PCRE2 is not available in this build of ripgrep. "
            "Install a PCRE2-enabled ripgrep binary."
        )


_ensure_pcre2_available()


_SLUG_LINE_PATTERN = re.compile(r"^slug:\s*(\S+)", re.MULTILINE)
_SLUG_SEGMENT_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_CANONICAL_SLUG_VALUE_PATTERN = (
    rf"{_SLUG_SEGMENT_PATTERN}\.{_SLUG_SEGMENT_PATTERN}\.(?:{_SLUG_SEGMENT_PATTERN}\.)?{_SLUG_SEGMENT_PATTERN}"
)
_FRONTMATTER_SLUG_VALUE_PREFIX_PATTERN = (
    r"(?m)\A---\s*\n(?:(?!^---\s*$)[^\n]*\n)*^slug:\s*\K"
)
_MARKDOWN_FILE_SLUG_CANDIDATE_PATTERN = (
    r"(?m)\A---\s*\n(?:(?!^---\s*$)[^\n]*\n)*^slug:\s*(\S+)\s*$|\A"
)
IMAGE_PATTERN = r"!\[[^\]]*\]\((?![^)]*_thumb\.)[^)]+\)"
_IMAGE_PATTERN_ALL = r"!\[[^\]]*\]\([^)]+\)"
DEFAULT_STUDIO_ROOT = Path("~/Studio").expanduser().resolve()


def _normalize_root(root: Path | None) -> Path:
    return Path(root or DEFAULT_STUDIO_ROOT).expanduser().resolve()


def rg_search(
    pattern: str,
    *,
    root: Path | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    multiline: bool = False,
) -> list[dict[str, Any]]:
    root_path = _normalize_root(root)
    if not root_path.exists():
        raise RipgrepError(f"studio root does not exist: {root_path}")

    args = [
        "rg",
        "--json",
        "--pcre2",
    ]
    if multiline:
        args.append("--multiline")

    if include:
        for glob_pattern in include:
            args.extend(["--glob", glob_pattern])

    if exclude:
        for glob_pattern in exclude:
            args.extend(["--glob", f"!{glob_pattern}"])

    args.extend([pattern, str(root_path)])

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

    events: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        event = _parse_event(line)
        if event.get("type") == "match":
            events.append(event)

    return events


def build_slug_index(root: Path | None = None) -> dict[str, Path]:
    root_path = _normalize_root(root)
    rows = find_markdown_slugs(
        root=root_path,
        canonical_only=False,
        exclude_placeholders=True,
    )

    index: dict[str, Path] = {}
    for row in rows:
        slug = row["slug"]
        absolute_path = row["file"]
        if slug in index:
            raise RipgrepError("duplicate slug detected")
        index[slug] = absolute_path

    return index


def find_markdown_images(
    *,
    root: Path | None = None,
    exclude_thumbs: bool = True,
) -> list[dict[str, Any]]:
    root_path = _normalize_root(root)
    pattern = IMAGE_PATTERN if exclude_thumbs else _IMAGE_PATTERN_ALL
    events = rg_search(
        pattern,
        root=root_path,
        include=["*.md"],
    )

    results: list[dict[str, Any]] = []
    for event in events:
        data = event.get("data", {})
        if not isinstance(data, dict):
            continue

        lines = data.get("lines", {})
        text = lines.get("text", "") if isinstance(lines, dict) else ""

        file_path = _extract_path(data)
        if file_path is None:
            continue

        results.append(
            {
                "file": _resolve_match_path(
                    root=root_path,
                    matched_path=file_path,
                ),
                "line": text,
            }
        )

    return results


def find_markdown_slugs(
    *,
    root: Path | None = None,
    canonical_only: bool = False,
    exclude_placeholders: bool = True,
) -> list[dict[str, Any]]:
    root_path = _normalize_root(root)

    value_pattern = _CANONICAL_SLUG_VALUE_PATTERN if canonical_only else r"\S+"
    if exclude_placeholders:
        value_pattern = rf"(?!(?i:__slug__|null|~)\s*$){value_pattern}"

    pattern = rf"{_FRONTMATTER_SLUG_VALUE_PREFIX_PATTERN}{value_pattern}\s*$"
    events = rg_search(
        pattern,
        root=root_path,
        include=["*.md", "*.markdown"],
        multiline=True,
    )

    rows: list[dict[str, Any]] = []
    for event in events:
        data = event.get("data", {})
        if not isinstance(data, dict):
            continue

        slug = _extract_slug(data)
        if slug is None:
            continue

        file_path = _extract_path(data)
        if file_path is None:
            continue

        resolved = _resolve_match_path(root=root_path, matched_path=file_path)
        if resolved.suffix.lower() not in {".md", ".markdown"}:
            continue

        rows.append({"file": resolved, "slug": slug})

    return rows


def find_files_with_slug(slug: str, *, root: Path | None = None) -> list[Path]:
    root_path = _normalize_root(root)
    escaped = re.escape(slug.strip())
    pattern = rf"{_FRONTMATTER_SLUG_VALUE_PREFIX_PATTERN}{escaped}\s*$"
    events = rg_search(
        pattern,
        root=root_path,
        include=["*.md", "*.markdown"],
        multiline=True,
    )

    files: list[Path] = []
    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        file_path = _extract_path(data)
        if file_path is None:
            continue

        resolved = _resolve_match_path(root=root_path, matched_path=file_path)
        if resolved.suffix.lower() not in {".md", ".markdown"}:
            continue
        files.append(resolved)

    return sorted(set(files))


def find_markdown_slug_candidates(
    *,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    root_path = _normalize_root(root)
    events = rg_search(
        _MARKDOWN_FILE_SLUG_CANDIDATE_PATTERN,
        root=root_path,
        include=["*.md", "*.markdown"],
        multiline=True,
    )

    rows: list[dict[str, Any]] = []
    seen_files: set[Path] = set()
    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue

        file_path = _extract_path(data)
        if file_path is None:
            continue
        resolved = _resolve_match_path(root=root_path, matched_path=file_path)
        if resolved in seen_files:
            continue
        if resolved.suffix.lower() not in {".md", ".markdown"}:
            continue

        seen_files.add(resolved)
        rows.append({"file": resolved, "slug": _extract_slug(data)})

    return rows


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
