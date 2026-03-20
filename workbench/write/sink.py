"""Unified NDJSON write sink with writeback and writenew modes."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Iterable

from workbench.io.files import atomic_write_text
from workbench.write.common import (
    WriteError,
    derive_new_path,
    iter_input_records,
    resolve_existing_path,
    resolve_writenew_directory,
)


class WriteMode(StrEnum):
    WRITEBACK = "writeback"
    WRITENEW = "writenew"


def write_records(
    *,
    input_stream: Iterable[str],
    mode: WriteMode | str,
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
) -> list[Path]:
    selected_mode = WriteMode(mode)
    new_directory = (
        resolve_writenew_directory(cwd=cwd, target_dir=target_dir)
        if selected_mode is WriteMode.WRITENEW
        else None
    )

    written_paths: list[Path] = []
    for index, record in enumerate(iter_input_records(input_stream), start=1):
        if selected_mode is WriteMode.WRITEBACK:
            path = resolve_existing_path(record)
        else:
            assert new_directory is not None
            path = derive_new_path(record, new_directory)
            if path.exists():
                raise WriteError(f"record {index}: file exists: {path}")

        atomic_write_text(path, record.content)
        written_paths.append(path)

    return written_paths


def writeback(
    *,
    input_stream: Iterable[str],
) -> list[Path]:
    return write_records(input_stream=input_stream, mode=WriteMode.WRITEBACK)


def writenew(
    *,
    input_stream: Iterable[str],
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
) -> list[Path]:
    return write_records(
        input_stream=input_stream,
        mode=WriteMode.WRITENEW,
        cwd=cwd,
        target_dir=target_dir,
    )


__all__ = ["WriteMode", "write_records", "writeback", "writenew"]
