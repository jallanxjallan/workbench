"""Show the raw git object for an annotated batch tag."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.runtime.git_repo import GitRepoError, git


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="show-batch",
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
    batch_id = str(args.batch_id).strip()
    if not batch_id:
        print("[show-batch] error: batch id is required", file=sys.stderr)
        return 1

    try:
        output = git(Path(args.repo), "show", f"batch/{batch_id}")
    except GitRepoError as exc:
        print(f"[show-batch] error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(output)
    if not output.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
