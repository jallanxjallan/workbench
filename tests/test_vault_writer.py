from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from workbench.interop.document import Document
from workbench.lib.vault_writer import write_vault_records
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


def _write_markdown(path: Path, *, slug: str | None, batch: str | None, body: str) -> None:
    metadata: dict[str, object] = {}
    if slug is not None:
        metadata["slug"] = slug
    if batch is not None:
        metadata["batch"] = batch
    document = Document(metadata=metadata, content=body)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document.write_text(), encoding="utf-8")


def test_writevault_basic_write_stages_new_file(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body","input_record":{"source":"x"},"filename_hint":"First Flight"}\n'
        ),
        overwrite=False,
        folder="notes",
        template=None,
        cwd=vault,
    )

    target = vault / "notes" / "First Flight.md"
    assert written == [target]
    assert target.read_text(encoding="utf-8") == "Body"
    assert _git(vault, "diff", "--cached", "--name-only") == "notes/First Flight.md"


def test_writevault_overwrite_succeeds_when_slug_and_batch_match(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    target = vault / "notes" / "first-flight.md"
    _write_markdown(
        target,
        slug="omaf.first-flight",
        batch="omaf.rewrite-01",
        body="Old body",
    )
    _git(vault, "add", "notes/first-flight.md")
    _git(vault, "commit", "-m", "seed note")

    write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Updated body","input_record":{"source":"x"},"slug":"omaf.first-flight","batch":"omaf.rewrite-01"}\n'
        ),
        overwrite=True,
        folder="notes",
        template=None,
        cwd=vault,
    )

    assert target.read_text(encoding="utf-8") == "Updated body"
    assert _git(vault, "diff", "--cached", "--name-only") == "notes/first-flight.md"


def test_writevault_overwrite_fails_on_slug_mismatch(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    target = vault / "notes" / "first-flight.md"
    _write_markdown(
        target,
        slug="omaf.first-flight",
        batch="omaf.rewrite-01",
        body="Old body",
    )
    _git(vault, "add", "notes/first-flight.md")
    _git(vault, "commit", "-m", "seed note")

    with pytest.raises(WriteError, match="existing slug"):
        write_vault_records(
            input_stream=io.StringIO(
                '{"content":"Updated body","input_record":{"source":"x"},"slug":"site.first-flight","batch":"omaf.rewrite-01"}\n'
            ),
            overwrite=True,
            folder="notes",
            template=None,
            cwd=vault,
        )


def test_writevault_overwrite_fails_on_batch_mismatch(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    target = vault / "notes" / "first-flight.md"
    _write_markdown(
        target,
        slug="omaf.first-flight",
        batch="omaf.rewrite-01",
        body="Old body",
    )
    _git(vault, "add", "notes/first-flight.md")
    _git(vault, "commit", "-m", "seed note")

    with pytest.raises(WriteError, match="existing batch"):
        write_vault_records(
            input_stream=io.StringIO(
                '{"content":"Updated body","input_record":{"source":"x"},"slug":"omaf.first-flight","batch":"omaf.rewrite-02"}\n'
            ),
            overwrite=True,
            folder="notes",
            template=None,
            cwd=vault,
        )


def test_writevault_protects_existing_unslugged_artifact(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    target = vault / "notes" / "artifact.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("artifact\n", encoding="utf-8")
    _git(vault, "add", "notes/artifact.md")
    _git(vault, "commit", "-m", "seed artifact")

    with pytest.raises(WriteError, match="artifact or workspace file"):
        write_vault_records(
            input_stream=io.StringIO(
                '{"content":"Updated body","input_record":{"source":"x"},"filename_hint":"artifact"}\n'
            ),
            overwrite=True,
            folder="notes",
            template=None,
            cwd=vault,
        )


def test_writevault_overwrite_fails_when_file_has_unstaged_modifications(
    tmp_path: Path,
) -> None:
    vault = _init_vault_repo(tmp_path)
    target = vault / "notes" / "first-flight.md"
    _write_markdown(
        target,
        slug="omaf.first-flight",
        batch="omaf.rewrite-01",
        body="Old body",
    )
    _git(vault, "add", "notes/first-flight.md")
    _git(vault, "commit", "-m", "seed note")
    target.write_text("locally modified\n", encoding="utf-8")

    with pytest.raises(WriteError, match="modified file"):
        write_vault_records(
            input_stream=io.StringIO(
                '{"content":"Updated body","input_record":{"source":"x"},"slug":"omaf.first-flight","batch":"omaf.rewrite-01"}\n'
            ),
            overwrite=True,
            folder="notes",
            template=None,
            cwd=vault,
        )
