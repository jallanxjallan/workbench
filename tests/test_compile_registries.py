from __future__ import annotations

import json
from pathlib import Path

import yaml

import workbench.cli.compile_registries as compile_registries_cli
from workbench.lib.compile_registries import (
    compile_editorial_registry,
    compile_regex_registry,
    compile_registries,
)


def _write_editorial_yaml(studio_root: Path) -> Path:
    source = studio_root / "registries" / "editorial.yaml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        (
            "folders:\n"
            "  passages:\n"
            "    path: passages\n"
            "    score: 100\n"
            "\n"
            "classes:\n"
            "  passage:\n"
            "    template: content_item\n"
            "    folders: [passages]\n"
            "    score: 100\n"
            "\n"
            "templates:\n"
            "  content_item:\n"
            "    path: _common/templates/content_item.md\n"
            "    score: 100\n"
        ),
        encoding="utf-8",
    )
    return source


def _write_regex_yaml(studio_root: Path) -> Path:
    source = studio_root / "regex" / "indonesia_nickel_policy.yaml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        (
            "name: indonesia_nickel_policy\n"
            "engine: pcre2\n"
            "ignore_case: true\n"
            "and:\n"
            "  - indonesia\n"
            "  - nickel\n"
            "  - export\n"
        ),
        encoding="utf-8",
    )
    return source


def test_compile_editorial_registry_creates_json_with_matching_structure(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    runtime_root = tmp_path / "Workbench" / "_compiled"
    source = _write_editorial_yaml(studio_root)

    output = compile_editorial_registry(studio_root, runtime_root)

    assert output == runtime_root / "registries" / "editorial.json"
    assert output is not None
    assert output.is_file()

    source_data = yaml.safe_load(source.read_text(encoding="utf-8"))
    output_data = json.loads(output.read_text(encoding="utf-8"))
    assert output_data == source_data


def test_compile_regex_registry_writes_compiled_json(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    runtime_root = tmp_path / "Workbench" / "_compiled"
    _write_regex_yaml(studio_root)

    outputs = compile_regex_registry(studio_root, runtime_root)

    assert outputs == (runtime_root / "regex" / "indonesia_nickel_policy.json",)
    data = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert data == {
        "name": "indonesia_nickel_policy",
        "pattern": r"(?s)(?=.*indonesia)(?=.*nickel)(?=.*export)",
        "engine": "pcre2",
        "ignore_case": True,
        "version": 1,
    }


def test_compile_registries_skips_unchanged_sources(tmp_path: Path, capsys) -> None:
    studio_root = tmp_path / "Studio"
    runtime_root = tmp_path / "Workbench" / "_compiled"
    _write_editorial_yaml(studio_root)
    _write_regex_yaml(studio_root)

    first = compile_registries(studio_root, runtime_root)
    first_out = capsys.readouterr().out

    second = compile_registries(studio_root, runtime_root)
    second_out = capsys.readouterr().out

    assert len(first) == 2
    assert "compiled editorial" in first_out
    assert "compiled regex indonesia_nickel_policy" in first_out
    assert second == tuple()
    assert second_out.strip() == "registries up to date"


def test_cli_compile_registries_command_writes_artifacts(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    runtime_root = tmp_path / "Workbench" / "_compiled"
    _write_editorial_yaml(studio_root)
    _write_regex_yaml(studio_root)

    rc = compile_registries_cli.main(
        ["--studio-root", str(studio_root), "--runtime-root", str(runtime_root)]
    )

    assert rc == 0
    assert (runtime_root / "registries" / "editorial.json").is_file()
    assert (runtime_root / "regex" / "indonesia_nickel_policy.json").is_file()
