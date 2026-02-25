"""High-level batch conversion entrypoints."""

from __future__ import annotations

from workbench.framing.markdown import emit_markdown_batch, parse_markdown_batch
from workbench.interop import from_ndjson, to_ndjson
from workbench.tools.markdown_document import Document


def records_to_ndjson(docs: list[Document]) -> str:
    return to_ndjson(docs)


def ndjson_to_records(text: str) -> list[Document]:
    return from_ndjson(text)


def markdown_to_ndjson(text: str) -> str:
    return records_to_ndjson(parse_markdown_batch(text))


def ndjson_to_markdown(text: str) -> str:
    return emit_markdown_batch(ndjson_to_records(text))
