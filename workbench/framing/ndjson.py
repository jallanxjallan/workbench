"""NDJSON batch conversion for MarkdownRecord objects."""

from __future__ import annotations

import json

from workbench.framing.markdown import MarkdownRecord


def records_to_ndjson(records: list[MarkdownRecord]) -> str:
    lines = [
        json.dumps(
            {
                "metadata": record.metadata,
                "content": record.content,
            },
            ensure_ascii=False,
        )
        for record in records
    ]
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def ndjson_to_records(text: str) -> list[MarkdownRecord]:
    records: list[MarkdownRecord] = []

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_no}: {exc.msg}") from exc

        if not isinstance(obj, dict):
            raise ValueError(f"invalid JSON on line {line_no}: expected object")
        if "metadata" not in obj or "content" not in obj:
            raise ValueError(f"invalid JSON on line {line_no}: expected metadata/content fields")

        metadata = obj["metadata"]
        content = obj["content"]

        if not isinstance(metadata, dict):
            raise ValueError(f"invalid JSON on line {line_no}: metadata must be an object")
        if not isinstance(content, str):
            raise ValueError(f"invalid JSON on line {line_no}: content must be a string")

        records.append(MarkdownRecord(metadata=metadata, content=content))

    return records
