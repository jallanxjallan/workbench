"""Find and optionally prune duplicate files under a root path."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.assets.duplicates import (
    DuplicateScanResult,
    DuplicateScannerError,
    prune_duplicates,
    scan_for_duplicates,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="find-duplicates",
        description=__doc__,
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan (default: current working directory).",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove duplicate files after confirmation.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip prune confirmation prompt (only valid with --prune).",
    )
    parser.add_argument(
        "--algo",
        default="sha256",
        help="Hashing algorithm (default: sha256).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.yes and not args.prune:
        print("[find-duplicates] error: --yes is only valid with --prune", file=sys.stderr)
        return 1

    root = Path(args.root).expanduser().resolve()
    try:
        result = scan_for_duplicates(root=root, algorithm=args.algo)
    except DuplicateScannerError as exc:
        print(f"[find-duplicates] error: {exc}", file=sys.stderr)
        return 1

    _print_report(result)

    if not args.prune:
        return 0

    removals = sum(len(group.duplicates) for group in result.duplicate_groups)
    if removals == 0:
        print("No duplicate files to remove.")
        return 0

    print()
    print(f"This will remove {removals} duplicate files.")
    if not args.yes:
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted; no files removed.")
            return 0

    prune_result = prune_duplicates(result.duplicate_groups)
    print(f"Removed {len(prune_result.removed_paths)} duplicate files")

    if prune_result.failed_paths:
        for path, reason in prune_result.failed_paths:
            print(f"[find-duplicates] failed to remove {path}: {reason}", file=sys.stderr)
        return 1
    return 0


def _print_report(result: DuplicateScanResult) -> None:
    group_count = len(result.duplicate_groups)
    print(f"Found {group_count} duplicate group{'s' if group_count != 1 else ''}")

    for group in result.duplicate_groups:
        print()
        print(
            f"Duplicate group ({result.algorithm}: {group.hash_value[:12]}...)"
        )
        print()
        print("  KEEP:")
        print(f"    ./{_relative(result.root, group.keep)}")
        print()
        print("  DUPLICATES:")
        for duplicate in group.duplicates:
            print(f"    ./{_relative(result.root, duplicate)}")

    if result.skipped_files:
        for relative_path, reason in result.skipped_files:
            print(
                f"[find-duplicates] skipped {relative_path}: {reason}",
                file=sys.stderr,
            )


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
