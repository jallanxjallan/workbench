"""Compile Workbench regex YAML definitions to runtime JSON artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.regex.compile_patterns import (
    DEFAULT_PATTERN_OUTPUT_ROOT,
    DEFAULT_PATTERN_SOURCE_ROOT,
    PatternCompileError,
    compile_patterns,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile-regex",
        description=__doc__,
    )
    parser.add_argument(
        "--source-root",
        default=str(DEFAULT_PATTERN_SOURCE_ROOT),
        help=f"Regex source root (default: {DEFAULT_PATTERN_SOURCE_ROOT}).",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_PATTERN_OUTPUT_ROOT),
        help=f"Compiled output root (default: {DEFAULT_PATTERN_OUTPUT_ROOT}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source_root = Path(args.source_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    try:
        compile_patterns(source_root=source_root, output_root=output_root)
    except PatternCompileError as exc:
        print(f"[compile-regex] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[compile-regex] error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
