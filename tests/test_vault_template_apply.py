from __future__ import annotations

from pathlib import Path

import pytest

from workbench.cli.vault_template import (
    VaultTemplateError,
    apply_template_to_files,
)
from workbench.lib.frontmatter import parse_frontmatter


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_vault(tmp_path: Path) -> Path:
    vault_root = tmp_path / "VaultA"
    (vault_root / ".obsidian").mkdir(parents=True, exist_ok=True)
    (vault_root / "_common" / "templates").mkdir(parents=True, exist_ok=True)
    return vault_root


def test_apply_template_merges_frontmatter_and_inserts_body_when_empty(
    tmp_path: Path,
) -> None:
    vault_root = _init_vault(tmp_path)
    template_path = vault_root / "_common" / "templates" / "hhp.md"
    _write(
        template_path,
        "---\nproject: hhp\ntype: chapter\n---\n\n# {{title}}\n",
    )

    empty_target = vault_root / "HHP" / "chapter-01.md"
    _write(empty_target, "")

    populated_target = vault_root / "HHP" / "chapter-02.md"
    _write(
        populated_target,
        "---\nproject: hhp\nexisting_key: keep-me\n---\n\nExisting body.\n",
    )

    result = apply_template_to_files(
        template_name="hhp",
        filepaths=[str(empty_target), str(populated_target)],
    )

    assert result.processed_files == 2
    assert result.updated_files == 2

    empty_parsed = parse_frontmatter(empty_target.read_text(encoding="utf-8"))
    assert empty_parsed.error is None
    assert empty_parsed.data == {"project": "hhp", "type": "chapter"}
    assert empty_parsed.body.strip() == "# {{title}}"

    populated_parsed = parse_frontmatter(populated_target.read_text(encoding="utf-8"))
    assert populated_parsed.error is None
    assert populated_parsed.data == {
        "project": "hhp",
        "existing_key": "keep-me",
        "type": "chapter",
    }
    assert populated_parsed.body.strip() == "Existing body."


def test_apply_template_keeps_existing_values_when_template_differs(
    tmp_path: Path,
) -> None:
    vault_root = _init_vault(tmp_path)
    _write(
        vault_root / "_common" / "templates" / "hhp.md",
        "---\nproject: hhp\ntype: chapter\n---\n",
    )

    target = vault_root / "HHP" / "chapter-01.md"
    _write(target, "---\nproject: different\nauthor: alice\n---\n\nBody stays.\n")

    result = apply_template_to_files(
        template_name="hhp",
        filepaths=[str(target)],
    )

    assert result.processed_files == 1
    assert result.updated_files == 1

    parsed = parse_frontmatter(target.read_text(encoding="utf-8"))
    assert parsed.error is None
    assert parsed.data == {
        "project": "different",
        "author": "alice",
        "type": "chapter",
    }
    assert parsed.body.strip() == "Body stays."


def test_apply_template_migrates_existing_slug_to_legacy_slug(tmp_path: Path) -> None:
    vault_root = _init_vault(tmp_path)
    _write(
        vault_root / "_common" / "templates" / "hhp.md",
        "---\nproject: hhp\nslug: chapter-01\nstatus: draft\n---\n",
    )

    target = vault_root / "HHP" / "chapter-01.md"
    _write(
        target,
        "---\nproject: hhp\nslug: old-chapter-01\nauthor: alice\n---\n\nBody stays.\n",
    )

    result = apply_template_to_files(
        template_name="hhp",
        filepaths=[str(target)],
    )

    assert result.processed_files == 1
    assert result.updated_files == 1

    parsed = parse_frontmatter(target.read_text(encoding="utf-8"))
    assert parsed.error is None
    assert parsed.data == {
        "project": "hhp",
        "legacy_slug": "old-chapter-01",
        "slug": "chapter-01",
        "author": "alice",
        "status": "draft",
    }
    assert parsed.body.strip() == "Body stays."


def test_apply_template_rejects_template_outside_common_templates(
    tmp_path: Path,
) -> None:
    vault_root = _init_vault(tmp_path)
    _write(vault_root / "_common" / "templates" / "hhp.md", "---\nproject: hhp\n---\n")
    target = vault_root / "HHP" / "chapter-01.md"
    _write(target, "")

    rogue_template = tmp_path / "outside.md"
    _write(rogue_template, "---\nproject: rogue\n---\n")

    with pytest.raises(VaultTemplateError, match="must resolve under"):
        apply_template_to_files(
            template_name=str(rogue_template),
            filepaths=[str(target)],
        )
