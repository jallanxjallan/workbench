from __future__ import annotations

from pathlib import Path

import pytest

import workbench.cli.generate_slugs as generate_slugs_module
import workbench.cli.main as cli_main
import workbench.slug.writer as writer_module
from workbench.interop.document import Document


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_vault(tmp_path: Path) -> tuple[Path, Path]:
    studio_root = tmp_path / "Studio"
    vault_root = studio_root / "omaf"
    vault_root.mkdir(parents=True, exist_ok=True)
    (vault_root / ".obsidian").mkdir(parents=True, exist_ok=True)
    _write(vault_root / "_vault_registry.json", '{"mnemonic":"omaf"}\n')
    return studio_root, vault_root


def test_generate_slugs_write_replaces_placeholder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    studio_root, vault_root = _init_vault(tmp_path)
    target = vault_root / "content" / "First Flight.md"
    _write(target, "---\nclass: passage\nslug: __SLUG__\n---\n\nBody\n")

    monkeypatch.setattr(generate_slugs_module, "STUDIO_ROOT", studio_root)

    rc = cli_main.main(["generate-slugs", "--write"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "discovered 1 placeholder file(s)" in captured.out
    assert "generated 1 slug(s)" in captured.out
    assert "written 1 slug(s)" in captured.out

    updated = Document.read_file(target)
    assert updated.metadata["slug"] == "omaf.passage.first-flight"


def test_generate_slugs_detects_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    studio_root, vault_root = _init_vault(tmp_path)
    one = vault_root / "content" / "First Flight.md"
    two = vault_root / "archive" / "First Flight.md"
    _write(one, "---\nclass: passage\nslug: __SLUG__\n---\n\nOne\n")
    _write(two, "---\nclass: passage\nslug: __SLUG__\n---\n\nTwo\n")

    monkeypatch.setattr(generate_slugs_module, "STUDIO_ROOT", studio_root)

    rc = cli_main.main(["generate-slugs", "--write"])
    captured = capsys.readouterr()

    assert rc == 1
    assert "slug collision detected with" in captured.err
    assert "omaf.passage.first-flight" in captured.err
    assert Document.read_file(one).metadata["slug"] == "__SLUG__"
    assert Document.read_file(two).metadata["slug"] == "__SLUG__"


def test_generate_slugs_dry_run_does_not_modify_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    studio_root, vault_root = _init_vault(tmp_path)
    target = vault_root / "content" / "First Flight.md"
    _write(target, "---\nclass: passage\nslug: __SLUG__\n---\n\nBody\n")

    monkeypatch.setattr(generate_slugs_module, "STUDIO_ROOT", studio_root)

    rc = cli_main.main(["generate-slugs"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "generated 1 slug(s)" in captured.out
    assert "written 0 slug(s)" in captured.out
    assert Document.read_file(target).metadata["slug"] == "__SLUG__"


def test_generate_slugs_requires_mnemonic_in_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    studio_root, vault_root = _init_vault(tmp_path)
    target = vault_root / "contents" / "Aphorisms.md"
    _write(vault_root / "_vault_registry.json", "{}\n")
    _write(target, "---\nclass: passage\nslug: __SLUG__\n---\n\nBody\n")

    monkeypatch.setattr(generate_slugs_module, "STUDIO_ROOT", studio_root)

    rc = cli_main.main(["generate-slugs", "--write"])
    captured = capsys.readouterr()

    assert rc == 1
    assert "missing required key 'mnemonic'" in captured.err
    assert Document.read_file(target).metadata["slug"] == "__SLUG__"


def test_generate_slugs_skips_template_files_without_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, vault_root = _init_vault(tmp_path)
    target = vault_root / "instructions" / "00-templates" / "global.md"
    _write(target, "---\nslug: __SLUG__\n---\n\nBody\n")

    monkeypatch.setattr(generate_slugs_module, "STUDIO_ROOT", studio_root)

    rc = cli_main.main(["generate-slugs", "--write"])

    assert rc == 0
    assert Document.read_file(target).metadata["slug"] == "__SLUG__"


def test_generate_slugs_ignores_obsidian_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, vault_root = _init_vault(tmp_path)
    target = vault_root / ".obsidian" / "global.md"
    _write(target, "---\nclass: passage\nslug: __SLUG__\n---\n\nBody\n")

    monkeypatch.setattr(generate_slugs_module, "STUDIO_ROOT", studio_root)

    rc = cli_main.main(["generate-slugs", "--write"])

    assert rc == 0
    assert Document.read_file(target).metadata["slug"] == "__SLUG__"


def test_generate_slugs_includes_optional_context_for_any_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, vault_root = _init_vault(tmp_path)
    target = vault_root / "content" / "First Flight.md"
    _write(
        target,
        "---\nclass: scene\ncontext: training\nslug: __SLUG__\n---\n\nBody\n",
    )

    monkeypatch.setattr(generate_slugs_module, "STUDIO_ROOT", studio_root)

    rc = cli_main.main(["generate-slugs", "--write"])

    assert rc == 0
    updated = Document.read_file(target)
    assert updated.metadata["slug"] == "omaf.scene.training.first-flight"


def test_generate_slugs_resolves_namespace_once_per_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    studio_root, vault_root = _init_vault(tmp_path)
    one = vault_root / "content" / "First Flight.md"
    two = vault_root / "content" / "Second Flight.md"
    _write(one, "---\nclass: passage\nslug: __SLUG__\n---\n\nOne\n")
    _write(two, "---\nclass: passage\nslug: __SLUG__\n---\n\nTwo\n")

    monkeypatch.setattr(generate_slugs_module, "STUDIO_ROOT", studio_root)

    calls = {"count": 0}
    original = writer_module.vault_namespace

    def _counting_namespace(path_value: str | Path) -> str:
        calls["count"] += 1
        return original(path_value)

    monkeypatch.setattr(writer_module, "vault_namespace", _counting_namespace)

    rc = cli_main.main(["generate-slugs", "--write"])

    assert rc == 0
    assert calls["count"] == 1
