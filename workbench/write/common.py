"""Shared helpers for write command implementations."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from workbench.framing.markdown import parse_markdown_batch
from workbench.tools.markdown_document import Document


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
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


def parse_documents(text: str) -> list[Document]:
    if text.strip() == "":
        return []
    return parse_markdown_batch(text)


def serialize_document(doc: Document) -> str:
    return doc.write_text()
