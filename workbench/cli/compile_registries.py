"""Compile control registry YAML files to runtime JSON registries."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.registry.compile_registries import (
    CompileRegistriesError,
    DEFAULT_REGISTRIES_ROOT,
    DEFAULT_RUNTIME_ROOT,
    compile_registries,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile-registries",
        description="Compile control registries into _compiled/registries.",
    )
    parser.add_argument(
        "--registries-root",
        default=str(DEFAULT_REGISTRIES_ROOT),
        help=f"Registry source root (default: {DEFAULT_REGISTRIES_ROOT}).",
    )
    parser.add_argument(
        "--runtime-root",
        default=str(DEFAULT_RUNTIME_ROOT),
        help=f"Compiled runtime root (default: {DEFAULT_RUNTIME_ROOT}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    registries_root = Path(args.registries_root).expanduser().resolve()
    runtime_root = Path(args.runtime_root).expanduser().resolve()

    try:
        compile_registries(registries_root, runtime_root)
    except CompileRegistriesError as exc:
        print(f"[compile-registries] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[compile-registries] error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
