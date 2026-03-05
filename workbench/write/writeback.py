"""Write AutoScribe batch records back to existing files."""

from __future__ import annotations

import argparse
import sys

from workbench.interop.document import Document
from workbench.lib.sentinel import (
    BATCH_SENTINEL_PATTERN,
    insert_batch_sentinel,
    read_batch_sentinel,
)
from workbench.write.common import (
    atomic_write_text,
    fetch_batch_records,
    normalize_batch_slug,
    resolve_record_slug,
    resolve_writeback_new_target_path,
    resolve_writeback_target_path,
    serialize_record,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="writeback",
        description=__doc__,
    )
    parser.add_argument(
        "batch_slug",
        help="Opaque AutoScribe batch slug.",
    )
    parser.add_argument(
        "--asc-bin",
        default="asc",
        help="AutoScribe CLI executable used for fetching records (default: asc).",
    )
    parser.add_argument(
        "--debug-routing",
        action="store_true",
        help="Print resolved routing targets for each record to stderr.",
    )
    return parser


def write_back_batch(
    batch_slug: str,
    *,
    asc_bin: str,
    debug_routing: bool,
) -> None:
    normalized_batch_slug = normalize_batch_slug(batch_slug)
    records = fetch_batch_records(normalized_batch_slug, asc_bin=asc_bin)

    for index, record in enumerate(records, start=1):
        target_path = resolve_writeback_target_path(
            record=record,
            record_index=index,
        )
        if not target_path.exists():
            raise FileNotFoundError(f"writeback: target does not exist: {target_path}")
        if target_path.is_dir():
            raise IsADirectoryError(f"writeback: target is a directory: {target_path}")

        existing_doc = Document.read_file(
            target_path,
            sentinel_pattern=BATCH_SENTINEL_PATTERN,
        )
        file_slug = existing_doc.metadata.get("slug")
        if not isinstance(file_slug, str) or not file_slug.strip():
            raise RuntimeError(f"writeback: file missing frontmatter slug: {target_path}")

        record_slug = resolve_record_slug(record, record_index=index)
        if file_slug.strip() != record_slug:
            raise RuntimeError(
                f"writeback: file slug mismatch at {target_path}: "
                f"file={file_slug!r} record={record_slug!r}"
            )

        sentinel_slug = read_batch_sentinel(target_path)
        if sentinel_slug is None:
            new_target = resolve_writeback_new_target_path(
                record=record,
                record_index=index,
                existing_path=target_path,
            )
            if new_target.exists():
                raise FileExistsError(
                    f"writeback: reroute target already exists: {new_target}"
                )
            if debug_routing:
                print(
                    f"[writeback] record {index} missing sentinel, reroute -> {new_target}",
                    file=sys.stderr,
                )
            atomic_write_text(
                new_target,
                serialize_record(record, batch_slug=normalized_batch_slug),
            )
            continue

        if sentinel_slug != normalized_batch_slug:
            raise RuntimeError(
                f"writeback: batch mismatch at {target_path}: "
                f"file={sentinel_slug!r} record={normalized_batch_slug!r}"
            )

        existing_doc.content = record.content
        if debug_routing:
            print(f"[writeback] record {index} overwrite -> {target_path}", file=sys.stderr)
        atomic_write_text(
            target_path,
            insert_batch_sentinel(
                existing_doc.write_text(),
                normalized_batch_slug,
            ),
        )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        write_back_batch(
            args.batch_slug,
            asc_bin=args.asc_bin,
            debug_routing=args.debug_routing,
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"writeback: {exc}", file=sys.stderr)
        return 1
