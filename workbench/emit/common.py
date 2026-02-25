"""Shared markdown document assembly helpers for emit adapters."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from workbench.framing.markdown import emit_markdown_batch
from workbench.interop import from_ndjson
from workbench.lib.ndjson import StreamError
from workbench.tools.markdown_document import Document

DEFAULT_BOUNDARY = "\n\n"


def records_to_markdown_documents(
    records: Iterable[Mapping[str, Any]],
    *,
    boundary: str = DEFAULT_BOUNDARY,
) -> str:
    docs = [
        _document_from_record(record, record_no)
        for record_no, record in enumerate(records, start=1)
    ]
    return emit_markdown_batch(docs)


def _document_from_record(record: Mapping[str, Any], record_no: int) -> Document:
    if "metadata" not in record or "content" not in record:
        raise StreamError(
            f"NDJSON record {record_no} must include metadata and content fields"
        )

    metadata = record["metadata"]
    content = record["content"]

    if not isinstance(metadata, dict):
        raise StreamError(f"NDJSON record {record_no} metadata must be an object")
    if not isinstance(content, str):
        raise StreamError(f"NDJSON record {record_no} content must be a string")

    return Document(metadata=metadata, content=content)


def ndjson_to_markdown_documents(
    text: str,
    *,
    boundary: str = DEFAULT_BOUNDARY,
) -> str:
    return emit_markdown_batch(from_ndjson(text))
