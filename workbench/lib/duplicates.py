"""Backward-compatible facade for generic duplicate scanning helpers."""

from workbench.assets.dedup import (
    DuplicateGroup,
    DuplicateScanResult,
    DuplicateScannerError,
    PruneResult,
    prune_duplicates,
    scan_for_duplicates,
)

__all__ = [
    "DuplicateGroup",
    "DuplicateScanResult",
    "DuplicateScannerError",
    "PruneResult",
    "scan_for_duplicates",
    "prune_duplicates",
]
