from __future__ import annotations

"""
Immutable, per-run configuration snapshot loaded from a manifest JSON file.

Design:
- A single hard-coded environment variable points to the manifest file
- The manifest is loaded exactly once at construction time
- Values are exposed via dot-notation attributes
- Top-level manifest keys become snake_case-friendly attributes
- Nested dicts are wrapped so dot notation continues to work if needed
- Environment or manifest changes after construction have NO effect

Example:
    export AUTOSCRIBE_MANIFEST=/path/to/manifest.json

    config = load_config()
    config.workspace_root
    config.sql_ledger_path

If a manifest value is itself an object, it is also accessible with dot notation:
    config.redis.host
"""

import json
from pathlib import Path
from typing import Any, Mapping

from config.runtime import env_path


MANIFEST_ENV_VAR = "WORKSPACE_MANIFEST"


def _normalize_key(name: str) -> str:
    """Normalize manifest keys for attribute-style access."""
    return name.replace("-", "_")


class ConfigNode:
    """Read-only wrapper that exposes mapping values via attributes."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._data: dict[str, Any] = {}
        self._raw_keys: dict[str, str] = {}

        for raw_key, value in data.items():
            key = _normalize_key(str(raw_key))
            self._data[key] = self._wrap(value)
            self._raw_keys[key] = str(raw_key)

    def _wrap(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return ConfigNode(value)
        if isinstance(value, list):
            return [self._wrap(item) for item in value]
        return value

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError as exc:
            raise AttributeError(f"Config variable '{name}' is not set") from exc

    def __getitem__(self, key: str) -> Any:
        return self._data[_normalize_key(key)]

    def __contains__(self, key: str) -> bool:
        return _normalize_key(key) in self._data

    def get(self, name: str, default: Any = None) -> Any:
        return self._data.get(_normalize_key(name), default)

    @property
    def keys(self) -> set[str]:
        return set(self._data.keys())

    def as_dict(self) -> dict[str, Any]:
        def unwrap(value: Any) -> Any:
            if isinstance(value, ConfigNode):
                return value.as_dict()
            if isinstance(value, list):
                return [unwrap(item) for item in value]
            return value

        return {key: unwrap(value) for key, value in self._data.items()}


class Config(ConfigNode):
    def __init__(self) -> None:
        path = env_path(MANIFEST_ENV_VAR, resolve=True)
        if path is None:
            raise RuntimeError(
                f"Required environment variable '{MANIFEST_ENV_VAR}' is not set"
            )
        if not path.is_file():
            raise RuntimeError(
                f"Manifest file from '{MANIFEST_ENV_VAR}' does not exist: {path}"
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON in manifest file: {path}") from exc

        if not isinstance(payload, Mapping):
            raise RuntimeError(
                f"Manifest root must be a JSON object, got {type(payload).__name__}"
            )

        self._manifest_env_var = MANIFEST_ENV_VAR
        self._manifest_path = path
        super().__init__(payload)

    @property
    def manifest_env_var(self) -> str:
        return self._manifest_env_var

    @property
    def manifest_path(self) -> Path:
        return self._manifest_path


class LazyConfig:
    """Load the manifest-backed config on first access."""

    def __init__(self) -> None:
        self._loaded: Config | None = None

    def load(self) -> Config:
        if self._loaded is None:
            self._loaded = Config()
        return self._loaded

    def __getattr__(self, name: str) -> Any:
        return getattr(self.load(), name)


def load_config() -> Config:
    return config.load()


config = LazyConfig()
