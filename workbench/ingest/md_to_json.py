"""Convert null-delimited markdown stdin into NDJSON records."""

from __future__ import annotations

import argparse
import json
import sys


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="md-to-json",
        description=__doc__,
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)

    buffer = bytearray()
    read = sys.stdin.buffer.read

    while True:
        chunk = read(8192)
        if not chunk:
            break

        buffer.extend(chunk)

        while True:
            try:
                idx = buffer.index(0)
            except ValueError:
                break

            record = buffer[:idx]
            del buffer[: idx + 1]

            if not record:
                continue

            content = record.decode("utf-8")
            sys.stdout.write(
                json.dumps(
                    {
                        "content": content,
                        "input_record": {},
                    },
                    ensure_ascii=False,
                )
            )
            sys.stdout.write("\n")

    if buffer:
        content = buffer.decode("utf-8")
        sys.stdout.write(
            json.dumps(
                {
                    "content": content,
                    "input_record": {},
                },
                ensure_ascii=False,
            )
        )
        sys.stdout.write("\n")

    return 0
