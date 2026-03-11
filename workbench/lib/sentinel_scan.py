"""Sentinel-based file selection helpers for `wkb scan-sentinel`."""

from __future__ import annotations

import os
from pathlib import Path
import re

from workbench.lib.paths import PathError, ensure_within
from workbench.lib.rg import RipgrepError, rg_search

_BATCH_SENTINEL_LINE_RE = re.compile(
    r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$",
    re.IGNORECASE,
)
_RG_BATCH_SENTINEL_LINE_REGEX = r"^---\s*ASC\s+BATCH:\s*[a-z0-9._-]+\s*---\s*$"
_MARKDOWN_SUFFIXES = {".md", ".markdown"}


def is_valid_batch_slug(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())


class SentinelScanError(RuntimeError):
    pass


def scan_paths_for_batch_sentinel(
    *,
    root: Path,
    raw_paths: list[str],
    follow_symlinks: bool = False,
) -> list[str]:
    query_paths = _normalize_query_paths(root=root, raw_paths=raw_paths)
    rows = _scan_with_rg(
        root=root,
        query_paths=query_paths,
        follow_symlinks=follow_symlinks,
    )
    return sorted(set(rows))


def _normalize_query_paths(*, root: Path, raw_paths: list[str]) -> list[str]:
    query = raw_paths if raw_paths else ["."]
    normalized: list[str] = []

    for raw in query:
        if not isinstance(raw, str) or not raw.strip():
            raise SentinelScanError("path must be a non-empty string")

        candidate = Path(raw.strip()).expanduser()
        path = candidate if candidate.is_absolute() else (root / candidate)
        path = path.absolute()
        try:
            ensure_within(root, path, raw=raw)
        except PathError as exc:
            raise SentinelScanError(f"path is outside studio root: {raw}") from exc

        if not path.exists():
            raise SentinelScanError(f"path does not exist: {raw}")

        rel = path.relative_to(root)
        normalized.append(str(rel) if str(rel) else ".")

    return sorted(set(normalized)) if normalized else ["."]


def _scan_with_rg(
    *,
    root: Path,
    query_paths: list[str],
    follow_symlinks: bool,
) -> list[str]:
    try:
        files = _collect_markdown_files(
            root=root,
            query_paths=query_paths,
            follow_symlinks=follow_symlinks,
        )
    except OSError as exc:
        raise SentinelScanError(str(exc)) from exc

    rows: list[str] = []
    try:
        matches = rg_search(
            pattern=_RG_BATCH_SENTINEL_LINE_REGEX,
            files=files,
            extensions=["md", "markdown"],
            exclude_dirs=[],
        )
        for record in matches:
            line_number = record.get("line")
            if not isinstance(line_number, int) or line_number != 1:
                continue

            line_text = record.get("text")
            if not isinstance(line_text, str):
                continue
            if extract_batch_slug_from_first_line(line_text) is None:
                continue

            path_value = record.get("path")
            if not isinstance(path_value, Path):
                continue
            rows.append(_to_relative_posix(root=root, matched_path=path_value))
    except RipgrepError as exc:
        raise SentinelScanError(str(exc)) from exc

    return rows


def _collect_markdown_files(
    *,
    root: Path,
    query_paths: list[str],
    follow_symlinks: bool,
) -> list[Path]:
    root_path = root.expanduser().resolve()
    discovered: set[Path] = set()

    for raw in query_paths:
        candidate = (root_path / raw).resolve() if raw != "." else root_path
        if candidate.is_file():
            if candidate.suffix.lower() in _MARKDOWN_SUFFIXES:
                discovered.add(candidate)
            continue
        if not candidate.is_dir():
            continue

        for dirpath, dirnames, filenames in os.walk(
            candidate,
            followlinks=follow_symlinks,
        ):
            if not follow_symlinks:
                dirnames[:] = [
                    name
                    for name in dirnames
                    if not (Path(dirpath) / name).is_symlink()
                ]
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if file_path.suffix.lower() in _MARKDOWN_SUFFIXES:
                    discovered.add(file_path.resolve())

    return sorted(discovered)


def _to_relative_posix(*, root: Path, matched_path: Path) -> str:
    normalized = _normalize_match_path(matched_path.as_posix())
    normalized_path = Path(normalized)
    root_path = root.expanduser().resolve()
    if normalized_path.is_absolute():
        try:
            return normalized_path.relative_to(root_path).as_posix()
        except ValueError:
            return normalized_path.as_posix()
    return normalized


def _normalize_match_path(path_text: str) -> str:
    normalized = path_text.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def extract_batch_slug_from_first_line(first_line: str) -> str | None:
    found = _BATCH_SENTINEL_LINE_RE.match(first_line)
    if not found:
        return None

    slug = found.group("slug").strip("\"' ")
    if not is_valid_batch_slug(slug):
        return None

    return slug


__all__ = [
    "SentinelScanError",
    "scan_paths_for_batch_sentinel",
    "extract_batch_slug_from_first_line",
    "is_valid_batch_slug",
]
