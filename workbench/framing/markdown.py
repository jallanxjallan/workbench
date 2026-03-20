"""Single-document markdown framing helper."""

from __future__ import annotations

import re

from workbench.interop.document import Document

MULTI_DOCUMENT_ERROR = "Multi-document markdown streams are not supported. Use NDJSON."
_MULTI_DOCUMENT_CANDIDATE_RE = re.compile(r"(?:\r?\n){2}(?P<start>---[ \t]*\r?\n)")

# Backward-compatible alias for downstream type imports.
MarkdownRecord = Document


def _has_additional_document(text: str) -> bool:
    for match in _MULTI_DOCUMENT_CANDIDATE_RE.finditer(text):
        candidate = text[match.start("start") :]
        inspected = Document.inspect_text(candidate)
        if inspected.has_frontmatter and inspected.error is None:
            return True
    return False


def parse_markdown_stream(text: str) -> list[Document]:
    if text.strip() == "":
        return []
    if _has_additional_document(text):
        raise ValueError(MULTI_DOCUMENT_ERROR)
    return [Document.read_text(text)]


def emit_markdown_stream(docs: list[Document]) -> str:
    if not docs:
        return ""
    if len(docs) > 1:
        raise ValueError(MULTI_DOCUMENT_ERROR)

    doc = docs[0]
    if not isinstance(doc, Document):
        raise ValueError("record 1 must be a Document")
    return doc.write_text()
