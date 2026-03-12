from __future__ import annotations

import io
from pathlib import Path

import pytest

import workbench.write.writeback as writeback_module
from workbench.interop.document import Document
from workbench.lib.regex_registry import RegexPattern
from workbench.write.common import WriteError


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _markdown(*, slug: str, body: str) -> str:
    doc = Document(metadata={"slug": slug, "state": "draft"}, content=body)
    return doc.write_text()


def test_writeback_aborts_on_slug_validation_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "vault" / "passages" / "hornbill.md"
    _write(target, _markdown(slug="hornbill", body="Old"))

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


def test_writeback_routes_to_path_from_slug_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hornbill = tmp_path / "vault" / "passages" / "hornbill.md"
    condor = tmp_path / "vault" / "passages" / "condor.md"
    _write(hornbill, _markdown(slug="hornbill", body="Old hornbill"))
    _write(condor, _markdown(slug="condor", body="Old condor"))

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


def test_build_slug_index_parses_dict_rows_from_rg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = tmp_path / "vault" / "notes" / "hornbill.md"
    two = tmp_path / "vault" / "notes" / "condor.md"
    _write(one, _markdown(slug="hornbill", body="One"))
    _write(two, _markdown(slug="condor", body="Two"))

    calls: list[tuple[str, Path]] = []

    def _fake_load_regex(name: str) -> RegexPattern:
        assert name == "slug_field"
        return RegexPattern(
            name="slug_field",
            pattern=r"slug:\s*[a-z0-9._-]+",
            engine="default",
            ignore_case=False,
        )

    def _fake_rg_search(
        *,
        pattern: str,
        root: Path,
        files=None,
        extensions=None,
        exclude_dirs=None,
    ):
        _ = files, extensions, exclude_dirs
        calls.append((pattern, root))
        yield {
            "path": one,
            "line": 2,
            "text": "slug: hornbill",
            "groups": [],
            "before": [],
            "after": [],
        }
        yield {
            "path": two,
            "line": 2,
            "text": "slug: condor",
            "groups": [],
            "before": [],
            "after": [],
        }

    monkeypatch.setattr(writeback_module, "load_regex", _fake_load_regex)
    monkeypatch.setattr(writeback_module, "rg_search", _fake_rg_search)

    index = writeback_module.build_slug_index(tmp_path / "vault")

    assert calls == [(r"slug:\s*[a-z0-9._-]+", (tmp_path / "vault").resolve())]
    assert index == {
        "condor": two,
        "hornbill": one,
    }
