"""Write NDJSON records back to existing vault artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from workbench.interop.document import Document
from workbench.lib.rg import RipgrepError, rg_search
from workbench.lib.sentinel import (
    BATCH_SENTINEL_PATTERN,
    read_batch_sentinel,
)
from workbench.write.common import (
    WriteError,
    atomic_write_text,
    has_piped_stdin,
    iter_input_records,
)

MARKDOWN_SUFFIXES = (".md", ".markdown")


def build_slug_index(root: Path) -> dict[str, Path]:
    root_path = Path(root).expanduser().resolve()
    matches = rg_search(r"slug:\s*\S+", root_path)
    files: set[Path] = set()

    for line in matches:
        try:
            row = json.loads(line)
            raw_path = row["path"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue

        file_path = Path(raw_path)
        if file_path.is_absolute():
            resolved = file_path.resolve()
        else:
            resolved = (root_path / file_path).resolve()
        if resolved.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        files.add(resolved)

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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="write-back",
        description=__doc__,
    )
    parser.add_argument(
        "--studio-root",
        default=str(Path.home().resolve() / "Studio"),
        help="Studio root used for ripgrep slug resolution (default: ~/Studio).",
    )
    return parser


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


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        parser.print_usage(sys.stderr)
        print("ERROR: expected NDJSON input from stdin (pipe or < file)", file=sys.stderr)
        return 1
    try:
        write_back_records(
            studio_root=args.studio_root,
            debug_routing=False,
            input_stream=sys.stdin,
        )
        return 0
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
