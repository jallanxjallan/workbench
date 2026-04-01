from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from scan import rg_search
from upload.manifest import ManifestHelperError, build_record as build_manifest_record
from upload.markdown import MarkdownHelperError, build_payload as build_markdown_payload
from vault.validate import validate_vault


SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]
UPLOAD_EXTENSIONS = ["md", "markdown", "json"]

# broad line finder for rg
SLUG_SCAN_PATTERN = r"slug\s*:"

# actual slug parser, done in python from matched line text
SLUG_VALUE_PATTERN = r"[a-z]{3}\.[a-z]+(?:-[a-z]+)*\.[a-z0-9]{5,8}"
SLUG_IN_TEXT_RE = re.compile(rf'"?slug"?\s*:\s*"?(?P<slug>{SLUG_VALUE_PATTERN})"?')
FULL_SLUG_RE = re.compile(
    r"^(?P<prefix>[a-z]{3})\.(?P<hint>[a-z]+(?:-[a-z]+)*)\.(?P<identity>[a-z0-9]{5,8})$"
)


@dataclass(frozen=True)
class FoundFile:
    slug: str
    path: Path


@dataclass(frozen=True)
class PrefixSpec:
    record_type: str
    builder: str
    pandoc_defaults: str | None = None


PREFIX_SPECS: dict[str, PrefixSpec] = {
    "pss": PrefixSpec("prompt", "markdown", "upload_prompts"),
    "img": PrefixSpec("prompt", "markdown", "upload_prompts"),
    "scn": PrefixSpec("prompt", "markdown", "upload_prompts"),
    "gbl": PrefixSpec("instruction", "markdown", "upload_instructions"),
    "cxt": PrefixSpec("instruction", "markdown", "upload_instructions"),
    "spc": PrefixSpec("instruction", "markdown", "upload_instructions"),
    "bat": PrefixSpec("batch", "manifest"),
    "pkg": PrefixSpec("package", "manifest"),
    "web": PrefixSpec("prompt", "markdown", "upload_prompts"),
}


class UploadError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) > 1:
        print("upload: accepts at most one optional root path", file=sys.stderr)
        return 1

    root = Path(args[0]).expanduser().resolve() if args else Path.cwd().resolve()

    try:
        run(root=root, output=sys.stdout, err=sys.stderr)
    except (UploadError, MarkdownHelperError, ManifestHelperError) as exc:
        print(f"upload: {exc}", file=sys.stderr)
        return 1

    return 0


def run(*, root: Path, output: TextIO, err: TextIO) -> None:
    vault_root = validate_vault(root)
    emitted = 0

    for found in build_slug_index(vault_root):
        record = build_record(found)
        output.write(json.dumps(record, ensure_ascii=False))
        output.write("\n")
        emitted += 1

    if emitted == 0:
        raise UploadError(f"no uploadable note/manifest files found under: {vault_root}")

    print(f"upload: emitted {emitted} record(s)", file=err)


def build_slug_index(root: Path) -> list[FoundFile]:
    records = rg_search(
        pattern=SLUG_SCAN_PATTERN,
        root=root,
        extensions=UPLOAD_EXTENSIONS,
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

        validate_slug(slug)

        existing_slug = by_path.get(path)
        if existing_slug is not None and existing_slug != slug:
            raise UploadError(f"multiple upload slugs found in one file: {path}")

        existing_path = by_slug.get(slug)
        if existing_path is not None and existing_path != path:
            raise UploadError(f"duplicate upload slug found in multiple files: {slug}")

        by_path[path] = slug
        by_slug[slug] = path

    return [
        FoundFile(slug=slug, path=path)
        for path, slug in sorted(by_path.items(), key=lambda item: str(item[0]))
    ]


def build_record(found: FoundFile) -> dict:
    spec = prefix_spec(found.slug)

    if spec.builder == "markdown":
        if found.path.suffix.lower() not in {".md", ".markdown"}:
            raise UploadError(f"slug/path mismatch for markdown record: {found.path}")
        if spec.pandoc_defaults is None:
            raise UploadError(f"missing pandoc defaults for slug: {found.slug}")

        return {
            "type": spec.record_type,
            "identity": found.slug,
            "payload": build_markdown_payload(found.path, slug=found.slug),
        }

    if spec.builder == "manifest":
        if found.path.suffix.lower() != ".json":
            raise UploadError(f"slug/path mismatch for manifest record: {found.path}")
        return build_manifest_record(found.path, slug=found.slug)

    raise UploadError(f"unsupported builder for slug: {found.slug}")


def validate_slug(slug: str) -> None:
    match = FULL_SLUG_RE.fullmatch(slug)
    if match is None:
        raise UploadError(f"invalid slug shape: {slug}")

    prefix = match.group("prefix")
    if prefix not in PREFIX_SPECS:
        raise UploadError(f"unsupported slug prefix: {slug}")


def prefix_spec(slug: str) -> PrefixSpec:
    validate_slug(slug)
    return PREFIX_SPECS[slug.split(".", 1)[0]]


if __name__ == "__main__":
    raise SystemExit(main())
