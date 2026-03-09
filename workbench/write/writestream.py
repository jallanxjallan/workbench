"""Pass stdin markdown stream through unchanged."""

from __future__ import annotations

import argparse
import sys

from workbench.framing.markdown import parse_markdown_batch
from workbench.lib.streams import read_stdin_text, write_stdout_text


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="write-stream",
        description=__doc__,
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        text = read_stdin_text()
        parse_markdown_batch(text)
        write_stdout_text(text)
        return 0
    except ValueError as exc:
        print(f"write-stream: {exc}", file=sys.stderr)
        return 1
