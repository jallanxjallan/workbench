"""Pure ingest writer for NDJSON streams."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from workbench.runtime.vaults import is_obsidian_vault
from workbench.io.files import atomic_write_text
from workbench.write.common import WriteError


INGEST_DIRNAME = "_ingest"
WRITEVAULT_LOG_FILENAME = "writevault.log"


@dataclass(frozen=True)
class WritevaultSummary:
    records_processed: int = 0
    files_written: int = 0
    skipped_slug: int = 0
    skipped_missing_content: int = 0
    skipped_invalid_ndjson: int = 0
    skipped_filesystem_error: int = 0


def discover_vault_root(start: Path) -> Path:
    candidate = start.expanduser().resolve()
    for path in (candidate, *candidate.parents):
        if is_obsidian_vault(path):
            return path
    raise WriteError("writevault must be run inside an Obsidian vault")


def write_ingest_records(
    *,
    input_stream: Iterable[str],
    cwd: Path | None = None,
    log_path: Path | None = None,
    debug_routing: bool = False,
) -> list[Path]:
    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    vault_root = discover_vault_root(working_dir)
    ingest_dir = (vault_root / INGEST_DIRNAME).resolve()
    ingest_dir.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []
    processed = 0
    written = 0
    skipped_slug = 0
    skipped_missing_content = 0
    skipped_invalid_ndjson = 0
    skipped_filesystem_error = 0

    for line_number, raw_line in enumerate(input_stream, start=1):
        if not raw_line.strip():
            continue
        processed += 1
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            skipped_invalid_ndjson += 1
            _log_warning(
                log_path,
                f"writevault warning: invalid NDJSON record skipped ({exc})",
            )
            continue

        if not isinstance(record, dict):
            skipped_invalid_ndjson += 1
            _log_warning(log_path, "writevault warning: non-object record skipped")
            continue

        content = record.get("content")
        if not isinstance(content, str) or content == "":
            skipped_missing_content += 1
            _log_warning(log_path, "writevault warning: record missing content")
            continue

        input_record = record.get("input_record")
        if input_record is None:
            input_record = {}
        if not isinstance(input_record, dict):
            skipped_invalid_ndjson += 1
            _log_warning(log_path, "writevault warning: invalid input_record skipped")
            continue

        slug = _clean_optional_string(input_record.get("slug"))
        if slug is not None:
            skipped_slug += 1
            _log_warning(
                log_path,
                "writevault warning: slug detected in ingest stream\n"
                f"slug: {slug}\n"
                "record skipped",
            )
            continue

        try:
            target_path = _resolve_target_path(ingest_dir=ingest_dir, record=record)
            atomic_write_text(target_path, content)
        except OSError as exc:
            skipped_filesystem_error += 1
            _log_warning(
                log_path,
                f"writevault warning: filesystem error writing record ({exc})",
            )
            continue

        if debug_routing:
            print(f"[writevault] record {line_number} -> {target_path}")

        written += 1
        written_paths.append(target_path)

    _log_summary(
        log_path,
        WritevaultSummary(
            records_processed=processed,
            files_written=written,
            skipped_slug=skipped_slug,
            skipped_missing_content=skipped_missing_content,
            skipped_invalid_ndjson=skipped_invalid_ndjson,
            skipped_filesystem_error=skipped_filesystem_error,
        ),
    )
    return written_paths


def default_log_path() -> Path:
    return Path.home().resolve() / ".autoscribe" / "logs" / WRITEVAULT_LOG_FILENAME


def _resolve_target_path(*, ingest_dir: Path, record: dict[str, Any]) -> Path:
    filename_hint = _extract_filename_hint(record)
    if filename_hint is not None:
        return _unique_path(ingest_dir, filename_hint)
    return _next_untitled_path(ingest_dir)


def _extract_filename_hint(record: dict[str, Any]) -> str | None:
    input_record = record.get("input_record")
    if not isinstance(input_record, dict):
        return None
    raw_hint = input_record.get("filename_hint")
    if not isinstance(raw_hint, str):
        return None
    hint = raw_hint.strip()
    if not hint:
        return None
    candidate = Path(hint)
    if not candidate.name == hint:
        return None
    suffix = candidate.suffix.lower()
    if suffix in {"", ".md", ".markdown"}:
        return candidate.name if suffix else f"{candidate.name}.md"
    return f"{candidate.stem}.md"


def _unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem or "Untitled"
    suffix = candidate.suffix or ".md"
    counter = 2
    while True:
        numbered = directory / f"{stem}_{counter}{suffix}"
        if not numbered.exists():
            return numbered
        counter += 1


def _next_untitled_path(directory: Path) -> Path:
    return _unique_path(directory, "Untitled.md")


def _clean_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _log_summary(log_path: Path | None, summary: WritevaultSummary) -> None:
    _append_log(
        log_path,
        "\n".join(
            [
                "writevault",
                f"records processed: {summary.records_processed}",
                f"files written: {summary.files_written}",
                f"skipped (slug present): {summary.skipped_slug}",
                f"skipped (missing content): {summary.skipped_missing_content}",
                f"skipped (invalid NDJSON): {summary.skipped_invalid_ndjson}",
                f"skipped (filesystem error): {summary.skipped_filesystem_error}",
            ]
        ),
    )


def _log_warning(log_path: Path | None, message: str) -> None:
    _append_log(log_path, message)


def _append_log(log_path: Path | None, message: str) -> None:
    target = log_path or default_log_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
    except OSError:
        return


__all__ = [
    "INGEST_DIRNAME",
    "WRITEVAULT_LOG_FILENAME",
    "default_log_path",
    "discover_vault_root",
    "write_ingest_records",
]
