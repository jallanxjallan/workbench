from __future__ import annotations

from pathlib import Path

import pytest

from workbench.config.vault_registry import load_vault_registry
from workbench.write.common import WriteError, resolve_target_path


def _registry(tmp_path: Path):
    path = tmp_path / "vaults.yaml"
    path.write_text(
        f"hhp: {tmp_path / 'hhp'}\nomaf: {tmp_path / 'omaf'}\n",
        encoding="utf-8",
    )
    return load_vault_registry(path)


def test_resolve_target_path_prefers_explicit_target_path(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    resolved = resolve_target_path(
        metadata={
            "target_path": "notes/a.md",
            "prompt_slug": "omaf.some-prompt",
            "instruction_slug": "hhp.some-instruction",
        },
        registry=registry,
        record_index=1,
    )
    assert resolved == (tmp_path / "omaf" / "notes" / "a.md").resolve()


def test_resolve_target_path_uses_prompt_slug_before_instruction_slug(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    resolved = resolve_target_path(
        metadata={
            "source_path": "docs/a.md",
            "prompt_slug": "omaf.some-prompt",
            "instruction_slug": "hhp.some-instruction",
        },
        registry=registry,
        record_index=1,
    )
    assert resolved == (tmp_path / "omaf" / "docs" / "a.md").resolve()


def test_resolve_target_path_fails_without_routing_metadata(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    with pytest.raises(WriteError, match="missing routing metadata"):
        resolve_target_path(
            metadata={"title": "No route"},
            registry=registry,
            record_index=1,
        )


def test_resolve_target_path_fails_when_prefix_is_not_registered(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    with pytest.raises(WriteError, match="not found in vault registry"):
        resolve_target_path(
            metadata={"prompt_slug": "websites.launch", "source_path": "docs/a.md"},
            registry=registry,
            record_index=1,
        )
