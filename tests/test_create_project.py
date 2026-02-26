from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from workbench.project import create as module_under_test


def _cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["git"], returncode=returncode, stdout=stdout, stderr=stderr)


def _make_studio(tmp_path: Path) -> tuple[Path, Path, Path]:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir()
    (studio_root / ".git").mkdir()
    vault_path = studio_root / "RealWriting"
    (vault_path / "projects").mkdir(parents=True)
    return studio_root, vault_path, studio_root / "registry.yaml"


def _write_registry(
    registry_path: Path,
    vault_path: Path,
    *,
    projects: list[dict[str, str]] | None = None,
) -> None:
    payload = {
        "vaults": [
            {
                "id": "realwriting",
                "name": "RealWriting",
                "path": str(vault_path),
            }
        ],
        "projects": projects or [],
    }
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_fails_if_studio_root_missing(tmp_path: Path) -> None:
    missing_root = tmp_path / "MissingStudio"

    try:
        module_under_test.create_project("realwriting", "One Man Air Force", studio_root=missing_root)
        assert False, "Expected CreateProjectError"
    except module_under_test.CreateProjectError as exc:
        assert "Studio root does not exist" in str(exc)


def test_fails_if_registry_missing(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir()
    (studio_root / ".git").mkdir()

    try:
        module_under_test.create_project("realwriting", "One Man Air Force", studio_root=studio_root)
        assert False, "Expected CreateProjectError"
    except module_under_test.CreateProjectError as exc:
        assert "registry.yaml is required" in str(exc)


def test_fails_if_git_missing(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir()
    vault_path = studio_root / "RealWriting"
    (vault_path / "projects").mkdir(parents=True)
    registry_path = studio_root / "registry.yaml"
    _write_registry(registry_path, vault_path)

    try:
        module_under_test.create_project("realwriting", "One Man Air Force", studio_root=studio_root)
        assert False, "Expected CreateProjectError"
    except module_under_test.CreateProjectError as exc:
        assert str(exc) == module_under_test.NOT_GIT_ERROR


def test_fails_if_working_tree_dirty(tmp_path: Path, monkeypatch) -> None:
    studio_root, vault_path, registry_path = _make_studio(tmp_path)
    _write_registry(registry_path, vault_path)

    def fake_run(cmd, capture_output, text):
        return _cp(stdout=" M README.md\n")

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)
    before = registry_path.read_text(encoding="utf-8")

    try:
        module_under_test.create_project("realwriting", "One Man Air Force", studio_root=studio_root)
        assert False, "Expected CreateProjectError"
    except module_under_test.CreateProjectError as exc:
        assert str(exc) == module_under_test.DIRTY_TREE_ERROR

    assert not (vault_path / "projects" / "One Man Air Force").exists()
    assert registry_path.read_text(encoding="utf-8") == before


def test_fails_if_vault_id_not_found(tmp_path: Path, monkeypatch) -> None:
    studio_root, vault_path, registry_path = _make_studio(tmp_path)
    _write_registry(registry_path, vault_path)

    def fake_run(cmd, capture_output, text):
        return _cp()

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    try:
        module_under_test.create_project("hackwork", "One Man Air Force", studio_root=studio_root)
        assert False, "Expected CreateProjectError"
    except module_under_test.CreateProjectError as exc:
        assert "Vault not found in registry" in str(exc)


def test_creates_project_directory_correctly(tmp_path: Path, monkeypatch) -> None:
    studio_root, vault_path, registry_path = _make_studio(tmp_path)
    _write_registry(registry_path, vault_path)

    calls: list[list[str]] = []
    responses = [_cp(), _cp(), _cp()]

    def fake_run(cmd, capture_output, text):
        calls.append(cmd)
        return responses.pop(0)

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    result = module_under_test.create_project(
        "realwriting",
        "One Man Air Force",
        studio_root=studio_root,
    )

    project_path = vault_path / "projects" / "One Man Air Force"
    assert project_path.is_dir()
    assert result.project_path == project_path
    assert calls[0] == ["git", "-C", str(studio_root), "status", "--porcelain"]


def test_generates_correct_mnemonic(tmp_path: Path, monkeypatch) -> None:
    studio_root, vault_path, registry_path = _make_studio(tmp_path)
    _write_registry(registry_path, vault_path)

    responses = [_cp(), _cp(), _cp()]

    def fake_run(cmd, capture_output, text):
        return responses.pop(0)

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    result = module_under_test.create_project(
        "realwriting",
        "One Man Air Force",
        studio_root=studio_root,
    )

    assert result.mnemonic == "omaf"


def test_handles_mnemonic_collision_deterministically(tmp_path: Path, monkeypatch) -> None:
    studio_root, vault_path, registry_path = _make_studio(tmp_path)
    _write_registry(
        registry_path,
        vault_path,
        projects=[
            {"mnemonic": "omaf", "name": "Old A", "vault": "realwriting"},
            {"mnemonic": "omaf2", "name": "Old B", "vault": "realwriting"},
        ],
    )

    responses = [_cp(), _cp(), _cp()]

    def fake_run(cmd, capture_output, text):
        return responses.pop(0)

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    result = module_under_test.create_project(
        "realwriting",
        "Orca Media Arts Festival",
        studio_root=studio_root,
    )

    assert result.mnemonic == "omaf3"


def test_updates_registry_correctly(tmp_path: Path, monkeypatch) -> None:
    studio_root, vault_path, registry_path = _make_studio(tmp_path)
    existing_project = {"mnemonic": "abc", "name": "Alpha Beta", "vault": "realwriting"}
    _write_registry(registry_path, vault_path, projects=[existing_project])

    responses = [_cp(), _cp(), _cp()]

    def fake_run(cmd, capture_output, text):
        return responses.pop(0)

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    module_under_test.create_project(
        "realwriting",
        "One Man Air Force",
        studio_root=studio_root,
    )

    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    assert payload["projects"][0] == existing_project
    assert payload["projects"][1] == {
        "mnemonic": "omaf",
        "name": "One Man Air Force",
        "vault": "realwriting",
    }


def test_produces_exactly_one_commit(tmp_path: Path, monkeypatch) -> None:
    studio_root, vault_path, registry_path = _make_studio(tmp_path)
    _write_registry(registry_path, vault_path)

    calls: list[list[str]] = []
    responses = [_cp(), _cp(), _cp()]

    def fake_run(cmd, capture_output, text):
        calls.append(cmd)
        return responses.pop(0)

    monkeypatch.setattr(module_under_test.subprocess, "run", fake_run)

    module_under_test.create_project(
        "realwriting",
        "One Man Air Force",
        studio_root=studio_root,
    )

    commit_calls = [call for call in calls if "commit" in call]
    assert len(commit_calls) == 1
