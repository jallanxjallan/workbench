"""Shared IO helpers for NDJSON and filesystem access."""

from workbench.io.files import ensure_directory, has_piped_stdin, overwrite_text, write_new_text
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
    "dump_record",
    "ensure_directory",
    "has_piped_stdin",
    "iter_ndjson",
    "iter_records",
    "make_record",
    "overwrite_text",
    "validate_record",
    "write_new_text",
]
