"""Generic filesystem and stdin helpers."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        delete=False,
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


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


__all__ = ["atomic_write_text", "ensure_directory", "has_piped_stdin"]
