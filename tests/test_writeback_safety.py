from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import workbench.write.writeback as writeback_module
from workbench.interop.document import Document
from workbench.lib.regex_registry import RegexPattern
from workbench.lib.sentinel import insert_batch_sentinel, read_batch_sentinel
from workbench.write.common import WriteError


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _markdown(*, slug: str, body: str, batch_slug: str | None) -> str:
    doc = Document(metadata={"slug": slug, "state": "draft"}, content=body)
    text = doc.write_text()
    if batch_slug is None:
        return text
    return insert_batch_sentinel(text, batch_slug)


def test_writeback_aborts_on_slug_validation_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "vault" / "passages" / "hornbill.md"
    _write(target, _markdown(slug="hornbill", body="Old", batch_slug="batch-1"))

    monkeypatch.setattr(
        writeback_module,
        "build_slug_index",
        lambda _root: {"wrong-slug": target},
    )

    ndjson = io.StringIO('{"slug":"wrong-slug","batch_slug":"batch-1","content":"Updated"}\n')
    with pytest.raises(WriteError, match="frontmatter slug does not match record.slug"):
        writeback_module.write_back_records(
            studio_root=str(tmp_path / "vault"),
            debug_routing=False,
            input_stream=ndjson,
        )


def test_writeback_aborts_when_batch_sentinel_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "vault" / "passages" / "hornbill.md"
    _write(target, _markdown(slug="hornbill", body="Old", batch_slug=None))

    monkeypatch.setattr(
        writeback_module,
        "build_slug_index",
        lambda _root: {"hornbill": target},
    )

    ndjson = io.StringIO('{"slug":"hornbill","batch_slug":"batch-1","content":"Updated"}\n')
    with pytest.raises(WriteError, match="batch sentinel missing"):
        writeback_module.write_back_records(
            studio_root=str(tmp_path / "vault"),
            debug_routing=False,
            input_stream=ndjson,
        )


def test_writeback_aborts_when_batch_sentinel_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "vault" / "passages" / "hornbill.md"
    _write(target, _markdown(slug="hornbill", body="Old", batch_slug="batch-old"))

    monkeypatch.setattr(
        writeback_module,
        "build_slug_index",
        lambda _root: {"hornbill": target},
    )

    ndjson = io.StringIO('{"slug":"hornbill","batch_slug":"batch-new","content":"Updated"}\n')
    with pytest.raises(WriteError, match="batch sentinel does not match record batch_slug"):
        writeback_module.write_back_records(
            studio_root=str(tmp_path / "vault"),
            debug_routing=False,
            input_stream=ndjson,
        )


def test_writeback_routes_to_path_from_slug_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hornbill = tmp_path / "vault" / "passages" / "hornbill.md"
    condor = tmp_path / "vault" / "passages" / "condor.md"
    _write(hornbill, _markdown(slug="hornbill", body="Old hornbill", batch_slug="batch-1"))
    _write(condor, _markdown(slug="condor", body="Old condor", batch_slug="batch-1"))

    monkeypatch.setattr(
        writeback_module,
        "build_slug_index",
        lambda _root: {"hornbill": hornbill, "condor": condor},
    )

    ndjson = io.StringIO('{"slug":"condor","batch_slug":"batch-1","content":"Updated condor"}\n')
    writeback_module.write_back_records(
        studio_root=str(tmp_path / "vault"),
        debug_routing=False,
        input_stream=ndjson,
    )

    hornbill_text = hornbill.read_text(encoding="utf-8")
    condor_text = condor.read_text(encoding="utf-8")

    assert "Old hornbill" in hornbill_text
    assert "Updated condor" in condor_text
    assert "Old condor" not in condor_text
    assert read_batch_sentinel(condor) is None
    assert read_batch_sentinel(hornbill) == "batch-1"


def test_build_slug_index_parses_ndjson_rows_from_rg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = tmp_path / "vault" / "notes" / "hornbill.md"
    two = tmp_path / "vault" / "notes" / "condor.md"
    _write(one, _markdown(slug="hornbill", body="One", batch_slug="batch-1"))
    _write(two, _markdown(slug="condor", body="Two", batch_slug="batch-1"))

    calls: list[tuple[str, Path, bool, bool]] = []

    def _fake_load_regex(name: str) -> RegexPattern:
        assert name == "slug_field"
        return RegexPattern(
            name="slug_field",
            pattern=r"slug:\s*[a-z0-9._-]+",
            engine="default",
            ignore_case=False,
        )

    def _fake_rg_search(
        pattern: str,
        root: Path,
        *,
        ignore_case: bool = False,
        pcre2: bool = False,
    ):
        calls.append((pattern, root, ignore_case, pcre2))
        yield json.dumps(
            {
                "path": str(one),
                "line": 2,
                "text": "slug: hornbill",
            }
        )
        yield json.dumps(
            {
                "path": str(two),
                "line": 2,
                "text": "slug: condor",
            }
        )

    monkeypatch.setattr(writeback_module, "load_regex", _fake_load_regex)
    monkeypatch.setattr(writeback_module, "rg_search", _fake_rg_search)

    index = writeback_module.build_slug_index(tmp_path / "vault")

    assert calls == [
        (r"slug:\s*[a-z0-9._-]+", (tmp_path / "vault").resolve(), False, False)
    ]
    assert index == {
        "condor": two,
        "hornbill": one,
    }
