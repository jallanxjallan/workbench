"""Write markdown batch documents into new files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workbench.io.streams import read_stdin_text
from workbench.lib.text import kebab_case
from workbench.tools.markdown_document import Document
from workbench.write.common import atomic_write_text, parse_documents, serialize_document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="writenew",
        description=__doc__,
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        help="Directory where new markdown files are created.",
    )
    return parser


def _file_stem(doc: Document, index: int) -> str:
    slug = doc.metadata.get("slug")
    if isinstance(slug, str) and slug.strip():
        return kebab_case(slug)
    return f"doc-{index:03d}"


def writenew_markdown_batch(text: str, target_dir: Path) -> None:
    docs = parse_documents(text)
    for index, doc in enumerate(docs, start=1):
        target_path = target_dir / f"{_file_stem(doc, index)}.md"
        if target_path.exists():
            raise FileExistsError(f"writenew: target already exists: {target_path}")
        atomic_write_text(target_path, serialize_document(doc))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        writenew_markdown_batch(
            read_stdin_text(),
            Path(args.target_dir).expanduser().resolve(),
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"writenew: {exc}", file=sys.stderr)
        return 1
