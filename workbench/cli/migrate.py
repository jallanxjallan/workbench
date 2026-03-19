"""Stream external markdown documents through the Pandoc ingest chain."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from workbench.config.roots import WORKBENCH_ROOT


DEFAULT_SOURCE = "hhp-import"
PANDOC_DATA_DIR = WORKBENCH_ROOT / "tools" / "tls" / "pandoc"
DEFAULTS_NAME = "ingest"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate",
        description=__doc__,
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=DEFAULT_SOURCE,
        help=f"Source directory to migrate (default: {DEFAULT_SOURCE}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source_arg = args.source
    source_dir = Path(source_arg).expanduser()

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Source directory not found: {source_arg}", file=sys.stderr)
        return 1

    find_proc = subprocess.Popen(
        ["find", str(source_dir), "-name", "*.md", "-print0"],
        stdout=subprocess.PIPE,
    )
    try:
        xargs_proc = subprocess.Popen(
            [
                "xargs",
                "-0",
                "-r",
                "-n",
                "1",
                "pandoc",
                "--data-dir",
                str(PANDOC_DATA_DIR),
                "--defaults",
                DEFAULTS_NAME,
            ],
            stdin=find_proc.stdout,
        )
    finally:
        if find_proc.stdout is not None:
            find_proc.stdout.close()

    xargs_code = xargs_proc.wait()
    find_code = find_proc.wait()
    if find_code != 0:
        return find_code
    return xargs_code


if __name__ == "__main__":
    raise SystemExit(main())
