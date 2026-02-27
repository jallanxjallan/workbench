"""Shared helpers for write command implementations."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workbench.config.vault_registry import VaultRegistry, VaultRegistryError
from workbench.lib.ndjson import StreamError, parse_ndjson
from workbench.lib.subprocess import CommandError, run_text
from workbench.interop.document import Document

_BATCH_SENTINEL_TEMPLATE = "--- ASC BATCH: {batch_slug} ---"
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


class WriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class WriteRecord:
    metadata: dict[str, Any]
    content: str


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        delete=False,
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def normalize_batch_slug(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise WriteError("batch slug must be a non-empty string")
    return normalized


def fetch_batch_records(batch_slug: str, *, asc_bin: str = "asc") -> list[WriteRecord]:
    slug = normalize_batch_slug(batch_slug)
    try:
        text = run_text([asc_bin, "emit", slug], check=True)
    except CommandError as exc:
        raise WriteError(f"failed to fetch records for batch '{slug}': {exc}") from exc

    try:
        raw_records = list(parse_ndjson(text.splitlines()))
    except StreamError as exc:
        raise WriteError(f"invalid NDJSON emitted for batch '{slug}': {exc}") from exc

    output: list[WriteRecord] = []
    for index, record in enumerate(raw_records, start=1):
        output.append(_coerce_record(record=record, index=index))
    return output


def _coerce_record(*, record: dict[str, Any], index: int) -> WriteRecord:
    content = record.get("content")
    if not isinstance(content, str):
        raise WriteError(f"record {index} missing string 'content' field")

    metadata: dict[str, Any] = {}
    from_metadata = record.get("metadata")
    if isinstance(from_metadata, dict):
        metadata.update(from_metadata)

    input_record = record.get("input_record")
    if isinstance(input_record, dict):
        for key, value in input_record.items():
            metadata.setdefault(str(key), value)

    for key in (
        "target_path",
        "source_path",
        "filepath",
        "path",
        "prompt_slug",
        "instruction_slug",
        "title",
        "slug",
    ):
        if key in record:
            metadata.setdefault(key, record[key])

    return WriteRecord(metadata=metadata, content=content)


def derive_routing_prefix(metadata: dict[str, Any]) -> str | None:
    for key in ("prompt_slug", "instruction_slug"):
        value = metadata.get(key)
        if not isinstance(value, str):
            continue
        raw = value.strip()
        if not raw:
            continue
        head = raw.split(".", 1)[0].strip()
        if head:
            return head
    return None


def resolve_target_path(
    *,
    metadata: dict[str, Any],
    registry: VaultRegistry,
    record_index: int,
) -> Path:
    target = _first_string(metadata, "target_path")
    if target:
        candidate = Path(target).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        prefix = derive_routing_prefix(metadata)
        if not prefix:
            raise WriteError(
                f"record {record_index} uses relative target_path but has no prompt_slug/instruction_slug prefix"
            )
        base = _resolve_base_path(registry=registry, prefix=prefix)
        return (base / candidate).resolve()

    base_prefix = derive_routing_prefix(metadata)
    if not base_prefix:
        raise WriteError(
            f"record {record_index} missing routing metadata; provide target_path, prompt_slug, or instruction_slug"
        )
    base = _resolve_base_path(registry=registry, prefix=base_prefix)

    relative = _first_string(metadata, "source_path", "filepath", "path")
    if relative:
        candidate = Path(relative).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (base / candidate).resolve()

    filename = _derive_filename(metadata=metadata, record_index=record_index)
    return base / filename


def serialize_record(record: WriteRecord, *, batch_slug: str) -> str:
    document = Document(metadata=record.metadata, content=record.content)
    sentinel = _BATCH_SENTINEL_TEMPLATE.format(batch_slug=normalize_batch_slug(batch_slug))
    return f"{sentinel}\n{document.write_text()}"


def _resolve_base_path(*, registry: VaultRegistry, prefix: str) -> Path:
    try:
        return registry.resolve_base_path(prefix)
    except VaultRegistryError as exc:
        raise WriteError(str(exc)) from exc


def _first_string(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _derive_filename(*, metadata: dict[str, Any], record_index: int) -> str:
    explicit = _first_string(metadata, "slug")
    if explicit:
        return f"{_slugify(explicit)}.md"

    title = _first_string(metadata, "title")
    if title:
        return f"{_slugify(title)}.md"

    return f"record-{record_index:03d}.md"


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = _NON_ALNUM_RE.sub("-", normalized)
    normalized = normalized.strip("-")
    return normalized or "document"
