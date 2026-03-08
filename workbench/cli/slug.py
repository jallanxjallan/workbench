"""Slug identity operations."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from workbench.cli.create_vault import load_registry
from workbench.config.roots import STUDIO_ROOT
from workbench.interop.document import Document
from workbench.lib.rg import (
    RipgrepError,
    find_files_with_slug,
    find_markdown_slug_candidates,
)
from workbench.slug.builder import build_slug
from workbench.slug.normalize import normalize_segment
from workbench.slug.validator import validate_slug
from workbench.slug.writer import ensure_slug, write_slug

MARKDOWN_SUFFIXES = (".md", ".markdown")
LEGACY_ACTIONS = {"build", "ensure", "validate"}


def _legacy_parser() -> argparse.ArgumentParser:
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


def _file_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slug",
        description=(
            "Generate deterministic vault slug for one markdown file: "
            "<vault_mnemonic>.<class>.<kebab-file-stem>."
        ),
    )
    parser.add_argument("file", help="Target markdown file.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Replace slug sentinel '__SLUG__' in frontmatter.",
    )
    return parser


def _read_paths_from_stdin() -> list[str]:
    return [line.strip() for line in sys.stdin if line.strip()]


def _has_slug(path: Path) -> bool:
    try:
        doc = Document.read_file(path)
    except ValueError as exc:
        raise ValueError(f"failed to parse markdown: {exc}") from exc
    return "slug" in dict(doc.metadata or {})


def find_vault_root(filepath: str | Path) -> Path:
    path = Path(filepath).expanduser().resolve()
    if path.is_file():
        start = path.parent
    else:
        start = path

    for parent in [start, *start.parents]:
        if (parent / "_vault_registry.yaml").is_file():
            return parent
        if (parent / "_vault_registry.json").is_file():
            return parent

    raise RuntimeError(f"Vault root not found for {path}")


def _resolve_registry_path(vault_root: Path) -> Path:
    yaml_path = vault_root / "_vault_registry.yaml"
    if yaml_path.is_file():
        return yaml_path

    json_path = vault_root / "_vault_registry.json"
    if json_path.is_file():
        return json_path

    raise RuntimeError(f"Vault registry not found under {vault_root}")


def _load_vault_mnemonic(vault_root: Path) -> str:
    registry_path = _resolve_registry_path(vault_root)
    data = load_registry(registry_path)

    raw = data.get("mnemonic")
    if not isinstance(raw, str) or not raw.strip():
        raw = data.get("vault")

    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError(f"Vault mnemonic is missing in {registry_path}")

    return normalize_segment(raw)


def _kebab(text: str) -> str:
    return normalize_segment(text)


def _slug_for_file(filepath: Path) -> str:
    doc = Document.read_file(filepath)
    metadata = dict(doc.metadata or {})

    file_class = metadata.get("class")
    if not isinstance(file_class, str) or not file_class.strip():
        raise RuntimeError(f"Missing required frontmatter key 'class' in {filepath}")

    vault_root = find_vault_root(filepath)
    vault_mnemonic = _load_vault_mnemonic(vault_root)
    class_segment = normalize_segment(file_class)
    stem_segment = _kebab(filepath.stem)

    return f"{vault_mnemonic}.{class_segment}.{stem_segment}"


def _check_collision(*, slug: str, filepath: Path) -> None:
    try:
        owners = find_files_with_slug(slug, root=STUDIO_ROOT)
    except RipgrepError as exc:
        raise RuntimeError(str(exc)) from exc
    target = filepath.resolve()
    conflicting = sorted(path for path in owners if path != target)
    if conflicting:
        raise RuntimeError(f"Slug collision detected: {slug}")


def _write_slug(filepath: Path, slug: str) -> None:
    try:
        write_slug(filepath, slug)
    except ValueError as exc:
        raise RuntimeError(f"{exc} in {filepath}") from exc


def _file_slug_command(args: argparse.Namespace) -> int:
    filepath = Path(args.file).expanduser().resolve()
    try:
        slug = _slug_for_file(filepath)
        _check_collision(slug=slug, filepath=filepath)
        if args.write:
            _write_slug(filepath, slug)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    print(slug)
    return 0


def build_slug_command(args: argparse.Namespace) -> int:
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


def ensure_slug_command(args: argparse.Namespace) -> int:
    raw_paths = [str(path) for path in args.paths]
    if args.stdin:
        raw_paths.extend(_read_paths_from_stdin())

    if not raw_paths:
        print("ERROR: provide file paths or use --stdin", file=sys.stderr)
        return 2

    created = 0
    validated = 0
    failed = 0
    paths = [Path(raw_path).expanduser().resolve() for raw_path in raw_paths]

    slug_owner_index: dict[str, set[Path]] = {}
    scan_roots = [str((path if path.is_dir() else path.parent).resolve()) for path in paths]
    if scan_roots:
        common_root = Path(os.path.commonpath(scan_roots)).resolve()
        try:
            for row in find_markdown_slug_candidates(root=common_root):
                file_path = row["file"]
                slug_value = row["slug"]
                if not isinstance(slug_value, str):
                    continue
                normalized = slug_value.strip()
                if not normalized or normalized.lower() in {"__slug__", "null", "~"}:
                    continue
                slug_owner_index.setdefault(normalized, set()).add(file_path)
        except RipgrepError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    for path in paths:
        try:
            had_slug = _has_slug(path)
            ensure_slug(
                path,
                namespace=args.namespace,
                slug_owner_index=slug_owner_index,
            )
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
    try:
        candidates = find_markdown_slug_candidates(
            root=root,
        )
    except RipgrepError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    markdown_files = sorted(row["file"] for row in candidates)
    slug_values_by_file: dict[Path, list[str]] = {}
    for row in candidates:
        slug_value = row["slug"]
        if not isinstance(slug_value, str):
            continue
        slug_values_by_file.setdefault(row["file"], []).append(slug_value)

    for path in markdown_files:
        values = slug_values_by_file.get(path.resolve(), [])
        if not values:
            errors.append(f"{path}: missing slug")
            continue

        if len(values) > 1:
            errors.append(f"{path}: multiple slug fields in frontmatter")
            continue

        slug_value = values[0]

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


def _legacy_main(argv: list[str]) -> int:
    parser = _legacy_parser()
    args = parser.parse_args(argv)

    if args.action == "build":
        return build_slug_command(args)
    if args.action == "ensure":
        return ensure_slug_command(args)
    if args.action == "validate":
        return _validate(args)

    parser.print_help()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in LEGACY_ACTIONS:
        return _legacy_main(args)

    parser = _file_parser()
    parsed = parser.parse_args(args)
    return _file_slug_command(parsed)
