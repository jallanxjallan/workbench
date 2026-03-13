from __future__ import annotations

import json
from pathlib import Path

import pytest

from workbench.regex.compile_patterns import (
    PatternCompileError,
    compile_patterns,
)
from workbench.cli.compile_regex import main as compile_regex_main


def _write_yaml(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_compile_patterns_builds_and_pattern_json_and_logs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    output_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "indonesia_nickel_policy.yaml",
        (
            "name: indonesia_nickel_policy\n"
            "engine: pcre2\n"
            "ignore_case: true\n"
            "and:\n"
            "  - indonesia\n"
            "  - nickel\n"
            "  - export\n"
        ),
    )

    outputs = compile_patterns(source_root=source_root, output_root=output_root)

    assert outputs == (output_root / "indonesia_nickel_policy.json",)
    data = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert data == {
        "name": "indonesia_nickel_policy",
        "pattern": r"(?s)(?=.*indonesia)(?=.*nickel)(?=.*export)",
        "engine": "pcre2",
        "ignore_case": True,
        "version": 1,
    }

    out = capsys.readouterr().out.strip()
    assert out == "compiled indonesia_nickel_policy"


def test_compile_patterns_preserves_or_regex_terms(tmp_path: Path) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    output_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "languages.yaml",
        (
            "name: languages\n"
            "engine: default\n"
            "ignore_case: false\n"
            "or:\n"
            "  - c++\n"
            "  - a.b\n"
            "  - (rust)\n"
        ),
    )

    outputs = compile_patterns(source_root=source_root, output_root=output_root)
    data = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert data["pattern"] == r"(c++|a.b|(rust))"


def test_compile_patterns_rejects_missing_name(tmp_path: Path) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    output_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "missing_name.yaml",
        "engine: default\nor:\n  - indonesia\n",
    )

    with pytest.raises(PatternCompileError, match="missing required 'name'"):
        compile_patterns(source_root=source_root, output_root=output_root)


def test_compile_patterns_rejects_both_and_and_or(tmp_path: Path) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    output_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "invalid_mode.yaml",
        (
            "name: invalid_mode\n"
            "engine: pcre2\n"
            "and:\n"
            "  - indonesia\n"
            "or:\n"
            "  - malaysia\n"
        ),
    )

    with pytest.raises(PatternCompileError, match="exactly one of 'and' or 'or'"):
        compile_patterns(source_root=source_root, output_root=output_root)


def test_compile_patterns_rejects_empty_term(tmp_path: Path) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    output_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "invalid_terms.yaml",
        (
            "name: invalid_terms\n"
            "engine: default\n"
            "or:\n"
            "  - indonesia\n"
            "  - \"\"\n"
        ),
    )

    with pytest.raises(PatternCompileError, match="non-empty strings"):
        compile_patterns(source_root=source_root, output_root=output_root)


def test_compile_patterns_rejects_and_without_pcre2(tmp_path: Path) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    output_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "invalid_engine.yaml",
        (
            "name: invalid_engine\n"
            "engine: default\n"
            "and:\n"
            "  - indonesia\n"
            "  - nickel\n"
        ),
    )

    with pytest.raises(PatternCompileError, match="require engine 'pcre2'"):
        compile_patterns(source_root=source_root, output_root=output_root)


def test_compile_patterns_rejects_name_filename_mismatch(tmp_path: Path) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    output_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "filename_name_mismatch.yaml",
        (
            "name: other_name\n"
            "engine: default\n"
            "or:\n"
            "  - indonesia\n"
        ),
    )

    with pytest.raises(PatternCompileError, match="must match filename stem"):
        compile_patterns(source_root=source_root, output_root=output_root)


def test_compile_regex_cli_compiles_outputs(tmp_path: Path) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    runtime_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "ai_regulation.yaml",
        (
            "name: ai_regulation\n"
            "engine: default\n"
            "ignore_case: true\n"
            "or:\n"
            "  - ai act\n"
            "  - eu regulation\n"
        ),
    )

    rc = compile_regex_main(
        ["--source-root", str(source_root), "--output-root", str(runtime_root)]
    )

    assert rc == 0
    assert (runtime_root / "ai_regulation.json").is_file()


def test_compile_patterns_removes_stale_compiled_outputs(tmp_path: Path) -> None:
    source_root = tmp_path / "Control" / "Regex" / "definitions"
    output_root = tmp_path / "Workbench" / "_compiled" / "regex"
    _write_yaml(
        source_root / "slug_field.yaml",
        (
            "name: slug_field\n"
            "engine: default\n"
            "ignore_case: false\n"
            "or:\n"
            "  - \"slug:\\\\s*[a-z0-9._-]+\"\n"
        ),
    )
    output_root.mkdir(parents=True, exist_ok=True)
    stale = output_root / "obsolete_pattern.json"
    stale.write_text("{\"name\": \"obsolete_pattern\"}\n", encoding="utf-8")

    outputs = compile_patterns(source_root=source_root, output_root=output_root)

    assert outputs == (output_root / "slug_field.json",)
    assert not stale.exists()
