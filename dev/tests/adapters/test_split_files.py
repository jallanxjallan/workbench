from __future__ import annotations

import io
import json
import sys

from workbench.adapters import split_files


def _run_split(
    records: list[dict[str, object]], *, args: list[str] | None = None
) -> tuple[int, list[dict[str, object]]]:
    stdin_payload = "".join(json.dumps(record) + "\n" for record in records)
    stdin_buf = io.StringIO(stdin_payload)
    stdout_buf = io.StringIO()

    old_stdin, old_stdout = sys.stdin, sys.stdout
    try:
        sys.stdin, sys.stdout = stdin_buf, stdout_buf
        rc = split_files.main(args or [])
    finally:
        sys.stdin, sys.stdout = old_stdin, old_stdout

    rows = [json.loads(line) for line in stdout_buf.getvalue().splitlines() if line.strip()]
    return rc, rows


def test_no_markers_emits_single_output_record() -> None:
    rc, rows = _run_split([{"content": "plain text\n", "stem": "My Note"}])

    assert rc == 0
    assert len(rows) == 1
    row = rows[0]
    assert row["section_index"] == 1
    assert row["split_stem"] == "my_note"
    assert row["output_path"] == "_new/my_note/my_note--001.md"
    assert row["content"] == "plain text\n"


def test_markers_split_into_expected_sections() -> None:
    content = "A\n<!-- AS:SECTION -->\nB\n<!-- AS:SECTION -->\nC\n"
    rc, rows = _run_split([{"content": content}], args=["--stem", "demo"])

    assert rc == 0
    assert len(rows) == 3
    assert [row["content"] for row in rows] == ["A\n", "B\n", "C\n"]
    assert [row["output_path"] for row in rows] == [
        "_new/demo/demo--001.md",
        "_new/demo/demo--002.md",
        "_new/demo/demo--003.md",
    ]


def test_strip_and_drop_empty_behavior() -> None:
    content = (
        "\n\nfirst\n\n"
        "<!-- AS:SECTION -->\n\n\n"
        "<!-- AS:SECTION -->\n\nsecond\n\n"
    )
    rc, rows = _run_split([{"content": content}], args=["--stem", "trim"])

    assert rc == 0
    assert len(rows) == 2
    assert [row["content"] for row in rows] == ["first\n", "second\n"]
    assert [row["section_index"] for row in rows] == [1, 2]


def test_deterministic_naming_for_stem_digits_and_flat() -> None:
    content = "one\n<!-- AS:SECTION -->\ntwo\n"
    rc, rows = _run_split(
        [{"content": content}],
        args=["--stem", "Alpha Beta", "--digits", "4", "--flat"],
    )

    assert rc == 0
    assert [row["output_path"] for row in rows] == [
        "_new/alpha_beta--0001.md",
        "_new/alpha_beta--0002.md",
    ]


def test_stem_derives_from_source_file_when_needed() -> None:
    rc, rows = _run_split([{"content": "x", "source_file": "drafts/Source Name.md"}])

    assert rc == 0
    assert len(rows) == 1
    assert rows[0]["split_stem"] == "source_name"
    assert rows[0]["output_path"] == "_new/source_name/source_name--001.md"
    assert rows[0]["source_file"] == "drafts/Source Name.md"


def test_stem_derives_from_output_path_before_source_file() -> None:
    rc, rows = _run_split(
        [
            {
                "content": "x",
                "output_path": "notes/Output Name.md",
                "source_file": "drafts/Source Name.md",
            }
        ]
    )

    assert rc == 0
    assert len(rows) == 1
    assert rows[0]["split_stem"] == "output_name"
    assert rows[0]["output_path"] == "_new/output_name/output_name--001.md"
