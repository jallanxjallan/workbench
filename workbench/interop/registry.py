"""Vault registry resolution helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path("00-system") / "project_registry.json"
_PROJECT_CODE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PROJECT_CODE_KEYS = ("project_code", "code", "projectCode", "slug", "mnemonic")


def find_vault_root(start: Path) -> Path:
    cursor = Path(start).expanduser().resolve()
    if cursor.is_file() or (not cursor.exists() and cursor.suffix):
        cursor = cursor.parent

    while True:
        if (cursor / _REGISTRY_PATH).is_file():
            return cursor
        if cursor.parent == cursor:
            break
        cursor = cursor.parent

    raise FileNotFoundError(
        f"no vault root found from '{start}' (missing {_REGISTRY_PATH})"
    )


def load_registry(vault_root: Path) -> dict[str, Any]:
    registry_path = Path(vault_root) / _REGISTRY_PATH
    if not registry_path.is_file():
        raise FileNotFoundError(f"registry file not found: {registry_path}")

    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid registry JSON: {registry_path}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"registry must be a JSON object: {registry_path}")
    return payload


def resolve_project_code(target_dir: Path, registry: dict[str, Any]) -> str:
    target = Path(target_dir).expanduser().resolve()
    vault_root = find_vault_root(target)
    try:
        relative = target.relative_to(vault_root)
    except ValueError as exc:
        raise ValueError(f"target directory is outside vault root: {target}") from exc

    if len(relative.parts) < 2 or relative.parts[0] != "projects":
        raise ValueError(
            "slug generation is only allowed inside <vault_root>/projects/<project_name>/"
        )

    project_name = relative.parts[1]
    code = _lookup_project_code(registry, project_name)
    if not _PROJECT_CODE_RE.fullmatch(code):
        raise ValueError(
            f"invalid project code '{code}' for project '{project_name}' in registry"
        )
    return code


def _lookup_project_code(registry: dict[str, Any], project_name: str) -> str:
    projects = registry.get("projects")
    if isinstance(projects, dict):
        if project_name not in projects:
            raise KeyError(f"project '{project_name}' not found in registry")
        extracted = _extract_project_code(projects[project_name])
        if extracted is None:
            raise ValueError(
                f"project '{project_name}' is missing project_code in registry"
            )
        return extracted

    if project_name in registry:
        extracted = _extract_project_code(registry[project_name])
        if extracted is None:
            raise ValueError(
                f"project '{project_name}' is missing project_code in registry"
            )
        return extracted

    raise KeyError(f"project '{project_name}' not found in registry")


def _extract_project_code(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    if not isinstance(value, dict):
        return None

    for key in _PROJECT_CODE_KEYS:
        code = value.get(key)
        if isinstance(code, str) and code.strip():
            return code.strip()

    identity = value.get("identity")
    if isinstance(identity, dict):
        for key in _PROJECT_CODE_KEYS:
            code = identity.get(key)
            if isinstance(code, str) and code.strip():
                return code.strip()

    return None
