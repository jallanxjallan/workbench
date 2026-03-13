#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import panflute as pf

try:
    from workbench.interop import Document, to_ndjson
except ModuleNotFoundError:
    workbench_root = Path(os.environ.get("WORKBENCH_ROOT", str(Path.home() / "Workbench"))).expanduser()
    if str(workbench_root) not in sys.path:
        sys.path.insert(0, str(workbench_root))
    from workbench.interop import Document, to_ndjson


def _meta_to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return pf.stringify(value)


def prepare(doc: pf.Doc) -> None:
    pattern_meta = doc.get_metadata("split-pattern", None)
    if pattern_meta is None:
        raise ValueError("No split-pattern metadata provided.")

    pattern_str = _meta_to_str(pattern_meta)
    doc.split_regex = re.compile(pattern_str)
    doc.current_blocks = []
    doc.markdown_items = []


def _finalize_section(doc: pf.Doc) -> None:
    if not doc.current_blocks:
        return

    section_doc = pf.Doc(*doc.current_blocks)
    markdown = pf.convert_text(section_doc, input_format="panflute", output_format="markdown")
    doc.markdown_items.append(markdown)
    doc.current_blocks.clear()


def action(block: pf.Element, doc: pf.Doc):
    if not isinstance(block, pf.Block):
        return None

    text = pf.stringify(block).strip()
    if text and doc.split_regex.search(text):
        _finalize_section(doc)
        doc.current_blocks.append(block)
        return []

    doc.current_blocks.append(block)
    return []


def _records_from_markdown_items(markdown_items: list[str], source_file: str | None) -> list[Document]:
    records: list[Document] = []
    for idx, markdown in enumerate(markdown_items, start=1):
        records.append(
            Document(
                metadata={
                    "section_index": idx,
                    "source_file": source_file,
                },
                content=markdown,
            )
        )
    return records


def _emit_payload_to_parent_stdout(payload: str) -> None:
    parent_stdout = Path(f"/proc/{os.getppid()}/fd/1")
    try:
        with parent_stdout.open("w", encoding="utf-8") as out:
            out.write(payload)
            out.flush()
    except OSError:
        sys.stderr.write(payload)
        sys.stderr.flush()


def finalize(doc: pf.Doc) -> None:
    _finalize_section(doc)

    if not doc.markdown_items:
        doc.content = []
        return

    source_file = doc.get_metadata("source-file", None)
    records = _records_from_markdown_items(doc.markdown_items, source_file)
    payload = to_ndjson(records)
    _emit_payload_to_parent_stdout(payload)

    doc.content = []


def main(doc: pf.Doc | None = None):
    return pf.run_filter(action, prepare=prepare, finalize=finalize)


if __name__ == "__main__":
    main()
