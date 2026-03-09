from __future__ import annotations

import builtins
from pathlib import Path
import shutil

import pytest

import workbench.cli.find_duplicates as find_duplicates_cli
import workbench.cli.main as cli_main


def _fixture_root() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata_duplicates"


def _copy_fixture(tmp_path: Path) -> Path:
    destination = tmp_path / "data"
    shutil.copytree(_fixture_root(), destination)
    return destination


def test_dry_run_detects_duplicates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _copy_fixture(tmp_path)

    rc = cli_main.main(["find-duplicates", "--root", str(root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Found 1 duplicate group" in out
    assert "./a/file1.txt" in out
    assert "./b/file1.txt" in out
    assert "./c/file1_copy.txt" in out


def test_prune_deletes_only_duplicates_with_yes_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _copy_fixture(tmp_path)

    rc = find_duplicates_cli.main(["--root", str(root), "--prune", "--yes"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Removed 2 duplicate files" in out
    assert (root / "a" / "file1.txt").exists()
    assert not (root / "b" / "file1.txt").exists()
    assert not (root / "c" / "file1_copy.txt").exists()
    assert (root / "d" / "file2.txt").exists()


def test_prune_confirmation_prompt_aborts_without_yes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    asked: dict[str, str] = {}

    def _fake_input(prompt: str) -> str:
        asked["prompt"] = prompt
        return "n"

    monkeypatch.setattr(builtins, "input", _fake_input)

    rc = find_duplicates_cli.main(["--root", str(root), "--prune"])
    out = capsys.readouterr().out

    assert rc == 0
    assert asked["prompt"] == "Proceed? [y/N] "
    assert "Aborted; no files removed." in out
    assert (root / "a" / "file1.txt").exists()
    assert (root / "b" / "file1.txt").exists()
    assert (root / "c" / "file1_copy.txt").exists()


def test_yes_bypasses_confirmation_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    called = {"value": False}

    def _input_must_not_be_called(prompt: str) -> str:
        called["value"] = True
        raise AssertionError(f"input() should not be called: {prompt}")

    monkeypatch.setattr(builtins, "input", _input_must_not_be_called)

    rc = find_duplicates_cli.main(["--root", str(root), "--prune", "--yes"])

    assert rc == 0
    assert called["value"] is False
