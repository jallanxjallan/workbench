from __future__ import annotations

import json
from pathlib import Path

import yaml

import workbench.cli.compile_registries as compile_registries_cli
from workbench.registry.compile_registries import (
    compile_editorial_registry,
    compile_pipeline_registry,
    compile_registries,
    compile_verbs_registry,
)


def _write_registry_yaml(registries_root: Path, name: str, payload: str) -> Path:
    source = registries_root / f"{name}.yaml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(payload, encoding="utf-8")
    return source


def _write_standard_registries(registries_root: Path) -> None:
    _write_registry_yaml(
        registries_root,
        "editorial",
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
    )
    _write_registry_yaml(registries_root, "pipeline", "pipeline: {}\n")
    _write_registry_yaml(registries_root, "verbs", "verbs: {}\n")


def test_compile_editorial_registry_creates_json_with_matching_structure(tmp_path: Path) -> None:
    registries_root = tmp_path / "Control" / "Registry"
    runtime_root = tmp_path / "Workbench" / "_compiled"
    source = _write_registry_yaml(
        registries_root,
        "editorial",
        "folders: {}\nclasses: {}\ntemplates: {}\n",
    )

    output = compile_editorial_registry(registries_root, runtime_root)

    assert output == runtime_root / "registries" / "editorial.json"
    assert output is not None
    assert output.is_file()

    source_data = yaml.safe_load(source.read_text(encoding="utf-8"))
    output_data = json.loads(output.read_text(encoding="utf-8"))
    assert output_data == source_data


def test_compile_pipeline_and_verbs_registry_write_json(tmp_path: Path) -> None:
    registries_root = tmp_path / "Control" / "Registry"
    runtime_root = tmp_path / "Workbench" / "_compiled"
    _write_registry_yaml(registries_root, "pipeline", "pipeline:\n  mode: strict\n")
    _write_registry_yaml(registries_root, "verbs", "verbs:\n  write: {}\n")

    pipeline_output = compile_pipeline_registry(registries_root, runtime_root)
    verbs_output = compile_verbs_registry(registries_root, runtime_root)

    assert pipeline_output == runtime_root / "registries" / "pipeline.json"
    assert verbs_output == runtime_root / "registries" / "verbs.json"
    assert json.loads(pipeline_output.read_text(encoding="utf-8")) == {
        "pipeline": {"mode": "strict"}
    }
    assert json.loads(verbs_output.read_text(encoding="utf-8")) == {"verbs": {"write": {}}}


def test_compile_registries_skips_unchanged_sources(tmp_path: Path, capsys) -> None:
    registries_root = tmp_path / "Control" / "Registry"
    runtime_root = tmp_path / "Workbench" / "_compiled"
    _write_standard_registries(registries_root)

    first = compile_registries(registries_root, runtime_root)
    first_out = capsys.readouterr().out

    second = compile_registries(registries_root, runtime_root)
    second_out = capsys.readouterr().out

    assert len(first) == 3
    assert "compiled editorial" in first_out
    assert "compiled pipeline" in first_out
    assert "compiled verbs" in first_out
    assert second == tuple()
    assert second_out.strip() == "registries up to date"


def test_cli_compile_registries_command_writes_artifacts(tmp_path: Path) -> None:
    registries_root = tmp_path / "Control" / "Registry"
    runtime_root = tmp_path / "Workbench" / "_compiled"
    _write_standard_registries(registries_root)

    rc = compile_registries_cli.main(
        ["--registries-root", str(registries_root), "--runtime-root", str(runtime_root)]
    )

    assert rc == 0
    assert (runtime_root / "registries" / "editorial.json").is_file()
    assert (runtime_root / "registries" / "pipeline.json").is_file()
    assert (runtime_root / "registries" / "verbs.json").is_file()
