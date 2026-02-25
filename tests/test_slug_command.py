from __future__ import annotations

import json
import re

from workbench.identity.slug_cmd import main as slug_main


def _create_vault(tmp_path):
    vault_root = tmp_path / "vault"
    target_dir = vault_root / "projects" / "odyssey" / "drafts"
    target_dir.mkdir(parents=True, exist_ok=True)
    registry = {"projects": {"odyssey": {"project_code": "omaf"}}}
    registry_path = vault_root / "00-system" / "project_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return target_dir


def test_slug_command_success(tmp_path, capsys) -> None:
    target_dir = _create_vault(tmp_path)

    exit_code = slug_main([str(target_dir), "Chapter 03: The Blockade Run.md"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert re.fullmatch(
        r"omaf-chapter-03-the-blockade-run-[0-9a-z]{5}",
        captured.out.strip(),
    )


def test_slug_command_failure(tmp_path, capsys) -> None:
    target_dir = tmp_path / "not-a-vault" / "projects" / "odyssey"
    target_dir.mkdir(parents=True, exist_ok=True)

    exit_code = slug_main([str(target_dir), "Example.md"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "project_registry.json" in captured.err
