"""CLI wrapper for ordered slug selection dispatch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from transport import emit_paths
from upload.dispatch import BatchDispatchError, dispatch_batch



def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slug_filepaths",
        description=__doc__,
    )
    parser.add_argument("selection_json", help="Path to ordered slug selection JSON")
    return parser



def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = dispatch_batch(Path(args.selection_json))
    except BatchDispatchError as exc:
        print(f"slug_filepaths: {exc}", file=sys.stderr)
        return 1

    emit_paths(result.paths, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
