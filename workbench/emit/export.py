"""Emit export command surface (reserved for outward artifact exporters)."""

from __future__ import annotations

import argparse


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="export",
        description=__doc__,
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    return 0
