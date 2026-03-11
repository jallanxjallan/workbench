"""Write NDJSON records back to existing vault artifacts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from workbench.interop.document import Document
from workbench.lib.rg import RipgrepError, rg_search
from workbench.lib.regex_registry import RegexRegistryError, load_regex
from workbench.lib.sentinel import (
    BATCH_SENTINEL_PATTERN,
    read_batch_sentinel,
)
from workbench.write.common import (
    WriteError,
    atomic_write_text,
    iter_input_records,
)

MARKDOWN_SUFFIXES = (".md", ".markdown")


def build_slug_index(root: Path) -> dict[str, Path]:
    root_path = Path(root).expanduser().resolve()
    try:
        pattern = load_regex("slug_field")
    except RegexRegistryError as exc:
        raise RipgrepError(str(exc)) from exc

    matches = rg_search(pattern=pattern.pattern, root=root_path)
    files: set[Path] = set()

    for match in matches:
        line_number = match["line"]
        text = match["text"]
        _ = line_number, text
        file_path = match["path"]

        if file_path.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        files.add(file_path)

    index: dict[str, Path] = {}
    for file_path in sorted(files):
        doc = Document.read_file(file_path, sentinel_pattern=BATCH_SENTINEL_PATTERN)
        raw_slug = doc.metadata.get("slug")
        if not isinstance(raw_slug, str):
            continue
        slug = raw_slug.strip()
        if not slug or slug.lower() in {"__slug__", "null", "~"}:
            continue
        if slug in index:
            raise RipgrepError("duplicate slug detected")
        index[slug] = file_path

    return index


def write_back_records(
    *,
    studio_root: str,
    debug_routing: bool,
    input_stream: Iterable[str],
) -> None:
    try:
        slug_index = build_slug_index(Path(studio_root))
    except RipgrepError as exc:
        raise WriteError(str(exc)) from exc

    for index, record in enumerate(iter_input_records(input_stream), start=1):
        if record.slug is None:
            raise WriteError(f"record {index}: missing required record field: slug")

        target_path = slug_index.get(record.slug)
        if target_path is None:
            raise WriteError(f"slug not found: {record.slug}")
        existing_doc = Document.read_file(
            target_path,
            sentinel_pattern=BATCH_SENTINEL_PATTERN,
        )

        file_slug = existing_doc.metadata.get("slug")
        if not isinstance(file_slug, str) or not file_slug.strip():
            raise WriteError("frontmatter slug does not match record.slug")
        if file_slug.strip() != record.slug:
            raise WriteError("frontmatter slug does not match record.slug")

        sentinel_slug = read_batch_sentinel(target_path)
        if sentinel_slug is None:
            raise WriteError("batch sentinel missing")
        if sentinel_slug != record.batch_slug:
            raise WriteError("batch sentinel does not match record batch_slug")

        existing_doc.content = record.content

        if debug_routing:
            print(f"[write-back] record {index} overwrite -> {target_path}", file=sys.stderr)

        atomic_write_text(target_path, existing_doc.write_text())
