from __future__ import annotations

from collections.abc import Callable


def is_final_trailer_record(record: dict, *, key: str = "_op", value: str | None = None) -> bool:
    if not isinstance(record, dict):
        return False
    if key not in record:
        return False
    if value is None:
        return True
    return record.get(key) == value


def split_final_trailer(
    records: list[dict],
    *,
    predicate: Callable[[dict], bool],
) -> tuple[list[dict], dict]:
    trailer_indexes = [index for index, record in enumerate(records) if predicate(record)]

    if not trailer_indexes:
        raise ValueError("Expected exactly one final trailer record, but none were found.")

    if len(trailer_indexes) > 1:
        raise ValueError("Expected exactly one final trailer record, but found multiple trailers.")

    trailer_index = trailer_indexes[0]
    if trailer_index != len(records) - 1:
        raise ValueError("Trailer record must be the final record.")

    return records[:trailer_index], records[trailer_index]


def require_single_final_trailer(
    records: list[dict],
    *,
    predicate: Callable[[dict], bool],
) -> tuple[list[dict], dict]:
    return split_final_trailer(records, predicate=predicate)
