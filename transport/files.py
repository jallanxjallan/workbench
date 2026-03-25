from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TextIO


def read_text(path: Path, encoding: str = "utf-8") -> str:
    return path.read_text(encoding=encoding)


def write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.write_text(content, encoding=encoding)


def emit_paths(paths: Iterable[Path], stream: TextIO) -> None:
    for path in paths:
        stream.write(f"{path}\n")


def read_paths(stream: TextIO) -> list[Path]:
    paths: list[Path] = []
    for line in stream:
        stripped = line.strip()
        if not stripped:
            continue
        paths.append(Path(stripped))
    return paths


def ensure_regular_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {path}")
