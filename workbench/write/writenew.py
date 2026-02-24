"""Write markdown batch documents into new files."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from workbench.framing.markdown import MarkdownRecord, emit_markdown_batch, parse_markdown_batch
from workbench.io.streams import read_stdin_text
from workbench.lib.text import kebab_case


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


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        delete=False,
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def _parse_documents(text: str) -> list[MarkdownRecord]:
    if text.strip() == "":
        return []
    return parse_markdown_batch(text)


def _file_stem(record: MarkdownRecord, index: int) -> str:
    slug = record.metadata.get("slug")
    if isinstance(slug, str) and slug.strip():
        return kebab_case(slug)
    return f"doc-{index:03d}"


def writenew_markdown_batch(text: str, target_dir: Path) -> None:
    docs = _parse_documents(text)
    for index, doc in enumerate(docs, start=1):
        target_path = target_dir / f"{_file_stem(doc, index)}.md"
        if target_path.exists():
            raise FileExistsError(f"writenew: target already exists: {target_path}")
        _atomic_write_text(target_path, emit_markdown_batch([doc]))


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
