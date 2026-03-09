"""Compile Studio YAML registries into vault runtime JSON registries."""

from __future__ import annotations

import json
from pathlib import Path

from workbench.cli.create_vault import load_registry
from workbench.config.roots import WORKBENCH_ROOT


class CompileRegistriesError(RuntimeError):
    """Raised when registry compilation fails."""


DEFAULT_RUNTIME_REGISTRIES_ROOT = (
    WORKBENCH_ROOT / "obsidian" / "vault-registries" / "studio"
)


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise CompileRegistriesError(f"Registry source not found: {path}")

    parsed = load_registry(path)
    if not isinstance(parsed, dict):
        raise CompileRegistriesError(f"Registry root must be a mapping: {path}")
    return parsed


def compile_editorial_registry(studio_root: Path, runtime_root: Path) -> Path:
    src = studio_root / "registries" / "editorial.yaml"
    dst = runtime_root / "editorial.json"

    dst.parent.mkdir(parents=True, exist_ok=True)
    data = _load_yaml_mapping(src)
    dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return dst


def compile_verbs_registry(studio_root: Path, runtime_root: Path) -> None:
    # Stub for future implementation.
    _ = studio_root
    _ = runtime_root


def compile_pipeline_registry(studio_root: Path, runtime_root: Path) -> None:
    # Stub for future implementation.
    _ = studio_root
    _ = runtime_root


def compile_registries(
    studio_root: Path, runtime_root: Path = DEFAULT_RUNTIME_REGISTRIES_ROOT
) -> Path:
    editorial_dst = compile_editorial_registry(studio_root, runtime_root)
    compile_verbs_registry(studio_root, runtime_root)
    compile_pipeline_registry(studio_root, runtime_root)
    return editorial_dst


__all__ = [
    "CompileRegistriesError",
    "DEFAULT_RUNTIME_REGISTRIES_ROOT",
    "compile_editorial_registry",
    "compile_pipeline_registry",
    "compile_registries",
    "compile_verbs_registry",
]
