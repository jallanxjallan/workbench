from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Placeholder imports for Codex to reconcile against the real tree.
from repo import file_is_dirty
from resolve import resolve_slug_to_filepath


class WriteBackError(Exception):
    """Raised when a writeback record cannot be prepared safely."""


def _require_dict(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WriteBackError(f"Expected {field_name} to be a dict.")
    return value


def _require_nonempty_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WriteBackError(f"Expected {field_name} to be a non-empty string.")
    return value.strip()


def _slug_from_record(record: dict[str, Any]) -> str:
    input_record = _require_dict(record.get("input_record"), field_name="input_record")
    return _require_nonempty_string(
        input_record.get("slug"),
        field_name="input_record.slug",
    )


def _resolve_existing_file(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser().resolve()

    if not path.exists():
        raise WriteBackError(f"Writeback target does not exist: {path}")

    if not path.is_file():
        raise WriteBackError(f"Writeback target is not a file: {path}")

    return path


def prepare_writeback_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Prepare one NDJSON record for writeback.

    The returned object is the original record plus a `materialize` block
    describing where the downstream renderer/materializer must install the
    rendered markdown artifact.

    Guardrails:
    - input_record.slug must exist
    - slug must resolve to an existing file
    - target file must be clean in git
    """
    if not isinstance(record, dict):
        raise WriteBackError("Record must be a dict.")

    slug = _slug_from_record(record)
    destination = _resolve_existing_file(resolve_slug_to_filepath(slug))

    if file_is_dirty(destination):
        raise WriteBackError(f"Writeback target is dirty: {destination}")

    prepared = dict(record)
    prepared["materialize"] = {
        "mode": "writeback",
        "slug": slug,
        "destination": str(destination),
    }
    return prepared


def prepare_writeback_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Prepare multiple NDJSON records for writeback.

    Git cleanliness is checked separately for every record.
    """
    prepared: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        try:
            prepared.append(prepare_writeback_record(record))
        except WriteBackError as exc:
            raise WriteBackError(f"Record {index}: {exc}") from exc

    return prepared


def read_ndjson(stream: str) -> list[dict[str, Any]]:
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
            raise WriteBackError(
                f"Invalid NDJSON at line {line_number}: {exc.msg}"
            ) from exc

        if not isinstance(record, dict):
            raise WriteBackError(
                f"NDJSON line {line_number} must decode to an object."
            )

        records.append(record)

    return records


def write_ndjson(records: list[dict[str, Any]]) -> str:
    """
    Serialize prepared records back to NDJSON.
    """
    return "\n".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        for record in records
    )


def prepare_writeback_ndjson(stream: str) -> str:
    """
    Read NDJSON, prepare every record for writeback, and emit NDJSON.

    This is the main module-level entry point for a future CLI wrapper.
    """
    records = read_ndjson(stream)
    prepared = prepare_writeback_records(records)
    return write_ndjson(prepared)