from __future__ import annotations

from workbench.emit.assemble import assemble_record_markdown_documents
from workbench.emit.export import export_records_to_markdown
from workbench.emit.record_to_markdown import record_to_markdown


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
