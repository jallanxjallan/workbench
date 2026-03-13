from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from workbench.cli import writevault as writevault_cli
from workbench.write.common import WriteError


def _init_vault_repo(tmp_path: Path) -> Path:
    vault = tmp_path / "VaultA"
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "_vault_registry.json").write_text(
        json.dumps({"mnemonic": "vault-a"}) + "\n",
        encoding="utf-8",
    )
    return vault


def test_writevault_parser_is_flagless() -> None:
    args = writevault_cli.parser().parse_args([])

    assert vars(args) == {}


def test_writevault_rejects_when_vault_registry_is_missing(tmp_path: Path) -> None:
    with pytest.raises(WriteError, match="registered Studio vault"):
        writevault_cli.run(
            input_stream=io.StringIO(
                '{"content":"Body","input_record":{"origin":{"source_type":"stdin"}}}\n'
            ),
            cwd=tmp_path,
        )


def test_writevault_discovers_vault_from_nested_cwd_and_writes_to_ingest(
    tmp_path: Path,
) -> None:
    vault = _init_vault_repo(tmp_path)
    nested = vault / "drafts"
    nested.mkdir(parents=True, exist_ok=True)

    writevault_cli.run(
        input_stream=io.StringIO(
            '{"content":"Draft body","input_record":{"filename_hint":"first-flight","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=nested,
    )

    target = vault / "_ingest" / "first-flight.md"
    assert target.read_text(encoding="utf-8") == "Draft body"


def test_writevault_skips_records_with_input_record_slug(tmp_path: Path, monkeypatch) -> None:
    vault = _init_vault_repo(tmp_path)
    log_path = tmp_path / "logs" / "writevault.log"
    monkeypatch.setattr("workbench.lib.vault_writer.default_log_path", lambda: log_path)

    writevault_cli.run(
        input_stream=io.StringIO(
            '{"content":"Body","input_record":{"slug":"omaf.first-flight","batch":"omaf.rewrite-03","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    assert not any((vault / "_ingest").glob("*.md"))
    assert "slug detected in ingest stream" in log_path.read_text(encoding="utf-8")


def test_writevault_ignores_templates_directory(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    templates_root = vault / "_templates"
    templates_root.mkdir(parents=True, exist_ok=True)
    (templates_root / "wrapper.md").write_text(
        "# Wrapped\n\n{{content}}\n",
        encoding="utf-8",
    )

    writevault_cli.run(
        input_stream=io.StringIO(
            '{"content":"Body","input_record":{"class":"note","filename_hint":"Wrapped Note","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    target = vault / "_ingest" / "Wrapped Note.md"
    assert target.read_text(encoding="utf-8") == "Body"
