"""Compatibility wrapper for ingest-only writevault behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from workbench.lib.vault_writer import (
    INGEST_DIRNAME,
    VAULT_REGISTRY_FILENAME,
    discover_vault_root,
    write_ingest_records,
)


def write_vault_records(
    *,
    input_stream: Iterable[str],
    cwd: Path | None = None,
    debug_routing: bool = False,
) -> list[Path]:
    return write_ingest_records(
        input_stream=input_stream,
        cwd=cwd,
        debug_routing=debug_routing,
    )


__all__ = [
    "INGEST_DIRNAME",
    "VAULT_REGISTRY_FILENAME",
    "discover_vault_root",
    "write_vault_records",
]
