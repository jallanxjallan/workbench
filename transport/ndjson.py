from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from typing import TextIO


def loads_record(line: str) -> dict:
    stripped = line.strip()
    if not stripped:
        raise ValueError("NDJSON line is blank.")

    try:
        record = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid NDJSON record: {exc.msg}") from exc

    if not isinstance(record, dict):
        raise ValueError("NDJSON record must decode to a JSON object.")

    return record


def dumps_record(record: dict) -> str:
    if not isinstance(record, dict):
        raise TypeError("NDJSON record must be a dict.")
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"))


def iter_records(stream: TextIO) -> Iterator[dict]:
    for line_number, line in enumerate(stream, start=1):
        if not line.strip():
            continue

        try:
            yield loads_record(line)
        except ValueError as exc:
            raise ValueError(f"Invalid NDJSON at line {line_number}: {exc}") from exc


def read_all_records(stream: TextIO) -> list[dict]:
    return list(iter_records(stream))


def write_record(stream: TextIO, record: dict) -> None:
    stream.write(f"{dumps_record(record)}\n")


def write_records(stream: TextIO, records: Iterable[dict]) -> None:
    for record in records:
        write_record(stream, record)
