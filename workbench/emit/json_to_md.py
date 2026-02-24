"""Convert NDJSON batch stdin into markdown records."""

from __future__ import annotations

import argparse
import sys

from workbench.framing.batch import ndjson_to_markdown
from workbench.io.streams import read_stdin_text, write_stdout_text


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="json-to-md",
        description=__doc__,
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        write_stdout_text(ndjson_to_markdown(read_stdin_text()))
        return 0
    except ValueError as exc:
        print(f"json-to-md: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
