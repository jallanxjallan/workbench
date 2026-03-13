from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from workbench.write.vault import write_vault_records
from workbench.write.common import WriteError


def _init_vault_repo(tmp_path: Path) -> Path:
    vault = tmp_path / "VaultA"
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "_vault_registry.json").write_text(
        json.dumps({"mnemonic": "vault-a"}) + "\n",
        encoding="utf-8",
    )
    return vault


def _write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_writevault_skips_slugged_record(tmp_path: Path, monkeypatch) -> None:
    vault = _init_vault_repo(tmp_path)
    log_path = tmp_path / "writevault.log"
    monkeypatch.setattr("workbench.lib.vault_writer.default_log_path", lambda: log_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Updated body\\n","input_record":{"slug":"omaf.first-flight","class":"passage","origin":{"source_type":"file","path":"/tmp/first-flight.md"}}}\n'
        ),
        cwd=vault,
    )

    assert written == []
    assert "slug detected in ingest stream" in log_path.read_text(encoding="utf-8")


def test_writevault_writes_raw_content_to_ingest(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"filename_hint":"k3f7","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    target = vault / "_ingest" / "k3f7.md"
    assert written == [target]
    assert target.read_text(encoding="utf-8") == "Body\n"


def test_writevault_slugless_record_creates_new_ingest_file_without_writeback(
    tmp_path: Path,
) -> None:
    vault = _init_vault_repo(tmp_path)
    existing = vault / "_ingest" / "Inbox.md"
    _write_markdown(existing, "First body\n")

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Second body\\n","input_record":{"class":"note","filename_hint":"Inbox","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "Inbox_2.md"]
    assert existing.read_text(encoding="utf-8") == "First body\n"
    assert written[0].read_text(encoding="utf-8") == "Second body\n"


def test_writevault_ignores_invalid_records_and_continues(tmp_path: Path, monkeypatch) -> None:
    vault = _init_vault_repo(tmp_path)
    log_path = tmp_path / "writevault.log"
    monkeypatch.setattr("workbench.lib.vault_writer.default_log_path", lambda: log_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '\n'.join(
                [
                    '{"content":"Good\\n","input_record":{"filename_hint":"Good","origin":{"source_type":"stdin"}}}',
                    '{"input_record":{"filename_hint":"Missing","origin":{"source_type":"stdin"}}}',
                    '{"content":"Bad json"',
                    '{"content":"Also good\\n","input_record":{"filename_hint":"Also Good","origin":{"source_type":"stdin"}}}',
                    "",
                ]
            )
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "Good.md", vault / "_ingest" / "Also Good.md"]
    assert (vault / "_ingest" / "Good.md").read_text(encoding="utf-8") == "Good\n"
    assert (vault / "_ingest" / "Also Good.md").read_text(encoding="utf-8") == "Also good\n"
    log_text = log_path.read_text(encoding="utf-8")
    assert "invalid NDJSON record skipped" in log_text
    assert "record missing content" in log_text


def test_writevault_does_not_require_templates_directory(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"class":"note","filename_hint":"No Template","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "No Template.md"]
    assert written[0].read_text(encoding="utf-8") == "Body\n"


def test_writevault_accepts_minimal_stdin_record(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "Untitled.md"]
    assert written[0].read_text(encoding="utf-8") == "Body\n"


def test_writevault_file_style_record_uses_filename_hint(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"filename_hint":"Some File.md","origin":{"source_type":"file","path":"/tmp/source/Some File.md"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "Some File.md"]
    assert written[0].read_text(encoding="utf-8") == "Body\n"


@pytest.mark.parametrize(
    ("payload", "expected_written"),
    [
        ('{"content":"Body\\n"}\n', ["Untitled.md"]),
        ('{"content":"Body\\n","input_record":"oops"}\n', []),
        ('{"content":"Body\\n","input_record":{}}\n', ["Untitled.md"]),
        ('{"content":"Body\\n","input_record":{"origin":{}}}\n', ["Untitled.md"]),
        ('{"content":"Body\\n","origin":{"source_type":"stdin"}}\n', ["Untitled.md"]),
    ],
)
def test_writevault_tolerates_noncanonical_records(
    tmp_path: Path,
    payload: str,
    expected_written: list[str],
) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(input_stream=io.StringIO(payload), cwd=vault)

    assert written == [vault / "_ingest" / name for name in expected_written]
