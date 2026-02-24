from __future__ import annotations

import pytest

from workbench.emit.record_to_markdown import record_to_markdown
from workbench.framing.batch import markdown_to_ndjson
from workbench.framing.markdown import MarkdownRecord, emit_markdown_batch
from workbench.ingest.markdown_to_record import convert_markdown_stream, markdown_text_to_record_batch


def test_markdown_to_record_primitive_matches_batch_converter() -> None:
    source = "---\ntitle: Alpha\n---\n\nBody"
    assert markdown_text_to_record_batch(source) == markdown_to_ndjson(source)


def test_record_to_markdown_primitive_single_record() -> None:
    record = {"metadata": {"title": "Alpha"}, "content": "Body"}
    assert record_to_markdown(record) == emit_markdown_batch(
        [MarkdownRecord(metadata={"title": "Alpha"}, content="Body")]
    )


def test_markdown_to_record_stream_entrypoint_is_functional() -> None:
    markdown_input = "---\ntitle: Stream\n---\n\nBody"
    ndjson_output: list[str] = []
    convert_markdown_stream(read_text=lambda: markdown_input, write_text=ndjson_output.append)
    assert ndjson_output == [markdown_to_ndjson(markdown_input)]


def test_record_to_markdown_requires_string_content() -> None:
    with pytest.raises(ValueError, match="record content must be a string"):
        record_to_markdown({"metadata": {}, "content": None})
