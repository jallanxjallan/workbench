from __future__ import annotations

import io
from typing import Iterable, List

from workbench.lib.ndjson import StreamError, emit_ndjson, parse_ndjson
from workbench.tools.markdown_document import Document

__all__ = [
    "Document",
    "to_ndjson",
    "from_ndjson",
]


def to_ndjson(docs: Iterable[Document]) -> str:
    """
    Serialize Document objects to compliant NDJSON.

    Schema:
        {"metadata": <object>, "content": <string>}
    """
    lines = [
        emit_ndjson(
            {
                "metadata": doc.metadata,
                "content": doc.content,
            }
        )
        for doc in docs
    ]

    return "\n".join(lines) + ("\n" if lines else "")


def from_ndjson(text: str) -> List[Document]:
    """
    Parse compliant NDJSON into Document objects.
    """
    documents: List[Document] = []

    for record_no, record in enumerate(parse_ndjson(io.StringIO(text)), start=1):
        if "metadata" not in record or "content" not in record:
            raise StreamError(
                f"NDJSON record {record_no} must include metadata and content fields"
            )

        metadata = record["metadata"]
        content = record["content"]

        if not isinstance(metadata, dict):
            raise StreamError(
                f"NDJSON record {record_no} metadata must be an object"
            )

        if not isinstance(content, str):
            raise StreamError(
                f"NDJSON record {record_no} content must be a string"
            )

        documents.append(Document(metadata=metadata, content=content))

    return documents
