"""Single-record conversion primitive for emit flows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from workbench.interop.document import Document


def _record_metadata(record: Mapping[str, Any]) -> dict[str, Any]:
    metadata = record.get("metadata")
    if metadata is None:
        return {}
    if not isinstance(metadata, dict):
        raise ValueError("record metadata must be an object when present")
    return dict(metadata)


def _record_content(record: Mapping[str, Any]) -> str:
    content = record.get("content")
    if not isinstance(content, str):
        raise ValueError("record content must be a string")
    return content


def record_to_markdown(record: Mapping[str, Any]) -> str:
    """Convert a single NDJSON-style record to one markdown document."""
    document = Document(
        metadata=_record_metadata(record),
        content=_record_content(record),
    )
    return document.write_text()
