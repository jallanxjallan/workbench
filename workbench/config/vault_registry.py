"""Vault routing registry loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class VaultRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class VaultRegistry:
    _mapping: dict[str, Path]
    source: Path

    def resolve_base_path(self, prefix: str) -> Path:
        normalized = str(prefix).strip()
        if not normalized:
            raise VaultRegistryError("routing prefix must be a non-empty string")
        if normalized not in self._mapping:
            raise VaultRegistryError(
                f"routing prefix '{normalized}' not found in vault registry: {self.source}"
            )
        return self._mapping[normalized]


def default_registry_path() -> Path:
    return Path(__file__).with_name("vaults.yaml")


def load_vault_registry(path: Path | None = None) -> VaultRegistry:
    registry_path = (
        Path(path).expanduser().resolve() if path is not None else default_registry_path()
    )
    if not registry_path.is_file():
        raise VaultRegistryError(f"vault registry not found: {registry_path}")

    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise VaultRegistryError(f"invalid YAML in vault registry: {registry_path}") from exc

    if not isinstance(payload, dict):
        raise VaultRegistryError(
            f"vault registry must be a mapping of prefix -> path: {registry_path}"
        )

    mapping: dict[str, Path] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not key.strip():
            raise VaultRegistryError("vault registry keys must be non-empty strings")
        if not isinstance(value, str) or not value.strip():
            raise VaultRegistryError(
                f"vault registry value for '{key}' must be a non-empty string path"
            )
        mapping[key.strip()] = Path(value).expanduser().resolve()

    if not mapping:
        raise VaultRegistryError(f"vault registry is empty: {registry_path}")

    return VaultRegistry(_mapping=mapping, source=registry_path)

