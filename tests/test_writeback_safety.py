from __future__ import annotations

from pathlib import Path

import pytest

import workbench.write.writeback as writeback_module
from workbench.interop.document import Document
from workbench.lib.sentinel import insert_batch_sentinel, strip_batch_sentinel
from workbench.write.common import WriteRecord


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_markdown(*, slug: str, content: str, batch_slug: str | None = None) -> str:
    doc = Document(metadata={"slug": slug, "class": "passage"}, content=content)
    markdown = doc.write_text()
    if batch_slug is None:
        return markdown
    return insert_batch_sentinel(markdown, batch_slug)


def test_writeback_overwrite_allowed_when_slug_and_sentinel_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "demo.md"
    _write(target, _make_markdown(slug="demo", content="Old", batch_slug="batch-1"))

    record = WriteRecord(
        metadata={"slug": "demo"},
        content="Updated",
        input_record={"path": str(target), "slug": "demo"},
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: [record],
    )

    writeback_module.write_back_batch(
        "batch-1",
        asc_bin="asc",
        debug_routing=False,
    )

    written = target.read_text(encoding="utf-8")
    assert written.startswith("--- ASC BATCH: batch-1 ---\n")
    assert "Updated" in written
    assert "Old" not in written

    parsed = Document.read_text(strip_batch_sentinel(written))
    assert parsed.metadata["slug"] == "demo"
    assert parsed.content.strip() == "Updated"


def test_writeback_slug_mismatch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "demo.md"
    original = _make_markdown(slug="demo", content="Old", batch_slug="batch-1")
    _write(target, original)

    record = WriteRecord(
        metadata={"slug": "other"},
        content="Updated",
        input_record={"path": str(target), "slug": "other"},
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: [record],
    )

    with pytest.raises(RuntimeError, match="slug mismatch"):
        writeback_module.write_back_batch(
            "batch-1",
            asc_bin="asc",
            debug_routing=False,
        )

    assert target.read_text(encoding="utf-8") == original


def test_writeback_batch_mismatch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "demo.md"
    original = _make_markdown(slug="demo", content="Old", batch_slug="batch-old")
    _write(target, original)

    record = WriteRecord(
        metadata={"slug": "demo"},
        content="Updated",
        input_record={"path": str(target), "slug": "demo"},
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: [record],
    )

    with pytest.raises(RuntimeError, match="batch mismatch"):
        writeback_module.write_back_batch(
            "batch-new",
            asc_bin="asc",
            debug_routing=False,
        )

    assert target.read_text(encoding="utf-8") == original


def test_writeback_missing_sentinel_creates_new_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "legacy.md"
    original = _make_markdown(slug="demo", content="Old", batch_slug=None)
    _write(target, original)

    record = WriteRecord(
        metadata={"slug": "demo"},
        content="Updated",
        input_record={"path": str(target), "slug": "demo"},
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: [record],
    )

    writeback_module.write_back_batch(
        "batch-1",
        asc_bin="asc",
        debug_routing=False,
    )

    new_path = tmp_path / "demo.md"
    assert new_path.exists()
    assert target.read_text(encoding="utf-8") == original

    written = new_path.read_text(encoding="utf-8")
    assert written.startswith("--- ASC BATCH: batch-1 ---\n")
    parsed = Document.read_text(strip_batch_sentinel(written))
    assert parsed.metadata["slug"] == "demo"
    assert parsed.content.strip() == "Updated"
