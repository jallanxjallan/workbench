"""Publish Studio context and batch instructions as a separate flow."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.config.roots import STUDIO_ROOT
from workbench.control.publish import (
    ControlPublishError,
    DEFAULT_COMPILED_CONTEXT_ROOT,
    DEFAULT_INGEST_COMMAND,
    publish_context,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="publish-context",
        description=__doc__,
    )
    parser.add_argument(
        "--studio-root",
        default=str(STUDIO_ROOT),
        help=f"Studio root (default: {STUDIO_ROOT}).",
    )
    parser.add_argument(
        "--compiled-root",
        default=str(DEFAULT_COMPILED_CONTEXT_ROOT),
        help=f"Compiled context output root (default: {DEFAULT_COMPILED_CONTEXT_ROOT}).",
    )
    parser.add_argument(
        "--ingest-command",
        default=" ".join(DEFAULT_INGEST_COMMAND),
        help="Command used for ASC ingest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compile context/batch instructions without invoking ingest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    ingest_command = tuple(part for part in str(args.ingest_command).strip().split(" ") if part)
    if not ingest_command:
        print("[publish-context] error: ingest command cannot be empty", file=sys.stderr)
        return 1

    studio_root = Path(args.studio_root).expanduser().resolve()
    compiled_root = Path(args.compiled_root).expanduser().resolve()

    try:
        publish_context(
            studio_root=studio_root,
            compiled_root=compiled_root,
            ingest_command=ingest_command,
            dry_run=bool(args.dry_run),
        )
    except ControlPublishError as exc:
        print(f"[publish-context] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[publish-context] error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
