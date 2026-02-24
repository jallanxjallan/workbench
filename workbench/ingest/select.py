"""Selection commands for ingest pipelines."""

from __future__ import annotations

import argparse

from workbench.ingest import _select_records, _select_sentinel


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="select",
        description=__doc__,
    )
    sub = parser.add_subparsers(dest="select_command")

    sentinel = sub.add_parser(
        "sentinel",
        help="Select files by ASC batch sentinel and optionally snapshot boundary.",
    )
    sentinel.add_argument("args", nargs=argparse.REMAINDER)

    records = sub.add_parser(
        "records",
        help="Resolve selected markdown paths into NDJSON content records.",
    )
    records.add_argument("args", nargs=argparse.REMAINDER)

    return parser


def _trim(argv: list[str]) -> list[str]:
    return [arg for arg in argv if arg != "--"]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    parsed = parser.parse_args(argv)

    if parsed.select_command == "sentinel":
        return _select_sentinel.main(_trim(parsed.args))
    if parsed.select_command == "records":
        return _select_records.main(_trim(parsed.args))

    parser.print_help()
    return 0
