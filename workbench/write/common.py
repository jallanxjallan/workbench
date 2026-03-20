"""Shared helpers for write command implementations."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Iterator
import unicodedata

from workbench.io.ndjson import iter_ndjson

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MULTI_DASH_RE = re.compile(r"-{2,}")
_MAX_SEMANTIC_BASE_LENGTH = 48


class WriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class WriteRecord:
    envelope: dict[str, Any]
    content: str
    slug: str | None
    filename_hint: str | None
    provenance: dict[str, Any] | None
    origin: dict[str, Any] | None


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


def _coerce_record(*, record: dict[str, Any], index: int) -> WriteRecord:
    content = record.get("content")
    if not isinstance(content, str):
        raise WriteError(f"record {index}: missing required record field: content")

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
