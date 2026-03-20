"""Shared IO helpers for NDJSON and filesystem access."""

from workbench.io.files import atomic_write_text, ensure_directory, has_piped_stdin
from workbench.io.ndjson import iter_ndjson
from workbench.io.records import (
    RecordContractError,
    dump_record,
    iter_records,
    make_record,
    validate_record,
)

__all__ = [
    "RecordContractError",
    "atomic_write_text",
    "dump_record",
    "ensure_directory",
    "has_piped_stdin",
    "iter_ndjson",
    "iter_records",
    "make_record",
    "validate_record",
]
