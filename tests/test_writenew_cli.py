from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from workbench.cli import writenew as writenew_cli
from workbench.interop.document import Document
from workbench.write.common import WriteError


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_vault(root: Path, *, name: str = "HHP", vault_field: str = "hhp") -> Path:
    vault = root / name
    vault.mkdir(parents=True, exist_ok=True)
    _write(vault / "_vault_registry.json", json.dumps({"vault": vault_field}) + "\n")
    return vault


def _run(
    *,
    vault: Path,
    folder: str = "contents",
    template: str = "passage",
    ndjson: str,
    confirm: str = "y",
) -> bool:
    return writenew_cli.run(
        folder=folder,
        template=template,
        input_stream=io.StringIO(ndjson),
        cwd=vault,
        tty_reader=io.StringIO(confirm + "\n"),
    )


def test_writenew_rejects_non_vault_current_directory(tmp_path: Path) -> None:
    with pytest.raises(WriteError, match="_vault_registry.json"):
        writenew_cli.run(
            folder="contents",
            template="passage",
            input_stream=io.StringIO(
                '{"batch_slug":"b","content":"Body","filename_hint":"alpha"}\n'
            ),
            cwd=tmp_path,
            tty_reader=io.StringIO("y\n"),
        )


def test_writenew_does_not_scan_upward_for_vault(tmp_path: Path) -> None:
    vault = _init_vault(tmp_path, name="RootVault")
    child = vault / "nested"
    child.mkdir(parents=True, exist_ok=True)

    with pytest.raises(WriteError, match="_vault_registry.json"):
        writenew_cli.run(
            folder="contents",
            template="passage",
            input_stream=io.StringIO(
                '{"batch_slug":"b","content":"Body","filename_hint":"alpha"}\n'
            ),
            cwd=child,
            tty_reader=io.StringIO("y\n"),
        )


def test_writenew_parser_defaults_folder_and_template() -> None:
    args = writenew_cli.parser().parse_args([])
    assert args.folder == "contents"
    assert args.template == "passage"


def test_writenew_uses_default_folder_and_template(tmp_path: Path) -> None:
    vault = _init_vault(tmp_path)
    _write(vault / "_common" / "templates" / "passage.md", "---\nclass: passage\n---\n")

    completed = _run(
        vault=vault,
        ndjson='{"batch_slug":"batch-1","content":"Test Body","filename_hint":"Test Passage"}\n',
    )

    assert completed is True
    target = vault / "contents" / "test-passage.md"
    assert target.exists()
    parsed = Document.read_file(target)
    assert parsed.metadata["class"] == "passage"
    assert parsed.metadata["batch"] == "batch-1"
    assert parsed.content.strip() == "Test Body"


def test_writenew_honors_explicit_folder_and_template(tmp_path: Path) -> None:
    vault = _init_vault(tmp_path)
    _write(vault / "_common" / "templates" / "topic.md", "---\nclass: topic\n---\n")

    completed = _run(
        vault=vault,
        folder="topics",
        template="topic",
        ndjson='{"batch_slug":"batch-1","content":"Body","filename_hint":"Batavia Triptych"}\n',
    )

    assert completed is True
    target = vault / "topics" / "batavia-triptych.md"
    assert target.exists()
    parsed = Document.read_file(target)
    assert parsed.metadata["class"] == "topic"
    assert parsed.metadata["batch"] == "batch-1"


def test_writenew_rejects_underscore_prefixed_template(tmp_path: Path) -> None:
    vault = _init_vault(tmp_path)
    _write(vault / "_common" / "templates" / "_hidden.md", "---\nclass: passage\n---\n")

    with pytest.raises(WriteError, match="starting with '_'"):
        _run(
            vault=vault,
            template="_hidden",
            ndjson='{"batch_slug":"batch-1","content":"Body"}\n',
        )


def test_writenew_confirmation_no_cancels_without_writing(tmp_path: Path) -> None:
    vault = _init_vault(tmp_path)
    _write(vault / "_common" / "templates" / "passage.md", "---\nclass: passage\n---\n")

    completed = _run(
        vault=vault,
        ndjson='{"batch_slug":"batch-1","content":"Body","filename_hint":"cancelled"}\n',
        confirm="n",
    )

    assert completed is False
    assert not (vault / "contents" / "cancelled.md").exists()


def test_writenew_confirmation_yes_proceeds(tmp_path: Path) -> None:
    vault = _init_vault(tmp_path)
    _write(vault / "_common" / "templates" / "passage.md", "---\nclass: passage\n---\n")

    completed = _run(
        vault=vault,
        ndjson='{"batch_slug":"batch-1","content":"Body","filename_hint":"confirmed"}\n',
        confirm="y",
    )

    assert completed is True
    assert (vault / "contents" / "confirmed.md").exists()


def test_writenew_preserves_stream_record_handling_and_collisions(
    tmp_path: Path,
) -> None:
    vault = _init_vault(tmp_path)
    _write(
        vault / "_common" / "templates" / "passage.md",
        "---\nclass: passage\nstate: candidate\nslug: __SLUG__\n---\n\n# Template Body\n",
    )
    _write(vault / "contents" / "freeberg.md", "existing\n")

    completed = _run(
        vault=vault,
        ndjson=(
            '{"batch_slug":"omaf.research","content":"First","filename_hint":"freeberg","provenance":{"tool":"pandoc","source":"one"}}\n'
            '{"batch_slug":"omaf.research","content":"Second","filename_hint":"freeberg"}\n'
        ),
    )

    assert completed is True
    one = Document.read_file(vault / "contents" / "freeberg-2.md")
    two = Document.read_file(vault / "contents" / "freeberg-3.md")

    assert one.metadata["class"] == "passage"
    assert one.metadata["batch"] == "omaf.research"
    assert one.metadata["state"] == "candidate"
    assert one.metadata["origin"] == {"tool": "pandoc", "source": "one"}
    assert "slug" not in one.metadata
    assert one.content.strip() == "First"

    assert two.metadata["class"] == "passage"
    assert two.metadata["batch"] == "omaf.research"
    assert two.content.strip() == "Second"

