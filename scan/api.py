"""Public ripgrep search API."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .command import rg_build_command
from .config import DEFAULT_EXCLUDE_DIRS, DEFAULT_EXTENSIONS
from .normalize import (
    _normalize_candidate_files,
    _normalize_exclude,
    _normalize_extension,
    _normalize_root,
)
from .runtime import _iter_rg_records


def rg_search(
    *,
    pattern: str,
    root: Path | None = None,
    files: Iterable[Path] | None = None,
    extensions: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> list[dict[str, object]]:
    """
    Search with ripgrep and return normalized match records.

    Exactly one of ``root`` or ``files`` must be provided.
    """

    if (root is None) == (files is None):
        raise ValueError("exactly one of root or files must be provided")

    normalized_exts = tuple(
        _normalize_extension(ext)
        for ext in (DEFAULT_EXTENSIONS if extensions is None else extensions)
    )
    normalized_excludes = tuple(
        _normalize_exclude(directory)
        for directory in (
            DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs
        )
    )

    if root is not None:
        cmd = rg_build_command(
            pattern=pattern,
            root=_normalize_root(root),
            extensions=list(normalized_exts),
            exclude_dirs=list(normalized_excludes),
        )
        return list(_iter_rg_records(cmd=cmd, pattern=pattern))

    assert files is not None
    candidates = _normalize_candidate_files(
        files,
        extensions=normalized_exts,
        exclude_dirs=normalized_excludes,
    )
    if not candidates:
        return []

    cmd = rg_build_command(
        pattern=pattern,
        files=candidates,
        extensions=[],
        exclude_dirs=[],
    )
    return list(_iter_rg_records(cmd=cmd, pattern=pattern))
