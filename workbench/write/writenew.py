"""Write AutoScribe batch records into new files."""

from __future__ import annotations

import argparse
import sys

from workbench.write.common import (
    WriteError,
    atomic_write_text,
    fetch_batch_records,
    normalize_batch_slug,
    resolve_writenew_target_path,
    serialize_record,
    validate_record_batch_slug,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="writenew",
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


def write_new_batch(
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
        target_path = resolve_writenew_target_path(
            record=record,
            record_index=index,
        )
        if target_path.exists():
            raise WriteError(f"target already exists: {target_path}")
        if debug_routing:
            print(f"[writenew] record {index} -> {target_path}", file=sys.stderr)
        atomic_write_text(target_path, serialize_record(record))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        write_new_batch(
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
