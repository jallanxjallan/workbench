"""Scan markdown files for ASC batch sentinel lines."""

from __future__ import annotations

import argparse
import json
import sys

from workbench.config.roots import STUDIO_ROOT
from workbench.lib.sentinel_scan import SentinelScanError, scan_paths_for_batch_sentinel


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scan-sentinel",
        description=__doc__,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Studio-root relative files/directories to scan (default: .).",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Traverse symlink directories while scanning.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    raw_paths = args.paths or ["."]

    try:
        rows = scan_paths_for_batch_sentinel(
            root=STUDIO_ROOT,
            raw_paths=raw_paths,
            follow_symlinks=args.follow_symlinks,
        )
        for path in rows:
            sys.stdout.write(json.dumps({"path": path}, ensure_ascii=False) + "\n")
        return 0
    except SentinelScanError as exc:
        print(f"[scan-sentinel] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
