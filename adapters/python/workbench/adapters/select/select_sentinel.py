from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

try:
    from workbench.adapters.select.sentinel_scan import (
        SelectError,
        scan_batch_sentinel_records,
    )
    from workbench.adapters.select.snapshot_boundary import prepare_snapshot_boundary
except ImportError:  # pragma: no cover - script-mode fallback
    from sentinel_scan import SelectError, scan_batch_sentinel_records
    from snapshot_boundary import prepare_snapshot_boundary


_BATCH_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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
    parser.add_argument(
        "--batch-slug",
        help="Explicit batch slug for snapshot commit metadata.",
    )

    snapshot_group = parser.add_mutually_exclusive_group()
    snapshot_group.add_argument(
        "--snapshot",
        dest="snapshot",
        action="store_true",
        default=True,
        help="Enable snapshot boundary commit behavior (default).",
    )
    snapshot_group.add_argument(
        "--no-snapshot",
        dest="snapshot",
        action="store_false",
        help="Disable snapshot boundary commit behavior.",
    )
    return parser


def _is_valid_batch_slug(value: str) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if not normalized or normalized != value:
        return False
    return _BATCH_SLUG_RE.fullmatch(normalized) is not None


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

        if args.snapshot:
            batch_slug = "mixed"
            if isinstance(args.batch_slug, str) and args.batch_slug.strip():
                if not _is_valid_batch_slug(args.batch_slug):
                    raise SelectError("--batch-slug must be valid when provided")
                batch_slug = args.batch_slug

            boundary_rows = [
                {"path": row["path"], "batch_slug": batch_slug} for row in rows
            ]
            boundary = prepare_snapshot_boundary(cwd=cwd, rows=boundary_rows)
            if boundary.paths:
                mode = "amended" if boundary.amended else "committed"
                print(
                    (
                        f"[select_sentinel] {mode} snapshot {boundary.commit_hash} "
                        f"batch={boundary.batch_slug} files={len(boundary.paths)}"
                    ),
                    file=sys.stderr,
                )
            else:
                print(
                    (
                        "[select_sentinel] all selected files are clean; "
                        f"snapshot unchanged (batch={boundary.batch_slug} files={len(rows)})"
                    ),
                    file=sys.stderr,
                )

        for row in rows:
            print(json.dumps({"path": row["path"]}, ensure_ascii=False))
        return 0
    except SelectError as exc:
        print(f"[select_sentinel] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
