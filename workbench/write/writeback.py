"""Write AutoScribe batch records back to existing files."""

from __future__ import annotations

import argparse
import copy
import sys

from workbench.interop.document import Document
from workbench.lib.sentinel import (
    BATCH_SENTINEL_PATTERN,
    insert_batch_sentinel,
    read_batch_sentinel,
)
from workbench.write.common import (
    WriteError,
    atomic_write_text,
    fetch_batch_records,
    normalize_batch_slug,
    resolve_origin_slug,
    resolve_writeback_target_path,
    validate_record_batch_slug,
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
    requested_batch_slug = normalize_batch_slug(batch_slug)

    for index, record in enumerate(
        fetch_batch_records(requested_batch_slug, asc_bin=asc_bin),
        start=1,
    ):
        validate_record_batch_slug(
            record=record,
            requested_batch_slug=requested_batch_slug,
            record_index=index,
        )

        target_path = resolve_writeback_target_path(
            record=record,
            record_index=index,
        )
        if not target_path.exists():
            raise WriteError(f"target does not exist: {target_path}")
        if target_path.is_dir():
            raise WriteError(f"target path is a directory: {target_path}")

        existing_doc = Document.read_file(
            target_path,
            sentinel_pattern=BATCH_SENTINEL_PATTERN,
        )

        origin_slug = resolve_origin_slug(record=record, record_index=index)
        if origin_slug is not None:
            file_slug = existing_doc.metadata.get("slug")
            if not isinstance(file_slug, str) or not file_slug.strip():
                raise WriteError("frontmatter slug does not match record origin.slug")
            if file_slug.strip() != origin_slug:
                raise WriteError("frontmatter slug does not match record origin.slug")

        sentinel_slug = read_batch_sentinel(target_path)
        if sentinel_slug != record.batch_slug:
            raise WriteError("batch sentinel does not match record batch_slug")

        existing_doc.metadata["autoscribe"] = copy.deepcopy(record.envelope)
        existing_doc.content = record.content

        if debug_routing:
            print(f"[writeback] record {index} overwrite -> {target_path}", file=sys.stderr)
        atomic_write_text(
            target_path,
            insert_batch_sentinel(
                existing_doc.write_text(),
                record.batch_slug,
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
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
