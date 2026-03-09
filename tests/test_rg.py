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
        assert args[:4] == ["rg", "--json", "--pcre2", "--multiline"]
        assert "--glob" in args
        assert "*.md" in args
        assert "*.markdown" in args
        assert args[-1] == str(studio_root.resolve())
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


def test_rg_search_supports_include_exclude_and_match_filtering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True)
    stdout = "\n".join(
        [
            json.dumps({"type": "begin", "data": {"path": {"text": str(studio_root / "note.md")}}}),
            _match_event(studio_root / "note.md", "slug: alpha.slug\n"),
        ]
    )

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [
            "rg",
            "--json",
            "--pcre2",
            "--glob",
            "*.md",
            "--glob",
            "!**/_archive/**",
            "slug",
            str(studio_root.resolve()),
        ]
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    events = rg_module.rg_search(
        "slug",
        root=studio_root,
        include=["*.md"],
        exclude=["**/_archive/**"],
    )

    assert len(events) == 1
    assert events[0]["type"] == "match"


def test_find_markdown_images_uses_thumb_excluding_pattern(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True)
    note_path = studio_root / "note.md"
    stdout = _match_event(note_path, "![alt](images/photo.jpg)\n")

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [
            "rg",
            "--json",
            "--pcre2",
            "--glob",
            "*.md",
            rg_module.IMAGE_PATTERN,
            str(studio_root.resolve()),
        ]
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    results = rg_module.find_markdown_images(root=studio_root)

    assert results == [
        {
            "file": note_path.resolve(),
            "line": "![alt](images/photo.jpg)\n",
        }
    ]


def test_ensure_pcre2_available_raises_without_feature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == ["rg", "--version"]
        return subprocess.CompletedProcess(args, 0, stdout="ripgrep 13.0.0\nfeatures:-simd\n", stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    with pytest.raises(
        RipgrepError,
        match="PCRE2 is not available in this build of ripgrep",
    ):
        rg_module._ensure_pcre2_available()


def test_find_files_with_slug_uses_frontmatter_pattern(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True)
    note_path = studio_root / "vault" / "note.md"
    stdout = _match_event(note_path, "slug: omaf.passage.note\n")

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args[:4] == ["rg", "--json", "--pcre2", "--multiline"]
        pattern = args[-2]
        assert "slug:" in pattern
        assert "omaf\\.passage\\.note" in pattern
        assert args[-1] == str(studio_root.resolve())
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    files = rg_module.find_files_with_slug("omaf.passage.note", root=studio_root)

    assert files == [note_path.resolve()]


def test_find_markdown_slugs_can_include_placeholders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True)
    note_path = studio_root / "note.md"
    stdout = _match_event(note_path, "slug: __SLUG__\n")

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pattern = args[-2]
        assert "(?!(?i:__slug__|null|~)\\s*$)" not in pattern
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    rows = rg_module.find_markdown_slugs(
        root=studio_root,
        canonical_only=False,
        exclude_placeholders=False,
    )

    assert rows == [{"file": note_path.resolve(), "slug": "__SLUG__"}]


def test_find_slug_sentinels_uses_single_rg_list_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True)
    one = studio_root / "vault" / "one.md"
    two = studio_root / "vault" / "two.markdown"
    not_markdown = studio_root / "vault" / "three.txt"
    stdout = "\n".join([str(one), str(two), str(not_markdown)])

    calls = {"count": 0}

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls["count"] += 1
        assert args == [
            "rg",
            "-l",
            "--pcre2",
            "--glob",
            "*.md",
            "--glob",
            "*.markdown",
            r"^slug:\s*__SLUG__",
            str(studio_root.resolve()),
        ]
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(rg_module.subprocess, "run", _fake_run)

    paths = rg_module.find_slug_sentinels(studio_root)

    assert calls["count"] == 1
    assert paths == [one.resolve(), two.resolve()]
