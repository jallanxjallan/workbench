"""Compile Control sources into Workbench _compiled/control artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.control.compile import (
    ControlCompileError,
    DEFAULT_COMPILED_CONTROL_ROOT,
    DEFAULT_CONTROL_ROOT,
    compile_control,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile-control",
        description=__doc__,
    )
    parser.add_argument(
        "--control-root",
        default=str(DEFAULT_CONTROL_ROOT),
        help=f"Control source root (default: {DEFAULT_CONTROL_ROOT}).",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_COMPILED_CONTROL_ROOT),
        help=f"Control compiled output root (default: {DEFAULT_COMPILED_CONTROL_ROOT}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    control_root = Path(args.control_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()

    try:
        compile_control(control_root=control_root, output_root=output_root)
    except ControlCompileError as exc:
        print(f"[compile-control] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[compile-control] error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
