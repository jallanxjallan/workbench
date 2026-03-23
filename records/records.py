"""Canonical NDJSON record helpers."""

from __future__ import annotations

import copy
import json
from typing import Any, Iterable, Iterator

from records.ndjson import iter_ndjson


CANONICAL_TOP_LEVEL_KEYS = frozenset({"content", "input_record"})


class RecordContractError(RuntimeError):
    """Raised when an NDJSON record violates the canonical contract."""


def make_record(*, content: str, input_record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(content, str):
        raise RecordContractError("content must be a string")
    if not isinstance(input_record, dict):
        raise RecordContractError("input_record must be an object")
    return {
        "content": content,
        "input_record": copy.deepcopy(input_record),
    }


def validate_record(record: dict[str, Any], *, index: int | None = None) -> dict[str, Any]:
    label = f"record {index}" if index is not None else "record"
    if not isinstance(record, dict):
        raise RecordContractError(f"{label}: NDJSON record must be an object")

    keys = set(record)
    if not keys == CANONICAL_TOP_LEVEL_KEYS:
        expected = ", ".join(sorted(CANONICAL_TOP_LEVEL_KEYS))
        found = ", ".join(sorted(keys))
        raise RecordContractError(
            f"{label}: invalid top-level fields: expected {{{expected}}}, found {{{found}}}"
        )

    content = record.get("content")
    if not isinstance(content, str):
        raise RecordContractError(f"{label}: content must be a string")

    input_record = record.get("input_record")
    if not isinstance(input_record, dict):
        raise RecordContractError(f"{label}: input_record must be an object")

    return {
        "content": content,
        "input_record": copy.deepcopy(input_record),
    }


def iter_records(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    try:
        for index, record in enumerate(iter_ndjson(stream), start=1):
            yield validate_record(record, index=index)
    except (ValueError, json.JSONDecodeError) as exc:
        raise RecordContractError(f"invalid NDJSON input: {exc}") from exc


def dump_record(record: dict[str, Any]) -> str:
    normalized = validate_record(record)
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":")) + "\n"
