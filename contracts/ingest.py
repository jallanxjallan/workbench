from __future__ import annotations

from collections.abc import Mapping


INGEST_RESULT_OPERATION_KEY = "_op"
INGEST_RESULT_OPERATION = "asc.ingest.result"
INGEST_STATUS_KEY = "status"
INGEST_STATUS_OK = "ok"
INGEST_STATUS_FAILED = "failed"
INGEST_BATCH_ID_KEY = "batch_id"
INGEST_ERROR_KEY = "error"
INGEST_RECORD_COUNT_KEY = "record_count"


def is_ingest_result_trailer(record: Mapping[str, object]) -> bool:
    return record.get(INGEST_RESULT_OPERATION_KEY) == INGEST_RESULT_OPERATION
