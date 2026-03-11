"""Compile URI-linked sources into managed vault assets/frontmatter entries."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.config.roots import STUDIO_ROOT
from workbench.lib.compile_assets import CompileAssetsError, compile_assets


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile-assets",
        description=__doc__,
    )
    parser.add_argument(
        "--studio-root",
        default=str(STUDIO_ROOT),
        help="Studio root to scan (default: ~/Studio).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    studio_root = Path(args.studio_root).expanduser().resolve()

    try:
        result = compile_assets(studio_root)
    except CompileAssetsError as exc:
        print(f"[compile-assets] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[compile-assets] error: {exc}", file=sys.stderr)
        return 1

    print(
        "[compile-assets] complete: "
        f"scanned {result.scanned_files} file(s), "
        f"matched {result.matched_links} URI link(s), "
        f"updated {len(result.updated_files)} file(s), "
        f"generated {result.generated_assets} thumbnail(s), "
        f"reused {result.reused_assets} existing asset(s), "
        f"removed {result.removed_inline_links} inline link(s)"
    )

    if result.errors:
        for detail in result.errors:
            print(f"[compile-assets] warning: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
