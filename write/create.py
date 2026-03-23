"""NDJSON writenew execution for the current registered vault."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from records.files import write_new_text
from write.common import (
    WriteError,
    WriteRecord,
    derive_new_path,
    iter_input_records,
    resolve_writenew_directory,
)
from write.frontmatter import (
    FrontmatterBuildError,
    VaultContext,
    build_writenew_document,
    discover_writenew_vault_context,
)

DEFAULT_TEMPLATE_ID = "content"
DEFAULT_KIND = "passage"


def run(
    *,
    input_stream: Iterable[str],
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
    overrides: dict[str, object] | None = None,
) -> None:
    writenew(
        input_stream=input_stream,
        cwd=cwd,
        target_dir=target_dir,
        template_id=DEFAULT_TEMPLATE_ID,
        class_name=DEFAULT_KIND,
        overrides=overrides,
    )


def writenew(
    *,
    input_stream: Iterable[str],
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
    template_id: str | None = None,
    class_name: str | None = None,
    overrides: dict[str, object] | None = None,
) -> list[Path]:
    records = list(iter_input_records(input_stream))
    directory = resolve_writenew_directory(cwd=cwd, target_dir=target_dir)
    try:
        vault_context = discover_writenew_vault_context(cwd=cwd)
    except RuntimeError as exc:
        raise WriteError(str(exc)) from exc

    return _writenew_records(
        records,
        directory,
        template_id=template_id or DEFAULT_TEMPLATE_ID,
        class_name=class_name,
        overrides=overrides,
        vault_context=vault_context,
    )


def _writenew_records(
    records: list[WriteRecord],
    directory: Path,
    *,
    template_id: str,
    class_name: str | None,
    overrides: dict[str, object] | None,
    vault_context: VaultContext,
) -> list[Path]:
    written_paths: list[Path] = []

    for index, record in enumerate(records, start=1):
        path = derive_new_path(record, directory).resolve()
        record_overrides: dict[str, Any] = dict(overrides or {})
        record_overrides["input_record"] = dict(record.input_record.envelope)
        try:
            content = build_writenew_document(
                source_text=record.content,
                template_id=template_id,
                class_name=class_name,
                target_path=path,
                vault_context=vault_context,
                overrides=record_overrides,
            )
        except FrontmatterBuildError as exc:
            raise WriteError(
                _format_writenew_error(index=index, record=record, path=path, reason=str(exc))
            ) from exc

        try:
            write_new_text(path, content)
        except FileExistsError as exc:
            raise WriteError(
                _format_writenew_error(index=index, record=record, path=path, reason="file exists")
            ) from exc
        except OSError as exc:
            raise WriteError(
                _format_writenew_error(index=index, record=record, path=path, reason=str(exc))
            ) from exc
        written_paths.append(path)

    return written_paths


def _format_writenew_error(*, index: int, record: WriteRecord, path: Path, reason: str) -> str:
    slug = record.input_record.slug
    if slug:
        return f"writenew failed: record {index}: slug {slug}: {path}: {reason}"
    return f"writenew failed: record {index}: {path}: {reason}"
