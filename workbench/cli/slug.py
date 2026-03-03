"""Slug identity operations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workbench.lib.frontmatter import parse_frontmatter
from workbench.slug.builder import build_slug
from workbench.slug.validator import validate_slug
from workbench.slug.writer import ensure_slug

MARKDOWN_SUFFIXES = (".md", ".markdown")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slug",
        description=__doc__,
    )
    sub = parser.add_subparsers(dest="action")

    build = sub.add_parser("build", help="Build slug from canonical parts.")
    build.add_argument("--namespace", help="Namespace segment.")
    build.add_argument("--class", dest="class_name", required=True, help="Object class.")
    build.add_argument("--seed", required=True, help="Seed segment.")
    build.add_argument("--context", help="Instruction context segment.")

    ensure = sub.add_parser(
        "ensure",
        help="Validate existing slugs or write missing slugs for markdown files.",
    )
    ensure.add_argument("paths", nargs="*", help="Markdown file paths.")
    ensure.add_argument("--namespace", help="Namespace for slug construction.")
    ensure.add_argument(
        "--stdin",
        action="store_true",
        help="Read newline-delimited file paths from stdin.",
    )

    validate = sub.add_parser(
        "validate",
        help="Validate slug integrity for all markdown files under a directory.",
    )
    validate.add_argument("root", help="Directory to scan recursively.")

    return parser


def _read_paths_from_stdin() -> list[str]:
    return [line.strip() for line in sys.stdin if line.strip()]


def _has_slug(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    parsed = parse_frontmatter(raw)
    if parsed.error:
        raise ValueError(f"failed to parse frontmatter: {parsed.error}")
    return "slug" in dict(parsed.data or {})


def _build(args: argparse.Namespace) -> int:
    try:
        slug = build_slug(
            namespace=args.namespace,
            class_name=args.class_name,
            seed=args.seed,
            context=args.context,
        )
        print(slug)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1


def _ensure(args: argparse.Namespace) -> int:
    raw_paths = [str(path) for path in args.paths]
    if args.stdin:
        raw_paths.extend(_read_paths_from_stdin())

    if not raw_paths:
        print("ERROR: provide file paths or use --stdin", file=sys.stderr)
        return 2

    created = 0
    validated = 0
    failed = 0

    for raw_path in raw_paths:
        path = Path(raw_path).expanduser().resolve()
        try:
            had_slug = _has_slug(path)
            ensure_slug(path, namespace=args.namespace)
            if had_slug:
                validated += 1
            else:
                created += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR: {path}: {exc}", file=sys.stderr)

    print(f"created: {created}")
    print(f"validated: {validated}")
    print(f"failed: {failed}")
    return 1 if failed else 0


def _validate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: directory does not exist: {root}", file=sys.stderr)
        return 2

    errors: list[str] = []
    seen_slugs: dict[str, Path] = {}
    markdown_files = sorted(
        path for path in root.rglob("*") if path.suffix.lower() in MARKDOWN_SUFFIXES
    )

    for path in markdown_files:
        raw = path.read_text(encoding="utf-8")
        parsed = parse_frontmatter(raw)
        if parsed.error:
            errors.append(f"{path}: frontmatter parse failed: {parsed.error}")
            continue

        data = dict(parsed.data or {})
        if "slug" not in data:
            errors.append(f"{path}: missing slug")
            continue

        slug_value = data["slug"]
        if not isinstance(slug_value, str):
            errors.append(f"{path}: slug must be a string")
            continue

        try:
            validate_slug(slug_value)
        except ValueError as exc:
            errors.append(f"{path}: invalid slug '{slug_value}': {exc}")
            continue

        prior = seen_slugs.get(slug_value)
        if prior is not None:
            errors.append(
                f"{path}: duplicate slug '{slug_value}' (already used by {prior})"
            )
            continue
        seen_slugs[slug_value] = path

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"validated files: {len(markdown_files)}")
        print(f"errors: {len(errors)}")
        return 1

    print(f"validated files: {len(markdown_files)}")
    print("errors: 0")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.action == "build":
        return _build(args)
    if args.action == "ensure":
        return _ensure(args)
    if args.action == "validate":
        return _validate(args)

    parser.print_help()
    return 0
