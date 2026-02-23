"""
Convert null-delimited markdown stdin into NDJSON records (streaming).
"""

from __future__ import annotations

import argparse
import json
import sys


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "md_to_json",
        help=__doc__.strip(),
        description=__doc__,
    )
    parser.set_defaults(runner=run)


def run(args: argparse.Namespace) -> int:  # noqa: ARG001
    buffer = bytearray()

    read = sys.stdin.buffer.read

    while True:
        chunk = read(8192)
        if not chunk:
            break

        buffer.extend(chunk)

        while True:
            try:
                idx = buffer.index(0)  # null byte
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

    # Emit remainder if no trailing null
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
