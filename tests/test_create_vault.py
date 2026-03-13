from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import workbench.cli.create_vault as create_vault_module
from workbench.slug.identity import slug as identity_slug


def _write_file(path: Path, content: str = "{}\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _configure_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path, Path]:
    studio_root = tmp_path / "Studio"
    obsidian_root = studio_root / "obsidian"
    template_root = obsidian_root / "templates"
    common_root = obsidian_root / "common"
    dropbox_assets_root = tmp_path / "Dropbox" / "Assets"

    _write_file(template_root / ".obsidian" / "app.json", content="{}\n")
    _write_file(template_root / ".obsidian" / "hotkeys.json", content="{}\n")
    _write_file(common_root / "templates" / "passage.md", content="# passage\n")
    monkeypatch.setattr(create_vault_module, "STUDIO_ROOT", studio_root)
    monkeypatch.setattr(create_vault_module, "OBSIDIAN_ROOT", obsidian_root)
    monkeypatch.setattr(create_vault_module, "VAULT_TEMPLATE_ROOT", template_root)
    monkeypatch.setattr(create_vault_module, "OBSIDIAN_COMMON_ROOT", common_root)
    monkeypatch.setattr(create_vault_module, "DROPBOX_ASSETS_ROOT", dropbox_assets_root)

    return studio_root, template_root, common_root, dropbox_assets_root


def _read_registry(vault_path: Path) -> dict[str, object]:
    raw = (vault_path / "_vault_registry.json").read_text(encoding="utf-8").strip()
    assert raw
    return json.loads(raw)


def test_create_vault_new_path_creates_registry_template_and_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, _, common_root, dropbox_assets_root = _configure_roots(tmp_path, monkeypatch)

    result = create_vault_module.create_vault("omaf")
    vault_path = studio_root / "omaf"
    vault_mnemonic = identity_slug("omaf")
    assets_target = (dropbox_assets_root / vault_mnemonic).resolve()

    assert result.status == create_vault_module.STATUS_CREATED
    assert result.vault_path == vault_path
    assert result.registry_created is True

    assert (vault_path / "_vault_registry.json").is_file()
    assert (vault_path / ".obsidian").is_dir()
    assert (vault_path / "_common").is_symlink()
    assert (vault_path / "_assets").is_symlink()
    assert os.readlink(vault_path / "_common") == os.path.relpath(
        common_root.resolve(), start=vault_path.resolve()
    )
    assert (vault_path / "_assets").resolve() == assets_target
    assert assets_target.is_dir()

    registry = _read_registry(vault_path)
    assert set(registry.keys()) == {
        "vault_id",
        "created",
        "tool",
        "version",
        "mnemonic",
        "project_mnemonic",
        "assets_symlink_path",
        "assets_target_path",
        "registry_paths",
    }
    assert isinstance(registry["vault_id"], str)
    assert len(registry["vault_id"]) == 26
    assert registry["tool"] == "workbench"
    assert registry["version"] == 1
    assert registry["mnemonic"] == vault_mnemonic
    assert registry["project_mnemonic"] == vault_mnemonic
    assert registry["assets_symlink_path"] == str((vault_path / "_assets").absolute())
    assert registry["assets_target_path"] == str(assets_target)
    assert str(registry["created"]).endswith("Z")
    assert (
        registry["registry_paths"]["assets_symlink"] == registry["assets_symlink_path"]
    )
    assert registry["registry_paths"]["assets_target"] == registry["assets_target_path"]


def test_create_vault_uses_literal_argument_folder_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, _, _, dropbox_assets_root = _configure_roots(tmp_path, monkeypatch)

    result = create_vault_module.create_vault("My Project")
    vault_path = studio_root / "My Project"
    mnemonic = identity_slug("My Project")

    assert result.vault_path == vault_path
    assert vault_path.is_dir()
    assert (vault_path / "_assets").resolve() == (dropbox_assets_root / mnemonic).resolve()
    registry = _read_registry(vault_path)
    assert registry["mnemonic"] == mnemonic


def test_create_vault_existing_folder_preserves_existing_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, _, _, _ = _configure_roots(tmp_path, monkeypatch)

    existing = studio_root / "existing"
    existing.mkdir(parents=True, exist_ok=True)
    _write_file(existing / "file.md", content="existing\n")

    result = create_vault_module.create_vault("existing")

    assert result.status == create_vault_module.STATUS_INITIALIZED
    assert (existing / "file.md").read_text(encoding="utf-8") == "existing\n"
    assert (existing / "_vault_registry.json").is_file()
    assert (existing / ".obsidian").is_dir()
    assert (existing / "_common").is_symlink()
    assert (existing / "_assets").is_symlink()


def test_create_vault_existing_registry_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, _, _, _ = _configure_roots(tmp_path, monkeypatch)

    existing = studio_root / "existing"
    existing.mkdir(parents=True, exist_ok=True)
    _write_file(existing / "note.md", content="keep\n")

    first = create_vault_module.create_vault("existing")
    first_registry = (existing / "_vault_registry.json").read_text(encoding="utf-8")

    second = create_vault_module.create_vault("existing")
    second_registry = (existing / "_vault_registry.json").read_text(encoding="utf-8")

    assert first.status == create_vault_module.STATUS_INITIALIZED
    assert second.status == create_vault_module.STATUS_ALREADY
    assert first_registry == second_registry
    assert (existing / "note.md").read_text(encoding="utf-8") == "keep\n"


def test_create_vault_without_argument_uses_cwd_if_studio_direct_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, _, _, _ = _configure_roots(tmp_path, monkeypatch)
    target = studio_root / "cwd-vault"
    target.mkdir(parents=True, exist_ok=True)

    result = create_vault_module.create_vault(None, cwd=target)

    assert result.vault_path == target
    assert result.status == create_vault_module.STATUS_INITIALIZED
    assert (target / "_vault_registry.json").is_file()


def test_create_vault_without_argument_fails_outside_studio_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, _ = _configure_roots(tmp_path, monkeypatch)
    outside = tmp_path / "outside"
    outside.mkdir(parents=True, exist_ok=True)

    with pytest.raises(
        create_vault_module.CreateVaultError,
        match="vault path is required unless current directory is a direct child of Studio",
    ):
        create_vault_module.create_vault(None, cwd=outside)


def test_create_vault_fails_when_common_path_exists_and_is_not_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, _, _, _ = _configure_roots(tmp_path, monkeypatch)

    existing = studio_root / "existing"
    existing.mkdir(parents=True, exist_ok=True)
    (existing / "_common").mkdir(parents=True, exist_ok=False)

    with pytest.raises(
        create_vault_module.CreateVaultError, match="Unsafe existing _common"
    ):
        create_vault_module.create_vault("existing")


def test_main_prints_status_messages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    studio_root, _, _, _ = _configure_roots(tmp_path, monkeypatch)

    rc_created = create_vault_module.main(["omaf"])
    created_output = capsys.readouterr().out
    assert rc_created == 0
    assert "Created new vault:" in created_output
    assert "omaf" in created_output

    existing = studio_root / "existing"
    existing.mkdir(parents=True, exist_ok=True)
    _write_file(existing / "file.md", "keep\n")

    rc_init = create_vault_module.main(["existing"])
    init_output = capsys.readouterr().out
    assert rc_init == 0
    assert "Initialized existing folder as vault:" in init_output
    assert "existing" in init_output
    assert "Existing files preserved." in init_output

    rc_already = create_vault_module.main(["existing"])
    already_output = capsys.readouterr().out
    assert rc_already == 0
    assert "Vault already initialized:" in already_output
    assert "existing" in already_output
