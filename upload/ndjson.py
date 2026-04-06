from __future__ import annotations

from typing import Any


class NdjsonEmitError(RuntimeError):
    pass


def _require_non_empty_string(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise NdjsonEmitError(f"record field must be a non-empty string: {key}")
    return value.strip()


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise NdjsonEmitError("record must be an object")

    validated: dict[str, Any] = {
        "type": _require_non_empty_string(record, "type"),
        "slug": _require_non_empty_string(record, "slug"),
    }

    kind = record.get("kind")
    if kind is not None:
        if not isinstance(kind, str) or not kind.strip():
            raise NdjsonEmitError("record field must be a non-empty string: kind")
        validated["kind"] = kind.strip()

    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise NdjsonEmitError("record field must be an object: payload")
    validated["payload"] = payload

    return validated