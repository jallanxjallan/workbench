"""Publish compiled control/context instruction payloads to ASC ingest."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
from typing import Any

from workbench.config.roots import STUDIO_ROOT, WORKBENCH_ROOT
from workbench.control.compile import DEFAULT_COMPILED_CONTROL_ROOT
from workbench.interop.document import Document
from workbench.runtime.vaults import studio_vault_roots

ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
DEFAULT_INGEST_COMMAND = ("asc-ingest",)
DEFAULT_COMPILED_CONTEXT_ROOT = WORKBENCH_ROOT / "_compiled" / "context"
_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_SKIP_DIR_NAMES = frozenset({
    ".git",
    ".obsidian",
    "__pycache__",
    "_compiled",
    "_control",
    "_staging",
    "archive",
    "node_modules",
    "venv",
    ".venv",
})


class ControlPublishError(RuntimeError):
    """Raised when publish flow fails."""


def _encode_ulid(value: int) -> str:
    chars: list[str] = []
    remaining = value
    for _ in range(26):
        chars.append(ULID_ALPHABET[remaining & 0x1F])
        remaining >>= 5
    return "".join(reversed(chars))


def _generate_ulid() -> str:
    timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if timestamp_ms >= (1 << 48):
        raise ControlPublishError("ULID timestamp overflow")
    randomness = secrets.randbits(80)
    return _encode_ulid((timestamp_ms << 80) | randomness)


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ControlPublishError(f"compiled artifact not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ControlPublishError(f"invalid JSON artifact: {path}") from exc


def _build_control_records(compiled_root: Path) -> list[dict[str, str]]:
    payload = _read_json(compiled_root / "global_instructions.json")
    if not isinstance(payload, dict):
        raise ControlPublishError("global_instructions.json must be an object")
    entries = payload.get("global_instructions")
    if not isinstance(entries, list):
        raise ControlPublishError("global_instructions payload must include a list")

    records: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ControlPublishError("global_instructions entries must be objects")
        slug = entry.get("slug")
        sysmessage = entry.get("sysmessage")
        if not isinstance(slug, str) or not slug.strip():
            raise ControlPublishError("global_instructions entry missing slug")
        if not isinstance(sysmessage, str) or not sysmessage.strip():
            raise ControlPublishError(f"global instruction {repr(slug)} missing sysmessage")
        records.append(
            {
                "ulid": _generate_ulid(),
                "slug": slug.strip(),
                "sysmessage": sysmessage.strip(),
            }
        )
    return records


def _run_ingest(
    *,
    records: list[dict[str, str]],
    command: tuple[str, ...],
) -> None:
    ndjson = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    try:
        process = subprocess.run(
            list(command),
            input=ndjson,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ControlPublishError(f"ingest command not found: {command[0]}") from exc

    if not process.returncode == 0:
        detail = process.stderr.strip() or process.stdout.strip() or "ingest command failed"
        raise ControlPublishError(detail)


def publish_control(
    *,
    compiled_root: Path = DEFAULT_COMPILED_CONTROL_ROOT,
    ingest_command: tuple[str, ...] = DEFAULT_INGEST_COMMAND,
    dry_run: bool = False,
    ndjson_out: Path | None = None,
) -> list[dict[str, str]]:
    records = _build_control_records(Path(compiled_root).expanduser().resolve())
    if ndjson_out is not None:
        output = Path(ndjson_out).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )
    if not dry_run:
        _run_ingest(records=records, command=ingest_command)
    print(f"published control instructions={len(records)} dry_run={str(dry_run).lower()}")
    return records


def _extract_instruction(path: Path) -> tuple[str, str, str] | None:
    inspected = Document.inspect_file(path)
    if inspected.error:
        raise ControlPublishError(f"invalid instruction markdown {path}: {inspected.error}")
    if not inspected.has_frontmatter or not isinstance(inspected.metadata, dict):
        return None

    metadata = inspected.metadata
    if not metadata.get("type") == "instruction":
        return None

    raw_slug = metadata.get("slug")
    raw_scope = metadata.get("scope")
    if not isinstance(raw_slug, str) or not raw_slug.strip():
        raise ControlPublishError(f"instruction missing slug: {path}")
    if not isinstance(raw_scope, str) or not raw_scope.strip():
        prefix = raw_slug.strip().split(".", 1)[0]
        raw_scope = {"cxt": "context", "spc": "specific", "ins": "specific"}.get(prefix)
    if raw_scope not in {"context", "specific"}:
        return None

    body = inspected.body.strip()
    if not body:
        raise ControlPublishError(f"instruction body is empty: {path}")

    return raw_slug.strip(), body, raw_scope


def _iter_markdown_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in _SKIP_DIR_NAMES)
        current_path = Path(current_root)
        for filename in sorted(filenames):
            candidate = current_path / filename
            if candidate.suffix.lower() not in _MARKDOWN_SUFFIXES:
                continue
            paths.append(candidate.resolve())
    return paths


def _compile_context_payload(studio_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    contexts: list[dict[str, str]] = []
    specifics: list[dict[str, str]] = []
    for vault_root in studio_vault_roots(Path(studio_root)):
        for source in _iter_markdown_files(vault_root):
            extracted = _extract_instruction(source)
            if extracted is None:
                continue
            slug, sysmessage, scope = extracted
            record = {"slug": slug, "sysmessage": sysmessage}
            if scope == "context":
                contexts.append(record)
            else:
                specifics.append(record)
    return contexts, specifics


def publish_context(
    *,
    studio_root: Path = STUDIO_ROOT,
    compiled_root: Path = DEFAULT_COMPILED_CONTEXT_ROOT,
    ingest_command: tuple[str, ...] = DEFAULT_INGEST_COMMAND,
    dry_run: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    root = Path(studio_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ControlPublishError(f"studio root not found: {root}")

    context_records, specific_records = _compile_context_payload(root)
    output_root = Path(compiled_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "context_instructions.json").write_text(
        json.dumps({"context_instructions": context_records}, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_root / "specific_instructions.json").write_text(
        json.dumps({"specific_instructions": specific_records}, indent=2) + "\n",
        encoding="utf-8",
    )

    publish_records = [
        {"ulid": _generate_ulid(), **record, "scope": "context"}
        for record in context_records
    ] + [
        {"ulid": _generate_ulid(), **record, "scope": "specific"}
        for record in specific_records
    ]

    if not dry_run and publish_records:
        _run_ingest(records=publish_records, command=ingest_command)
    print(
        "published context "
        f"context={len(context_records)} specific={len(specific_records)} "
        f"dry_run={str(dry_run).lower()}"
    )
    return context_records, specific_records


__all__ = [
    "ControlPublishError",
    "DEFAULT_COMPILED_CONTEXT_ROOT",
    "DEFAULT_INGEST_COMMAND",
    "publish_context",
    "publish_control",
]
