from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from workbench.lib import rg as rg_module
from workbench.lib.rg import RipgrepError


def _match_event(path: Path, line: str) -> str:
    return json.dumps(
        {
            "type": "match",
            "data": {
                "path": {"text": str(path)},
                "lines": {"text": line},
            },
        }
    )


def test_build_slug_index_detects_markdown_slugs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True)
    alpha = studio_root / "vault" / "alpha.md"
    beta = studio_root / "vault" / "beta.md"
    stdout = "\n".join(
        [
            _match_event(alpha, "slug: alpha.slug\n"),
            _match_event(beta, "slug: beta.slug\n"),
        ]
    )

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [
            "rg",
            "--json",
            "--pcre2",
            "--glob",
            "*.md",
            r"^slug:\s*(\S+)",
            str(studio_root.resolve()),
        ]
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    index = rg_module.build_slug_index(studio_root)

    assert index == {
        "alpha.slug": alpha.resolve(),
        "beta.slug": beta.resolve(),
    }


def test_build_slug_index_raises_on_duplicate_slug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True)
    one = studio_root / "vault-a" / "one.md"
    two = studio_root / "vault-b" / "two.md"
    stdout = "\n".join(
        [
            _match_event(one, "slug: shared.slug\n"),
            _match_event(two, "slug: shared.slug\n"),
        ]
    )

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    with pytest.raises(RipgrepError, match="duplicate slug detected"):
        rg_module.build_slug_index(studio_root)


def test_build_slug_index_ignores_non_markdown_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True)
    markdown = studio_root / "vault" / "entry.md"
    text = studio_root / "vault" / "note.txt"
    stdout = "\n".join(
        [
            _match_event(markdown, "slug: md.slug\n"),
            _match_event(text, "slug: txt.slug\n"),
        ]
    )

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    index = rg_module.build_slug_index(studio_root)

    assert "md.slug" in index
    assert "txt.slug" not in index
