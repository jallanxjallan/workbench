from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stdout

from workbench.framing.markdown import MULTI_DOCUMENT_ERROR, emit_markdown_batch
from workbench.tools.markdown_document import Document
from workbench.write.writeback import main as writeback_main
from workbench.write.writenew import main as writenew_main
from workbench.write.writestream import main as writestream_main


def _create_vault(tmp_path):
    vault_root = tmp_path / "vault"
    target_dir = vault_root / "projects" / "odyssey" / "drafts"
    target_dir.mkdir(parents=True, exist_ok=True)
    registry = {
        "projects": {
            "odyssey": {
                "project_code": "omaf",
            }
        }
    }
    registry_path = vault_root / "00-system" / "project_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return target_dir


def test_writenew_creates_file(tmp_path) -> None:
    doc = Document(metadata={"slug": "legacy", "title": "The Blockade Run"}, content="First body")
    stream = emit_markdown_batch([doc])
    target_dir = _create_vault(tmp_path)

    stdin_backup = sys.stdin
    try:
        sys.stdin = io.StringIO(stream)
        exit_code = writenew_main(["--target-dir", str(target_dir)])
    finally:
        sys.stdin = stdin_backup

    assert exit_code == 0
    files = sorted(target_dir.glob("*.md"))
    assert len(files) == 1
    written = Document.read_text(files[0].read_text(encoding="utf-8"))
    slug = written.metadata.get("slug")
    assert isinstance(slug, str)
    assert slug == files[0].stem
    assert slug != "legacy"
    assert re.fullmatch(r"omaf-the-blockade-run-[0-9a-z]{5}", slug)


def test_writenew_rejects_multi_document_markdown(tmp_path, capsys) -> None:
    stream = (
        "---\nslug: one\n---\n\nOne\n\n"
        "---\nslug: two\n---\n\nTwo\n"
    )
    target_dir = tmp_path / "target"

    stdin_backup = sys.stdin
    try:
        sys.stdin = io.StringIO(stream)
        exit_code = writenew_main(["--target-dir", str(target_dir)])
    finally:
        sys.stdin = stdin_backup

    assert exit_code == 1
    assert MULTI_DOCUMENT_ERROR in capsys.readouterr().err


def test_writeback_overwrites_existing(tmp_path) -> None:
    project_root = tmp_path / "project"
    existing = project_root / "docs" / "entry.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("---\nslug: demo\n---\n\nOld", encoding="utf-8")

    updated = emit_markdown_batch(
        [
            Document(
                metadata={"source_path": "docs/entry.md", "slug": "demo"},
                content="New body",
            )
        ]
    )

    stdin_backup = sys.stdin
    try:
        sys.stdin = io.StringIO(updated)
        exit_code = writeback_main(["--project-root", str(project_root)])
    finally:
        sys.stdin = stdin_backup

    assert exit_code == 0
    assert existing.read_text(encoding="utf-8") == updated


def test_writeback_requires_slug_even_with_source_path(tmp_path, capsys) -> None:
    project_root = tmp_path / "project"
    existing = project_root / "docs" / "entry.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("---\nslug: demo\n---\n\nOld", encoding="utf-8")

    updated = emit_markdown_batch(
        [
            Document(
                metadata={"source_path": "docs/entry.md"},
                content="New body",
            )
        ]
    )

    stdin_backup = sys.stdin
    try:
        sys.stdin = io.StringIO(updated)
        exit_code = writeback_main(["--project-root", str(project_root)])
    finally:
        sys.stdin = stdin_backup

    assert exit_code == 1
    assert "requires frontmatter slug" in capsys.readouterr().err


def test_writeback_rejects_slug_mismatch_for_source_path(tmp_path, capsys) -> None:
    project_root = tmp_path / "project"
    existing = project_root / "docs" / "entry.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("---\nslug: demo\n---\n\nOld", encoding="utf-8")

    updated = emit_markdown_batch(
        [
            Document(
                metadata={"source_path": "docs/entry.md", "slug": "changed"},
                content="New body",
            )
        ]
    )

    stdin_backup = sys.stdin
    try:
        sys.stdin = io.StringIO(updated)
        exit_code = writeback_main(["--project-root", str(project_root)])
    finally:
        sys.stdin = stdin_backup

    assert exit_code == 1
    assert "slug mismatch for target" in capsys.readouterr().err


def test_writestream_passthrough() -> None:
    source = "---\nslug: passthrough\n---\n\nBody"
    stdin_backup = sys.stdin
    try:
        sys.stdin = io.StringIO(source)
        with redirect_stdout(io.StringIO()) as captured:
            exit_code = writestream_main([])
    finally:
        sys.stdin = stdin_backup

    assert exit_code == 0
    assert captured.getvalue() == source


def test_writestream_rejects_multi_document_markdown(capsys) -> None:
    source = (
        "---\nslug: one\n---\n\nOne\n\n"
        "---\nslug: two\n---\n\nTwo\n"
    )
    stdin_backup = sys.stdin
    try:
        sys.stdin = io.StringIO(source)
        exit_code = writestream_main([])
    finally:
        sys.stdin = stdin_backup

    assert exit_code == 1
    assert MULTI_DOCUMENT_ERROR in capsys.readouterr().err
