"""CLI wrapper for guarded creation of new markdown files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

from _depreciated.document_files import has_piped_stdin
from write.common import WriteError
from write.create import run

DEFAULT_TARGET_SUBDIR = "_ingest"
DEFAULT_TEMPLATE_ID = "content"
DEFAULT_KIND = "passage"


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(
        prog="writenew",
        description="Create new markdown files in the current vault _ingest directory from canonical NDJSON without overwriting.",
    )
    command_parser.add_argument(
        "--target-dir",
        help="Optional output directory. Defaults to <current-vault>/_ingest.",
    )
    command_parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a top-level frontmatter field. May be repeated.",
    )
    return command_parser


def default_target_dir(cwd: Path | None = None) -> Path:
    base = cwd or Path.cwd()
    return base / DEFAULT_TARGET_SUBDIR


def parse_overrides(items: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for item in items:
        if "=" not in item:
            raise WriteError(f"invalid --set override (expected KEY=VALUE): {item}")
        key, raw_value = item.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            raise WriteError(f"invalid --set override (empty key): {item}")
        try:
            value = yaml.safe_load(raw_value)
        except Exception as exc:
            raise WriteError(f"invalid --set override for {normalized_key}: {exc}") from exc
        parsed[normalized_key] = value
    return parsed


def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)

    if not has_piped_stdin(sys.stdin):
        command_parser.print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1

    try:
        run(
            input_stream=sys.stdin,
            target_dir=args.target_dir,
            overrides=parse_overrides(args.overrides),
        )
        return 0
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
