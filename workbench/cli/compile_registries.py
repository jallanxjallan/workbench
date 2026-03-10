"""Compile Studio registry YAML files to runtime JSON registries."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.config.roots import STUDIO_ROOT
from workbench.lib.compile_registries import (
    CompileRegistriesError,
    DEFAULT_RUNTIME_REGISTRIES_ROOT,
    compile_registries,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile-registries",
        description=(
            "Compile all Workbench registries, including editorial and "
            "regex outputs."
        ),
    )
    parser.add_argument(
        "--studio-root",
        default=str(STUDIO_ROOT),
        help="Studio root directory (default: ~/Studio).",
    )
    parser.add_argument(
        "--runtime-root",
        default=str(DEFAULT_RUNTIME_REGISTRIES_ROOT),
        help=(
            "Runtime registries root (default: "
            "~/Workbench/_compiled)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    studio_root = Path(args.studio_root).expanduser().resolve()
    runtime_root = Path(args.runtime_root).expanduser().resolve()

    try:
        compile_registries(studio_root, runtime_root)
    except CompileRegistriesError as exc:
        print(f"[compile-registries] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[compile-registries] error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
