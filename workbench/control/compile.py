"""Compile Control sources into Workbench control artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from workbench.cli.create_vault import load_registry
from workbench.config.roots import STUDIO_ROOT, WORKBENCH_CONTROL_ROOT, WORKBENCH_ROOT
from workbench.interop.document import Document
from workbench.scan.rg import RipgrepError, rg_search
from workbench.regex.compile_patterns import PatternCompileError, compile_pattern_file

_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_SLUG_LINE_PATTERN = r"^\s*slug:\s*([a-z0-9._-]+)\s*$"

DEFAULT_CONTROL_ROOT = WORKBENCH_CONTROL_ROOT
DEFAULT_COMPILED_CONTROL_ROOT = WORKBENCH_ROOT / "_compiled" / "control"


class ControlCompileError(RuntimeError):
    """Raised when control compilation fails."""


@dataclass(frozen=True)
class GlobalInstruction:
    slug: str
    sysmessage: str
    source: Path


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ControlCompileError(f"control source not found: {path}")
    try:
        loaded = load_registry(path)
    except Exception as exc:  # noqa: BLE001
        raise ControlCompileError(f"invalid YAML source {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ControlCompileError(f"YAML root must be a mapping: {path}")
    return loaded


def _iter_yaml_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise ControlCompileError(f"required directory missing: {directory}")
    return sorted(path for path in directory.glob("*.yaml") if path.is_file())


def _compile_verbs(control_root: Path) -> dict[str, dict[str, Any]]:
    verbs_dir = control_root / "verbs"
    compiled: dict[str, dict[str, Any]] = {}
    for source in _iter_yaml_files(verbs_dir):
        compiled[source.stem] = _read_yaml_mapping(source)
    return compiled


def _compile_regex(control_root: Path) -> dict[str, dict[str, Any]]:
    regex_dir = control_root / "Regex" / "definitions"
    compiled: dict[str, dict[str, Any]] = {}
    for source in _iter_yaml_files(regex_dir):
        try:
            payload = compile_pattern_file(source)
        except PatternCompileError as exc:
            raise ControlCompileError(str(exc)) from exc
        name = payload["name"]
        if not isinstance(name, str) or not name:
            raise ControlCompileError(f"compiled regex missing name: {source}")
        if name in compiled:
            raise ControlCompileError(f"duplicate regex name detected: {name}")
        compiled[name] = payload
    return compiled


def _validate_global_instruction(path: Path) -> GlobalInstruction:
    inspected = Document.inspect_file(path)
    if inspected.error:
        raise ControlCompileError(f"invalid instruction markdown {path}: {inspected.error}")
    if not inspected.has_frontmatter or not isinstance(inspected.metadata, dict):
        raise ControlCompileError(f"instruction requires frontmatter: {path}")

    metadata = inspected.metadata
    raw_slug = metadata.get("slug")
    if not isinstance(raw_slug, str) or not raw_slug.strip():
        raise ControlCompileError(f"instruction missing non-empty slug: {path}")
    slug = raw_slug.strip()

    if slug != path.stem:
        raise ControlCompileError(f"instruction slug must match filename stem: {path}")
    if not slug.startswith("gbl."):
        raise ControlCompileError(f"global instruction slug must start with gbl.: {path}")

    raw_type = metadata.get("type")
    if raw_type != "instruction":
        raise ControlCompileError(f"global instruction type must be 'instruction': {path}")

    raw_scope = metadata.get("scope")
    if raw_scope != "global":
        raise ControlCompileError(f"global instruction scope must be 'global': {path}")

    body = inspected.body.strip()
    if not body:
        raise ControlCompileError(f"instruction body is empty: {path}")

    return GlobalInstruction(
        slug=slug,
        sysmessage=body,
        source=path,
    )


def discover_slug_occurrences(*, roots: tuple[Path, ...]) -> dict[str, set[Path]]:
    slug_map: dict[str, set[Path]] = {}
    for root in roots:
        root_path = Path(root).expanduser().resolve()
        if not root_path.exists() or not root_path.is_dir():
            continue

        try:
            matches = rg_search(
                pattern=_SLUG_LINE_PATTERN,
                root=root_path,
                extensions=["md", "markdown"],
            )
            for match in matches:
                groups = match["groups"]
                file_path = match["path"]
                if (
                    not isinstance(groups, list)
                    or not groups
                    or not isinstance(groups[0], str)
                    or not isinstance(file_path, Path)
                ):
                    continue
                slug = groups[0]
                slug_map.setdefault(slug, set()).add(file_path.resolve())
        except RipgrepError as exc:
            raise ControlCompileError(str(exc)) from exc
    return slug_map


def _compile_global_instructions(control_root: Path) -> dict[str, dict[str, str]]:
    directory = control_root / "instructions" / "global"
    if not directory.is_dir():
        raise ControlCompileError(f"required directory missing: {directory}")

    roots = (control_root, STUDIO_ROOT)
    slug_occurrences = discover_slug_occurrences(roots=roots)
    compiled: dict[str, dict[str, str]] = {}

    for source in sorted(directory.iterdir()):
        if not source.is_file() or source.suffix.lower() not in _MARKDOWN_SUFFIXES:
            continue
        instruction = _validate_global_instruction(source)
        if instruction.slug in compiled:
            raise ControlCompileError(f"duplicate global instruction slug: {instruction.slug}")

        owners = slug_occurrences.get(instruction.slug, set())
        foreign = sorted(path for path in owners if path.resolve() != instruction.source.resolve())
        if foreign:
            preview = ", ".join(str(path) for path in foreign[:3])
            raise ControlCompileError(
                f"slug already exists in control/studio roots: {instruction.slug}: {preview}"
            )

        compiled[instruction.slug] = {
            "slug": instruction.slug,
            "sysmessage": instruction.sysmessage,
        }
    return compiled


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def compile_control(
    control_root: Path = DEFAULT_CONTROL_ROOT,
    output_root: Path = DEFAULT_COMPILED_CONTROL_ROOT,
) -> tuple[Path, ...]:
    source_root = Path(control_root).expanduser().resolve()
    compiled_root = Path(output_root).expanduser().resolve()

    if not source_root.exists() or not source_root.is_dir():
        raise ControlCompileError(f"control root not found: {source_root}")

    verbs = _compile_verbs(source_root)
    global_instructions = _compile_global_instructions(source_root)
    regex = _compile_regex(source_root)

    verbs_out = _write_json(
        compiled_root / "verbs.json",
        {
            "verbs": [verbs[name] for name in sorted(verbs)],
            "index": {name: verbs[name] for name in sorted(verbs)},
        },
    )
    global_out = _write_json(
        compiled_root / "global_instructions.json",
        {
            "global_instructions": [
                global_instructions[slug] for slug in sorted(global_instructions)
            ]
        },
    )
    regex_out = _write_json(
        compiled_root / "regex.json",
        {"regex": [regex[name] for name in sorted(regex)]},
    )

    print(f"compiled control verbs={len(verbs)} globals={len(global_instructions)} regex={len(regex)}")
    return (verbs_out, global_out, regex_out)


__all__ = [
    "ControlCompileError",
    "DEFAULT_COMPILED_CONTROL_ROOT",
    "DEFAULT_CONTROL_ROOT",
    "compile_control",
    "discover_slug_occurrences",
]
