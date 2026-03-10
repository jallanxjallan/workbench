"""Write NDJSON records into new vault candidate files."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Iterable

from workbench.interop.document import Document
from workbench.write.common import (
    WriteError,
    WriteRecord,
    atomic_write_text,
    ensure_directory,
    iter_input_records,
    preferred_filename_stem,
    resolve_unique_markdown_path,
)


@dataclass(frozen=True)
class WriteSchema:
    schema: str
    class_name: str
    defaults: dict[str, Any]


def write_new_records(
    *,
    schema_name: str,
    target_path: str,
    studio_root: str,
    debug_routing: bool,
    input_stream: Iterable[str],
) -> None:
    schema = load_schema(schema_name=schema_name, studio_root=studio_root)
    target_dir = ensure_directory(target_path)

    for index, record in enumerate(iter_input_records(input_stream), start=1):
        stem = preferred_filename_stem(record)
        output_path = resolve_unique_markdown_path(target_dir, stem)
        metadata = build_frontmatter(schema=schema, record=record)
        markdown = Document(metadata=metadata, content=record.content).write_text()

        if debug_routing:
            print(f"[write-new] record {index} -> {output_path}", file=sys.stderr)
        atomic_write_text(output_path, markdown)


def write_new_records_with_template(
    *,
    template_path: str,
    target_path: str,
    debug_routing: bool,
    input_stream: Iterable[str],
) -> None:
    schema = load_schema_from_template(template_path=template_path)
    target_dir = ensure_directory(target_path)

    for index, record in enumerate(iter_input_records(input_stream), start=1):
        stem = preferred_filename_stem(record)
        output_path = resolve_unique_markdown_path(target_dir, stem)
        metadata = build_frontmatter(schema=schema, record=record)
        markdown = Document(metadata=metadata, content=record.content).write_text()

        if debug_routing:
            print(f"[write-new] record {index} -> {output_path}", file=sys.stderr)
        atomic_write_text(output_path, markdown)


def load_schema(*, schema_name: str, studio_root: str) -> WriteSchema:
    normalized = str(schema_name).strip()
    if not normalized:
        raise WriteError("schema name must be a non-empty string")
    if "/" in normalized or "\\" in normalized:
        raise WriteError("schema name must not contain path separators")

    root = Path(studio_root).expanduser().resolve()
    schema_dir = root / "_schemas"
    schema_path = _resolve_schema_path(schema_dir=schema_dir, schema_name=normalized)
    if schema_path is None:
        raise WriteError(f"schema not found: {normalized} under {schema_dir}")

    try:
        raw = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WriteError(f"failed to read schema: {schema_path}") from exc

    try:
        payload = Document.parse_metadata_block(raw)
    except ValueError as exc:
        raise WriteError(f"invalid schema YAML: {schema_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise WriteError(f"invalid schema file: {schema_path}")

    class_name = payload.get("class")
    if not isinstance(class_name, str) or not class_name.strip():
        raise WriteError(f"schema missing required non-empty 'class': {schema_path}")

    defaults = payload.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise WriteError(f"schema defaults must be a mapping: {schema_path}")

    schema_id = payload.get("schema")
    if isinstance(schema_id, str) and schema_id.strip():
        schema_version = schema_id.strip()
    else:
        schema_version = normalized

    return WriteSchema(
        schema=schema_version,
        class_name=class_name.strip(),
        defaults=copy.deepcopy(defaults),
    )


def load_schema_from_template(*, template_path: str) -> WriteSchema:
    path = Path(template_path).expanduser().resolve()
    if not path.is_file():
        raise WriteError(f"template file not found: {path}")

    try:
        parsed = Document.read_file(path)
    except (ValueError, OSError, FileNotFoundError) as exc:
        raise WriteError(f"failed to parse template markdown: {path}") from exc

    payload = dict(parsed.metadata or {})
    class_name = payload.get("class")
    if not isinstance(class_name, str) or not class_name.strip():
        raise WriteError(f"template missing required non-empty 'class': {path}")

    defaults = copy.deepcopy(payload)
    defaults.pop("class", None)

    return WriteSchema(
        schema=path.stem,
        class_name=class_name.strip(),
        defaults=defaults,
    )


def build_frontmatter(*, schema: WriteSchema, record: WriteRecord) -> dict[str, Any]:
    metadata: dict[str, Any] = {"class": schema.class_name, "batch": record.batch_slug}
    for key, value in schema.defaults.items():
        if key in {"class", "batch", "slug"}:
            continue
        metadata[key] = copy.deepcopy(value)

    merged_origin = record.provenance or record.origin
    if merged_origin is not None:
        metadata["origin"] = copy.deepcopy(merged_origin)

    metadata.pop("slug", None)
    return metadata


def _resolve_schema_path(*, schema_dir: Path, schema_name: str) -> Path | None:
    direct = schema_dir / schema_name
    if direct.is_file():
        return direct

    yaml_path = schema_dir / f"{schema_name}.yaml"
    if yaml_path.is_file():
        return yaml_path

    yml_path = schema_dir / f"{schema_name}.yml"
    if yml_path.is_file():
        return yml_path

    return None
