"""Write AutoScribe batch records back to existing files."""

from __future__ import annotations

import argparse
import sys

from workbench.write.common import (
    atomic_write_text,
    fetch_batch_records,
    normalize_batch_slug,
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
        if debug_routing:
            print(f"[writeback] record {index} -> {target_path}", file=sys.stderr)
        atomic_write_text(
            target_path,
            serialize_record(record, batch_slug=normalized_batch_slug),
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
