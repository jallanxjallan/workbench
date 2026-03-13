from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from workbench.cli import writevault as writevault_cli
from workbench.interop.document import Document
from workbench.write.common import WriteError


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _init_vault_repo(tmp_path: Path) -> Path:
    vault = tmp_path / "VaultA"
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "_vault_registry.json").write_text(
        json.dumps({"mnemonic": "vault-a"}) + "\n",
        encoding="utf-8",
    )
    _git(vault, "init")
    _git(vault, "config", "user.email", "workbench-tests@example.com")
    _git(vault, "config", "user.name", "Workbench Tests")
    (vault / "README.md").write_text("seed\n", encoding="utf-8")
    _git(vault, "add", "README.md")
    _git(vault, "commit", "-m", "seed")
    return vault


def test_writevault_parser_is_flagless() -> None:
    args = writevault_cli.parser().parse_args([])

    assert vars(args) == {}


def test_writevault_rejects_when_vault_registry_is_missing(tmp_path: Path) -> None:
    with pytest.raises(WriteError, match="_vault_registry.json"):
        writevault_cli.run(
            input_stream=io.StringIO('{"content":"Body","input_record":{}}\n'),
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
            '{"content":"Draft body","input_record":{"slug":"omaf.first-flight","class":"passage"},"slug":"omaf.first-flight"}\n'
        ),
        cwd=nested,
    )

    target = vault / "_ingest" / "first-flight.md"
    assert Document.read_file(target).metadata == {
        "slug": "omaf.first-flight",
        "class": "passage",
    }
    assert _git(vault, "diff", "--cached", "--name-only") == "_ingest/first-flight.md"


def test_writevault_accepts_batch_field_without_writing_it(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    writevault_cli.run(
        input_stream=io.StringIO(
            '{"content":"Body","input_record":{"slug":"omaf.first-flight"},"slug":"omaf.first-flight","batch":"omaf.rewrite-03"}\n'
        ),
        cwd=vault,
    )

    target = vault / "_ingest" / "first-flight.md"
    assert Document.read_file(target).metadata == {"slug": "omaf.first-flight"}


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
            '{"content":"Body","input_record":{"class":"note"},"filename_hint":"Wrapped Note"}\n'
        ),
        cwd=vault,
    )

    target = vault / "_ingest" / "Wrapped Note.md"
    assert target.read_text(encoding="utf-8") == "---\nclass: note\n---\n\nBody"
