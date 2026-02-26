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


def test_create_project_success(tmp_path: Path, monkeypatch, capsys) -> None:
    home, studio = _prepare_home(monkeypatch, tmp_path)

    exit_code = create_project_main(["RealRiting", "omaf"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Project created:" in captured.out
    assert "Studio commit created:" in captured.out

    vault_root = studio / "RealRiting"
    project_root = vault_root / "omaf"
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
    assert entry["vault"] == "RealRiting"
    assert entry["project_root"] == str(project_root.resolve())
    assert entry["assets_root"] == str(assets_root.resolve())
    assert entry["instructions_root"] == str(instructions_root.resolve())
    assert entry["created_at"].endswith("Z")

    commit_message = _run_git(studio, ["log", "-1", "--pretty=format:%B"])
    assert (
        commit_message.strip()
        == "PROJECT create: omaf in RealRiting\n\n"
        "- registry entry added\n"
        "- vault structure created\n"
        "- assets linked\n"
        "- instructions linked"
    )


def test_create_project_rejects_duplicate_mnemonic(tmp_path: Path, monkeypatch, capsys) -> None:
    _, studio = _prepare_home(monkeypatch, tmp_path)
    registry_path = studio / "project_registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "omaf": {
                    "vault": "RealRiting",
                    "project_root": str((studio / "RealRiting" / "omaf").resolve()),
                    "assets_root": str((studio.parent / "Dropbox" / "Assets" / "omaf").resolve()),
                    "instructions_root": str((studio / "instructions" / "omaf").resolve()),
                    "created_at": "2026-01-01T00:00:00Z",
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    _commit_all(studio, "seed registry")

    exit_code = create_project_main(["RealRiting", "omaf"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "project mnemonic already exists in registry: omaf" in captured.err


def test_create_project_rejects_invalid_vault_name(capsys) -> None:
    exit_code = create_project_main(["NotAVault", "omaf"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "invalid vault_name 'NotAVault'" in captured.err


def test_create_project_rejects_invalid_mnemonic(capsys) -> None:
    exit_code = create_project_main(["RealRiting", "Bad-Name"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "invalid project_mnemonic 'Bad-Name'" in captured.err


def test_create_project_rerun_fails_cleanly(tmp_path: Path, monkeypatch, capsys) -> None:
    _, studio = _prepare_home(monkeypatch, tmp_path)

    first_exit = create_project_main(["HackWork", "client_alpha"])
    capsys.readouterr()
    second_exit = create_project_main(["HackWork", "client_alpha"])
    captured = capsys.readouterr()

    assert first_exit == 0
    assert second_exit == 1
    assert "project mnemonic already exists in registry: client_alpha" in captured.err
    assert _run_git(studio, ["rev-list", "--count", "HEAD"]).strip() == "1"


def test_create_project_detects_broken_symlink(tmp_path: Path, monkeypatch, capsys) -> None:
    home, studio = _prepare_home(monkeypatch, tmp_path)
    project_root = studio / "RealRiting" / "broken_link_project"
    wrong_target = home / "Dropbox" / "Assets" / "wrong-target"
    wrong_target.mkdir(parents=True, exist_ok=True)
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "assets").symlink_to(wrong_target)
    _commit_all(studio, "seed malformed project")

    exit_code = create_project_main(["RealRiting", "broken_link_project"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "symlink target mismatch" in captured.err


def test_create_project_creates_common_once_per_vault(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _, studio = _prepare_home(monkeypatch, tmp_path)

    first_exit = create_project_main(["RealRiting", "alpha"])
    capsys.readouterr()
    second_exit = create_project_main(["RealRiting", "beta"])
    capsys.readouterr()

    assert first_exit == 0
    assert second_exit == 0

    vault_root = studio / "RealRiting"
    assert (vault_root / "_common").is_dir()
    assert len(list(vault_root.glob("_common"))) == 1
    assert not (vault_root / "alpha" / "_common").exists()
    assert not (vault_root / "beta" / "_common").exists()


def test_create_project_aborts_when_studio_tree_is_dirty(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _, studio = _prepare_home(monkeypatch, tmp_path)
    (studio / "unrelated.txt").write_text("dirty\n", encoding="utf-8")

    exit_code = create_project_main(["HackWork", "client_beta"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Studio git working tree is dirty for unrelated files" in captured.err
    assert not (studio / "HackWork" / "client_beta").exists()
