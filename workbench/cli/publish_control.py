"""Publish compiled control global instructions to ASC ingest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.control.publish import (
    ControlPublishError,
    DEFAULT_INGEST_COMMAND,
    publish_control,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="publish-control",
        description=__doc__,
    )
    parser.add_argument(
        "--compiled-root",
        default=None,
        help="Compiled control root (default: Workbench/_compiled/control).",
    )
    parser.add_argument(
        "--ingest-command",
        default=" ".join(DEFAULT_INGEST_COMMAND),
        help="Command used for ASC ingest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build records without invoking ingest.",
    )
    parser.add_argument(
        "--ndjson-out",
        default=None,
        help="Optional path to write generated NDJSON records.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    ingest_command = tuple(part for part in str(args.ingest_command).strip().split(" ") if part)
    if not ingest_command:
        print("[publish-control] error: ingest command cannot be empty", file=sys.stderr)
        return 1

    compiled_root = (
        None if args.compiled_root is None else Path(args.compiled_root).expanduser().resolve()
    )
    ndjson_out = None if args.ndjson_out is None else Path(args.ndjson_out).expanduser().resolve()

    kwargs: dict[str, object] = {
        "ingest_command": ingest_command,
        "dry_run": bool(args.dry_run),
        "ndjson_out": ndjson_out,
    }
    if compiled_root is not None:
        kwargs["compiled_root"] = compiled_root

    try:
        publish_control(**kwargs)
    except ControlPublishError as exc:
        print(f"[publish-control] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[publish-control] error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
