"""CLI wrapper for writing NDJSON records back to existing vault artifacts."""

from __future__ import annotations

import argparse
import sys

from workbench.config.roots import STUDIO_ROOT
from workbench.write.common import WriteError, has_piped_stdin
from workbench.write.writeback import write_back_records


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="writeback",
        description="Write NDJSON records back to existing vault artifacts.",
    )
    parser.add_argument(
        "--studio-root",
        default=str(STUDIO_ROOT),
        help="Studio root used for ripgrep slug resolution (default: ~/Studio).",
    )
    return parser


def run(*, studio_root: str) -> None:
    write_back_records(
        studio_root=studio_root,
        debug_routing=False,
        input_stream=sys.stdin,
    )


def main(argv: list[str] | None = None) -> int:
    arg_parser = parser()
    args = arg_parser.parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        arg_parser.print_usage(sys.stderr)
        print("ERROR: expected NDJSON input from stdin (pipe or < file)", file=sys.stderr)
        return 1
    try:
        run(studio_root=args.studio_root)
        return 0
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
