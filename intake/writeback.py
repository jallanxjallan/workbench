from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any, TextIO

import repo
from scan import resolve_slug_to_filepath
from transport import read_all_records, write_records
from vault.validate import require_vault_root


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


def _resolve_vault_root(vault_root: str | Path | None) -> Path:
    origin = Path.cwd() if vault_root is None else Path(vault_root)
    return require_vault_root(origin)


def prepare_writeback_record(
    record: dict[str, Any],
    *,
    vault_root: str | Path | None = None,
) -> dict[str, Any]:
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

    root = _resolve_vault_root(vault_root)
    slug = _slug_from_record(record)
    destination = _resolve_existing_file(resolve_slug_to_filepath(slug, root))

    if repo.is_file_dirty(root, destination):
        raise WriteBackError(f"Writeback target is dirty: {destination}")

    prepared = dict(record)
    prepared["materialize"] = {
        "mode": "writeback",
        "slug": slug,
        "destination": str(destination),
    }
    return prepared


def prepare_writeback_records(
    records: list[dict[str, Any]],
    *,
    vault_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Prepare multiple NDJSON records for writeback.

    Git cleanliness is checked separately for every record.
    """
    prepared: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        try:
            prepared.append(
                prepare_writeback_record(
                    record,
                    vault_root=vault_root,
                )
            )
        except WriteBackError as exc:
            raise WriteBackError(f"Record {index}: {exc}") from exc

    return prepared


def read_ndjson(stream: str) -> list[dict[str, Any]]:
    """
    Parse an NDJSON string into a list of dict records.

    Blank lines are ignored.
    """
    try:
        return read_all_records(StringIO(stream))
    except ValueError as exc:
        raise WriteBackError(str(exc)) from exc


def write_ndjson(records: list[dict[str, Any]]) -> str:
    """
    Serialize prepared records back to NDJSON.
    """
    output = StringIO()
    write_records(output, records)
    return output.getvalue()


def prepare_writeback_ndjson(
    stream: str,
    *,
    vault_root: str | Path | None = None,
) -> str:
    """
    Read NDJSON, prepare every record for writeback, and emit NDJSON.

    This is the main module-level entry point for a future CLI wrapper.
    """
    records = read_ndjson(stream)
    prepared = prepare_writeback_records(records, vault_root=vault_root)
    return write_ndjson(prepared)


def prepare_writeback_stream(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    vault_root: str | Path | None = None,
) -> None:
    output_stream.write(
        prepare_writeback_ndjson(
            input_stream.read(),
            vault_root=vault_root,
        )
    )
