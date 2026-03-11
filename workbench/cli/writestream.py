"""CLI wrapper that validates and passes markdown stream through unchanged."""

from __future__ import annotations

import argparse
import sys

from workbench.lib.streams import read_stdin_text, write_stdout_text
from workbench.write.writestream import write_stream_text


def parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="writestream",
        description="Pass stdin markdown stream through unchanged.",
    )


def run(text: str) -> str:
    return write_stream_text(text)


def main(argv: list[str] | None = None) -> int:
    parser().parse_args(argv)
    try:
        text = read_stdin_text()
        write_stdout_text(run(text))
        return 0
    except ValueError as exc:
        print(f"writestream: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
