from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.lib.ndjson import emit_ndjson

try:
    from workbench.ingest._sentinel_scan import (
        SelectError,
        scan_batch_sentinel_records,
    )
except ImportError:  # pragma: no cover - script-mode fallback
    from _sentinel_scan import SelectError, scan_batch_sentinel_records


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="select_sentinel.py",
        description="Select markdown paths containing ASC batch sentinel lines.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Project-root relative files/directories to scan (default: .).",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Traverse symlink directories while scanning.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cwd = Path.cwd().resolve()
    raw_paths = args.paths or ["."]

    try:
        rows = scan_batch_sentinel_records(
            cwd=cwd,
            raw_paths=raw_paths,
            follow_symlinks=args.follow_symlinks,
        )

        for row in rows:
            sys.stdout.write(emit_ndjson({"path": row["path"]}) + "\n")
        return 0
    except SelectError as exc:
        print(f"[select_sentinel] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
