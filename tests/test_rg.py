from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from workbench.lib import rg as rg_module
from workbench.lib.rg import RipgrepError


def test_rg_search_executes_and_parses_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "Studio").resolve()
    root.mkdir(parents=True)
    stdout = "\n".join(
        [
            f"{root / 'vault' / 'one.md'}:12:slug: __SLUG__",
            f"{root / 'vault' / 'two.md'}:7:slug: __SLUG__",
        ]
    )

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [
            "rg",
            "--line-number",
            "--with-filename",
            "--absolute",
            "--color=never",
            "--no-follow",
            "slug:\\s*__SLUG__",
            str(root),
        ]
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    matches = [json.loads(line) for line in rg_module.rg_search(r"slug:\s*__SLUG__", root)]

    assert matches == [
        {"path": str(root / "vault" / "one.md"), "line": 12, "text": "slug: __SLUG__"},
        {"path": str(root / "vault" / "two.md"), "line": 7, "text": "slug: __SLUG__"},
    ]


def test_rg_search_ignores_malformed_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "Studio").resolve()
    root.mkdir(parents=True)
    stdout = "\n".join(
        [
            "bad line",
            f"{root / 'doc.md'}:4:slug: value",
            "also:bad",
        ]
    )

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    matches = [json.loads(line) for line in rg_module.rg_search("slug:", root)]

    assert matches == [
        {"path": str(root / "doc.md"), "line": 4, "text": "slug: value"},
    ]


def test_rg_search_returns_empty_on_no_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "Studio").resolve()
    root.mkdir(parents=True)

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    assert list(rg_module.rg_search("slug:", root)) == []


def test_rg_search_raises_on_nonsearch_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "Studio").resolve()
    root.mkdir(parents=True)

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 2, stdout="", stderr="regex parse error")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    with pytest.raises(RipgrepError, match="regex parse error"):
        list(rg_module.rg_search("[", root))


def test_rg_search_raises_when_rg_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "Studio").resolve()
    root.mkdir(parents=True)

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    with pytest.raises(RipgrepError, match="ripgrep \\(rg\\) not installed"):
        list(rg_module.rg_search("slug:", root))


def test_rg_search_supports_option_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "Studio").resolve()
    root.mkdir(parents=True)

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [
            "rg",
            "--line-number",
            "--with-filename",
            "--absolute",
            "--color=never",
            "-i",
            "--fixed-strings",
            "--pcre2",
            "--multiline",
            "--follow",
            "--glob",
            "*.md",
            "--glob",
            "*.markdown",
            "--glob",
            "!_common/*",
            "--glob",
            "!.obsidian/*",
            "slug:",
            str(root),
        ]
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    list(
        rg_module.rg_search(
            "slug:",
            root,
            ignore_case=True,
            fixed_strings=True,
            pcre2=True,
            multiline=True,
            follow_symlinks=True,
            extensions=(".md", ".markdown"),
            exclude_dirs=("_common", ".obsidian"),
        )
    )
