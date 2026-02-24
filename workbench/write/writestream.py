"""Pass stdin markdown stream through unchanged."""

from __future__ import annotations

import argparse

from workbench.io.streams import read_stdin_text, write_stdout_text


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="writestream",
        description=__doc__,
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    write_stdout_text(read_stdin_text())
    return 0
