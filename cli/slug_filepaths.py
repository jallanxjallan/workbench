"""Resolve canonical NDJSON slug records into markdown file-content records."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _depreciated.document_files import has_piped_stdin
from _depreciated.records import RecordContractError, dump_record, iter_records, make_record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slugs-to-files",
        description=__doc__,
    )
    return parser





def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        _parser().print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1
    return stream_slug_files()


if __name__ == "__main__":
    raise SystemExit(main())
