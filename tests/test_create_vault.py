from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import workbench.cli.create_vault as create_vault_module


def _write_file(path: Path, content: str = "{}\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _configure_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path]:
    studio_root = tmp_path / "Studio"
    obsidian_root = studio_root / "Obsidian"
    template_root = obsidian_root / "vault"
    common_root = obsidian_root / "common"

    _write_file(template_root / ".obsidian" / "app.json", content="{}\n")
    _write_file(template_root / ".obsidian" / "hotkeys.json", content="{}\n")
    _write_file(common_root / "templates" / "passage.md", content="# passage\n")

    monkeypatch.setattr(create_vault_module, "STUDIO_ROOT", studio_root)
    monkeypatch.setattr(create_vault_module, "OBSIDIAN_ROOT", obsidian_root)
    monkeypatch.setattr(create_vault_module, "VAULT_TEMPLATE_ROOT", template_root)
    monkeypatch.setattr(create_vault_module, "OBSIDIAN_COMMON_ROOT", common_root)

    return studio_root, template_root, common_root


def _read_registry(vault_path: Path) -> dict[str, object]:
    raw = (vault_path / "_vault_registry").read_text(encoding="utf-8").strip()
    assert raw
    line = raw.splitlines()[0]
    return json.loads(line)


def test_create_vault_new_path_creates_registry_template_and_common_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, _, common_root = _configure_roots(tmp_path, monkeypatch)

    result = create_vault_module.create_vault("omaf")
    vault_path = studio_root / "omaf"

    assert result.status == create_vault_module.STATUS_CREATED
    assert result.vault_path == vault_path
    assert result.registry_created is True

    assert (vault_path / "_vault_registry").is_file()
    assert (vault_path / ".obsidian").is_dir()
    assert (vault_path / "_common").is_symlink()
    assert os.readlink(vault_path / "_common") == os.path.relpath(
        common_root.resolve(), start=vault_path.resolve()
    )

    registry = _read_registry(vault_path)
    assert set(registry.keys()) == {"vault_id", "created", "tool", "version"}
    assert isinstance(registry["vault_id"], str)
    assert len(registry["vault_id"]) == 26
    assert registry["tool"] == "workbench"
    assert registry["version"] == 1
    assert str(registry["created"]).endswith("Z")


def test_create_vault_existing_folder_preserves_existing_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _ = _configure_roots(tmp_path, monkeypatch)

    existing = tmp_path / "Studio" / "existing"
    existing.mkdir(parents=True, exist_ok=True)
    _write_file(existing / "file.md", content="existing\n")

    result = create_vault_module.create_vault(str(existing))

    assert result.status == create_vault_module.STATUS_INITIALIZED
    assert (existing / "file.md").read_text(encoding="utf-8") == "existing\n"
    assert (existing / "_vault_registry").is_file()
    assert (existing / ".obsidian").is_dir()
    assert (existing / "_common").is_symlink()


def test_create_vault_existing_registry_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _ = _configure_roots(tmp_path, monkeypatch)

    existing = tmp_path / "Studio" / "existing"
    existing.mkdir(parents=True, exist_ok=True)
    _write_file(existing / "note.md", content="keep\n")

    first = create_vault_module.create_vault(str(existing))
    first_registry = (existing / "_vault_registry").read_text(encoding="utf-8")

    second = create_vault_module.create_vault(str(existing))
    second_registry = (existing / "_vault_registry").read_text(encoding="utf-8")

    assert first.status == create_vault_module.STATUS_INITIALIZED
    assert second.status == create_vault_module.STATUS_ALREADY
    assert first_registry == second_registry
    assert (existing / "note.md").read_text(encoding="utf-8") == "keep\n"


def test_create_vault_fails_when_common_path_exists_and_is_not_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _ = _configure_roots(tmp_path, monkeypatch)

    existing = tmp_path / "Studio" / "existing"
    existing.mkdir(parents=True, exist_ok=True)
    (existing / "_common").mkdir(parents=True, exist_ok=False)

    with pytest.raises(create_vault_module.CreateVaultError, match="Unsafe existing _common"):
        create_vault_module.create_vault(str(existing))


def test_main_prints_status_messages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    studio_root, _, _ = _configure_roots(tmp_path, monkeypatch)

    rc_created = create_vault_module.main(["omaf"])
    created_output = capsys.readouterr().out
    assert rc_created == 0
    assert "Created new vault:" in created_output
    assert "omaf" in created_output

    existing = studio_root / "existing"
    existing.mkdir(parents=True, exist_ok=True)
    _write_file(existing / "file.md", "keep\n")

    rc_init = create_vault_module.main([str(existing)])
    init_output = capsys.readouterr().out
    assert rc_init == 0
    assert "Initialized existing folder as vault:" in init_output
    assert "existing" in init_output
    assert "Existing files preserved." in init_output

    rc_already = create_vault_module.main([str(existing)])
    already_output = capsys.readouterr().out
    assert rc_already == 0
    assert "Vault already initialized:" in already_output
    assert "existing" in already_output
