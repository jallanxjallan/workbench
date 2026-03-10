"""CLI wrapper for writing NDJSON records into new vault files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.write.common import WriteError, has_piped_stdin
from workbench.write.writenew import write_new_records


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="write-new",
        description="Write NDJSON records into new vault candidate files.",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Schema name from Studio/_schemas (for example: passage).",
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Target folder where new markdown files are created.",
    )
    parser.add_argument(
        "--studio-root",
        default=str(Path.home().resolve() / "Studio"),
        help="Studio root containing _schemas (default: ~/Studio).",
    )
    parser.add_argument(
        "--debug-routing",
        action="store_true",
        help="Print resolved output file for each record to stderr.",
    )
    return parser


def run(
    *,
    schema: str,
    path: str,
    studio_root: str,
    debug_routing: bool,
) -> None:
    write_new_records(
        schema_name=schema,
        target_path=path,
        studio_root=studio_root,
        debug_routing=debug_routing,
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
        run(
            schema=args.schema,
            path=args.path,
            studio_root=args.studio_root,
            debug_routing=args.debug_routing,
        )
        return 0
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
