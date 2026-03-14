"""Resolve a batch commit into ordered file paths."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.config.roots import STUDIO_ROOT
from workbench.control.batch import BatchCommitError, load_batch_from_git_commit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="select-records",
        description=__doc__,
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path that contains the batch commit (default: current directory).",
    )
    parser.add_argument(
        "--commit",
        default="HEAD",
        help="Commit reference to inspect (default: HEAD).",
    )
    parser.add_argument(
        "--vault-root",
        action="append",
        default=None,
        help=f"Vault root used for slug resolution. Repeatable. Default: {STUDIO_ROOT}.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    roots = (
        tuple(Path(value).expanduser().resolve() for value in args.vault_root)
        if args.vault_root
        else (STUDIO_ROOT,)
    )

    try:
        batch = load_batch_from_git_commit(
            Path(args.repo),
            commit=str(args.commit),
            roots=roots,
        )
    except BatchCommitError as exc:
        print(f"[select-records] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[select-records] error: {exc}", file=sys.stderr)
        return 1

    for path in batch.files:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
