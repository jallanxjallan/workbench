from __future__ import annotations

from pathlib import Path

from workbench.interop.document import Document


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


def test_document_read_file_with_frontmatter(tmp_path: Path) -> None:
    base = Document(metadata={"class": "passage", "slug": "hornbill"}, content="Body\n")

    path = tmp_path / "entry.md"
    _write(path, base.write_text())
    parsed = Document.read_file(path)
    assert parsed.metadata == base.metadata
    assert parsed.content == base.content


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
