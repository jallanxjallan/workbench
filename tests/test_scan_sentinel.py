from __future__ import annotations

import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from workbench.cli import scan_sentinel as scan_sentinel_cli
from workbench.lib import sentinel_scan
from workbench.lib.sentinel_scan import (
    extract_batch_slug_from_first_line,
    scan_paths_for_batch_sentinel,
)

RG_MISSING = shutil.which("rg") is None


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.skipif(RG_MISSING, reason="rg is required")
def test_cli_smoke_outputs_ndjson_rows(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        tmp_path / "notes" / "alpha.md",
        "--- ASC BATCH: test.slug ---\n# Title\n",
    )
    _write(tmp_path / "notes" / "beta.md", "# No sentinel\n")
    monkeypatch.setattr(scan_sentinel_cli, "STUDIO_ROOT", tmp_path)

    rc = scan_sentinel_cli.main(["."])

    assert rc == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    rows = [json.loads(line) for line in lines]
    assert rows == [{"path": "notes/alpha.md"}]


@pytest.mark.skipif(RG_MISSING, reason="rg is required")
def test_scan_ignores_non_sentinel_and_non_top_line_matches(tmp_path: Path) -> None:
    _write(tmp_path / "good.md", "--- ASC BATCH: ok.slug ---\nBody\n")
    _write(tmp_path / "none.md", "# Heading\n")
    _write(tmp_path / "not_top.md", "# Heading\n--- ASC BATCH: late.slug ---\n")
    _write(tmp_path / "broken.md", "--- ASC BATCH: broken.slug --\n")

    rows = scan_paths_for_batch_sentinel(root=tmp_path, raw_paths=["."])

    assert rows == ["good.md"]


@pytest.mark.skipif(RG_MISSING, reason="rg is required")
def test_scan_recurses_nested_directories(tmp_path: Path) -> None:
    _write(
        tmp_path / "nested" / "deep" / "doc.md",
        "--- ASC BATCH: nested.slug ---\nContent\n",
    )

    rows = scan_paths_for_batch_sentinel(root=tmp_path, raw_paths=["nested"])

    assert rows == ["nested/deep/doc.md"]


def test_scan_normalizes_match_paths_with_backslashes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stdout = json.dumps(
        {
            "type": "match",
            "data": {
                "line_number": 1,
                "path": {"text": ".\\nested\\doc.md"},
                "lines": {"text": "--- ASC BATCH: slug.value ---\n"},
            },
        }
    )

    def _fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(sentinel_scan.subprocess, "run", _fake_run)

    rows = sentinel_scan._scan_with_rg(root=tmp_path, query_paths=["."], follow_symlinks=False)

    assert rows == ["nested/doc.md"]


def test_extract_batch_slug_from_first_line_rejects_malformed() -> None:
    assert extract_batch_slug_from_first_line("--- ASC BATCH: valid.slug ---") == "valid.slug"
    assert extract_batch_slug_from_first_line("--- ASC BATCH valid.slug ---") is None
    assert extract_batch_slug_from_first_line("--- ASC BATCH: valid.slug --") is None
    assert extract_batch_slug_from_first_line("not a sentinel") is None
