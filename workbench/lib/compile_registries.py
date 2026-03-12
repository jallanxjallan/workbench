"""Compile control YAML registries into runtime JSON registries."""

from __future__ import annotations

import json
from pathlib import Path

from workbench.cli.create_vault import load_registry
from workbench.config.roots import AUTOSCRIBE_CONTROL_ROOT, WORKBENCH_ROOT


class CompileRegistriesError(RuntimeError):
    """Raised when registry compilation fails."""


_CONTROL_REGISTRIES_ROOT = AUTOSCRIBE_CONTROL_ROOT / "registries"
_LEGACY_REGISTRIES_ROOT = WORKBENCH_ROOT / "registries"


def _resolve_default_registries_root() -> Path:
    if _CONTROL_REGISTRIES_ROOT.is_dir():
        return _CONTROL_REGISTRIES_ROOT
    return _LEGACY_REGISTRIES_ROOT


DEFAULT_REGISTRIES_ROOT = _resolve_default_registries_root()
DEFAULT_RUNTIME_ROOT = WORKBENCH_ROOT / "_compiled"
_REGISTRY_NAMES = ("editorial", "pipeline", "verbs")


def _needs_recompile(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    return src.stat().st_mtime > dst.stat().st_mtime


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise CompileRegistriesError(f"registry source not found: {path}")
    try:
        parsed = load_registry(path)
    except Exception as exc:  # noqa: BLE001
        raise CompileRegistriesError(f"invalid registry source {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise CompileRegistriesError(f"registry root must be a mapping: {path}")
    return parsed


def _compile_named_registry(
    *,
    name: str,
    registries_root: Path,
    runtime_root: Path,
) -> Path | None:
    src = registries_root / f"{name}.yaml"
    dst = runtime_root / "registries" / f"{name}.json"
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not src.is_file():
        raise CompileRegistriesError(f"registry source not found: {src}")
    if not _needs_recompile(src, dst):
        return None

    payload = _load_yaml_mapping(src)
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"compiled {name}")
    return dst


def compile_editorial_registry(registries_root: Path, runtime_root: Path) -> Path | None:
    return _compile_named_registry(
        name="editorial",
        registries_root=registries_root,
        runtime_root=runtime_root,
    )


def compile_pipeline_registry(registries_root: Path, runtime_root: Path) -> Path | None:
    return _compile_named_registry(
        name="pipeline",
        registries_root=registries_root,
        runtime_root=runtime_root,
    )


def compile_verbs_registry(registries_root: Path, runtime_root: Path) -> Path | None:
    return _compile_named_registry(
        name="verbs",
        registries_root=registries_root,
        runtime_root=runtime_root,
    )


def compile_registries(
    registries_root: Path = DEFAULT_REGISTRIES_ROOT,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
) -> tuple[Path, ...]:
    source_root = Path(registries_root).expanduser().resolve()
    compiled_root = Path(runtime_root).expanduser().resolve()
    compiled_root.mkdir(parents=True, exist_ok=True)
    (compiled_root / "registries").mkdir(parents=True, exist_ok=True)

    compiled_paths: list[Path] = []
    for name in _REGISTRY_NAMES:
        output = _compile_named_registry(
            name=name,
            registries_root=source_root,
            runtime_root=compiled_root,
        )
        if output is not None:
            compiled_paths.append(output)

    if not compiled_paths:
        print("registries up to date")
    return tuple(compiled_paths)


__all__ = [
    "CompileRegistriesError",
    "DEFAULT_REGISTRIES_ROOT",
    "DEFAULT_RUNTIME_ROOT",
    "compile_editorial_registry",
    "compile_pipeline_registry",
    "compile_registries",
    "compile_verbs_registry",
]
