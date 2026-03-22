"""Generic filesystem and stdin helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def overwrite_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as handle:
        handle.write(content)


def write_new_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding=encoding, newline="") as handle:
        handle.write(content)


def has_piped_stdin(stream: Any) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return True
    try:
        return not bool(isatty())
    except OSError:
        return True


def ensure_directory(path_value: str) -> Path:
    target = Path(path_value).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise RuntimeError(f"path is not a directory: {target}")
    return target


__all__ = ["ensure_directory", "has_piped_stdin", "overwrite_text", "write_new_text"]
