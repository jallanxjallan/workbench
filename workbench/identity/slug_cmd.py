"""Generate immutable vault slug."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workbench.interop.identity import create_slug


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slug",
        description=__doc__,
    )
    parser.add_argument("target_dir", help="Directory where the new identity will live.")
    parser.add_argument("filename", help="Filename hint used to build semantic slug base.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        slug = create_slug(
            Path(args.target_dir).expanduser().resolve(),
            args.filename,
        )
        print(slug)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
