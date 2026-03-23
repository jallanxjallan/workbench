"""Ripgrep command construction."""

from __future__ import annotations

from pathlib import Path

from .config import (
    CONTEXT_AFTER,
    CONTEXT_BEFORE,
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXTENSIONS,
)
from .normalize import _normalize_exclude, _normalize_extension, _normalize_root


def rg_build_command(
    *,
    pattern: str,
    root: Path | None = None,
    files_from: Path | None = None,
    files: list[Path] | None = None,
    extensions: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> list[str]:
    """
    Build a safe ripgrep command using argument lists.

    Exactly one of ``root``, ``files_from``, or ``files`` must be provided.
    """

    selectors = [root is not None, files_from is not None, files is not None]
    if sum(selectors) != 1:
        raise ValueError("exactly one of root, files_from, or files must be provided")

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

    command = [
        "rg",
        "--json",
        "--line-number",
        "--before-context",
        str(CONTEXT_BEFORE),
        "--after-context",
        str(CONTEXT_AFTER),
    ]

    for ext in normalized_exts:
        command.extend(["--glob", f"*.{ext}"])
    for directory in normalized_excludes:
        command.extend(["--glob", f"!**/{directory}/**"])

    if files_from is not None:
        command.extend(["--files-from", str(Path(files_from).expanduser().resolve())])

    command.append(pattern)

    if root is not None:
        command.append(str(_normalize_root(root)))
    if files is not None:
        command.extend(str(Path(file_path).expanduser().resolve()) for file_path in files)

    return command
