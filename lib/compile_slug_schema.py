"""Compile the authoritative Control slug schema into runtime artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import yaml

from workbench.config.roots import CONTROL_ROOT, WORKBENCH_ROOT

DEFAULT_SOURCE = CONTROL_ROOT / "registry" / "slug_schema.yaml"
DEFAULT_JSON_TARGETS = (
    WORKBENCH_ROOT / "workbench" / "runtime" / "slug_schema.json",
    WORKBENCH_ROOT / "obsidian" / "control" / "slug_schema.json",
)
DEFAULT_REGEX_TARGET = WORKBENCH_ROOT / "workbench" / "runtime" / "slug_regex.txt"


class SlugSchemaCompileError(RuntimeError):
    """Raised when the authoritative slug schema is invalid."""


@dataclass(frozen=True)
class CompileResult:
    source: Path
    json_targets: tuple[Path, ...]
    regex_target: Path
    version: int
    checksum: str
    normalized_regex: str


def normalize_regex(pattern: str) -> str:
    return re.sub(r"\s+", "", str(pattern or "").strip())


def _require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SlugSchemaCompileError(f"{label} must be a mapping")
    return value


def _require_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SlugSchemaCompileError(f"{label} must be a non-empty string")
    return value


def _require_bool(value: Any, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise SlugSchemaCompileError(f"{label} must be a boolean")
    return value


def _validate_field(field: Any, *, index: int, seen_names: set[str]) -> str:
    data = _require_mapping(field, label=f"slug.fields[{index}]")
    name = _require_string(data.get("name"), label=f"slug.fields[{index}].name")
    if name in seen_names:
        raise SlugSchemaCompileError(f"duplicate slug field name: {name}")
    seen_names.add(name)

    pattern = _require_string(data.get("pattern"), label=f"slug.fields[{index}].pattern")
    _require_bool(data.get("required"), label=f"slug.fields[{index}].required")

    try:
        re.compile(rf"^(?:{pattern})$")
    except re.error as exc:
        raise SlugSchemaCompileError(
            f"invalid slug.fields[{index}].pattern for {name}: {exc}"
        ) from exc
    return name


def _validate_schema(data: dict[str, Any]) -> tuple[int, str]:
    version = data.get("version")
    if not isinstance(version, int) or version < 1:
        raise SlugSchemaCompileError("version must be a positive integer")

    slug = _require_mapping(data.get("slug"), label="slug")
    separator = _require_string(slug.get("separator"), label="slug.separator")
    if separator != ".":
        raise SlugSchemaCompileError("slug.separator must be '.' for the current runtime")
    optional_seq = _require_bool(slug.get("optional_seq"), label="slug.optional_seq")

    fields = slug.get("fields")
    if not isinstance(fields, list) or not fields:
        raise SlugSchemaCompileError("slug.fields must be a non-empty list")

    seen_names: set[str] = set()
    field_names = [_validate_field(field, index=index, seen_names=seen_names) for index, field in enumerate(fields)]

    regex = _require_mapping(slug.get("regex"), label="slug.regex")
    full_pattern = _require_string(regex.get("full"), label="slug.regex.full")
    normalized = normalize_regex(full_pattern)
    if not normalized:
        raise SlugSchemaCompileError("slug.regex.full normalized to an empty pattern")

    try:
        compiled = re.compile(normalized)
    except re.error as exc:
        raise SlugSchemaCompileError(f"invalid slug.regex.full: {exc}") from exc

    group_names = set(compiled.groupindex)
    if group_names != set(field_names):
        raise SlugSchemaCompileError(
            "slug.regex.full named groups must match slug.fields names exactly"
        )

    if optional_seq:
        seq_fields = [field for field in fields if field.get("name") == "seq"]
        if len(seq_fields) != 1:
            raise SlugSchemaCompileError("slug.optional_seq requires exactly one seq field")
        if seq_fields[0].get("required") is not False:
            raise SlugSchemaCompileError("seq field must be optional when slug.optional_seq is true")

    return version, normalized


def _load_source(source: Path) -> dict[str, Any]:
    if not source.exists():
        raise SlugSchemaCompileError(f"slug schema source not found: {source}")
    try:
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SlugSchemaCompileError(f"could not parse slug schema YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SlugSchemaCompileError("slug schema root must be a mapping")
    return data


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def compile_slug_schema(
    *,
    source: Path = DEFAULT_SOURCE,
    json_targets: Sequence[Path] = DEFAULT_JSON_TARGETS,
    regex_target: Path = DEFAULT_REGEX_TARGET,
) -> CompileResult:
    source = Path(source).expanduser().resolve()
    resolved_targets = tuple(Path(target).expanduser().resolve() for target in json_targets)
    resolved_regex_target = Path(regex_target).expanduser().resolve()

    data = _load_source(source)
    version, normalized = _validate_schema(data)

    compiled_schema = copy.deepcopy(data)
    compiled_schema.setdefault("slug", {}).setdefault("regex", {})["normalized"] = normalized

    payload = json.dumps(compiled_schema, indent=2, sort_keys=True) + "\n"
    checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    for target in resolved_targets:
        _write_text(target, payload)
    _write_text(resolved_regex_target, normalized + "\n")

    return CompileResult(
        source=source,
        json_targets=resolved_targets,
        regex_target=resolved_regex_target,
        version=version,
        checksum=checksum,
        normalized_regex=normalized,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile-slug-schema",
        description=__doc__,
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--json-target",
        dest="json_targets",
        action="append",
        type=Path,
        help="override a JSON output target; repeat to emit to multiple locations",
    )
    parser.add_argument("--regex-target", type=Path, default=DEFAULT_REGEX_TARGET)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    json_targets = tuple(args.json_targets) if args.json_targets else DEFAULT_JSON_TARGETS
    try:
        result = compile_slug_schema(
            source=args.source,
            json_targets=json_targets,
            regex_target=args.regex_target,
        )
    except (SlugSchemaCompileError, OSError) as exc:
        print(f"[compile-slug-schema] error: {exc}", file=sys.stderr)
        return 1

    print(
        f"compiled slug schema version={result.version} checksum={result.checksum} "
        f"source={result.source}"
    )
    for target in result.json_targets:
        print(f"json -> {target}")
    print(f"regex -> {result.regex_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
