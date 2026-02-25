from __future__ import annotations

import pytest

from workbench.emit.assemble import assemble_ndjson_text, assemble_record_markdown_documents
from workbench.emit.export import export_ndjson_text, export_records_to_markdown
from workbench.emit.record_to_markdown import record_to_markdown
from workbench.framing.markdown import MULTI_DOCUMENT_ERROR
from workbench.lib.ndjson import StreamError


def _sample_record() -> dict[str, object]:
    return {
        "metadata": {"title": "Guardrail", "kind": "note"},
        "content": "Body line 1\nBody line 2",
    }


def test_assemble_adapter_uses_record_to_markdown_for_single_record() -> None:
    record = _sample_record()
    assembled = assemble_record_markdown_documents([record])
    assert assembled == record_to_markdown(record)


def test_export_adapter_uses_record_to_markdown_for_single_record() -> None:
    record = _sample_record()
    exported = export_records_to_markdown([record])
    assert exported == record_to_markdown(record)


def test_assemble_and_export_ndjson_adapters_match_output_for_single_record() -> None:
    ndjson_text = '{"metadata":{"title":"A"},"content":"Body A"}\n'
    assert assemble_ndjson_text(ndjson_text) == export_ndjson_text(ndjson_text)


def test_assemble_and_export_ndjson_adapters_reject_multi_record_input() -> None:
    ndjson_text = (
        '{"metadata":{"title":"A"},"content":"Body A"}\n'
        '{"metadata":{"title":"B"},"content":"Body B"}\n'
    )
    with pytest.raises(ValueError, match=MULTI_DOCUMENT_ERROR):
        assemble_ndjson_text(ndjson_text)
    with pytest.raises(ValueError, match=MULTI_DOCUMENT_ERROR):
        export_ndjson_text(ndjson_text)


def test_assemble_and_export_ndjson_adapters_match_error_behavior() -> None:
    bad = "{bad-json}\n"
    with pytest.raises(StreamError) as assemble_exc:
        assemble_ndjson_text(bad)
    with pytest.raises(StreamError) as export_exc:
        export_ndjson_text(bad)
    assert str(assemble_exc.value) == str(export_exc.value)
