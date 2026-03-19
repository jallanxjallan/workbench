"""Git confirmation commands."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.batch import InflightTagError, confirm_inflight


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="confirm",
        description=__doc__,
    )
    subparsers = parser.add_subparsers(dest="confirm_command", required=True)

    inflight = subparsers.add_parser(
        "inflight",
        help="Create an inflight/<batch-id> tag after successful ingest.",
    )
    inflight.add_argument("batch_id", help="Batch id to confirm.")
    inflight.add_argument(
        "--repo",
        default=".",
        help="Path inside the target vault repository (default: current directory).",
    )
    inflight.add_argument(
        "--push",
        action="store_true",
        help="Push the new inflight tag after creating it locally.",
    )
    inflight.add_argument(
        "--remote",
        default="origin",
        help="Remote used when --push is enabled (default: origin).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.confirm_command != "inflight":
        print(f"[confirm] error: unsupported confirm command: {args.confirm_command}", file=sys.stderr)
        return 1

    try:
        tag_name = confirm_inflight(
            batch_id=str(args.batch_id),
            repo=Path(args.repo),
            push=bool(args.push),
            remote=str(args.remote),
        )
    except InflightTagError as exc:
        print(f"[confirm] error: {exc}", file=sys.stderr)
        return 1

    print(tag_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
