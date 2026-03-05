from __future__ import annotations

import pytest

import workbench.write.common as common_module


def test_fetch_batch_records_is_lazy_and_stream_based(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def _fake_iter_stdout_lines(args: list[str], *, check: bool = True):
        calls.append(tuple(args))
        assert check is True
        yield '{"content":"one","origin":{"slug":"a","path":"/tmp/a.md"},"batch_slug":"batch-1"}\n'
        yield '{"content":"two","origin":{"slug":"b","path":"/tmp/b.md"},"batch_slug":"batch-1"}\n'

    monkeypatch.setattr(common_module, "iter_stdout_lines", _fake_iter_stdout_lines)

    records = common_module.fetch_batch_records("batch-1", asc_bin="asc")

    # Calling fetch should not execute subprocess logic until iteration starts.
    assert calls == []

    first = next(records)
    assert calls == [("asc", "emit", "batch-1")]
    assert first.content == "one"

    second = next(records)
    assert second.content == "two"

    with pytest.raises(StopIteration):
        next(records)
