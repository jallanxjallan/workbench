from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, TextIO

import yaml

from transport import read_all_records


class WriteNewError(Exception):
    """Raised when a new file cannot be written from an NDJSON record."""


def _require_dict(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WriteNewError(f"Expected {field_name} to be a dict.")
    return value


def _require_nonempty_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WriteNewError(f"Expected {field_name} to be a non-empty string.")
    return value.strip()


def _resolve_target_dir(
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
) -> Path:
    base = (cwd or Path.cwd()).expanduser().resolve()
    target = Path(target_dir).expanduser() if target_dir is not None else base / "_ingest"

    if not target.is_absolute():
        target = (base / target).resolve()
    else:
        target = target.resolve()

    if not target.exists():
        raise WriteNewError(f"Target directory does not exist: {target}")

    if not target.is_dir():
        raise WriteNewError(f"Target path is not a directory: {target}")

    return target


def _slug_from_record(record: dict[str, Any]) -> str:
    input_record = _require_dict(record.get("input_record"), field_name="input_record")
    return _require_nonempty_string(input_record.get("slug"), field_name="input_record.slug")


def _title_case_slug_hint(slug: str) -> str:
    parts = slug.split(".")
    if len(parts) >= 2 and parts[1].strip():
        words = [word.capitalize() for word in parts[1].split("-") if word]
        if words:
            return " ".join(words)
    return slug


def _filename_hint_from_record(record: dict[str, Any], *, slug: str) -> str:
    input_record = _require_dict(record.get("input_record"), field_name="input_record")
    hint = input_record.get("filename_hint")
    if hint is None:
        return _title_case_slug_hint(slug)
    return _require_nonempty_string(hint, field_name="input_record.filename_hint")


def _content_from_record(record: dict[str, Any]) -> str:
    return _require_nonempty_string(record.get("content"), field_name="content")


def _metadata_from_record(record: dict[str, Any]) -> dict[str, Any]:
    input_record = _require_dict(record.get("input_record"), field_name="input_record")
    if not input_record:
        raise WriteNewError("input_record must be non-empty.")
    return input_record


def _normalize_filename(filename_hint: str) -> str:
    filename = Path(filename_hint).name.strip()

    if not filename:
        raise WriteNewError("Filename hint resolves to an empty filename.")

    if filename in {".", ".."}:
        raise WriteNewError(f"Invalid filename hint: {filename_hint}")

    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    return filename


def _destination_for_record(record: dict[str, Any], *, target_dir: Path) -> Path:
    slug = _slug_from_record(record)
    filename_hint = _filename_hint_from_record(record, slug=slug)
    filename = _normalize_filename(filename_hint)
    destination = (target_dir / filename).resolve()

    if destination.parent != target_dir:
        raise WriteNewError(f"Destination escapes target directory: {destination}")

    if destination.exists():
        raise WriteNewError(f"Destination already exists: {destination}")

    return destination


def _render_with_pandoc(
    *,
    content: str,
    metadata: dict[str, Any],
    destination: Path,
    pandoc_bin: str = "pandoc",
) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".yaml",
        delete=False,
    ) as handle:
        yaml.safe_dump(
            metadata,
            handle,
            allow_unicode=True,
            sort_keys=False,
        )
        metadata_path = Path(handle.name)

    try:
        result = subprocess.run(
            [
                pandoc_bin,
                "--from",
                "markdown",
                "--to",
                "markdown",
                "--standalone",
                "--metadata-file",
                str(metadata_path),
                "--output",
                str(destination),
            ],
            input=content,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise WriteNewError(f"Pandoc executable not found: {pandoc_bin}") from exc
    finally:
        metadata_path.unlink(missing_ok=True)

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or f"pandoc exited with status {result.returncode}"
        raise WriteNewError(f"Pandoc failed for {destination.name}: {details}")

    if not destination.exists():
        raise WriteNewError(f"Pandoc reported success but no file was written: {destination}")


def writenew_record(
    record: dict[str, Any],
    *,
    target_dir: Path,
    pandoc_bin: str = "pandoc",
) -> Path:
    if not isinstance(record, dict):
        raise WriteNewError("Record must be a dict.")

    destination = _destination_for_record(record, target_dir=target_dir)
    content = _content_from_record(record)
    metadata = _metadata_from_record(record)

    _render_with_pandoc(
        content=content,
        metadata=metadata,
        destination=destination,
        pandoc_bin=pandoc_bin,
    )
    return destination


def resolve_writenew_target(
    *,
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
) -> tuple[Path, str]:
    resolved = _resolve_target_dir(cwd=cwd, target_dir=target_dir)
    return resolved.parent, resolved.name


def parse_top_level_overrides(items: list[str]) -> dict[str, object]:
    if items:
        raise WriteNewError("--set overrides are not supported by writenew")
    return {}


def run_writenew(
    input_stream: TextIO,
    *,
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
    overrides: dict[str, object] | None = None,
    pandoc_bin: str = "pandoc",
) -> None:
    if overrides:
        raise WriteNewError("--set overrides are not supported by writenew")

    resolved_target_dir = _resolve_target_dir(cwd=cwd, target_dir=target_dir)

    try:
        records = read_all_records(input_stream)
    except ValueError as exc:
        raise WriteNewError(str(exc)) from exc

    for index, record in enumerate(records, start=1):
        try:
            writenew_record(
                record,
                target_dir=resolved_target_dir,
                pandoc_bin=pandoc_bin,
            )
        except WriteNewError as exc:
            raise WriteNewError(f"Record {index}: {exc}") from exc


def writenew_stream(
    input_stream: TextIO,
    *,
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
    overrides: dict[str, object] | None = None,
) -> None:
    run_writenew(
        input_stream,
        cwd=cwd,
        target_dir=target_dir,
        overrides=overrides,
    )


def prepare_writenew_stream(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
    overrides: dict[str, object] | None = None,
) -> None:
    del output_stream
    run_writenew(
        input_stream,
        cwd=cwd,
        target_dir=target_dir,
        overrides=overrides,
    )
