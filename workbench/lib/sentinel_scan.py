"""Sentinel-based file selection helpers for `wkb scan-sentinel`."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

from workbench.lib.ndjson_stream import iter_ndjson
from workbench.lib.paths import PathError, ensure_within

_BATCH_SENTINEL_LINE_RE = re.compile(
    r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$",
    re.IGNORECASE,
)
_RG_BATCH_SENTINEL_REGEX = r"(?im)\A\s*---\s*ASC\s+BATCH:\s*[a-z0-9._-]+\s*---\s*$"


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
    cmd = [
        "rg",
        "--json",
        "--pcre2",
        "--multiline",
        "--glob",
        "*.md",
        _RG_BATCH_SENTINEL_REGEX,
        "--",
        *query_paths,
    ]
    if follow_symlinks:
        cmd.insert(1, "--follow")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SentinelScanError("rg command not found") from exc

    if proc.returncode not in (0, 1):
        raise SentinelScanError(proc.stderr.strip() or "rg scan failed")

    rows: list[str] = []
    try:
        for input_record in iter_ndjson(proc.stdout):
            if input_record.get("type") != "match":
                continue

            data = input_record.get("data")
            if not isinstance(data, dict):
                continue

            path_data = data.get("path")
            if not isinstance(path_data, dict):
                continue
            path_text = path_data.get("text")
            if not isinstance(path_text, str) or not path_text:
                continue

            rows.append(_normalize_match_path(path_text))
    except ValueError as exc:
        raise SentinelScanError("invalid rg output") from exc

    return rows


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
