"""Shared helpers for write command implementations."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from workbench.interop.document import Document
from workbench.lib.ndjson_stream import iter_ndjson
from workbench.lib.sentinel import insert_batch_sentinel
from workbench.lib.subprocess import CommandError, iter_stdout_lines


class WriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class WriteRecord:
    envelope: dict[str, Any]
    content: str
    origin: dict[str, Any]
    batch_slug: str


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


def normalize_batch_slug(value: Any, *, field: str = "batch slug") -> str:
    """Normalize batch identifiers."""
    if not isinstance(value, str):
        raise WriteError(f"{field} must be a non-empty string")

    normalized = value.strip()
    if not normalized:
        raise WriteError(f"{field} must be a non-empty string")
    return normalized


def fetch_batch_records(batch_slug: str, *, asc_bin: str = "asc") -> Iterator[WriteRecord]:
    requested_batch_slug = normalize_batch_slug(batch_slug)
    try:
        for index, record in enumerate(
            iter_ndjson(iter_stdout_lines([asc_bin, "emit", requested_batch_slug], check=True)),
            start=1,
        ):
            yield _coerce_record(record=record, index=index)
    except CommandError as exc:
        raise WriteError(
            f"failed to fetch records for batch '{requested_batch_slug}': {exc}"
        ) from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise WriteError(
            f"invalid NDJSON emitted for batch '{requested_batch_slug}': {exc}"
        ) from exc


def _coerce_record(*, record: dict[str, Any], index: int) -> WriteRecord:
    content = record.get("content")
    if not isinstance(content, str):
        raise WriteError(
            f"record {index}: missing required record field: content"
        )

    origin_raw = record.get("origin")
    if not isinstance(origin_raw, dict):
        raise WriteError(
            f"record {index}: missing required record field: origin"
        )

    batch_slug_raw = record.get("batch_slug")
    if not isinstance(batch_slug_raw, str) or not batch_slug_raw.strip():
        raise WriteError(
            f"record {index}: missing required record field: batch_slug"
        )

    batch_slug = normalize_batch_slug(batch_slug_raw, field="record batch_slug")

    return WriteRecord(
        envelope=copy.deepcopy(record),
        content=content,
        origin=copy.deepcopy(origin_raw),
        batch_slug=batch_slug,
    )


def resolve_writenew_target_path(*, record: WriteRecord, record_index: int) -> Path:
    return _resolve_origin_path(record=record, record_index=record_index)


def resolve_writeback_target_path(*, record: WriteRecord, record_index: int) -> Path:
    return _resolve_origin_path(record=record, record_index=record_index)


def resolve_origin_slug(*, record: WriteRecord, record_index: int) -> str | None:
    value = record.origin.get("slug")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WriteError(
            f"record {record_index}: invalid record field: origin.slug must be a non-empty string"
        )
    return value.strip()


def validate_record_batch_slug(
    *,
    record: WriteRecord,
    requested_batch_slug: str,
    record_index: int,
) -> None:
    if record.batch_slug != requested_batch_slug:
        raise WriteError(
            f"record {record_index}: record batch_slug does not match requested batch slug"
        )


def serialize_record(record: WriteRecord) -> str:
    document = Document(
        metadata={"autoscribe": copy.deepcopy(record.envelope)},
        content=record.content,
    )
    return insert_batch_sentinel(document.write_text(), record.batch_slug)


def _resolve_origin_path(*, record: WriteRecord, record_index: int) -> Path:
    path_value = record.origin.get("path")
    if path_value is None:
        raise WriteError(
            f"record {record_index}: missing required record field: origin.path"
        )

    if not isinstance(path_value, str) or not path_value.strip():
        raise WriteError(
            f"record {record_index}: invalid record field: origin.path must be a non-empty string"
        )

    target_path = Path(path_value.strip()).expanduser()
    if not target_path.is_absolute():
        raise WriteError(
            f"record {record_index}: origin.path must be an absolute path: {path_value!r}"
        )
    return target_path.resolve()
