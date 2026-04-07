from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TextIO

from scan import rg_search
from transport.pandoc import PandocError, PandocJob, run_pandoc_jobs_serial
from upload.prefixes import PrefixMapError, kind_for_slug, require_target
from vault.validate import validate_vault


SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]
DOCUMENT_EXTENSIONS = ["md", "markdown"]
DocumentTarget = Literal["prompt", "instruction"]

SLUG_SCAN_PATTERN = r"slug\s*:"
FULL_SLUG_RE = re.compile(
    r"^(?P<prefix>[a-z]{3})\.(?P<hint>[a-z]+(?:-[a-z]+)*)\.(?P<identity>[a-z0-9]{5,8})$"
)

PROMPT_PREFIXES = ("pss", "img", "scn")
INSTRUCTION_PREFIXES = ("gbl", "cxt", "spc")

PREFIXES_BY_TARGET: dict[DocumentTarget, tuple[str, ...]] = {
    "prompt": PROMPT_PREFIXES,
    "instruction": INSTRUCTION_PREFIXES,
}

PANDOC_DEFAULTS_BY_TARGET: dict[DocumentTarget, str] = {
    "prompt": "upload_prompts",
    "instruction": "upload_instructions",
}


class MarkdownHelperError(RuntimeError):
    pass


class UploadError(RuntimeError):
    pass


@dataclass(frozen=True)
class FoundDocument:
    slug: str
    path: Path


def prefixes_for_target(target: DocumentTarget) -> tuple[str, ...]:
    return PREFIXES_BY_TARGET[target]


def slug_line_regex_for_target(target: DocumentTarget) -> re.Pattern[str]:
    prefixes = prefixes_for_target(target)
    prefix_pattern = "|".join(re.escape(prefix) for prefix in sorted(prefixes))
    slug_value_pattern = (
        rf"(?:{prefix_pattern})"
        rf"\.[a-z]+(?:-[a-z]+)*"
        rf"\.[a-z0-9]{{5,8}}"
    )
    return re.compile(
        rf'^\s*slug\s*:\s*"?(?P<slug>{slug_value_pattern})"?\s*$'
    )


def build_pandoc_job(path: Path, *, target: DocumentTarget) -> PandocJob:
    return PandocJob(
        defaults=PANDOC_DEFAULTS_BY_TARGET[target],
        source_path=path,
    )


def emit_pandoc_stdout(
    path: Path,
    *,
    target: DocumentTarget,
    output: TextIO,
) -> None:
    job = build_pandoc_job(path, target=target)

    try:
        results = run_pandoc_jobs_serial([job])
    except PandocError as exc:
        raise MarkdownHelperError(f"pandoc failed: {exc}") from exc

    emitted_any = False

    for result in results:
        stdout = result.stdout
        if not stdout.strip():
            raise MarkdownHelperError("pandoc emitted no NDJSON output")

        output.write(stdout)
        if not stdout.endswith("\n"):
            output.write("\n")

        emitted_any = True

    if not emitted_any:
        raise MarkdownHelperError("pandoc returned no result")


def run_prompt(*, root: Path, output: TextIO, err: TextIO) -> None:
    _run_target(root=root, target="prompt", output=output, err=err)


def run_instruction(*, root: Path, output: TextIO, err: TextIO) -> None:
    _run_target(root=root, target="instruction", output=output, err=err)


def _run_target(
    *,
    root: Path,
    target: DocumentTarget,
    output: TextIO,
    err: TextIO,
) -> None:
    vault_root = validate_vault(root)
    documents = discover_documents(vault_root, target=target)

    if not documents:
        raise UploadError(
            f"no uploadable {target} files found under: {vault_root}"
        )

    emitted = 0
    failed = 0

    for found in documents:
        try:
            emit_pandoc_stdout(found.path, target=target, output=output)
        except MarkdownHelperError as exc:
            failed += 1
            print(
                f"upload: failed {found.slug} ({found.path}): {exc}",
                file=err,
            )
            continue

        emitted += 1

    print(
        f"upload: emitted {emitted} {target} record(s); "
        f"failed {failed} document(s)",
        file=err,
    )

    if emitted == 0:
        raise UploadError(
            f"all discovered {target} documents failed during pandoc emission"
        )


def discover_prompt_documents(root: Path) -> list[FoundDocument]:
    return discover_documents(root, target="prompt")


def discover_instruction_documents(root: Path) -> list[FoundDocument]:
    return discover_documents(root, target="instruction")


def discover_documents(
    root: Path,
    *,
    target: DocumentTarget,
) -> list[FoundDocument]:
    slug_line_re = slug_line_regex_for_target(target)

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

        match = slug_line_re.search(text)
        if match is None:
            continue

        slug = match.group("slug").strip()
        path = path.expanduser().resolve()

        if not path.is_file():
            continue

        validate_document_slug(slug, target=target)

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


def validate_document_slug(slug: str, *, target: DocumentTarget) -> None:
    match = FULL_SLUG_RE.fullmatch(slug)
    if match is None:
        raise UploadError(f"invalid slug shape: {slug}")

    prefix = match.group("prefix")
    if prefix not in prefixes_for_target(target):
        raise UploadError(
            f"{target} uploader does not accept slug prefix: {slug}"
        )

    identity = match.group("identity")
    if not any(ch.isdigit() for ch in identity):
        raise UploadError(
            f"slug identity must contain at least one digit: {slug}"
        )

    try:
        require_target(slug, target="document")
        kind = kind_for_slug(slug)
    except PrefixMapError as exc:
        raise UploadError(str(exc)) from exc

    if kind != target:
        raise UploadError(
            f"document kind mismatch for {slug}: expected {target!r}, got {kind!r}"
        )