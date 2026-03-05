from __future__ import annotations

from pathlib import Path

import pytest

import workbench.write.writeback as writeback_module
from workbench.interop.document import Document
from workbench.lib.sentinel import insert_batch_sentinel, strip_batch_sentinel
from workbench.write.common import WriteError, WriteRecord


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_markdown(
    *, metadata: dict[str, object], content: str, batch_slug: str | None
) -> str:
    doc = Document(metadata=metadata, content=content)
    markdown = doc.write_text()
    if batch_slug is None:
        return markdown
    return insert_batch_sentinel(markdown, batch_slug)


def _make_record(
    *,
    path: Path,
    slug: str,
    batch_slug: str,
    content: str,
    envelope_extra: dict[str, object] | None = None,
    origin_extra: dict[str, object] | None = None,
) -> WriteRecord:
    origin: dict[str, object] = {
        "slug": slug,
        "path": str(path),
    }
    if origin_extra:
        origin.update(origin_extra)

    envelope: dict[str, object] = {
        "batch_slug": batch_slug,
        "content": content,
        "origin": origin,
    }
    if envelope_extra:
        envelope.update(envelope_extra)

    return WriteRecord(
        envelope=envelope,
        content=content,
        origin=origin,
        batch_slug=batch_slug,
    )


@pytest.mark.parametrize(
    ("envelope_extra", "origin_extra"),
    [
        (
            {
                "analysis": {"label": "bird", "scores": [0.7, 0.9]},
                "dataset_file": "/Studio/datasets/hornbill.csv",
            },
            None,
        ),
        (
            None,
            {
                "trace": {
                    "worker": {"name": "captioner", "version": 3},
                    "ids": ["a", "b", "c"],
                }
            },
        ),
        (
            {
                "images": [
                    "/Studio/images/hornbill.jpg",
                    {"thumb": "/Studio/images/hornbill-thumb.jpg"},
                ]
            },
            None,
        ),
        (
            {
                "metadata": {
                    "owner": "jeremy",
                    "flags": {"reviewed": True, "draft": False},
                }
            },
            None,
        ),
    ],
)
def test_writeback_preserves_record_envelope_in_autoscribe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    envelope_extra: dict[str, object] | None,
    origin_extra: dict[str, object] | None,
) -> None:
    target = tmp_path / "hornbill.md"
    original_frontmatter = {
        "slug": "hornbill",
        "stage": "draft",
        "state": "active",
        "autoscribe": {"batch_slug": "old-batch", "origin": {"slug": "hornbill"}},
    }
    _write(
        target,
        _make_markdown(
            metadata=original_frontmatter,
            content="Old content",
            batch_slug="caption.generate",
        ),
    )

    record = _make_record(
        path=target,
        slug="hornbill",
        batch_slug="caption.generate",
        content="Updated content",
        envelope_extra=envelope_extra,
        origin_extra=origin_extra,
    )

    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: iter([record]),
    )

    writeback_module.write_back_batch(
        "caption.generate",
        asc_bin="asc",
        debug_routing=False,
    )

    written = target.read_text(encoding="utf-8")
    parsed = Document.read_text(strip_batch_sentinel(written))

    assert parsed.metadata["slug"] == "hornbill"
    assert parsed.metadata["stage"] == "draft"
    assert parsed.metadata["state"] == "active"
    assert parsed.metadata["autoscribe"] == record.envelope
    assert parsed.content.strip() == "Updated content"


def test_writeback_aborts_on_slug_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hornbill.md"
    original = _make_markdown(
        metadata={"slug": "hornbill", "stage": "draft"},
        content="Old",
        batch_slug="batch-1",
    )
    _write(target, original)

    record = _make_record(
        path=target,
        slug="wrong-slug",
        batch_slug="batch-1",
        content="Updated",
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: iter([record]),
    )

    with pytest.raises(WriteError, match="frontmatter slug does not match record origin.slug"):
        writeback_module.write_back_batch(
            "batch-1",
            asc_bin="asc",
            debug_routing=False,
        )

    assert target.read_text(encoding="utf-8") == original


def test_writeback_aborts_when_sentinel_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hornbill.md"
    original = _make_markdown(
        metadata={"slug": "hornbill"},
        content="Old",
        batch_slug="batch-old",
    )
    _write(target, original)

    record = _make_record(
        path=target,
        slug="hornbill",
        batch_slug="batch-new",
        content="Updated",
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: iter([record]),
    )

    with pytest.raises(WriteError, match="batch sentinel does not match record batch_slug"):
        writeback_module.write_back_batch(
            "batch-new",
            asc_bin="asc",
            debug_routing=False,
        )

    assert target.read_text(encoding="utf-8") == original


def test_writeback_aborts_when_sentinel_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hornbill.md"
    original = _make_markdown(
        metadata={"slug": "hornbill"},
        content="Old",
        batch_slug=None,
    )
    _write(target, original)

    record = _make_record(
        path=target,
        slug="hornbill",
        batch_slug="batch-1",
        content="Updated",
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: iter([record]),
    )

    with pytest.raises(WriteError, match="batch sentinel does not match record batch_slug"):
        writeback_module.write_back_batch(
            "batch-1",
            asc_bin="asc",
            debug_routing=False,
        )

    assert target.read_text(encoding="utf-8") == original


def test_writeback_aborts_when_record_batch_slug_differs_from_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hornbill.md"
    original = _make_markdown(
        metadata={"slug": "hornbill"},
        content="Old",
        batch_slug="batch-1",
    )
    _write(target, original)

    record = _make_record(
        path=target,
        slug="hornbill",
        batch_slug="batch-1",
        content="Updated",
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: iter([record]),
    )

    with pytest.raises(
        WriteError,
        match="record batch_slug does not match requested batch slug",
    ):
        writeback_module.write_back_batch(
            "batch-2",
            asc_bin="asc",
            debug_routing=False,
        )

    assert target.read_text(encoding="utf-8") == original


def test_writeback_rejects_non_absolute_origin_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = WriteRecord(
        envelope={
            "batch_slug": "batch-1",
            "content": "Updated",
            "origin": {"slug": "hornbill", "path": "relative/path.md"},
        },
        content="Updated",
        origin={"slug": "hornbill", "path": "relative/path.md"},
        batch_slug="batch-1",
    )
    monkeypatch.setattr(
        writeback_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: iter([record]),
    )

    with pytest.raises(WriteError, match="origin.path must be an absolute path"):
        writeback_module.write_back_batch(
            "batch-1",
            asc_bin="asc",
            debug_routing=False,
        )
