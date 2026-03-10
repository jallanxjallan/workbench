"""Compile Studio YAML registries into vault runtime JSON registries."""

from __future__ import annotations

import json
from pathlib import Path

from workbench.cli.create_vault import load_registry
from workbench.config.roots import WORKBENCH_ROOT
from workbench.regex.compile_patterns import PatternCompileError, compile_pattern_file


class CompileRegistriesError(RuntimeError):
    """Raised when registry compilation fails."""


DEFAULT_RUNTIME_REGISTRIES_ROOT = WORKBENCH_ROOT / "_compiled"


def _needs_recompile(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    return src.stat().st_mtime > dst.stat().st_mtime


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise CompileRegistriesError(f"Registry source not found: {path}")

    parsed = load_registry(path)
    if not isinstance(parsed, dict):
        raise CompileRegistriesError(f"Registry root must be a mapping: {path}")
    return parsed


def compile_editorial_registry(studio_root: Path, runtime_root: Path) -> Path | None:
    src = studio_root / "registries" / "editorial.yaml"
    dst = runtime_root / "registries" / "editorial.json"

    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.is_file():
        raise CompileRegistriesError(f"Registry source not found: {src}")
    if not _needs_recompile(src, dst):
        return None

    data = _load_yaml_mapping(src)
    dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("compiled editorial")
    return dst


def compile_regex_registry(studio_root: Path, runtime_root: Path) -> tuple[Path, ...]:
    src_dir = studio_root / "regex"
    dst_dir = runtime_root / "regex"
    dst_dir.mkdir(parents=True, exist_ok=True)

    if not src_dir.exists():
        return tuple()
    if not src_dir.is_dir():
        raise CompileRegistriesError(f"regex source is not a directory: {src_dir}")

    compiled_paths: list[Path] = []
    for src in sorted(src_dir.glob("*.yaml")):
        dst = dst_dir / f"{src.stem}.json"
        if not _needs_recompile(src, dst):
            continue
        try:
            compiled = compile_pattern_file(src)
        except PatternCompileError as exc:
            raise CompileRegistriesError(str(exc)) from exc
        dst.write_text(json.dumps(compiled, indent=2) + "\n", encoding="utf-8")
        compiled_paths.append(dst)
        print(f"compiled regex {src.stem}")

    return tuple(compiled_paths)


def compile_verbs_registry(studio_root: Path, runtime_root: Path) -> None:
    # TODO: implement registry compiler
    _ = studio_root
    _ = runtime_root
    pass


def compile_registries(
    studio_root: Path, runtime_root: Path = DEFAULT_RUNTIME_REGISTRIES_ROOT
) -> tuple[Path, ...]:
    runtime_root = Path(runtime_root).expanduser().resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "registries").mkdir(parents=True, exist_ok=True)
    (runtime_root / "regex").mkdir(parents=True, exist_ok=True)

    compiled_paths: list[Path] = []

    editorial_dst = compile_editorial_registry(studio_root, runtime_root)
    if editorial_dst is not None:
        compiled_paths.append(editorial_dst)

    compiled_paths.extend(compile_regex_registry(studio_root, runtime_root))

    compile_verbs_registry(studio_root, runtime_root)
    compile_pipeline_registry(studio_root, runtime_root)
    compile_vault_registry(studio_root, runtime_root)

    if not compiled_paths:
        print("registries up to date")

    return tuple(compiled_paths)


def compile_pipeline_registry(studio_root: Path, runtime_root: Path) -> None:
    # TODO: implement registry compiler
    _ = studio_root
    _ = runtime_root
    pass


def compile_vault_registry(studio_root: Path, runtime_root: Path) -> None:
    # TODO: implement registry compiler
    _ = studio_root
    _ = runtime_root
    pass


__all__ = [
    "CompileRegistriesError",
    "DEFAULT_RUNTIME_REGISTRIES_ROOT",
    "compile_regex_registry",
    "compile_editorial_registry",
    "compile_pipeline_registry",
    "compile_registries",
    "compile_vault_registry",
    "compile_verbs_registry",
]
