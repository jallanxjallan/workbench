from __future__ import annotations

import json
from pathlib import Path

import yaml

import workbench.cli.compile_registries as compile_registries_cli
from workbench.lib.compile_registries import compile_editorial_registry


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


def test_compile_editorial_registry_creates_json_with_matching_structure(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    runtime_root = tmp_path / "Workbench" / "obsidian" / "registries" / "studio"
    source = _write_editorial_yaml(studio_root)

    output = compile_editorial_registry(studio_root, runtime_root)

    assert output == runtime_root / "editorial.json"
    assert output.is_file()

    source_data = yaml.safe_load(source.read_text(encoding="utf-8"))
    output_data = json.loads(output.read_text(encoding="utf-8"))
    assert output_data == source_data


def test_compile_editorial_registry_creates_output_directory(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    runtime_root = tmp_path / "Workbench" / "obsidian" / "registries" / "studio"
    _write_editorial_yaml(studio_root)

    output_dir = runtime_root
    assert not output_dir.exists()

    compile_editorial_registry(studio_root, runtime_root)

    assert output_dir.is_dir()


def test_cli_compile_registries_command_writes_editorial_json(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    runtime_root = tmp_path / "Workbench" / "obsidian" / "registries" / "studio"
    _write_editorial_yaml(studio_root)

    rc = compile_registries_cli.main(
        ["--studio-root", str(studio_root), "--runtime-root", str(runtime_root)]
    )

    assert rc == 0
    assert (runtime_root / "editorial.json").is_file()
