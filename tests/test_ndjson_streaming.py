from __future__ import annotations

import io

import pytest

import workbench.write.common as common_module


def test_iter_input_records_is_lazy_and_stream_based() -> None:
    stream = io.StringIO(
        "\n".join(
            [
                '{"content":"one","batch_slug":"batch-1"}',
                '{"content":"two","batch_slug":"batch-1"}',
            ]
        )
        + "\n"
    )

    records = common_module.iter_input_records(stream)

    first = next(records)
    assert first.content == "one"
    assert first.batch_slug == "batch-1"

    second = next(records)
    assert second.content == "two"
    assert second.batch_slug == "batch-1"

    with pytest.raises(StopIteration):
        next(records)
