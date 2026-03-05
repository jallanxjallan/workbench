from __future__ import annotations

from pathlib import Path

from workbench.lib.sentinel import (
    insert_batch_sentinel,
    read_batch_sentinel,
    strip_batch_sentinel,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_read_batch_sentinel_present(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    _write(path, "--- ASC BATCH: batch_01 ---\n---\nslug: demo\n---\n\nBody\n")
    assert read_batch_sentinel(path) == "batch_01"


def test_read_batch_sentinel_absent(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    _write(path, "---\nslug: demo\n---\n\nBody\n")
    assert read_batch_sentinel(path) is None


def test_read_batch_sentinel_malformed_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    _write(path, "--- ASC BATCH: INVALID SLUG ---\n---\nslug: demo\n---\n\nBody\n")
    assert read_batch_sentinel(path) is None


def test_read_batch_sentinel_not_at_top_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    _write(path, "---\nslug: demo\n---\n\n--- ASC BATCH: batch_01 ---\nBody\n")
    assert read_batch_sentinel(path) is None


def test_strip_and_insert_batch_sentinel_roundtrip() -> None:
    base = "---\nslug: demo\n---\n\nBody\n"
    with_sentinel = insert_batch_sentinel(base, "batch_01")
    assert with_sentinel.startswith("--- ASC BATCH: batch_01 ---\n")
    assert strip_batch_sentinel(with_sentinel) == base
