"""Shared helpers for write sink implementations."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Iterator
import unicodedata

from io.files import ensure_directory
from io.records import RecordContractError, iter_records
from resolver import ResolverError, resolve_slugs
from runtime.vaults import VaultRuntimeError, discover_registered_vault_root


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


def normalize_non_empty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise WriteError(f"{field} must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise WriteError(f"{field} must be a non-empty string")
    return normalized


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


def discover_vault_root(start: Path) -> Path:
    try:
        return discover_registered_vault_root(start)
    except VaultRuntimeError as exc:
        raise WriteError(str(exc)) from exc


def resolve_writenew_directory(
    *,
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
) -> Path:
    if target_dir is not None:
        return ensure_directory(str(target_dir))

    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    vault_root = discover_vault_root(working_dir)
    return ensure_directory(str(vault_root / INGEST_DIRNAME))


def resolve_existing_path(record: WriteRecord) -> Path:
    slug = record.input_record.slug
    if slug is None:
        raise WriteError("writeback requires input_record.slug")

    try:
        path = resolve_slugs([slug])[0]
    except ResolverError as exc:
        raise WriteError(str(exc)) from exc

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise WriteError(f"missing target file for slug: {slug}")
    return resolved


def derive_new_path(record: WriteRecord, directory: Path) -> Path:
    return directory / normalize_markdown_filename(preferred_filename_stem(record))


def _coerce_record(*, record: dict[str, Any], index: int) -> WriteRecord:
    content = record["content"]
    input_record = record["input_record"]

    slug = _optional_string(input_record.get("slug"), index=index, field="input_record.slug")
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
