from __future__ import annotations

from transport.files import emit_paths, ensure_regular_file, read_paths, read_text, write_text
from transport.jsonfile import dump_json_file, load_json_file, load_json_object
from transport.ndjson import (
    dumps_record,
    iter_records,
    loads_record,
    read_all_records,
    write_record,
    write_records,
)
from transport.trailers import (
    is_final_trailer_record,
    require_single_final_trailer,
    split_final_trailer,
)

__all__ = [
    "dump_json_file",
    "dumps_record",
    "emit_paths",
    "ensure_regular_file",
    "is_final_trailer_record",
    "iter_records",
    "load_json_file",
    "load_json_object",
    "loads_record",
    "read_all_records",
    "read_paths",
    "read_text",
    "require_single_final_trailer",
    "split_final_trailer",
    "write_record",
    "write_records",
    "write_text",
]
