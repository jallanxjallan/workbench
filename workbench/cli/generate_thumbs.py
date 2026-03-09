"""Generate markdown image thumbnails under a root directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.lib.rg import DEFAULT_STUDIO_ROOT


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate-thumbs",
        description="Generate thumbnails for markdown image links under a root directory.",
        epilog="Example: wkb generate-thumbs ~/Studio",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_STUDIO_ROOT),
        help="Root directory to scan (default: ~/Studio).",
    )
    return parser


def _run_generate_thumbnails(root: Path) -> dict[str, object]:
    from workbench.lib.rg_generate_thumbnails import generate_thumbnails

    return generate_thumbnails(root)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.path).expanduser().resolve()
    try:
        summary = _run_generate_thumbnails(root)
        matched_files = int(summary.get("matched_files", 0))
        affected_files = list(summary.get("affected_files", []))
        if matched_files == 0:
            print(
                f"[generate-thumbs] complete: no markdown files with eligible image links were found under {root}; "
                "affected 0 file(s)"
            )
        else:
            print(
                f"[generate-thumbs] complete: affected {len(affected_files)} file(s) under {root}"
            )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[generate-thumbs] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
