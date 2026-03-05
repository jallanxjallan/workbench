"""Minimal NDJSON stream reader."""

from __future__ import annotations

import json
from typing import Any, Iterable, Iterator


def iter_ndjson(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in stream:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError("NDJSON record must be an object")
        yield obj
