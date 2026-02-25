"""NDJSON parse/emit primitives."""

from __future__ import annotations

import json
from typing import Any, Iterable, Iterator


class StreamError(RuntimeError):
    pass


def parse_ndjson(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line_no, raw in enumerate(stream, start=1):
        line = raw.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StreamError(f"invalid NDJSON at line {line_no}") from exc

        if not isinstance(obj, dict):
            raise StreamError(f"NDJSON record at line {line_no} must be an object")

        yield obj


def emit_ndjson(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False)
