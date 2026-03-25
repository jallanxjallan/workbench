from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


class MaterializeError(Exception):
    """Raised when a rendered tmp artifact cannot be materialized safely."""


def read_ndjson_records(stream: str) -> list[dict[str, Any]]:
    """
    Parse an NDJSON string into a list of dict records.

    Blank lines are ignored.
    """
    records: list[dict[str, Any]] = []

    for line_number, line in enumerate(stream.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise MaterializeError(
                f"Invalid NDJSON at line {line_number}: {exc.msg}"
            ) from exc

        if not isinstance(record, dict):
            raise MaterializeError(
                f"NDJSON line {line_number} must decode to an object."
            )

        records.append(record)

    return records


def _required_str(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MaterializeError(f"Record is missing required string field: {key}")
    return value


def _resolve_existing_tmp(tmp_path: str | Path) -> Path:
    path = Path(tmp_path).expanduser().resolve()

    if not path.exists():
        raise MaterializeError(f"Tmp markdown file does not exist: {path}")

    if not path.is_file():
        raise MaterializeError(f"Tmp markdown path is not a file: {path}")

    return path


def _resolve_destination(destination: str | Path) -> Path:
    path = Path(destination).expanduser().resolve()

    parent = path.parent
    if not parent.exists():
        raise MaterializeError(f"Destination parent does not exist: {parent}")

    if not parent.is_dir():
        raise MaterializeError(f"Destination parent is not a directory: {parent}")

    if path.exists():
        raise MaterializeError(f"Destination already exists: {path}")

    return path


def materialize_record(record: dict[str, Any]) -> Path:
    """
    Materialize one rendered tmp markdown file into its final destination.

    Required record fields:
    - tmp_path
    - destination

    Optional fields like mode or slug are ignored here except for diagnostics.
    """
    tmp_path = _resolve_existing_tmp(_required_str(record, "tmp_path"))
    destination = _resolve_destination(_required_str(record, "destination"))

    try:
        return Path(shutil.move(str(tmp_path), str(destination))).resolve()
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise MaterializeError(
            f"Failed to move tmp file {tmp_path} to {destination}"
        ) from exc


def materialize_ndjson(stream: str) -> list[Path]:
    """
    Materialize every record from an NDJSON string.

    Returns a list of final destination paths in input order.
    """
    records = read_ndjson_records(stream)
    written_paths: list[Path] = []

    for record in records:
        written_paths.append(materialize_record(record))

    return written_paths