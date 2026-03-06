from __future__ import annotations

import json
from io import StringIO

import pytest

import workbench.cli.main as cli_main
import workbench.cli.stream as stream_module
from workbench.cli.stream import stream_markdown


def _line(record: dict[str, object]) -> str:
    return json.dumps(record) + "\n"


def test_stream_markdown_concatenates_in_order() -> None:
    stdin = StringIO(
        _line({"content": "# one"})
        + _line({"content": "## two"})
        + _line({"content": "three"})
    )
    stdout = StringIO()

    stream_markdown(stdin=stdin, stdout=stdout)

    assert stdout.getvalue() == "# one\n\n## two\n\nthree\n\n"


def test_stream_markdown_skips_records_without_content() -> None:
    stdin = StringIO(
        _line({"content": "first"})
        + _line({"path": "missing.md"})
        + _line({"content": ""})
        + _line({"content": "last"})
    )
    stdout = StringIO()

    stream_markdown(stdin=stdin, stdout=stdout)

    assert stdout.getvalue() == "first\n\nlast\n\n"


def test_stream_markdown_is_incremental_not_full_buffered() -> None:
    class CountingInput:
        def __init__(self) -> None:
            self.count = 0

        def __iter__(self) -> CountingInput:
            return self

        def __next__(self) -> str:
            if self.count >= 1000:
                raise StopIteration
            self.count += 1
            return _line({"content": f"doc-{self.count}"})

    class StopAfterFirstRecordWriter:
        def __init__(self) -> None:
            self.write_calls = 0

        def write(self, value: str) -> int:
            self.write_calls += 1
            if self.write_calls >= 2:
                raise RuntimeError("stop after first record")
            return len(value)

    stdin = CountingInput()
    stdout = StopAfterFirstRecordWriter()

    with pytest.raises(RuntimeError, match="stop after first record"):
        stream_markdown(stdin=stdin, stdout=stdout)

    assert stdin.count == 1


def test_cli_dispatches_stream_command(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def _fake_stream_markdown() -> None:
        called["value"] = True

    monkeypatch.setattr(stream_module, "stream_markdown", _fake_stream_markdown)
    rc = cli_main.main(["stream"])

    assert rc == 0
    assert called["value"] is True
