"""High-level batch conversion entrypoints."""

from __future__ import annotations

from workbench.framing.markdown import emit_markdown_batch, parse_markdown_batch
from workbench.framing.ndjson import ndjson_to_records, records_to_ndjson


def markdown_to_ndjson(text: str) -> str:
    return records_to_ndjson(parse_markdown_batch(text))


def ndjson_to_markdown(text: str) -> str:
    return emit_markdown_batch(ndjson_to_records(text))
