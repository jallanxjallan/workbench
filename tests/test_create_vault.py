from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import workbench.cli.create_vault as create_vault_module


def _write_file(path: Path, content: str = "{}\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _configure_canonical_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    create_dropbox: bool = True,
) -> tuple[Path, Path, Path, Path]:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True, exist_ok=True)

    workbench_root = tmp_path / "Workbench"
    template_root = workbench_root / "assets" / "vault_template"
    common_root = workbench_root / "assets" / "obsidian_common"
    plugins_root = template_root / ".obsidian" / "plugins"

    for plugin_name in create_vault_module.REQUIRED_PLUGINS:
        plugin_dir = plugins_root / plugin_name
        plugin_dir.mkdir(parents=True, exist_ok=True)
        _write_file(plugin_dir / "main.js", content=f"// {plugin_name}\n")

    _write_file(template_root / ".obsidian" / "community-plugins.json", content="[]\n")
    _write_file(template_root / ".obsidian" / "core-plugins.json", content="[]\n")
    _write_file(template_root / ".obsidian" / "app.json")
    _write_file(template_root / ".obsidian" / "hotkeys.json")
    _write_file(common_root / "templates" / "passage.md")

    dropbox_assets_root = tmp_path / "Dropbox" / "Assets"
    if create_dropbox:
        dropbox_assets_root.mkdir(parents=True, exist_ok=True)

    obsidian_manager = tmp_path / ".config" / "obsidian" / "obsidian.json"
    _write_file(obsidian_manager, content='{"vaults":{},"openSchemes":{}}\n')

    monkeypatch.setattr(create_vault_module, "STUDIO_ROOT", studio_root)
    monkeypatch.setattr(create_vault_module, "WORKBENCH_ROOT", workbench_root)
    monkeypatch.setattr(create_vault_module, "VAULT_TEMPLATE_ROOT", template_root)
    monkeypatch.setattr(create_vault_module, "OBSIDIAN_COMMON_ROOT", common_root)
    monkeypatch.setattr(create_vault_module, "DROPBOX_ASSET_ROOT", dropbox_assets_root)
    monkeypatch.setattr(
        create_vault_module,
        "OBSIDIAN_MANAGER_CANDIDATES",
        (obsidian_manager,),
    )

    return studio_root, template_root, workbench_root, dropbox_assets_root


def test_derive_mnemonic_examples() -> None:
    assert create_vault_module._derive_mnemonic("HPPLawFirm") == "hlf"
    assert create_vault_module._derive_mnemonic("OneManAirForce") == "omaf"
    assert create_vault_module._derive_mnemonic("BataviaTriptych") == "bt"
    assert create_vault_module._derive_mnemonic("Memoir") == "mem"

    with pytest.raises(create_vault_module.CreateVaultError, match="too short"):
        create_vault_module._derive_mnemonic("A")


def test_derive_label_examples() -> None:
    assert create_vault_module._derive_label("HHPLawFirm") == "HHP Law Firm"
    assert create_vault_module._derive_label("OneManAirForce") == "One Man Air Force"
    assert create_vault_module._derive_label("memoir") == "Memoir"


def test_create_vault_provisions_expected_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    studio_root, _, _, dropbox_assets_root = _configure_canonical_roots(
        tmp_path, monkeypatch
    )

    result = create_vault_module.create_vault("HPPLawFirm")
    vault_path = studio_root / "HPPLawFirm"

    assert result.vault_path == vault_path
    assert result.mnemonic == "hlf"
    assert result.assets_path == dropbox_assets_root / "hlf"
    assert result.installed_plugins == len(create_vault_module.REQUIRED_PLUGINS)

    root_entries = {entry.name for entry in vault_path.iterdir()}
    assert ".obsidian" in root_entries
    assert ".git" in root_entries
    assert ".gitignore" in root_entries
    assert "_common" in root_entries
    assert "_vault_registry.json" in root_entries
    assert "assets" in root_entries
    assert (vault_path / ".git").is_dir()
    assert (
        (vault_path / ".gitignore").read_text(encoding="utf-8")
        == create_vault_module.GITIGNORE_TEMPLATE
    )
    git_config_text = (vault_path / ".git" / "config").read_text(encoding="utf-8")
    assert "[remote " not in git_config_text

    assert (vault_path / "_common").is_symlink()
    assert os.readlink(vault_path / "_common") == str(
        (tmp_path / "Workbench" / "assets" / "obsidian_common").resolve()
    )

    assert (vault_path / "assets").is_symlink()
    assert os.readlink(vault_path / "assets") == str(dropbox_assets_root / "hlf")
    vault_registry = json.loads(
        (vault_path / "_vault_registry.json").read_text(encoding="utf-8")
    )
    assert vault_registry == {"label": "HPP Law Firm", "mnemonic": "hlf"}

    plugin_entries = {
        entry.name for entry in (vault_path / ".obsidian" / "plugins").iterdir()
    }
    assert plugin_entries == set(create_vault_module.REQUIRED_PLUGINS)
    assert (vault_path / ".obsidian" / "hotkeys.json").is_file()

    manager_path = tmp_path / ".config" / "obsidian" / "obsidian.json"
    manager_data = json.loads(manager_path.read_text(encoding="utf-8"))
    assert "vaults" in manager_data
    vault_entries = list(manager_data["vaults"].values())
    assert len(vault_entries) == 1
    assert vault_entries[0]["path"] == str(vault_path)
    assert isinstance(vault_entries[0]["ts"], int)


def test_create_vault_no_assets_skips_dropbox_precondition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    studio_root, _, _, dropbox_assets_root = (
        _configure_canonical_roots(
            tmp_path,
            monkeypatch,
            create_dropbox=False,
        )
    )

    result = create_vault_module.create_vault("Memoir", no_assets=True)

    assert result.mnemonic == "mem"
    assert result.assets_path is None
    assert not (studio_root / "Memoir" / "assets").exists()
    assert dropbox_assets_root.exists() is False


def test_create_vault_updates_existing_obsidian_manager_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    studio_root, _, _, _ = _configure_canonical_roots(tmp_path, monkeypatch)
    manager_path = tmp_path / ".config" / "obsidian" / "obsidian.json"
    existing = {
        "vaults": {
            "abc123": {
                "path": str(studio_root / "HPPLawFirm"),
                "ts": 1000,
                "open": True,
            }
        },
        "openSchemes": {"scenes": True},
    }
    manager_path.write_text(json.dumps(existing), encoding="utf-8")

    create_vault_module.create_vault("HPPLawFirm")

    updated = json.loads(manager_path.read_text(encoding="utf-8"))
    assert set(updated["vaults"].keys()) == {"abc123"}
    assert updated["vaults"]["abc123"]["path"] == str(studio_root / "HPPLawFirm")
    assert isinstance(updated["vaults"]["abc123"]["ts"], int)
    assert updated["vaults"]["abc123"]["ts"] >= 1000
    assert updated["vaults"]["abc123"]["open"] is True


def test_create_vault_rolls_back_on_post_create_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    studio_root, _, _, dropbox_assets_root = _configure_canonical_roots(
        tmp_path, monkeypatch
    )

    def _boom(_: Path) -> None:
        raise create_vault_module.CreateVaultError(
            "ERROR: Simulated template copy failure."
        )

    monkeypatch.setattr(create_vault_module, "_copy_vault_template", _boom)

    with pytest.raises(
        create_vault_module.CreateVaultError, match="Simulated template copy failure"
    ):
        create_vault_module.create_vault("OneManAirForce")

    assert not (studio_root / "OneManAirForce").exists()
    assert not (dropbox_assets_root / "omaf").exists()


def test_create_vault_rolls_back_when_git_init_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    studio_root, _, _, dropbox_assets_root = _configure_canonical_roots(
        tmp_path, monkeypatch
    )

    def _boom(_: Path) -> None:
        raise create_vault_module.CreateVaultError("ERROR: Simulated git init failure.")

    monkeypatch.setattr(create_vault_module, "_initialize_local_git_repo", _boom)

    with pytest.raises(
        create_vault_module.CreateVaultError, match="Simulated git init failure"
    ):
        create_vault_module.create_vault("OneManAirForce")

    assert not (studio_root / "OneManAirForce").exists()
    assert not (dropbox_assets_root / "omaf").exists()


def test_create_vault_validates_preconditions_before_existing_path_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    studio_root = tmp_path / "Studio"
    existing_vault = studio_root / "HPPLawFirm"
    existing_vault.mkdir(parents=True, exist_ok=False)

    workbench_root = tmp_path / "Workbench"
    monkeypatch.setattr(create_vault_module, "STUDIO_ROOT", studio_root)
    monkeypatch.setattr(create_vault_module, "WORKBENCH_ROOT", workbench_root)
    monkeypatch.setattr(
        create_vault_module,
        "VAULT_TEMPLATE_ROOT",
        workbench_root / "assets" / "vault_template",
    )
    monkeypatch.setattr(
        create_vault_module,
        "OBSIDIAN_COMMON_ROOT",
        workbench_root / "assets" / "obsidian_common",
    )
    monkeypatch.setattr(
        create_vault_module,
        "DROPBOX_ASSET_ROOT",
        tmp_path / "Dropbox" / "Assets",
    )
    monkeypatch.setattr(
        create_vault_module,
        "OBSIDIAN_MANAGER_CANDIDATES",
        (tmp_path / ".config" / "obsidian" / "obsidian.json",),
    )

    with pytest.raises(
        create_vault_module.CreateVaultError, match="Required directory is missing"
    ):
        create_vault_module.create_vault("HPPLawFirm")


def test_main_prints_required_success_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_canonical_roots(tmp_path, monkeypatch)

    rc = create_vault_module.main(["HPPLawFirm"])
    output = capsys.readouterr().out

    assert rc == 0
    assert "create-vault: completed" in output
    assert "Vault created:" in output
    assert "  Name: HPPLawFirm" in output
    assert "  Mnemonic: hlf" in output
    assert "  Assets: " in output
