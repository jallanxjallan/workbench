from __future__ import annotations

import pytest

from workbench.framing.markdown import MarkdownRecord, emit_markdown_batch, parse_markdown_batch
from workbench.framing.ndjson import ndjson_to_records, records_to_ndjson


def test_single_record_round_trip() -> None:
    source = "---\ntitle: Alpha\nkind: note\n---\n\nBody line 1\nBody line 2"
    parsed = parse_markdown_batch(source)
    assert len(parsed) == 1
    assert parsed[0].metadata == {"title": "Alpha", "kind": "note"}
    assert parsed[0].content == "Body line 1\nBody line 2"
    assert emit_markdown_batch(parsed) == source


def test_multi_record_round_trip() -> None:
    records = [
        MarkdownRecord(metadata={"title": "One"}, content="A"),
        MarkdownRecord(metadata={"title": "Two", "tags": ["x", "y"]}, content="B\nC"),
    ]
    markdown = emit_markdown_batch(records)
    reparsed = parse_markdown_batch(markdown)
    assert reparsed == records
    assert emit_markdown_batch(reparsed) == markdown


def test_mixed_frontmatter_and_content() -> None:
    source = "---\ntitle: Mixed\n---\n\nFirst paragraph.\nSecond paragraph."
    parsed = parse_markdown_batch(source)
    assert parsed == [MarkdownRecord(metadata={"title": "Mixed"}, content="First paragraph.\nSecond paragraph.")]


def test_invalid_yaml_failure() -> None:
    source = "---\ntitle: [broken\n---\n\nBody"
    with pytest.raises(ValueError, match="invalid YAML"):
        parse_markdown_batch(source)


def test_invalid_json_failure() -> None:
    bad = '{"metadata": {}, "content": "ok"}\n{invalid}\n'
    with pytest.raises(ValueError, match="invalid JSON"):
        ndjson_to_records(bad)


def test_deterministic_output_check() -> None:
    records = [MarkdownRecord(metadata={"z": 1, "a": 2}, content="Deterministic body")]
    first = emit_markdown_batch(records)
    second = emit_markdown_batch(records)
    assert first == second
    assert (
        first
        == "---\nz: 1\na: 2\n---\n\nDeterministic body"
    )


def test_records_ndjson_batch_conversion() -> None:
    records = [
        MarkdownRecord(metadata={"title": "First"}, content="One"),
        MarkdownRecord(metadata={"title": "Second"}, content="Two"),
    ]
    ndjson_text = records_to_ndjson(records)
    restored = ndjson_to_records(ndjson_text)
    assert restored == records
