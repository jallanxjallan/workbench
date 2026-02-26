from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from workbench.cli import create_vault as module_under_test


def _cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["git"], returncode=returncode, stdout=stdout, stderr=stderr)


def _write_registry(studio_root: Path) -> None:
    (studio_root / "registry.yaml").write_text("vaults: []\nprojects: []\n", encoding="utf-8")


def test_fails_if_git_directory_missing(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir()
    _write_registry(studio_root)

    before = (studio_root / "registry.yaml").read_text(encoding="utf-8")
    try:
        module_under_test.create_vault("RealWriting", studio_root=studio_root)
        assert False, "Expected CreateVaultError"
    except module_under_test.CreateVaultError as exc:
        assert str(exc) == module_under_test.NOT_GIT_ERROR

    assert not (studio_root / "RealWriting").exists()
    assert (studio_root / "registry.yaml").read_text(encoding="utf-8") == before


def test_fails_if_working_tree_dirty(tmp_path: Path, monkeypatch) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir()
    (studio_root / ".git").mkdir()
    _write_registry(studio_root)

    git_calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text):
        git_calls.append(cmd)
        return _cp(stdout=" M instructions/README.md\n")

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)
    before = (studio_root / "registry.yaml").read_text(encoding="utf-8")

    try:
        module_under_test.create_vault("RealWriting", studio_root=studio_root)
        assert False, "Expected CreateVaultError"
    except module_under_test.CreateVaultError as exc:
        assert str(exc) == module_under_test.DIRTY_TREE_ERROR

    assert not (studio_root / "RealWriting").exists()
    assert (studio_root / "registry.yaml").read_text(encoding="utf-8") == before
    assert git_calls == [["git", "-C", str(studio_root), "status", "--porcelain"]]


def test_creates_vault_only_when_clean_and_commits_once(tmp_path: Path, monkeypatch) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir()
    (studio_root / ".git").mkdir()
    _write_registry(studio_root)

    results = [_cp(), _cp(), _cp()]
    git_calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text):
        git_calls.append(cmd)
        return results.pop(0)

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)
    vault_path = module_under_test.create_vault("RealWriting", studio_root=studio_root)

    assert vault_path == studio_root / "RealWriting"
    assert (studio_root / "RealWriting" / "_common").is_dir()
    assert (studio_root / "RealWriting" / "projects").is_dir()

    registry = yaml.safe_load((studio_root / "registry.yaml").read_text(encoding="utf-8"))
    assert registry["vaults"] == [
        {"name": "RealWriting", "path": str((studio_root / "RealWriting").resolve())}
    ]
    assert git_calls == [
        ["git", "-C", str(studio_root), "status", "--porcelain"],
        ["git", "-C", str(studio_root), "add", "registry.yaml", "RealWriting"],
        ["git", "-C", str(studio_root), "commit", "-m", "ADD vault RealWriting"],
    ]
    commit_calls = [call for call in git_calls if "commit" in call]
    assert len(commit_calls) == 1


def test_does_not_mutate_registry_if_preflight_fails(tmp_path: Path, monkeypatch) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir()
    (studio_root / ".git").mkdir()
    _write_registry(studio_root)

    original = (studio_root / "registry.yaml").read_text(encoding="utf-8")

    def fake_run(cmd, capture_output, text):
        return _cp(stdout="?? random.tmp\n")

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    try:
        module_under_test.create_vault("RealWriting", studio_root=studio_root)
        assert False, "Expected CreateVaultError"
    except module_under_test.CreateVaultError:
        pass

    assert (studio_root / "registry.yaml").read_text(encoding="utf-8") == original
