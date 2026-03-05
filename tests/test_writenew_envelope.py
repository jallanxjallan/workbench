from __future__ import annotations

from pathlib import Path

import pytest

import workbench.write.writenew as writenew_module
from workbench.interop.document import Document
from workbench.lib.sentinel import read_batch_sentinel, strip_batch_sentinel
from workbench.write.common import WriteError, WriteRecord


def test_writenew_writes_autoscribe_envelope_preserving_unknown_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hornbill.md"
    envelope: dict[str, object] = {
        "batch_slug": "caption.generate",
        "content": "Generated body",
        "origin": {
            "slug": "hornbill",
            "path": str(target),
            "nested": {"id": "abc", "flags": [1, 2, 3]},
        },
        "images": ["/Studio/images/hornbill.jpg"],
        "metadata": {"owner": "jeremy", "reviewed": True},
    }
    origin = envelope["origin"]
    assert isinstance(origin, dict)

    record = WriteRecord(
        envelope=envelope,
        content="Generated body",
        origin=origin,
        batch_slug="caption.generate",
    )

    monkeypatch.setattr(
        writenew_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: iter([record]),
    )

    writenew_module.write_new_batch(
        "caption.generate",
        asc_bin="asc",
        debug_routing=False,
    )

    assert target.exists()
    assert read_batch_sentinel(target) == "caption.generate"

    parsed = Document.read_text(strip_batch_sentinel(target.read_text(encoding="utf-8")))
    assert parsed.metadata["autoscribe"] == envelope
    assert parsed.content.strip() == "Generated body"


def test_writenew_rejects_non_absolute_origin_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = WriteRecord(
        envelope={
            "batch_slug": "batch-1",
            "content": "body",
            "origin": {"slug": "hornbill", "path": "relative.md"},
        },
        content="body",
        origin={"slug": "hornbill", "path": "relative.md"},
        batch_slug="batch-1",
    )

    monkeypatch.setattr(
        writenew_module,
        "fetch_batch_records",
        lambda *_args, **_kwargs: iter([record]),
    )

    with pytest.raises(WriteError, match="origin.path must be an absolute path"):
        writenew_module.write_new_batch(
            "batch-1",
            asc_bin="asc",
            debug_routing=False,
        )
