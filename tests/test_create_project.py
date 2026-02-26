from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from workbench.project.create import main as create_project_main


def _run_git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _prepare_home(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    studio = home / "Studio"
    studio.mkdir(parents=True, exist_ok=True)
    _run_git(studio, ["init"])
    monkeypatch.setenv("HOME", str(home))
    return home, studio


def _commit_all(repo: Path, message: str) -> None:
    _run_git(repo, ["add", "-A"])
    _run_git(
        repo,
        [
            "-c",
            "user.name=Workbench",
            "-c",
            "user.email=workbench@example.invalid",
            "commit",
            "-m",
            message,
        ],
    )


def _create(vault: str, title: str) -> int:
    return create_project_main(["--vault", vault, "--project", title])


def test_create_project_success(tmp_path: Path, monkeypatch, capsys) -> None:
    home, studio = _prepare_home(monkeypatch, tmp_path)

    exit_code = _create("RealRiting", "One Man Air Force")
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Project created:" in captured.out
    assert "Mnemonic: omaf" in captured.out
    assert "Studio commit created:" in captured.out

    vault_root = studio / "RealRiting"
    project_root = vault_root / "One Man Air Force"
    registry_path = studio / "project_registry.yaml"
    assets_root = home / "Dropbox" / "Assets" / "omaf"
    instructions_root = studio / "instructions" / "omaf"

    assert (vault_root / "_common").is_dir()
    assert project_root.is_dir()
    assert not (project_root / "_common").exists()
    assert (project_root / "01-drafts").is_dir()
    assert (project_root / "02-reference").is_dir()
    assert (project_root / "03-output").is_dir()
    assert assets_root.is_dir()
    assert instructions_root.is_dir()

    assets_link = project_root / "assets"
    instructions_link = project_root / "instructions"
    assert assets_link.is_symlink()
    assert instructions_link.is_symlink()
    assert assets_link.resolve() == assets_root.resolve()
    assert instructions_link.resolve() == instructions_root.resolve()

    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    entry = registry["omaf"]
    assert entry["title"] == "One Man Air Force"
    assert entry["vault"] == "RealRiting"
    assert entry["project_root"] == str(project_root.resolve())
    assert entry["assets_root"] == str(assets_root.resolve())
    assert entry["instructions_root"] == str(instructions_root.resolve())
    assert entry["created_at"].endswith("Z")

    commit_message = _run_git(studio, ["log", "-1", "--pretty=format:%B"])
    assert (
        commit_message.strip()
        == "PROJECT create: omaf — One Man Air Force in RealRiting\n\n"
        "- mnemonic auto-derived\n"
        "- registry entry added\n"
        "- vault structure created\n"
        "- assets linked\n"
        "- instructions linked"
    )


def test_create_project_rejects_duplicate_title(tmp_path: Path, monkeypatch, capsys) -> None:
    _, studio = _prepare_home(monkeypatch, tmp_path)
    existing_root = studio / "RealRiting" / "Batavia Triptych"
    existing_root.mkdir(parents=True, exist_ok=True)
    (existing_root / "seed.txt").write_text("existing\n", encoding="utf-8")
    _commit_all(studio, "seed existing title folder")

    exit_code = _create("RealRiting", "Batavia Triptych")
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "project title folder already exists" in captured.err


def test_create_project_rejects_duplicate_mnemonic_in_same_vault(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _prepare_home(monkeypatch, tmp_path)

    first_exit = _create("RealRiting", "One Man Air Force")
    capsys.readouterr()
    second_exit = _create("RealRiting", "Orca Media Arts Festival")
    captured = capsys.readouterr()

    assert first_exit == 0
    assert second_exit == 1
    assert "project mnemonic already exists in vault 'RealRiting': omaf" in captured.err


def test_create_project_rejects_cross_vault_mnemonic_collision(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _prepare_home(monkeypatch, tmp_path)

    first_exit = _create("RealRiting", "One Man Air Force")
    capsys.readouterr()
    second_exit = _create("HackWork", "Orca Media Arts Festival")
    captured = capsys.readouterr()

    assert first_exit == 0
    assert second_exit == 1
    assert "project mnemonic collision for 'omaf'" in captured.err
    assert "global uniqueness enforced" in captured.err


def test_create_project_rejects_invalid_vault_name(capsys) -> None:
    exit_code = _create("NotAVault", "One Man Air Force")
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "invalid vault_name 'NotAVault'" in captured.err


def test_create_project_rejects_invalid_project_name(capsys) -> None:
    exit_code = _create("RealRiting", "   ")
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "invalid project name" in captured.err


def test_create_project_aborts_when_studio_tree_is_dirty(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _, studio = _prepare_home(monkeypatch, tmp_path)
    (studio / "unrelated.txt").write_text("dirty\n", encoding="utf-8")

    exit_code = _create("HackWork", "Client Beta")
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Studio git working tree is dirty for unrelated files" in captured.err
    assert not (studio / "HackWork" / "Client Beta").exists()


def test_create_project_detects_broken_symlink(tmp_path: Path, monkeypatch, capsys) -> None:
    home, studio = _prepare_home(monkeypatch, tmp_path)
    project_root = studio / "RealRiting" / "Broken Link Project"
    wrong_target = home / "Dropbox" / "Assets" / "wrong-target"
    wrong_target.mkdir(parents=True, exist_ok=True)
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "assets").symlink_to(wrong_target)
    _commit_all(studio, "seed malformed project")

    exit_code = _create("RealRiting", "Broken Link Project")
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "symlink target mismatch" in captured.err
