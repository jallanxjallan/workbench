from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import workbench.cli.main as cli_main
import workbench.runtime.git_repo as git_repo_module
from workbench.runtime.git_commit_message import render_commit_message
from workbench.runtime.git_repo import (
    GitRepoError,
    commit_new_files,
    get_dirty_files,
    get_head_commit,
    get_repo_root,
    is_repo_clean,
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


def _write_templates(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "INIT: \"INIT {batch_slug} files:{file_count}\"\n"
            "STYLE: \"STYLE {batch_slug}\"\n"
        ),
        encoding="utf-8",
    )


def test_detect_repo_root(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    nested = repo / "a" / "b"
    nested.mkdir(parents=True, exist_ok=True)

    assert get_repo_root(nested) == repo.resolve()


def test_retrieve_commit_hash(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    commit = get_head_commit(repo)

    assert len(commit) == 40
    assert int(commit, 16) >= 0
    assert commit == _git(repo, "rev-parse", "HEAD")


def test_detect_dirty_repo(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    assert is_repo_clean(repo) is True

    dirty = repo / "draft.md"
    dirty.write_text("dirty\n", encoding="utf-8")

    assert is_repo_clean(repo) is False
    assert dirty.resolve() in get_dirty_files(repo)


def test_commit_new_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    template_registry = tmp_path / "Control" / "Registry" / "git_commit_messages.yaml"
    _write_templates(template_registry)
    monkeypatch.setattr(
        git_repo_module,
        "DEFAULT_COMMIT_TEMPLATE_REGISTRY",
        template_registry,
    )

    one = repo / "content" / "first.md"
    two = repo / "content" / "second.md"
    one.parent.mkdir(parents=True, exist_ok=True)
    one.write_text("one\n", encoding="utf-8")
    two.write_text("two\n", encoding="utf-8")

    commit_hash = commit_new_files(repo, [one, two], "omaf.first-flight")

    assert commit_hash == _git(repo, "rev-parse", "HEAD")
    assert _git(repo, "log", "-1", "--pretty=%s") == "INIT omaf.first-flight files:2"


def test_render_commit_template() -> None:
    rendered = render_commit_message(
        "INIT {batch_slug} files:{file_count}",
        batch_slug="omaf.first-flight",
        file_count=3,
    )

    assert rendered == "INIT omaf.first-flight files:3"

    with pytest.raises(ValueError, match="missing commit message fields"):
        render_commit_message("STYLE {batch_slug} {mode}", batch_slug="omaf.first-flight")


def test_cli_commit_uses_templates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    template_registry = tmp_path / "Control" / "Registry" / "git_commit_messages.yaml"
    _write_templates(template_registry)
    monkeypatch.setattr(
        git_repo_module,
        "DEFAULT_COMMIT_TEMPLATE_REGISTRY",
        template_registry,
    )
    target = repo / "README.md"
    target.write_text("updated\n", encoding="utf-8")

    rc = cli_main.main(["commit", "STYLE", "omaf.first-flight", "--repo", str(repo)])
    captured = capsys.readouterr()

    assert rc == 0
    assert len(captured.out.strip()) == 40
    assert _git(repo, "log", "-1", "--pretty=%s") == "STYLE omaf.first-flight"


def test_commit_new_files_rejects_missing_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    template_registry = tmp_path / "Control" / "Registry" / "git_commit_messages.yaml"
    _write_templates(template_registry)
    monkeypatch.setattr(
        git_repo_module,
        "DEFAULT_COMMIT_TEMPLATE_REGISTRY",
        template_registry,
    )

    with pytest.raises(GitRepoError, match="file does not exist"):
        commit_new_files(repo, [Path("missing.md")], "omaf.first-flight")
