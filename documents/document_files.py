"""Text file and stdin helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def read_text(path: Path, encoding: str = "utf-8") -> str:
    return path.read_text(encoding=encoding)


def overwrite_text(path: Path, content: str, encoding: str = "utf-8") -> str:
    with path.open("w", encoding=encoding) as handle:
        handle.write(content)
    return content


def write_text(path: Path, content: str, encoding: str = "utf-8") -> str:
    with path.open("x", encoding=encoding) as handle:
        handle.write(content)
    return content


def require_directory(path: str | Path) -> Path:
    directory = Path(path).expanduser()
    if not directory.is_dir():
        raise RuntimeError(f"path is not a directory: {directory}")
    return directory


def has_piped_stdin(stream: Any) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return True
    try:
        return not isatty()
    except OSError:
        return True


__all__ = [
    "has_piped_stdin",
    "overwrite_text",
    "read_text",
    "require_directory",
    "write_text",
]