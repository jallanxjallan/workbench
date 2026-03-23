"""Normalization helpers for ripgrep inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import RipgrepError


def _normalize_extension(ext: str) -> str:
    cleaned = ext.strip()
    if not cleaned:
        raise ValueError("extensions cannot contain empty values")
    if cleaned.startswith("."):
        cleaned = cleaned[1:]
    return cleaned


def _normalize_exclude(directory: str) -> str:
    cleaned = directory.strip().strip("/")
    if not cleaned:
        raise ValueError("exclude_dirs cannot contain empty values")
    return cleaned


def _normalize_root(root: Path) -> Path:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise RipgrepError(f"search root does not exist: {root_path}")
    return root_path


def _normalize_candidate_files(
    files: Iterable[Path],
    *,
    extensions: tuple[str, ...],
    exclude_dirs: tuple[str, ...],
) -> list[Path]:
    normalized: list[Path] = []
    extension_suffixes = {f".{ext.lower()}" for ext in extensions}
    excluded = set(exclude_dirs)

    for path in files:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            raise RipgrepError(f"candidate file does not exist: {file_path}")
        if not file_path.is_file():
            raise RipgrepError(f"candidate path is not a file: {file_path}")
        if extension_suffixes and file_path.suffix.lower() not in extension_suffixes:
            continue
        if any(part in excluded for part in file_path.parts):
            continue
        normalized.append(file_path)
    return normalized
