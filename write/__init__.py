"""Public write-domain primitives."""

from write.common import WriteError
from write.sink import WriteMode, write_records, writeback, writenew

__all__ = [
    "WriteError",
    "WriteMode",
    "write_records",
    "writeback",
    "writenew",
]
