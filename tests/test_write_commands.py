from __future__ import annotations

import io
import re
import sys

from workbench.framing.markdown import MULTI_DOCUMENT_ERROR
from workbench.tools.markdown_document import Document
from workbench.write.common import WriteRecord
from workbench.write.writeback import main as writeback_main
from workbench.write.writenew import main as writenew_main
from workbench.write.writestream import main as writestream_main

_ASC_SENTINEL_RE = re.compile(r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$")


def _write_registry(tmp_path, payload: dict[str, str]):
    path = tmp_path / "vaults.yaml"
    lines = [f"{key}: {value}" for key, value in payload.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _parse_doc(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if lines and _ASC_SENTINEL_RE.match(lines[0].strip()):
        text_without_sentinel = "".join(lines[1:])
    else:
        text_without_sentinel = text
    return Document.read_text(text_without_sentinel), text


def test_writenew_routes_by_prompt_slug_prefix(tmp_path, monkeypatch) -> None:
    target_root = tmp_path / "vault-hhp"
    registry = _write_registry(tmp_path, {"hhp": str(target_root)})
    records = [
        WriteRecord(
            metadata={"prompt_slug": "hhp.firms-biggest-case", "title": "The Blockade Run"},
            content="First body",
        )
    ]
    monkeypatch.setattr("workbench.write.writenew.fetch_batch_records", lambda *_args, **_kwargs: records)

    exit_code = writenew_main(["20260226-120001", "--vault-registry", str(registry)])

    assert exit_code == 0
    output = target_root / "the-blockade-run.md"
    assert output.exists()
    parsed, text = _parse_doc(output)
    assert text.startswith("--- ASC BATCH: 20260226-120001 ---")
    assert parsed.content == "First body"
    assert parsed.metadata["prompt_slug"] == "hhp.firms-biggest-case"


def test_writenew_uses_absolute_target_path(tmp_path, monkeypatch) -> None:
    registry = _write_registry(tmp_path, {"hhp": str(tmp_path / "vault-hhp")})
    output = tmp_path / "explicit.md"
    records = [
        WriteRecord(
            metadata={"target_path": str(output), "title": "Ignored"},
            content="Body",
        )
    ]
    monkeypatch.setattr("workbench.write.writenew.fetch_batch_records", lambda *_args, **_kwargs: records)

    exit_code = writenew_main(["batch-1", "--vault-registry", str(registry)])

    assert exit_code == 0
    assert output.exists()
    parsed, text = _parse_doc(output)
    assert text.startswith("--- ASC BATCH: batch-1 ---")
    assert parsed.content == "Body"


def test_writenew_fails_on_relative_target_without_routing(tmp_path, monkeypatch, capsys) -> None:
    registry = _write_registry(tmp_path, {"hhp": str(tmp_path / "vault-hhp")})
    records = [
        WriteRecord(
            metadata={"target_path": "notes/output.md"},
            content="Body",
        )
    ]
    monkeypatch.setattr("workbench.write.writenew.fetch_batch_records", lambda *_args, **_kwargs: records)

    exit_code = writenew_main(["batch-1", "--vault-registry", str(registry)])

    assert exit_code == 1
    assert "relative target_path" in capsys.readouterr().err


def test_writeback_overwrites_existing_using_instruction_slug_prefix(tmp_path, monkeypatch) -> None:
    target_root = tmp_path / "vault-hhp"
    target_file = target_root / "docs" / "entry.md"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("---\ntitle: Old\n---\n\nOld", encoding="utf-8")
    registry = _write_registry(tmp_path, {"hhp": str(target_root)})
    records = [
        WriteRecord(
            metadata={
                "instruction_slug": "hhp.use-legal-language",
                "source_path": "docs/entry.md",
                "title": "Updated",
            },
            content="New body",
        )
    ]
    monkeypatch.setattr("workbench.write.writeback.fetch_batch_records", lambda *_args, **_kwargs: records)

    exit_code = writeback_main(["batch-2", "--vault-registry", str(registry)])

    assert exit_code == 0
    parsed, text = _parse_doc(target_file)
    assert text.startswith("--- ASC BATCH: batch-2 ---")
    assert parsed.content == "New body"
    assert parsed.metadata["title"] == "Updated"


def test_writeback_requires_existing_target(tmp_path, monkeypatch, capsys) -> None:
    target_root = tmp_path / "vault-hhp"
    registry = _write_registry(tmp_path, {"hhp": str(target_root)})
    records = [
        WriteRecord(
            metadata={
                "instruction_slug": "hhp.use-legal-language",
                "source_path": "docs/missing.md",
            },
            content="New body",
        )
    ]
    monkeypatch.setattr("workbench.write.writeback.fetch_batch_records", lambda *_args, **_kwargs: records)

    exit_code = writeback_main(["batch-2", "--vault-registry", str(registry)])

    assert exit_code == 1
    assert "target does not exist" in capsys.readouterr().err


def test_writestream_passthrough(monkeypatch, capsys) -> None:
    source = "---\nslug: passthrough\n---\n\nBody"
    monkeypatch.setattr(sys, "stdin", io.StringIO(source))
    exit_code = writestream_main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == source


def test_writestream_rejects_multi_document_markdown(monkeypatch, capsys) -> None:
    source = (
        "---\nslug: one\n---\n\nOne\n\n"
        "---\nslug: two\n---\n\nTwo\n"
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(source))
    exit_code = writestream_main([])

    assert exit_code == 1
    assert MULTI_DOCUMENT_ERROR in capsys.readouterr().err
