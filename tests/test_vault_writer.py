from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from workbench.interop.document import Document
from workbench.write.vault import write_vault_records
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


def _write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_writevault_existing_slug_writeback_preserves_frontmatter(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    target = vault / "notes" / "first-flight.md"
    original = (
        "---\n"
        "slug: omaf.first-flight\n"
        "class: passage\n"
        "status: draft\n"
        "---\n"
        "\n"
        "Old body\n"
    )
    _write_markdown(target, original)
    _git(vault, "add", "notes/first-flight.md")
    _git(vault, "commit", "-m", "seed note")

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Updated body\\n","input_record":{"slug":"omaf.first-flight","class":"passage","origin":{"source_type":"file","path":"/tmp/first-flight.md"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [target]
    assert target.read_text(encoding="utf-8") == (
        "---\n"
        "slug: omaf.first-flight\n"
        "class: passage\n"
        "status: draft\n"
        "---\n"
        "\n"
        "Updated body\n"
    )
    assert _git(vault, "diff", "--cached", "--name-only") == "notes/first-flight.md"


def test_writevault_new_slugged_record_writes_to_ingest(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"slug":"omaf.first-flight.k3f7","class":"passage","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    target = vault / "_ingest" / "k3f7.md"
    assert written == [target]
    written_doc = Document.read_file(target)
    assert written_doc.metadata == {
        "slug": "omaf.first-flight.k3f7",
        "class": "passage",
        "origin": {"source_type": "stdin"},
    }
    assert written_doc.content == "Body\n"
    assert _git(vault, "diff", "--cached", "--name-only") == "_ingest/k3f7.md"


def test_writevault_slugless_record_creates_new_ingest_file_without_writeback(
    tmp_path: Path,
) -> None:
    vault = _init_vault_repo(tmp_path)
    existing = vault / "_ingest" / "Inbox.md"
    _write_markdown(existing, "First body\n")
    _git(vault, "add", "_ingest/Inbox.md")
    _git(vault, "commit", "-m", "seed ingest")

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Second body\\n","input_record":{"class":"note","filename_hint":"Inbox","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "Inbox-2.md"]
    assert existing.read_text(encoding="utf-8") == "First body\n"
    created = Document.read_file(written[0])
    assert created.metadata == {
        "class": "note",
        "filename_hint": "Inbox",
        "origin": {"source_type": "stdin"},
    }
    assert created.content == "Second body\n"


def test_writevault_slug_collision_aborts(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    _write_markdown(
        vault / "notes" / "first.md",
        "---\nslug: omaf.first-flight\n---\n\nOne\n",
    )
    _write_markdown(
        vault / "archive" / "first.md",
        "---\nslug: omaf.first-flight\n---\n\nTwo\n",
    )
    _git(vault, "add", "notes/first.md")
    _git(vault, "add", "archive/first.md")
    _git(vault, "commit", "-m", "seed collision")

    with pytest.raises(WriteError, match="multiple files match slug"):
        write_vault_records(
            input_stream=io.StringIO(
                '{"content":"Updated\\n","input_record":{"slug":"omaf.first-flight","origin":{"source_type":"stdin"}}}\n'
            ),
            cwd=vault,
        )


def test_writevault_requires_git_repo_before_writing(tmp_path: Path) -> None:
    vault = tmp_path / "VaultA"
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "_vault_registry.json").write_text(
        json.dumps({"mnemonic": "vault-a"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WriteError, match="git"):
        write_vault_records(
            input_stream=io.StringIO(
                '{"content":"Body\\n","input_record":{"class":"note","filename_hint":"Inbox","origin":{"source_type":"stdin"}}}\n'
            ),
            cwd=vault,
        )

    assert not (vault / "_ingest").exists()


def test_writevault_does_not_require_templates_directory(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"class":"note","filename_hint":"No Template","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "No Template.md"]
    assert written[0].read_text(encoding="utf-8") == (
        "---\nclass: note\nfilename_hint: No Template\norigin:\n  source_type: stdin\n---\n\nBody\n"
    )


def test_writevault_force_stages_ignored_ingest_files(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    (vault / ".gitignore").write_text("*\n!*/\n", encoding="utf-8")
    _git(vault, "add", "-f", ".gitignore")
    _git(vault, "commit", "-m", "ignore by default")

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"filename_hint":"Ignored Note","origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "Ignored Note.md"]
    assert _git(vault, "diff", "--cached", "--name-only") == "_ingest/Ignored Note.md"


def test_writevault_accepts_minimal_stdin_record(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"origin":{"source_type":"stdin"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "Untitled.md"]
    assert Document.read_file(written[0]).metadata == {"origin": {"source_type": "stdin"}}


def test_writevault_file_style_record_uses_filename_hint(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)

    written = write_vault_records(
        input_stream=io.StringIO(
            '{"content":"Body\\n","input_record":{"filename_hint":"Some File.md","origin":{"source_type":"file","path":"/tmp/source/Some File.md"}}}\n'
        ),
        cwd=vault,
    )

    assert written == [vault / "_ingest" / "Some File.md"]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ('{"content":"Body\\n"}\n', "missing required record field: input_record"),
        (
            '{"content":"Body\\n","input_record":"oops"}\n',
            "invalid record field: input_record",
        ),
        (
            '{"content":"Body\\n","input_record":{}}\n',
            "missing required record field: input_record.origin",
        ),
        (
            '{"content":"Body\\n","input_record":{"origin":{}}}\n',
            "missing required record field: input_record.origin.source_type",
        ),
        (
            '{"content":"Body\\n","origin":{"source_type":"stdin"}}\n',
            "missing required record field: input_record",
        ),
    ],
)
def test_writevault_rejects_invalid_canonical_records(
    tmp_path: Path,
    payload: str,
    message: str,
) -> None:
    vault = _init_vault_repo(tmp_path)

    with pytest.raises(WriteError, match=message):
        write_vault_records(input_stream=io.StringIO(payload), cwd=vault)
