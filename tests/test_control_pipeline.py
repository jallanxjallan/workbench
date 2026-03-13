from __future__ import annotations

import json
from pathlib import Path

import pytest

import workbench.control.compile as compile_module
import workbench.control.publish as publish_module
from workbench.control.compile import ControlCompileError, compile_control, discover_slug_occurrences
from workbench.control.publish import publish_context, publish_control


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _seed_control_tree(root: Path) -> None:
    _write(root / "verbs" / "editorial.yaml", "folders: {}\nclasses: {}\ntemplates: {}\n")
    _write(
        root / "Regex" / "definitions" / "slug_field.yaml",
        (
            "name: slug_field\n"
            "engine: default\n"
            "ignore_case: false\n"
            "or:\n"
            "  - \"slug:\\\\s*[a-z0-9._-]+\"\n"
        ),
    )
    _write(
        root / "instructions" / "global" / "gbl.voice-tight-prose.md",
        (
            "---\n"
            "slug: gbl.voice-tight-prose\n"
            "type: instruction\n"
            "scope: global\n"
            "---\n\n"
            "Write in short, direct prose.\n"
        ),
    )


def test_discover_slug_occurrences_scans_multiple_roots(tmp_path: Path) -> None:
    control_root = tmp_path / "control"
    studio_root = tmp_path / "Studio"
    _write(
        control_root / "instructions" / "global" / "one.md",
        "---\nslug: gbl.sample\n---\n\nOne\n",
    )
    _write(
        studio_root / "project" / "instructions" / "context" / "two.md",
        "---\nslug: gbl.sample\n---\n\nTwo\n",
    )

    seen = discover_slug_occurrences(roots=(control_root, studio_root))

    assert "gbl.sample" in seen
    assert len(seen["gbl.sample"]) == 2


def test_compile_control_writes_expected_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control_root = tmp_path / "control"
    studio_root = tmp_path / "Studio"
    output_root = tmp_path / "Workbench" / "_compiled" / "control"
    _seed_control_tree(control_root)
    studio_root.mkdir(parents=True)
    monkeypatch.setattr(compile_module, "STUDIO_ROOT", studio_root)

    outputs = compile_control(control_root=control_root, output_root=output_root)

    assert outputs == (
        output_root / "verbs.json",
        output_root / "global_instructions.json",
        output_root / "regex.json",
    )
    verbs = json.loads((output_root / "verbs.json").read_text(encoding="utf-8"))
    globals_payload = json.loads(
        (output_root / "global_instructions.json").read_text(encoding="utf-8")
    )
    regex = json.loads((output_root / "regex.json").read_text(encoding="utf-8"))

    assert "index" in verbs
    assert "editorial" in verbs["index"]
    assert globals_payload["global_instructions"][0]["slug"] == "gbl.voice-tight-prose"
    assert regex["regex"][0]["name"] == "slug_field"


def test_compile_control_rejects_duplicate_slug_in_studio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control_root = tmp_path / "control"
    studio_root = tmp_path / "Studio"
    output_root = tmp_path / "Workbench" / "_compiled" / "control"
    _seed_control_tree(control_root)
    _write(
        studio_root / "project" / "instructions" / "context" / "duplicate.md",
        "---\nslug: gbl.voice-tight-prose\n---\n\nDuplicate\n",
    )
    monkeypatch.setattr(compile_module, "STUDIO_ROOT", studio_root)

    with pytest.raises(ControlCompileError, match="slug already exists"):
        compile_control(control_root=control_root, output_root=output_root)


def test_publish_control_generates_ulids_and_ndjson(tmp_path: Path) -> None:
    compiled_root = tmp_path / "Workbench" / "_compiled" / "control"
    ndjson_out = tmp_path / "global.ndjson"
    _write(
        compiled_root / "global_instructions.json",
        json.dumps(
            {
                "global_instructions": [
                    {
                        "slug": "gbl.voice-tight-prose",
                        "sysmessage": "Keep prose tight.",
                    }
                ]
            }
        ),
    )

    records = publish_control(
        compiled_root=compiled_root,
        dry_run=True,
        ndjson_out=ndjson_out,
    )

    assert len(records) == 1
    assert records[0]["slug"] == "gbl.voice-tight-prose"
    assert len(records[0]["ulid"]) == 26
    ndjson_lines = [line for line in ndjson_out.read_text(encoding="utf-8").splitlines() if line]
    assert len(ndjson_lines) == 1
    payload = json.loads(ndjson_lines[0])
    assert payload["slug"] == "gbl.voice-tight-prose"
    assert payload["sysmessage"] == "Keep prose tight."


def test_publish_control_invokes_ingest_when_not_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled_root = tmp_path / "Workbench" / "_compiled" / "control"
    _write(
        compiled_root / "global_instructions.json",
        json.dumps(
            {
                "global_instructions": [
                    {
                        "slug": "gbl.prompt-safety",
                        "sysmessage": "Follow policy.",
                    }
                ]
            }
        ),
    )

    called: dict[str, object] = {}

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(args, input, text, capture_output, check):  # noqa: ANN001
        called["args"] = args
        called["input"] = input
        called["text"] = text
        called["capture_output"] = capture_output
        called["check"] = check
        return _Result()

    monkeypatch.setattr(publish_module.subprocess, "run", _fake_run)

    publish_control(
        compiled_root=compiled_root,
        ingest_command=("asc-ingest", "calls"),
        dry_run=False,
    )

    assert called["args"] == ["asc-ingest", "calls"]
    assert isinstance(called["input"], str)
    assert '"slug": "gbl.prompt-safety"' in str(called["input"])


def test_publish_context_compiles_context_and_batch(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    compiled_root = tmp_path / "Workbench" / "_compiled" / "context"
    _write(
        studio_root / "ProjectA" / "instructions" / "context" / "cxt.example.md",
        "---\nslug: cxt.example\n---\n\nContext body\n",
    )
    _write(
        studio_root / "ProjectA" / "instructions" / "batch" / "bch.example.md",
        "---\nslug: bch.example\n---\n\nBatch body\n",
    )

    context_records, batch_records = publish_context(
        studio_root=studio_root,
        compiled_root=compiled_root,
        dry_run=True,
    )

    assert len(context_records) == 1
    assert len(batch_records) == 1
    assert (compiled_root / "context_instructions.json").is_file()
    assert (compiled_root / "batch_instructions.json").is_file()
