"""Compile Studio regex YAML definitions into runtime JSON pattern specs."""

from __future__ import annotations

import json
import os
from pathlib import Path

from workbench.cli.create_vault import load_registry


SCHEMA_VERSION = 1
SUPPORTED_ENGINES = {"default", "pcre2"}

_WORKBENCH_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_STUDIO_ROOT = Path(
    os.environ.get("STUDIO_ROOT", str(Path.home().resolve() / "Studio"))
).expanduser().resolve()

DEFAULT_PATTERN_SOURCE_ROOT = _DEFAULT_STUDIO_ROOT / "regex"
DEFAULT_PATTERN_OUTPUT_ROOT = _WORKBENCH_ROOT / "_compiled" / "regex"


class PatternCompileError(RuntimeError):
    """Raised when a regex pattern definition is invalid."""


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise PatternCompileError(f"pattern source not found: {path}")

    try:
        parsed = load_registry(path)
    except Exception as exc:  # noqa: BLE001
        raise PatternCompileError(f"invalid pattern source {path}: {exc}") from exc

    if not isinstance(parsed, dict):
        raise PatternCompileError(f"pattern root must be a mapping: {path}")
    return parsed


def _validate_name(data: dict[str, object], path: Path) -> str:
    raw_name = data.get("name")
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise PatternCompileError(f"missing required 'name' in {path}")

    name = raw_name.strip()
    if name != path.stem:
        raise PatternCompileError(
            f"pattern name must match filename stem: {path.stem} != {name}"
        )
    return name


def _validate_engine(data: dict[str, object], *, path: Path) -> str:
    raw_engine = data.get("engine", "default")
    if not isinstance(raw_engine, str) or not raw_engine.strip():
        raise PatternCompileError(f"'engine' must be a non-empty string in {path}")

    engine = raw_engine.strip().lower()
    if engine not in SUPPORTED_ENGINES:
        raise PatternCompileError(
            f"unsupported engine '{engine}' in {path}; expected one of {sorted(SUPPORTED_ENGINES)}"
        )
    return engine


def _validate_ignore_case(data: dict[str, object], *, path: Path) -> bool:
    raw_ignore_case = data.get("ignore_case", False)
    if not isinstance(raw_ignore_case, bool):
        raise PatternCompileError(f"'ignore_case' must be boolean in {path}")
    return raw_ignore_case


def _validate_mode(data: dict[str, object], *, path: Path) -> str:
    has_and = "and" in data and data["and"] is not None
    has_or = "or" in data and data["or"] is not None
    if has_and == has_or:
        raise PatternCompileError(f"exactly one of 'and' or 'or' must be defined in {path}")
    return "and" if has_and else "or"


def _validate_terms(data: dict[str, object], *, mode: str, path: Path) -> list[str]:
    raw_terms = data.get(mode)
    if not isinstance(raw_terms, list) or not raw_terms:
        raise PatternCompileError(f"'{mode}' must be a non-empty list in {path}")

    terms: list[str] = []
    for index, term in enumerate(raw_terms, start=1):
        if not isinstance(term, str) or not term.strip():
            raise PatternCompileError(
                f"all '{mode}' terms must be non-empty strings in {path} (item {index})"
            )
        terms.append(term.strip())
    return terms


def _build_pattern(*, mode: str, terms: list[str]) -> str:
    if mode == "and":
        lookaheads = "".join(f"(?=.*{term})" for term in terms)
        return f"(?s){lookaheads}"
    return f"({'|'.join(terms)})"


def compile_pattern_file(path: Path) -> dict[str, object]:
    data = _load_yaml_mapping(path)
    name = _validate_name(data, path)
    engine = _validate_engine(data, path=path)
    ignore_case = _validate_ignore_case(data, path=path)
    mode = _validate_mode(data, path=path)
    terms = _validate_terms(data, mode=mode, path=path)

    if mode == "and" and engine != "pcre2":
        raise PatternCompileError(
            f"'and' patterns require engine 'pcre2' in {path}"
        )

    return {
        "name": name,
        "pattern": _build_pattern(mode=mode, terms=terms),
        "engine": engine,
        "ignore_case": ignore_case,
        "version": SCHEMA_VERSION,
    }


def compile_patterns(
    source_root: Path = DEFAULT_PATTERN_SOURCE_ROOT,
    output_root: Path = DEFAULT_PATTERN_OUTPUT_ROOT,
) -> tuple[Path, ...]:
    source_path = Path(source_root).expanduser().resolve()
    output_path = Path(output_root).expanduser().resolve()

    if not source_path.exists() or not source_path.is_dir():
        raise PatternCompileError(f"pattern source directory not found: {source_path}")

    output_path.mkdir(parents=True, exist_ok=True)

    compiled_paths: list[Path] = []
    seen_names: set[str] = set()

    for yaml_path in sorted(source_path.glob("*.yaml")):
        compiled = compile_pattern_file(yaml_path)
        name = str(compiled["name"])
        if name in seen_names:
            raise PatternCompileError(f"duplicate pattern name detected: {name}")
        seen_names.add(name)

        destination = output_path / f"{name}.json"
        destination.write_text(json.dumps(compiled, indent=2) + "\n", encoding="utf-8")
        compiled_paths.append(destination)
        print(f"compiled {name}")

    return tuple(compiled_paths)
