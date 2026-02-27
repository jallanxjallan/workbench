from __future__ import annotations

from pathlib import Path

import pytest

from workbench.config.vault_registry import VaultRegistryError, load_vault_registry


def test_load_vault_registry_resolves_existing_directories(tmp_path: Path) -> None:
    hhp = tmp_path / "hhp"
    hhp.mkdir(parents=True, exist_ok=False)
    websites = tmp_path / "websites"
    websites.mkdir(parents=True, exist_ok=False)

    registry_path = tmp_path / "vaults.yaml"
    registry_path.write_text(
        f"hhp: {hhp}\nwebsites: {websites}\n",
        encoding="utf-8",
    )

    registry = load_vault_registry(registry_path)

    assert registry.resolve_base_path("hhp") == hhp.resolve()
    assert registry.resolve_base_path("websites") == websites.resolve()


def test_load_vault_registry_rejects_missing_directory(tmp_path: Path) -> None:
    registry_path = tmp_path / "vaults.yaml"
    registry_path.write_text(
        "hhp: /tmp/does-not-exist-wkb-vault-registry\n", encoding="utf-8"
    )

    with pytest.raises(VaultRegistryError, match="does not exist"):
        load_vault_registry(registry_path)
