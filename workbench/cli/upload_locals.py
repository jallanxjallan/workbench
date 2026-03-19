"""NEEDS REPAIR: upload changed local registry files into the execution registry."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.registry.upload_locals import (
    DEFAULT_INGEST_COMMAND,
    DEFAULT_SELECT_COMMAND,
    UploadLocalsError,
    upload_locals,
)

# Tracked provisionally so the CLI surface is visible in git while the command
# is being repaired and validated.


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="upload-locals",
        description=__doc__,
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Vault repository root (default: current directory).",
    )
    parser.add_argument(
        "--select-command",
        default=" ".join(DEFAULT_SELECT_COMMAND),
        help="Command used to read existing execution-registry records.",
    )
    parser.add_argument(
        "--ingest-command",
        default=" ".join(DEFAULT_INGEST_COMMAND),
        help="Command used to overwrite execution-registry records.",
    )
    return parser


def _split_command(raw: str, *, flag: str) -> tuple[str, ...]:
    parts = tuple(part for part in str(raw).strip().split(" ") if part)
    if not parts:
        raise UploadLocalsError(f"{flag} cannot be empty")
    return parts


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        result = upload_locals(
            repo=Path(args.repo).expanduser().resolve(),
            select_command=_split_command(args.select_command, flag="--select-command"),
            ingest_command=_split_command(args.ingest_command, flag="--ingest-command"),
        )
    except UploadLocalsError as exc:
        print(f"[upload-locals] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[upload-locals] error: {exc}", file=sys.stderr)
        return 1

    if result.no_changes:
        print("no changes")
        return 0

    print(
        "uploaded locals "
        f"project={result.project} "
        f"instructions={result.uploaded_instructions} "
        f"packages={result.uploaded_packages} "
        f"commit={result.commit_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
