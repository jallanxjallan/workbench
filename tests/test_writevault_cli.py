from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from workbench.cli import writevault as writevault_cli
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
        json.dumps({"vault": "vault-a"}) + "\n",
        encoding="utf-8",
    )
    _git(vault, "init")
    _git(vault, "config", "user.email", "workbench-tests@example.com")
    _git(vault, "config", "user.name", "Workbench Tests")
    (vault / "README.md").write_text("seed\n", encoding="utf-8")
    _git(vault, "add", "README.md")
    _git(vault, "commit", "-m", "seed")
    return vault


def test_writevault_parser_defaults() -> None:
    args = writevault_cli.parser().parse_args([])

    assert args.overwrite is False
    assert args.folder is None
    assert args.template is None


def test_writevault_rejects_when_vault_registry_is_missing(tmp_path: Path) -> None:
    with pytest.raises(WriteError, match="_vault_registry.json"):
        writevault_cli.run(
            overwrite=False,
            folder=None,
            template=None,
            input_stream=io.StringIO('{"content":"Body","input_record":{}}\n'),
            cwd=tmp_path,
        )


def test_writevault_defaults_to_current_working_directory_inside_vault(
    tmp_path: Path,
) -> None:
    vault = _init_vault_repo(tmp_path)
    nested = vault / "drafts"
    nested.mkdir(parents=True, exist_ok=True)

    writevault_cli.run(
        overwrite=False,
        folder=None,
        template=None,
        input_stream=io.StringIO(
            '{"content":"Draft body","input_record":{},"slug":"omaf.first-flight"}\n'
        ),
        cwd=nested,
    )

    target = nested / "first-flight.md"
    assert target.read_text(encoding="utf-8") == "Draft body"
    assert _git(vault, "diff", "--cached", "--name-only") == "drafts/first-flight.md"


def test_writevault_accepts_batch_field_in_ndjson_contract(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    writevault_cli.run(
        overwrite=False,
        folder="notes",
        template=None,
        input_stream=io.StringIO(
            '{"content":"Body","input_record":{},"slug":"omaf.first-flight","batch":"omaf.rewrite-03"}\n'
        ),
        cwd=vault,
    )

    target = vault / "notes" / "first-flight.md"
    assert target.read_text(encoding="utf-8") == "Body"


def test_writevault_applies_template_from_vault_templates(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    templates_root = vault / "_templates"
    templates_root.mkdir(parents=True, exist_ok=True)
    (templates_root / "wrapper.md").write_text(
        "# Wrapped\n\n{{content}}\n",
        encoding="utf-8",
    )

    writevault_cli.run(
        overwrite=False,
        folder="notes",
        template="wrapper",
        input_stream=io.StringIO(
            '{"content":"Body","input_record":{},"filename_hint":"Wrapped Note"}\n'
        ),
        cwd=vault,
    )

    target = vault / "notes" / "Wrapped Note.md"
    assert target.read_text(encoding="utf-8") == "# Wrapped\n\nBody\n"
