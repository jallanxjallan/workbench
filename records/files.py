"""Generic filesystem and stdin helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def read_text(path: Path, encoding: str = "utf-8") -> str:
    file_path = Path(path).expanduser().resolve()
    return file_path.read_text(encoding=encoding)


def overwrite_text(path: Path, content: str, encoding: str = "utf-8") -> str:
    file_path = Path(path).expanduser().resolve()
    with file_path.open("w", encoding=encoding, newline="") as handle:
        handle.write(content)
    return content


def write_new_text(path: Path, content: str, encoding: str = "utf-8") -> str:
    file_path = Path(path).expanduser().resolve()
    with file_path.open("x", encoding=encoding, newline="") as handle:
        handle.write(content)
    return content


def require_directory(path_value: str | Path) -> Path:
    target = Path(path_value).expanduser().resolve()
    if not target.is_dir():
        raise RuntimeError(f"path is not a directory: {target}")
    return target


def has_piped_stdin(stream: Any) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return True
    try:
        return not bool(isatty())
    except OSError:
        return True


__all__ = [
    "has_piped_stdin",
    "overwrite_text",
    "read_text",
    "require_directory",
    "write_new_text",
]