from __future__ import annotations

from pathlib import Path

import pytest

from workbench.framing.batch import (
    markdown_to_ndjson,
    ndjson_to_markdown,
    ndjson_to_records,
    records_to_ndjson,
)
from workbench.framing.markdown import (
    MULTI_DOCUMENT_ERROR,
    emit_markdown_batch,
    parse_markdown_batch,
)
from workbench.lib.ndjson import StreamError
from workbench.tools.markdown_document import Document


def test_single_record_round_trip() -> None:
    source = "---\ntitle: Alpha\nkind: note\n---\n\nBody line 1\nBody line 2"
    parsed = parse_markdown_batch(source)
    assert parsed == [Document(metadata={"title": "Alpha", "kind": "note"}, content="Body line 1\nBody line 2")]
    assert len(parsed) == 1
    assert parsed[0].metadata == {"title": "Alpha", "kind": "note"}
    assert parsed[0].content == "Body line 1\nBody line 2"
    assert emit_markdown_batch(parsed) == source


def test_empty_input_parses_to_empty_list() -> None:
    assert parse_markdown_batch("") == []
    assert parse_markdown_batch(" \n\t\r\n") == []


def test_multi_document_input_is_rejected() -> None:
    source = (
        "---\ntitle: One\n---\n\nA\n\n"
        "---\ntitle: Two\n---\n\nB\n"
    )
    with pytest.raises(ValueError, match=MULTI_DOCUMENT_ERROR):
        parse_markdown_batch(source)


def test_invalid_yaml_failure_still_surfaces() -> None:
    source = "---\ntitle: [broken\n---\n\nBody"
    with pytest.raises(ValueError, match="invalid YAML"):
        parse_markdown_batch(source)


def test_emit_markdown_batch_rejects_more_than_one_document() -> None:
    docs = [
        Document(metadata={"title": "One"}, content="A"),
        Document(metadata={"title": "Two"}, content="B"),
    ]
    with pytest.raises(ValueError, match=MULTI_DOCUMENT_ERROR):
        emit_markdown_batch(docs)


def test_invalid_json_failure() -> None:
    bad = '{"metadata": {}, "content": "ok"}\n{invalid}\n'
    with pytest.raises(StreamError, match="invalid NDJSON"):
        ndjson_to_records(bad)


def test_deterministic_output_check() -> None:
    records = [Document(metadata={"z": 1, "a": 2}, content="Deterministic body")]
    first = emit_markdown_batch(records)
    second = emit_markdown_batch(records)
    assert first == second
    assert (
        first
        == "---\nz: 1\na: 2\n---\n\nDeterministic body"
    )


def test_ndjson_multi_record_conversion_still_works() -> None:
    records = [
        Document(metadata={"title": "First"}, content="One"),
        Document(metadata={"title": "Second"}, content="Two"),
    ]
    ndjson_text = records_to_ndjson(records)
    restored = ndjson_to_records(ndjson_text)
    assert restored == records


def test_markdown_to_ndjson_and_back_single_document() -> None:
    markdown = "---\ntitle: Single\n---\n\nBody"
    ndjson_text = markdown_to_ndjson(markdown)
    assert ndjson_to_records(ndjson_text) == [
        Document(metadata={"title": "Single"}, content="Body")
    ]
    restored_markdown = ndjson_to_markdown(ndjson_text)
    assert restored_markdown == markdown


def test_ndjson_to_markdown_rejects_multiple_records() -> None:
    ndjson_text = (
        '{"metadata":{"title":"One"},"content":"A"}\n'
        '{"metadata":{"title":"Two"},"content":"B"}\n'
    )
    with pytest.raises(ValueError, match=MULTI_DOCUMENT_ERROR):
        ndjson_to_markdown(ndjson_text)


def test_no_legacy_split_markdown_batch_symbol() -> None:
    for path in Path("workbench").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "split_markdown_batch" not in text
