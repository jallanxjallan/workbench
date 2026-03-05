"""Shared markdown document assembly helpers for emit flows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from workbench.emit.record_to_document import record_to_document
from workbench.framing.markdown import emit_markdown_batch
from workbench.interop import from_ndjson
from workbench.lib.ndjson import StreamError

DEFAULT_BOUNDARY = "\n\n"


def records_to_markdown_documents(
    records: Iterable[Mapping[str, Any]],
    *,
    boundary: str = DEFAULT_BOUNDARY,
) -> str:
    docs = []
    for record_no, record in enumerate(records, start=1):
        try:
            docs.append(record_to_document(record))
        except ValueError as exc:
            raise StreamError(f"invalid record at {record_no}: {exc}") from exc
    return emit_markdown_batch(docs)


def ndjson_to_markdown_documents(
    text: str,
    *,
    boundary: str = DEFAULT_BOUNDARY,
) -> str:
    return emit_markdown_batch(from_ndjson(text))
