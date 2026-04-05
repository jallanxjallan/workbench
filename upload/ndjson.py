from __future__ import annotations

import sys
import json
from typing import Any


class NdjsonEmitError(RuntimeError):
    pass


REQUIRED_FIELDS = ("type", "kind", "slug", "payload")


def emit_record(record: dict[str, Any]) -> None:
    validated = validate_record(record)
    sys.stdout.write(json.dumps(validated, ensure_ascii=False))
    sys.stdout.write("\n")


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise NdjsonEmitError("record must be an object")

    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        joined = ", ".join(missing)
        raise NdjsonEmitError(f"record missing required field(s): {joined}")

    record_type = require_text(record["type"], field_name="type")
    kind = require_text(record["kind"], field_name="kind")
    slug = require_text(record["slug"], field_name="slug")
    payload = require_object(record["payload"], field_name="payload")

    validated = dict(record)
    validated["type"] = record_type
    validated["kind"] = kind
    validated["slug"] = slug
    validated["payload"] = payload
    return validated


def require_text(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise NdjsonEmitError(f"{field_name} must be a string")

    text = value.strip()
    if not text:
        raise NdjsonEmitError(f"{field_name} must be a non-empty string")

    return text


def require_object(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NdjsonEmitError(f"{field_name} must be an object")

    return value