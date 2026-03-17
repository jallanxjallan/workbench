"""Compile an ordered vault-local batch tag and ingest the full NDJSON payload."""

from __future__ import annotations

import argparse
from pathlib import Path

from workbench.control.compile_batch import DEFAULT_INGEST_COMMAND, compile_batch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile-batch",
        description=__doc__,
    )
    parser.add_argument("batch_slug", help="Batch slug to compile from batch/<slug>.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Path inside the target vault repository (default: current directory).",
    )
    parser.add_argument(
        "--ingest-command",
        default=" ".join(DEFAULT_INGEST_COMMAND),
        help="Command used for ASC ingest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    ingest_command = tuple(part for part in str(args.ingest_command).strip().split(" ") if part)
    if not ingest_command:
        print("[compile-batch] error: ingest command cannot be empty")
        return 1

    return compile_batch(
        batch_slug=str(args.batch_slug),
        repo=Path(args.repo),
        ingest_command=ingest_command,
    )


if __name__ == "__main__":
    raise SystemExit(main())
