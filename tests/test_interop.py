from __future__ import annotations

import pytest

from workbench.interop import Document, from_ndjson, to_ndjson
from workbench.lib.ndjson import StreamError


def test_single_document_round_trip() -> None:
    docs = [Document(metadata={"title": "One"}, content="Body")]
    payload = to_ndjson(docs)
    assert payload.endswith("\n")
    assert from_ndjson(payload) == docs


def test_multiple_documents_round_trip() -> None:
    docs = [
        Document(metadata={"title": "One"}, content="A"),
        Document(metadata={"title": "Two"}, content="B"),
    ]
    payload = to_ndjson(docs)
    assert payload.count("\n") == 2
    assert from_ndjson(payload) == docs


def test_invalid_ndjson_raises_stream_error() -> None:
    with pytest.raises(StreamError, match="invalid NDJSON"):
        from_ndjson('{"metadata": {}, "content": "ok"}\n{bad}\n')


def test_schema_violation_raises_stream_error() -> None:
    missing_metadata = '{"content":"Body"}\n'
    with pytest.raises(
        StreamError,
        match="must include metadata and content fields",
    ):
        from_ndjson(missing_metadata)
