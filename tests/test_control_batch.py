from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from workbench.control.batch import (
    BatchCommitError,
    build_batch_from_commit_message,
    load_batch_from_git_commit,
    parse_batch_commit_message,
    resolve_slug_file,
)


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


def test_parse_batch_commit_message_accepts_canonical_format() -> None:
    parsed = parse_batch_commit_message(
        (
            "compile: 20260314-174322\n\n"
            "files: 3\n\n"
            "order:\n"
            "1 omaf.chapter-03.a83d1\n"
            "2 omaf.chapter-04.b92df\n"
            "3 omaf.chapter-05.c13ae\n"
        )
    )

    assert parsed.verb == "compile"
    assert parsed.batch_verb == "batch.compile"
    assert parsed.batch_id == "20260314-174322"
    assert parsed.count == 3
    assert parsed.slugs == (
        "omaf.chapter-03.a83d1",
        "omaf.chapter-04.b92df",
        "omaf.chapter-05.c13ae",
    )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "compile: 20260314-1743\n\nfiles: 1\n\norder:\n1 omaf.chapter-03.a83d1\n",
            "invalid batch commit header",
        ),
        (
            "draft: 20260314-174322\n\nfiles: 1\n\norder:\n1 omaf.chapter-03.a83d1\n",
            "invalid batch commit header",
        ),
        (
            "compile: 20260314-174322\nfiles: 1\n\norder:\n1 omaf.chapter-03.a83d1\n",
            "expected blank line after batch header",
        ),
        (
            "compile: 20260314-174322\n\nfiles: 2\n\norder:\n1 omaf.chapter-03.a83d1\n",
            "files count mismatch",
        ),
        (
            "compile: 20260314-174322\n\nfiles: 2\n\norder:\n1 omaf.chapter-03.a83d1\n3 omaf.chapter-04.b92df\n",
            "invalid order index",
        ),
        (
            "compile: 20260314-174322\n\nfiles: 2\n\norder:\n1 omaf.chapter-03.a83d1\n2 omaf.chapter-03.a83d1\n",
            "duplicate batch slug",
        ),
    ],
)
def test_parse_batch_commit_message_rejects_invalid_batches(
    message: str,
    expected: str,
) -> None:
    with pytest.raises(BatchCommitError, match=expected):
        parse_batch_commit_message(message)


def test_resolve_slug_file_requires_exactly_one_match(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    first = _write(
        studio_root / "ProjectA" / "drafts" / "one.md",
        "---\nslug: omaf.chapter-03.a83d1\n---\n\nOne\n",
    )
    _write(
        studio_root / "ProjectA" / "drafts" / "two.md",
        "---\nslug: omaf.chapter-04.b92df\n---\n\nTwo\n",
    )

    assert resolve_slug_file("omaf.chapter-03.a83d1", roots=(studio_root,)) == first.resolve()

    with pytest.raises(BatchCommitError, match="slug not found"):
        resolve_slug_file("omaf.chapter-99.missing", roots=(studio_root,))

    _write(
        studio_root / "ProjectB" / "drafts" / "duplicate.md",
        "---\nslug: omaf.chapter-03.a83d1\n---\n\nDuplicate\n",
    )

    with pytest.raises(BatchCommitError, match="slug resolved to multiple files"):
        resolve_slug_file("omaf.chapter-03.a83d1", roots=(studio_root,))


def test_build_batch_from_commit_message_reconstructs_ordered_files(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    middle = _write(
        studio_root / "Novel" / "drafts" / "chapter-04.md",
        "---\nslug: omaf.chapter-04.b92df\n---\n\nFour\n",
    )
    first = _write(
        studio_root / "Novel" / "drafts" / "chapter-03.md",
        "---\nslug: omaf.chapter-03.a83d1\n---\n\nThree\n",
    )
    last = _write(
        studio_root / "Novel" / "drafts" / "chapter-05.md",
        "---\nslug: omaf.chapter-05.c13ae\n---\n\nFive\n",
    )

    batch = build_batch_from_commit_message(
        (
            "submit: 20260314-174322\n\n"
            "files: 3\n\n"
            "order:\n"
            "1 omaf.chapter-03.a83d1\n"
            "2 omaf.chapter-04.b92df\n"
            "3 omaf.chapter-05.c13ae\n"
        ),
        roots=(studio_root,),
    )

    assert batch.verb == "submit"
    assert batch.batch_verb == "batch.submit"
    assert batch.count == 3
    assert batch.files == (first.resolve(), middle.resolve(), last.resolve())
    assert batch.as_dict()["files"] == [
        str(first.resolve()),
        str(middle.resolve()),
        str(last.resolve()),
    ]


def test_load_batch_from_git_commit_reads_commit_protocol(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    studio_root = tmp_path / "Studio"
    first = _write(
        studio_root / "ProjectA" / "drafts" / "one.md",
        "---\nslug: omaf.chapter-03.a83d1\n---\n\nOne\n",
    )
    second = _write(
        studio_root / "ProjectA" / "drafts" / "two.md",
        "---\nslug: omaf.chapter-04.b92df\n---\n\nTwo\n",
    )
    message_file = tmp_path / "batch-message.txt"
    message_file.write_text(
        (
            "ost: 20260314-174322\n\n"
            "files: 2\n\n"
            "order:\n"
            "1 omaf.chapter-04.b92df\n"
            "2 omaf.chapter-03.a83d1\n"
        ),
        encoding="utf-8",
    )

    _git(repo, "commit", "--allow-empty", "--file", str(message_file))

    batch = load_batch_from_git_commit(repo, roots=(studio_root,))

    assert batch.verb == "ost"
    assert batch.batch_id == "20260314-174322"
    assert batch.files == (second.resolve(), first.resolve())
