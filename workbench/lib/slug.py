"""Batch slug helpers."""

from __future__ import annotations


def is_valid_batch_slug(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())
