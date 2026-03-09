from __future__ import annotations

from pathlib import Path

import pytest

import workbench.cli.generate_thumbs as generate_thumbs_module
import workbench.cli.main as cli_main


def test_generate_thumbs_main_defaults_to_studio_root(
    monkeypatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    studio_root = (tmp_path / "Studio").resolve()
    called: dict[str, Path] = {}

    def _fake_run(root: Path) -> dict[str, object]:
        called["root"] = root
        return {"matched_files": 0, "affected_files": []}

    monkeypatch.setattr(generate_thumbs_module, "DEFAULT_STUDIO_ROOT", studio_root)
    monkeypatch.setattr(generate_thumbs_module, "_run_generate_thumbnails", _fake_run)

    rc = generate_thumbs_module.main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert called["root"] == studio_root
    assert "no markdown files with eligible image links were found" in out
    assert "affected 0 file(s)" in out


def test_generate_thumbs_main_accepts_optional_path(
    monkeypatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    custom_root = tmp_path / "custom"
    called: dict[str, Path] = {}

    def _fake_run(root: Path) -> dict[str, object]:
        called["root"] = root
        return {"matched_files": 1, "affected_files": [root / "a.md"]}

    monkeypatch.setattr(generate_thumbs_module, "_run_generate_thumbnails", _fake_run)

    rc = generate_thumbs_module.main([str(custom_root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert called["root"] == custom_root.resolve()
    assert "affected 1 file(s)" in out


def test_cli_dispatches_generate_thumbs_command(
    monkeypatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    called: dict[str, Path] = {}

    def _fake_run(root: Path) -> dict[str, object]:
        called["root"] = root
        return {"matched_files": 1, "affected_files": [root / "changed.md"]}

    monkeypatch.setattr(generate_thumbs_module, "_run_generate_thumbnails", _fake_run)

    rc = cli_main.main(["generate-thumbs", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert called["root"] == tmp_path.resolve()
    assert "affected 1 file(s)" in out


def test_generate_thumbs_help_message(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        generate_thumbs_module.main(["--help"])
    out = capsys.readouterr().out

    assert exc.value.code == 0
    assert "usage: generate-thumbs" in out
    assert "Root directory to scan (default: ~/Studio)." in out
