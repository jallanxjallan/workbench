from __future__ import annotations

from pathlib import Path
from typing import Any, TextIO

from scan import RipgrepError, resolve_slug_to_filepath
from transport import iter_records, read_text, write_record
from vault.validate import require_vault_root


class SlugToPathError(RuntimeError):
    """Raised when slug-to-path streaming cannot resolve a canonical record."""


def _require_dict(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SlugToPathError(f"{field_name} must be an object")
    return value


def _require_slug(record: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    input_record = _require_dict(record.get("input_record"), field_name="input_record")
    slug = input_record.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise SlugToPathError("input_record.slug must be a non-empty string")
    return slug.strip(), dict(input_record)


def stream_slug_to_path_records(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    cwd: Path | None = None,
) -> None:
    vault_root = require_vault_root(Path.cwd() if cwd is None else cwd)
    index = 0

    try:
        for index, record in enumerate(iter_records(input_stream), start=1):
            slug, input_record = _require_slug(record)
            resolved_path = resolve_slug_to_filepath(slug, vault_root)
            origin = _require_dict(
                input_record.get("origin", {}),
                field_name="input_record.origin",
            )
            origin["filepath"] = str(resolved_path)
            input_record["origin"] = origin
            write_record(
                output_stream,
                {
                    "content": read_text(resolved_path),
                    "input_record": input_record,
                },
            )
    except (SlugToPathError, RipgrepError, ValueError, OSError) as exc:
        raise SlugToPathError(f"slug_to_path failed at record {index}: {exc}") from exc
