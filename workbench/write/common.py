"""Shared helpers for write command implementations."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from workbench.interop.identity import normalize_semantic_base
from workbench.lib.ndjson_stream import iter_ndjson


class WriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class WriteRecord:
    envelope: dict[str, Any]
    content: str
    batch_slug: str
    slug: str | None
    filename_hint: str | None
    provenance: dict[str, Any] | None
    origin: dict[str, Any] | None


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


def normalize_non_empty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise WriteError(f"{field} must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise WriteError(f"{field} must be a non-empty string")
    return normalized


def iter_input_records(stream: Iterable[str]) -> Iterator[WriteRecord]:
    try:
        for index, record in enumerate(iter_ndjson(stream), start=1):
            yield _coerce_record(record=record, index=index)
    except (ValueError, json.JSONDecodeError) as exc:
        raise WriteError(f"invalid NDJSON input: {exc}") from exc


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
        raise WriteError(f"path is not a directory: {target}")
    return target


def preferred_filename_stem(record: WriteRecord) -> str:
    hint = record.filename_hint
    if hint:
        return normalize_semantic_base(hint)
    return "unknown"


def resolve_unique_markdown_path(directory: Path, stem: str) -> Path:
    clean_stem = normalize_semantic_base(stem)
    candidate = directory / f"{clean_stem}.md"
    if not candidate.exists():
        return candidate

    suffix = 2
    while True:
        candidate = directory / f"{clean_stem}-{suffix}.md"
        if not candidate.exists():
            return candidate
        suffix += 1


def _coerce_record(*, record: dict[str, Any], index: int) -> WriteRecord:
    content = record.get("content")
    if not isinstance(content, str):
        raise WriteError(f"record {index}: missing required record field: content")

    batch_slug = normalize_non_empty_string(
        record.get("batch_slug"), field=f"record {index} batch_slug"
    )

    slug = _optional_string(record.get("slug"), index=index, field="slug")
    filename_hint = _optional_string(
        record.get("filename_hint"), index=index, field="filename_hint"
    )
    provenance = _optional_mapping(
        record.get("provenance"), index=index, field="provenance"
    )
    origin = _optional_mapping(record.get("origin"), index=index, field="origin")

    return WriteRecord(
        envelope=copy.deepcopy(record),
        content=content,
        batch_slug=batch_slug,
        slug=slug,
        filename_hint=filename_hint,
        provenance=provenance,
        origin=origin,
    )


def _optional_string(value: Any, *, index: int, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WriteError(f"record {index}: invalid record field: {field}")
    return value.strip()


def _optional_mapping(value: Any, *, index: int, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise WriteError(f"record {index}: invalid record field: {field}")
    return copy.deepcopy(value)
