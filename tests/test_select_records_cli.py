from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import workbench.cli.main as cli_main


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "workbench-tests@example.com")
    _git(repo, "config", "user.name", "Workbench Tests")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "seed")
    return repo


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_select_records_emits_ordered_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    vault = tmp_path / "Studio"
    second = _write(
        vault / "ProjectA" / "drafts" / "chapter-04.md",
        "---\nslug: omaf.chapter-04.b92df\n---\n\nFour\n",
    )
    first = _write(
        vault / "ProjectA" / "drafts" / "chapter-03.md",
        "---\nslug: omaf.chapter-03.a83d1\n---\n\nThree\n",
    )
    third = _write(
        vault / "ProjectA" / "drafts" / "chapter-05.md",
        "---\nslug: omaf.chapter-05.c13ae\n---\n\nFive\n",
    )
    message_file = tmp_path / "batch-message.txt"
    message_file.write_text(
        (
            "compile: 20260314-174322\n\n"
            "files: 3\n\n"
            "order:\n"
            "1 omaf.chapter-03.a83d1\n"
            "2 omaf.chapter-04.b92df\n"
            "3 omaf.chapter-05.c13ae\n"
        ),
        encoding="utf-8",
    )
    _git(repo, "commit", "--allow-empty", "--file", str(message_file))

    rc = cli_main.main(
        [
            "select-records",
            "--repo",
            str(repo),
            "--vault-root",
            str(vault),
        ]
    )
    captured = capsys.readouterr()

    assert rc == 0
    assert captured.err == ""
    assert captured.out.splitlines() == [
        str(first.resolve()),
        str(second.resolve()),
        str(third.resolve()),
    ]


def test_select_records_rejects_invalid_batch_commit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    vault = tmp_path / "Studio"
    _write(
        vault / "ProjectA" / "drafts" / "chapter-03.md",
        "---\nslug: omaf.chapter-03.a83d1\n---\n\nThree\n",
    )
    message_file = tmp_path / "bad-batch-message.txt"
    message_file.write_text(
        (
            "compile: 20260314-1743\n\n"
            "files: 1\n\n"
            "order:\n"
            "1 omaf.chapter-03.a83d1\n"
        ),
        encoding="utf-8",
    )
    _git(repo, "commit", "--allow-empty", "--file", str(message_file))

    rc = cli_main.main(
        [
            "select-records",
            "--repo",
            str(repo),
            "--vault-root",
            str(vault),
        ]
    )
    captured = capsys.readouterr()

    assert rc == 1
    assert captured.out == ""
    assert "invalid batch commit header" in captured.err
