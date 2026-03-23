"""Minimal NDJSON stream reader."""

from __future__ import annotations

import json
from typing import Any, Iterable, Iterator


def iter_ndjson(stream: Iterable[str] | str) -> Iterator[dict[str, Any]]:
    source = stream.splitlines() if isinstance(stream, str) else stream
    for line in source:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError("NDJSON record must be an object")
        yield obj
from __future__ import annotations

from hashlib import sha256
from typing import Any

from markdown import Document


def _normalize_uploaded_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _hash_uploaded_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def compile_document_record(
    *,
    slug: str,
    document: Document,
    origin: str,
    filepath: str,
    kind: str = "instruction",
) -> dict[str, Any]:
    """Compile one validated Document into an NDJSON-ready upload record."""
    normalized_slug = slug.strip()
    if not normalized_slug:
        raise ValueError("slug must be non-empty")

    normalized_origin = origin.strip()
    if not normalized_origin:
        raise ValueError("origin must be non-empty")

    normalized_kind = kind.strip()
    if not normalized_kind:
        raise ValueError("kind must be non-empty")

    content = _normalize_uploaded_text(document.content)

    return {
        "slug": normalized_slug,
        "kind": normalized_kind,
        "hash": _hash_uploaded_text(content),
        "content": content,
        "input_record": {
            "origin": normalized_origin,
            "filepath": filepath,
        },
    }