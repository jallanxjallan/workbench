"""Canonical record -> Document adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from workbench.interop.document import Document


def record_to_document(record: Mapping[str, Any]) -> Document:
    if not isinstance(record, Mapping):
        raise ValueError("record must be an object")

    content = record.get("content")
    if not isinstance(content, str):
        raise ValueError("record content must be a string")

    metadata = record.get("input_record")
    if metadata is None:
        metadata = record.get("metadata")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError("record input_record must be an object")

    return Document(
        metadata=dict(metadata),
        content=content,
    )
