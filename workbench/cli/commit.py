"""Create standardized repository commits from message templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workbench.runtime.git_repo import GitRepoError, commit_batch, get_repo_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="commit",
        description=__doc__,
    )
    parser.add_argument("commit_type", help="Commit template key (for example INIT or STYLE).")
    parser.add_argument("batch_slug", help="Batch slug used for template rendering.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path (default: current directory).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        repo = get_repo_root(Path(args.repo))
        commit_hash = commit_batch(repo, args.batch_slug, args.commit_type)
    except GitRepoError as exc:
        print(f"[commit] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[commit] error: {exc}", file=sys.stderr)
        return 1

    print(commit_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
