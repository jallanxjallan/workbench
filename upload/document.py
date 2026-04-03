from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from scan import rg_search
from transport.pandoc import PandocError, PandocJob, run_pandoc_jobs_serial
from upload.ndjson import NdjsonEmitError, validate_record

from upload.prefixes import (
    DOCUMENT_PREFIXES,
    PrefixMapError,
    require_target,
    pandoc_defaults_for_slug,
)
from vault.validate import validate_vault


SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]
DOCUMENT_EXTENSIONS = ["md", "markdown"]

SLUG_SCAN_PATTERN = r"slug\s*:"
SLUG_VALUE_PATTERN = r"[a-z]{3}\.[a-z]+(?:-[a-z]+)*\.[a-z0-9]{5,8}"
SLUG_IN_TEXT_RE = re.compile(
    rf'^\s*slug\s*:\s*"?(?P<slug>{SLUG_VALUE_PATTERN})"?\s*$'
)
FULL_SLUG_RE = re.compile(
    r"^(?P<prefix>[a-z]{3})\.(?P<hint>[a-z]+(?:-[a-z]+)*)\.(?P<identity>[a-z0-9]{5,8})$"
)


class MarkdownHelperError(RuntimeError):
    pass


@dataclass(frozen=True)
class FoundDocument:
    slug: str
    path: Path


class UploadError(RuntimeError):
    pass


def build_ndjson_line(path: Path, *, slug: str) -> str:
    try:
        defaults = pandoc_defaults_for_slug(slug)
    except PrefixMapError as exc:
        raise MarkdownHelperError(str(exc)) from exc

    try:
        results = list(
            run_pandoc_jobs_serial(
                [
                    PandocJob(
                        defaults=defaults,
                        source_path=path,
                    )
                ]
            )
        )
    except PandocError as exc:
        raise MarkdownHelperError(f"pandoc failed: {exc}") from exc

    if len(results) != 1:
        raise MarkdownHelperError("unexpected pandoc result count")

    lines = [line for line in results[0].stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise MarkdownHelperError("pandoc must emit exactly one NDJSON line")

    raw_line = lines[0]

    try:
        parsed = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        raise MarkdownHelperError(f"pandoc emitted invalid JSON: {exc}") from exc

    try:
        validate_record(parsed)
    except NdjsonEmitError as exc:
        raise MarkdownHelperError(f"pandoc emitted invalid upload record: {exc}") from exc

    return raw_line


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) > 1:
        print("upload: accepts at most one optional root path", file=sys.stderr)
        return 1

    root = Path(args[0]).expanduser().resolve() if args else Path.cwd().resolve()

    try:
        run(root=root, output=sys.stdout, err=sys.stderr)
    except (UploadError, PrefixMapError) as exc:
        print(f"upload: {exc}", file=sys.stderr)
        return 1

    return 0


def run(*, root: Path, output: TextIO, err: TextIO) -> None:
    vault_root = validate_vault(root)
    documents = discover_documents(vault_root)

    if not documents:
        raise UploadError(f"no uploadable prompt/instruction files found under: {vault_root}")

    emitted = 0
    failed = 0

    for found in documents:
        try:
            raw_line = build_ndjson_line(found.path, slug=found.slug)
        except MarkdownHelperError as exc:
            failed += 1
            print(
                f"upload: failed {found.slug} ({found.path}): {exc}",
                file=err,
            )
            continue

        output.write(raw_line)
        output.write("\n")
        emitted += 1

    print(
        f"upload: emitted {emitted} record(s); failed {failed} document(s)",
        file=err,
    )

    if emitted == 0:
        raise UploadError("all discovered documents failed during pandoc/NDJSON emission")


def discover_documents(root: Path) -> list[FoundDocument]:
    records = rg_search(
        pattern=SLUG_SCAN_PATTERN,
        root=root,
        extensions=DOCUMENT_EXTENSIONS,
        exclude_dirs=SCAN_EXCLUDE_DIRS,
    )

    by_path: dict[Path, str] = {}
    by_slug: dict[str, Path] = {}

    for record in records:
        path = record.get("path")
        text = record.get("text")

        if not isinstance(path, Path):
            continue
        if not isinstance(text, str):
            continue

        match = SLUG_IN_TEXT_RE.search(text)
        if match is None:
            continue

        slug = match.group("slug").strip()
        path = path.expanduser().resolve()

        if not path.is_file():
            continue

        validate_document_slug(slug)

        existing_slug = by_path.get(path)
        if existing_slug is not None and existing_slug != slug:
            raise UploadError(f"multiple upload slugs found in one file: {path}")

        existing_path = by_slug.get(slug)
        if existing_path is not None and existing_path != path:
            raise UploadError(f"duplicate upload slug found in multiple files: {slug}")

        by_path[path] = slug
        by_slug[slug] = path

    return [
        FoundDocument(slug=slug, path=path)
        for path, slug in sorted(by_path.items(), key=lambda item: str(item[0]))
    ]


def validate_document_slug(slug: str) -> None:
    match = FULL_SLUG_RE.fullmatch(slug)
    if match is None:
        raise UploadError(f"invalid slug shape: {slug}")

    prefix = match.group("prefix")
    if prefix not in DOCUMENT_PREFIXES:
        raise UploadError(f"document uploader does not accept slug prefix: {slug}")

    require_target(slug, target="document")


if __name__ == "__main__":
    raise SystemExit(main())