"""Shared helpers for write command implementations."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workbench.emit.record_to_document import record_to_document
from workbench.lib.sentinel import insert_batch_sentinel
from workbench.lib.ndjson import StreamError, parse_ndjson
from workbench.lib.subprocess import CommandError, run_text

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


class WriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class WriteRecord:
    metadata: dict[str, Any]
    content: str
    input_record: dict[str, Any] | None


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


def normalize_batch_slug(value: str) -> str:
    """Normalize batch identifiers."""
    normalized = str(value).strip()
    if not normalized:
        raise WriteError("batch slug must be a non-empty string")
    return normalized


def fetch_batch_records(batch_slug: str, *, asc_bin: str = "asc") -> list[WriteRecord]:
    slug = normalize_batch_slug(batch_slug)
    try:
        text = run_text([asc_bin, "emit", slug], check=True)
    except CommandError as exc:
        raise WriteError(f"failed to fetch records for batch '{slug}': {exc}") from exc

    try:
        raw_records = list(parse_ndjson(text.splitlines()))
    except StreamError as exc:
        raise WriteError(f"invalid NDJSON emitted for batch '{slug}': {exc}") from exc

    output: list[WriteRecord] = []
    for index, record in enumerate(raw_records, start=1):
        output.append(_coerce_record(record=record, index=index))
    return output


def _coerce_record(*, record: dict[str, Any], index: int) -> WriteRecord:
    content = record.get("content")
    if not isinstance(content, str):
        raise WriteError(f"record {index} missing string 'content' field")

    metadata: dict[str, Any] = {}
    from_metadata = record.get("metadata")
    if isinstance(from_metadata, dict):
        metadata.update(from_metadata)

    input_record_raw = record.get("input_record")
    input_record: dict[str, Any] | None = None
    if isinstance(input_record_raw, dict):
        input_record = dict(input_record_raw)
        for key, value in input_record.items():
            metadata.setdefault(str(key), value)

    for key in (
        "target_path",
        "target_dir",
        "source_path",
        "filepath",
        "path",
        "title",
        "slug",
    ):
        if key in record:
            metadata.setdefault(key, record[key])

    return WriteRecord(
        metadata=metadata,
        content=content,
        input_record=input_record,
    )


def resolve_writenew_target_path(
    *,
    metadata: dict[str, Any],
    record_index: int,
) -> Path:
    target_dir = _first_string(metadata, "target_dir")
    if target_dir is None:
        raise WriteError(
            f"record {record_index} missing target_dir; writenew requires explicit target directory (legacy routing removed)"
        )

    directory = Path(target_dir).expanduser()
    if not directory.is_absolute():
        raise WriteError(
            f"record {record_index} target_dir must be an absolute path: {target_dir!r}"
        )

    filename = _derive_filename(metadata=metadata, record_index=record_index)
    return directory.resolve() / filename


def resolve_writeback_target_path(
    *,
    record: WriteRecord,
    record_index: int,
) -> Path:
    if not isinstance(record.input_record, dict):
        raise WriteError(
            f"record {record_index} missing input_record['path']; writeback requires explicit absolute path"
        )
    path_value = record.input_record.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise WriteError(
            f"record {record_index} missing input_record['path']; writeback requires explicit absolute path"
        )
    normalized = path_value.strip()

    target_path = Path(normalized).expanduser()
    if not target_path.is_absolute():
        raise WriteError(
            f"record {record_index} path must be an absolute path: {normalized!r}"
        )
    return target_path.resolve()


def resolve_writeback_new_target_path(
    *,
    record: WriteRecord,
    record_index: int,
    existing_path: Path,
) -> Path:
    target_dir = _first_string(record.metadata, "target_dir")
    if target_dir is not None:
        directory = Path(target_dir).expanduser()
        if not directory.is_absolute():
            raise WriteError(
                f"record {record_index} target_dir must be an absolute path: {target_dir!r}"
            )
        root = directory.resolve()
    else:
        root = existing_path.parent.resolve()

    filename = _derive_filename(metadata=record.metadata, record_index=record_index)
    candidate = root / filename
    if candidate.resolve() == existing_path.resolve():
        candidate = candidate.with_name(f"{candidate.stem}--new{candidate.suffix}")
    return candidate


def resolve_record_slug(record: WriteRecord, *, record_index: int) -> str:
    if isinstance(record.input_record, dict):
        raw = record.input_record.get("slug")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

    fallback = record.metadata.get("slug")
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()

    raise WriteError(f"record {record_index} missing input_record['slug']")


def serialize_record(record: WriteRecord, *, batch_slug: str) -> str:
    metadata_source: dict[str, Any]
    if isinstance(record.input_record, dict):
        metadata_source = dict(record.input_record)
    else:
        metadata_source = dict(record.metadata)

    payload: dict[str, Any] = {
        "content": record.content,
        "input_record": metadata_source,
    }
    document = record_to_document(payload)
    return insert_batch_sentinel(document.write_text(), normalize_batch_slug(batch_slug))


def _first_string(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _derive_filename(*, metadata: dict[str, Any], record_index: int) -> str:
    explicit = _first_string(metadata, "slug")
    if explicit:
        return f"{_slugify(explicit)}.md"

    title = _first_string(metadata, "title")
    if title:
        return f"{_slugify(title)}.md"

    return f"record-{record_index:03d}.md"


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = _NON_ALNUM_RE.sub("-", normalized)
    normalized = normalized.strip("-")
    return normalized or "document"
