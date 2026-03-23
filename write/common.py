"""Shared helpers for write execution modules."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Iterator
import unicodedata

from records.files import ensure_directory
from records.records import RecordContractError, iter_records
from vault.discover import VaultRuntimeError, discover_registered_vault_root


INGEST_DIRNAME = "_ingest"

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MULTI_DASH_RE = re.compile(r"-{2,}")
_MAX_SEMANTIC_BASE_LENGTH = 48


class WriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class WriteInputRecord:
    envelope: dict[str, Any]
    slug: str | None
    filename_hint: str | None


@dataclass(frozen=True)
class WriteRecord:
    content: str
    input_record: WriteInputRecord


def iter_input_records(stream: Iterable[str]) -> Iterator[WriteRecord]:
    try:
        for index, record in enumerate(iter_records(stream), start=1):
            yield _coerce_record(record=record, index=index)
    except RecordContractError as exc:
        raise WriteError(str(exc)) from exc


def preferred_filename_stem(record: WriteRecord) -> str:
    hint = record.input_record.filename_hint
    if hint:
        return normalize_semantic_base(hint)
    return "doc"


def normalize_semantic_base(filename: str) -> str:
    base_name = os.path.basename(str(filename))
    stem, _ = os.path.splitext(base_name)
    normalized = unicodedata.normalize("NFKD", stem)
    no_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = no_diacritics.lower()
    dashed = _NON_ALNUM_RE.sub("-", lowered)
    collapsed = _MULTI_DASH_RE.sub("-", dashed).strip("-")
    clipped = collapsed[:_MAX_SEMANTIC_BASE_LENGTH].strip("-")
    return clipped or "doc"


def normalize_markdown_filename(filename: str) -> str:
    return f"{normalize_semantic_base(filename)}.md"


def resolve_writenew_directory(
    *,
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
) -> Path:
    if target_dir is not None:
        return ensure_directory(str(target_dir))

    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    try:
        vault_root = discover_registered_vault_root(working_dir)
    except VaultRuntimeError as exc:
        raise WriteError(str(exc)) from exc
    return ensure_directory(str(vault_root / INGEST_DIRNAME))


def derive_new_path(record: WriteRecord, directory: Path) -> Path:
    return directory / normalize_markdown_filename(preferred_filename_stem(record))


def _coerce_record(*, record: dict[str, Any], index: int) -> WriteRecord:
    content = record["content"]
    input_record = record["input_record"]
    metadata = input_record.get("metadata")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise WriteError(f"record {index}: invalid record field: input_record.metadata")

    slug = _optional_string(
        metadata.get("slug"),
        index=index,
        field="input_record.metadata.slug",
    )
    filename_hint = _optional_string(
        input_record.get("filename_hint"),
        index=index,
        field="input_record.filename_hint",
    )

    return WriteRecord(
        content=content,
        input_record=WriteInputRecord(
            envelope=copy.deepcopy(input_record),
            slug=slug,
            filename_hint=filename_hint,
        ),
    )


def _optional_string(value: Any, *, index: int, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WriteError(f"record {index}: invalid record field: {field}")
    return value.strip()
