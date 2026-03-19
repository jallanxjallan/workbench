"""Emit canonical NDJSON slug records from a batch tag."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.batch.repository import BatchRepositoryError, load_batch_manifest
from workbench.ingest.records import dump_record, make_record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batch-slugs",
        description=__doc__,
    )
    parser.add_argument("batch_id", help="Batch id resolved from tag batch/<id>.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path containing the batch tag (default: current directory).",
    )
    return parser


def emit_batch_slug_records(*, batch_id: str, repo: Path | str = ".", stdout: object | None = None) -> int:
    stream = sys.stdout if stdout is None else stdout
    try:
        manifest = load_batch_manifest(batch_id, repo=repo)
    except BatchRepositoryError as exc:
        print(f"[batch-slugs] error: {exc}", file=sys.stderr)
        return 1

    for slug in manifest.order:
        stream.write(dump_record(make_record(content="", input_record={"slug": slug})))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return emit_batch_slug_records(
        batch_id=str(args.batch_id),
        repo=Path(args.repo),
    )


if __name__ == "__main__":
    raise SystemExit(main())
