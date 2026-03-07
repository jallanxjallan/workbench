from __future__ import annotations

from pathlib import Path

from workbench.interop.document import Document
from workbench.lib.sentinel import BATCH_SENTINEL_PATTERN, insert_batch_sentinel


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_document_roundtrip_preserves_frontmatter() -> None:
    doc = Document(
        metadata={"class": "passage", "slug": "omaf.passage.hornbill", "tags": ["a", "b"]},
        content="Body\n",
    )
    rendered = doc.write_text()
    reparsed = Document.read_text(rendered)

    assert reparsed.metadata == doc.metadata
    assert reparsed.content == doc.content


def test_document_read_file_supports_batch_sentinel(tmp_path: Path) -> None:
    base = Document(metadata={"class": "passage", "slug": "hornbill"}, content="Body\n")
    with_sentinel = insert_batch_sentinel(base.write_text(), "batch-1")

    path = tmp_path / "sentinel.md"
    _write(path, with_sentinel)
    parsed = Document.read_file(path, sentinel_pattern=BATCH_SENTINEL_PATTERN)
    assert parsed.metadata == base.metadata
    assert parsed.content.endswith(base.content)


def test_document_content_rewrite_preserves_metadata(tmp_path: Path) -> None:
    target = tmp_path / "entry.md"
    original = Document(
        metadata={"class": "passage", "slug": "omaf.passage.entry", "state": "draft"},
        content="Old\n",
    )
    _write(target, original.write_text())

    doc = Document.read_file(target)
    metadata_before = dict(doc.metadata or {})
    doc.content = "Updated\n"
    _write(target, doc.write_text())

    rewritten = Document.read_file(target)
    assert rewritten.metadata == metadata_before
    assert rewritten.content == "Updated\n"
