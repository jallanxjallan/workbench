"""Ingest an ordered batch tag through Pandoc and ASC, then confirm inflight."""

from __future__ import annotations

import argparse
from pathlib import Path

from workbench.control.ingest_batch import DEFAULT_INGEST_COMMAND, run_and_confirm


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest-batch",
        description=__doc__,
    )
    parser.add_argument("batch_id", help="Batch id to ingest from batch/<batch-id>.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Path inside the target vault repository (default: current directory).",
    )
    parser.add_argument(
        "--ingest-command",
        default=" ".join(DEFAULT_INGEST_COMMAND),
        help="ASC ingest command prefix (default: asc ingest).",
    )
    parser.add_argument(
        "--push-inflight",
        action="store_true",
        help="Push the inflight tag after local creation.",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Remote used when --push-inflight is enabled (default: origin).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    ingest_command = tuple(part for part in str(args.ingest_command).strip().split(" ") if part)
    if not ingest_command:
        print("[ingest-batch] error: ingest command cannot be empty")
        return 1

    return run_and_confirm(
        batch_id=str(args.batch_id),
        repo=Path(args.repo),
        ingest_command=ingest_command,
        push_inflight=bool(args.push_inflight),
        remote=str(args.remote),
    )


if __name__ == "__main__":
    raise SystemExit(main())
