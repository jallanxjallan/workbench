"""Validate an annotated batch tag and report its basic shape."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.batch.repository import BatchRepositoryError, load_batch_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate-batch",
        description=__doc__,
    )
    parser.add_argument("batch_id", help="Batch id resolved from tag batch/<id>.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path containing the batch tag (default: current directory).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = load_batch_manifest(str(args.batch_id), repo=Path(args.repo))
    except BatchRepositoryError as exc:
        print(f"[validate-batch] error: {exc}", file=sys.stderr)
        return 1

    description = manifest.description or ""
    print(
        f"valid batch/{manifest.batch} "
        f"slugs={len(manifest.order)} "
        f"description={description!r}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
