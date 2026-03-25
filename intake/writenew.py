from __future__ import annotations

from pathlib import Path
from typing import Any


class WriteNewError(Exception):
    """Raised when a new record cannot be prepared for vault materialization."""


def _require_dict(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WriteNewError(f"Expected {field_name} to be a dict.")
    return value


def _require_nonempty_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WriteNewError(f"Expected {field_name} to be a non-empty string.")
    return value.strip()


def _resolve_vault_root(vault_root: str | Path) -> Path:
    root = Path(vault_root).expanduser().resolve()

    if not root.exists():
        raise WriteNewError(f"Vault root does not exist: {root}")

    if not root.is_dir():
        raise WriteNewError(f"Vault root is not a directory: {root}")

    return root


def _resolve_ingest_dir(vault_root: Path, ingest_dir_name: str) -> Path:
    ingest_dir = (vault_root / ingest_dir_name).resolve()

    if not ingest_dir.exists():
        raise WriteNewError(f"Ingest directory does not exist: {ingest_dir}")

    if not ingest_dir.is_dir():
        raise WriteNewError(f"Ingest path is not a directory: {ingest_dir}")

    return ingest_dir


def _slug_from_record(record: dict[str, Any]) -> str:
    input_record = _require_dict(record.get("input_record"), field_name="input_record")
    return _require_nonempty_string(input_record.get("slug"), field_name="input_record.slug")


def _filename_hint_from_record(record: dict[str, Any], *, slug: str) -> str:
    input_record = _require_dict(record.get("input_record"), field_name="input_record")
    hint = input_record.get("filename_hint")

    if hint is None:
        return slug

    return _require_nonempty_string(hint, field_name="input_record.filename_hint")


def _normalize_filename(filename_hint: str) -> str:
    candidate = Path(filename_hint).name.strip()

    if not candidate:
        raise WriteNewError("Filename hint resolves to an empty filename.")

    if candidate in {".", ".."}:
        raise WriteNewError(f"Invalid filename hint: {filename_hint}")

    if not candidate.endswith(".md"):
        candidate = f"{candidate}.md"

    return candidate


def _destination_for_record(
    record: dict[str, Any],
    *,
    vault_root: Path,
    ingest_dir_name: str,
) -> Path:
    slug = _slug_from_record(record)
    filename_hint = _filename_hint_from_record(record, slug=slug)
    filename = _normalize_filename(filename_hint)

    ingest_dir = _resolve_ingest_dir(vault_root, ingest_dir_name)
    destination = (ingest_dir / filename).resolve()

    if destination.parent != ingest_dir:
        raise WriteNewError(f"Destination escapes ingest directory: {destination}")

    if destination.exists():
        raise WriteNewError(f"Destination already exists: {destination}")

    return destination


def prepare_writenew_record(
    record: dict[str, Any],
    *,
    vault_root: str | Path,
    ingest_dir_name: str = "_ingest",
) -> dict[str, Any]:
    """
    Prepare a new-file render record.

    The returned dict is the original NDJSON object plus install metadata for the
    downstream pandoc/materializer chain. The document content and metadata remain
    otherwise untouched.

    Assumptions:
    - record["input_record"]["slug"] is required
    - record["input_record"]["filename_hint"] is optional; falls back to slug
    - new files are written only under <vault_root>/<ingest_dir_name>
    - parent directories must already exist
    - overwrites are forbidden
    """
    if not isinstance(record, dict):
        raise WriteNewError("Record must be a dict.")

    root = _resolve_vault_root(vault_root)
    destination = _destination_for_record(
        record,
        vault_root=root,
        ingest_dir_name=ingest_dir_name,
    )

    prepared = dict(record)
    prepared["materialize"] = {
        "mode": "writenew",
        "slug": _slug_from_record(record),
        "destination": str(destination),
    }
    return prepared