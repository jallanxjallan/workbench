from __future__ import annotations

import io
from pathlib import Path
import shutil

import pytest

from workbench.lib import rg as rg_module
from workbench.lib.rg import RipgrepError, rg_run, rg_search

pytestmark = pytest.mark.skipif(shutil.which("rg") is None, reason="rg not installed")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_rg_search_basic_match_returns_record_contract(tmp_path: Path) -> None:
    root = tmp_path / "Studio"
    target = _write(
        root / "vault" / "doc.md",
        "top line\nneedle line\nbottom line\n",
    )

    matches = list(rg_search(pattern="needle", root=root))

    assert len(matches) == 1
    assert matches[0] == {
        "path": target.resolve(),
        "line": 2,
        "text": "needle line",
        "groups": [],
        "before": ["top line"],
        "after": ["bottom line"],
    }


def test_rg_search_capture_groups_preserved_in_order(tmp_path: Path) -> None:
    root = tmp_path / "Studio"
    _write(
        root / "vault" / "doc.md",
        "wrk:omaf.check-sources\n",
    )

    matches = list(
        rg_search(
            pattern=r"^(wrk):([a-z0-9_-]+)\.([a-z0-9_-]+)",
            root=root,
        )
    )

    assert len(matches) == 1
    assert matches[0]["groups"] == ["wrk", "omaf", "check-sources"]


def test_rg_search_context_always_present(tmp_path: Path) -> None:
    root = tmp_path / "Studio"
    _write(
        root / "vault" / "doc.md",
        "line-1\nline-2\nline-3\nline-4\nline-5\n",
    )

    matches = list(rg_search(pattern=r"line-3", root=root))

    assert len(matches) == 1
    assert matches[0]["before"] == ["line-1", "line-2"]
    assert matches[0]["after"] == ["line-4", "line-5"]


def test_rg_search_candidate_files_only_scans_provided_files(tmp_path: Path) -> None:
    root = tmp_path / "Studio"
    include = _write(root / "vault" / "include.md", "target\n")
    _write(root / "vault" / "exclude.md", "target\n")

    matches = list(rg_search(pattern="target", files=[include]))

    assert len(matches) == 1
    assert matches[0]["path"] == include.resolve()


def test_rg_search_files_mode_raises_on_missing_candidate(tmp_path: Path) -> None:
    missing = tmp_path / "Studio" / "vault" / "missing.md"

    with pytest.raises(RipgrepError, match="candidate file does not exist"):
        list(rg_search(pattern="target", files=[missing]))


def test_rg_search_files_mode_filters_scope_before_invoking_rg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    include = _write(tmp_path / "Studio" / "vault" / "ok.md", "target\n")
    excluded = _write(tmp_path / "Studio" / "_compiled" / "skip.md", "target\n")
    captured: dict[str, list[str]] = {}

    def _fake_rg_run(*, cmd: list[str], pattern: str):
        _ = pattern
        captured["cmd"] = cmd
        yield from ()

    monkeypatch.setattr(rg_module, "rg_run", _fake_rg_run)

    list(rg_search(pattern="target", files=[include, excluded]))

    assert str(include.resolve()) in captured["cmd"]
    assert str(excluded.resolve()) not in captured["cmd"]
    assert "--glob" not in captured["cmd"]


def test_rg_search_applies_default_directory_exclusions(tmp_path: Path) -> None:
    root = tmp_path / "Studio"
    hidden = _write(root / "_compiled" / "hidden.md", "needle\n")
    visible = _write(root / "vault" / "visible.md", "needle\n")

    matches = list(rg_search(pattern="needle", root=root))
    paths = {match["path"] for match in matches}

    assert visible.resolve() in paths
    assert hidden.resolve() not in paths


def test_rg_run_raises_ripgrep_error_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("not-json\n")
            self.stderr = io.StringIO("")
            self._returncode = 0

        def kill(self) -> None:
            return None

        def wait(self) -> int:
            return self._returncode

        def poll(self) -> int:
            return self._returncode

    monkeypatch.setattr(rg_module.subprocess, "Popen", lambda *_args, **_kwargs: _FakeProcess())

    with pytest.raises(RipgrepError, match="invalid ripgrep JSON output"):
        list(rg_run(cmd=["rg", "--json", "needle", "."], pattern="needle"))


def test_rg_run_raises_when_match_arrives_before_begin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    doc = _write(tmp_path / "vault" / "doc.md", "needle\n")
    stream = (
        '{"type":"match","data":{"path":{"text":"%s"},"lines":{"text":"needle\\n"},"line_number":1}}\n'
        '{"type":"summary","data":{"stats":{}}}\n'
    ) % doc

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO(stream)
            self.stderr = io.StringIO("")
            self._returncode = 0

        def kill(self) -> None:
            return None

        def wait(self) -> int:
            return self._returncode

        def poll(self) -> int:
            return self._returncode

    monkeypatch.setattr(
        rg_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _FakeProcess(),
    )

    with pytest.raises(RipgrepError, match="unexpected ripgrep event sequence"):
        list(rg_run(cmd=["rg", "--json", "needle", "."], pattern="needle"))


def test_rg_run_raises_on_incomplete_output_missing_end(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    doc = _write(tmp_path / "vault" / "doc.md", "needle\n")
    stream = (
        '{"type":"begin","data":{"path":{"text":"%s"}}}\n'
        '{"type":"match","data":{"path":{"text":"%s"},"lines":{"text":"needle\\n"},"line_number":1}}\n'
        '{"type":"summary","data":{"stats":{}}}\n'
    ) % (doc, doc)

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO(stream)
            self.stderr = io.StringIO("")
            self._returncode = 0

        def kill(self) -> None:
            return None

        def wait(self) -> int:
            return self._returncode

        def poll(self) -> int:
            return self._returncode

    monkeypatch.setattr(
        rg_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _FakeProcess(),
    )

    with pytest.raises(RipgrepError, match="missing end event"):
        list(rg_run(cmd=["rg", "--json", "needle", "."], pattern="needle"))


def test_rg_run_raises_on_regex_engine_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    doc = _write(tmp_path / "vault" / "doc.md", "bar\n")
    stream = (
        '{"type":"begin","data":{"path":{"text":"%s"}}}\n'
        '{"type":"match","data":{"path":{"text":"%s"},"lines":{"text":"bar\\n"},"line_number":1}}\n'
        '{"type":"end","data":{"path":{"text":"%s"}}}\n'
        '{"type":"summary","data":{"stats":{}}}\n'
    ) % (doc, doc, doc)

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO(stream)
            self.stderr = io.StringIO("")
            self._returncode = 0

        def kill(self) -> None:
            return None

        def wait(self) -> int:
            return self._returncode

        def poll(self) -> int:
            return self._returncode

    monkeypatch.setattr(
        rg_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _FakeProcess(),
    )

    with pytest.raises(RipgrepError, match="regex engine mismatch"):
        list(rg_run(cmd=["rg", "--json", "needle", "."], pattern="needle"))


def test_rg_run_raises_on_non_monotonic_line_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    doc = _write(tmp_path / "vault" / "doc.md", "needle\nother\n")
    stream = (
        '{"type":"begin","data":{"path":{"text":"%s"}}}\n'
        '{"type":"match","data":{"path":{"text":"%s"},"lines":{"text":"needle\\n"},"line_number":10}}\n'
        '{"type":"context","data":{"path":{"text":"%s"},"lines":{"text":"other\\n"},"line_number":5}}\n'
        '{"type":"end","data":{"path":{"text":"%s"}}}\n'
        '{"type":"summary","data":{"stats":{}}}\n'
    ) % (doc, doc, doc, doc)

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO(stream)
            self.stderr = io.StringIO("")
            self._returncode = 0

        def kill(self) -> None:
            return None

        def wait(self) -> int:
            return self._returncode

        def poll(self) -> int:
            return self._returncode

    monkeypatch.setattr(
        rg_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _FakeProcess(),
    )

    with pytest.raises(RipgrepError, match="non-monotonic line order"):
        list(rg_run(cmd=["rg", "--json", "needle", "."], pattern="needle"))
