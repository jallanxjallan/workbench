from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from workbench.lib import rg as rg_module
from workbench.lib.rg import RGMatch, RipgrepError


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

    def _fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert args == [
            "rg",
            "--line-number",
            "--no-heading",
            "--color=never",
            "slug:\\s*__SLUG__",
            str(root),
        ]
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    matches = rg_module.rg_search(r"slug:\s*__SLUG__", root)

    assert matches == [
        RGMatch(path=root / "vault" / "one.md", line=12, text="slug: __SLUG__"),
        RGMatch(path=root / "vault" / "two.md", line=7, text="slug: __SLUG__"),
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

    def _fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    matches = rg_module.rg_search("slug:", root)

    assert matches == [RGMatch(path=root / "doc.md", line=4, text="slug: value")]


def test_rg_search_returns_empty_on_no_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "Studio").resolve()
    root.mkdir(parents=True)

    def _fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    assert rg_module.rg_search("slug:", root) == []


def test_rg_search_raises_on_nonsearch_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "Studio").resolve()
    root.mkdir(parents=True)

    def _fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 2, stdout="", stderr="regex parse error")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    with pytest.raises(RipgrepError, match="regex parse error"):
        rg_module.rg_search("[", root)


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
        rg_module.rg_search("slug:", root)
