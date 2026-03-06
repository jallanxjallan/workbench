from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import workbench.cli.main as cli_main
import workbench.cli.scan_sentinel as scan_sentinel_cli
from workbench.lib.sentinel_scan import (
    _scan_with_rg,
    extract_batch_slug,
    extract_batch_slug_from_first_line,
    scan_paths_for_batch_sentinel,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_extract_batch_slug_from_first_line_valid() -> None:
    assert extract_batch_slug_from_first_line("--- ASC BATCH: alpha.beta ---") == "alpha.beta"


def test_extract_batch_slug_from_first_line_malformed_returns_none() -> None:
    assert extract_batch_slug_from_first_line("--- ASC BATCH:    ---") is None


def test_extract_batch_slug_not_at_top_returns_none(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    _write(note, "intro\n--- ASC BATCH: alpha.beta ---\n")
    assert extract_batch_slug(note) is None


def test_scan_paths_for_batch_sentinel_detects_and_ignores(tmp_path: Path) -> None:
    if shutil.which("rg") is None:
        pytest.skip("rg command not available")

    _write(tmp_path / "good.md", "--- ASC BATCH: batch.one ---\nbody\n")
    _write(tmp_path / "missing.md", "body only\n")
    _write(tmp_path / "invalid.md", "--- ASC BATCH:    ---\nbody\n")

    found = scan_paths_for_batch_sentinel(cwd=tmp_path, raw_paths=["."])
    assert found == ["good.md"]


def test_scan_with_rg_parses_only_valid_first_line_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "match",
                    "data": {
                        "path": {"text": "good.md"},
                        "line_number": 1,
                        "lines": {"text": "--- ASC BATCH: batch.one ---\n"},
                    },
                }
            ),
            json.dumps(
                {
                    "type": "match",
                    "data": {
                        "path": {"text": "later.md"},
                        "line_number": 2,
                        "lines": {"text": "--- ASC BATCH: batch.two ---\n"},
                    },
                }
            ),
            json.dumps(
                {
                    "type": "match",
                    "data": {
                        "path": {"text": "invalid.md"},
                        "line_number": 1,
                        "lines": {"text": "--- ASC BATCH:    ---\n"},
                    },
                }
            ),
        ]
    )

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["rg"],
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr("workbench.lib.sentinel_scan.subprocess.run", _fake_run)
    found = _scan_with_rg(cwd=Path.cwd(), query_paths=["."], follow_symlinks=False)
    assert found == ["good.md"]


def test_scan_sentinel_cli_dispatch_outputs_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        scan_sentinel_cli,
        "scan_paths_for_batch_sentinel",
        lambda **kwargs: ["a.md", "b.md"],
    )

    rc = cli_main.main(["scan-sentinel", "."])
    out = capsys.readouterr().out
    rows = [json.loads(line) for line in out.splitlines() if line.strip()]

    assert rc == 0
    assert rows == [{"path": "a.md"}, {"path": "b.md"}]
