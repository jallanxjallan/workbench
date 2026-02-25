from __future__ import annotations

import json
import re

import pytest

from workbench.interop.identity import create_slug
from workbench.interop.registry import find_vault_root, load_registry, resolve_project_code
from workbench.interop.slug import compose_slug, generate_suffix, normalize_semantic_base


def _write_registry(vault_root, payload) -> None:
    registry_path = vault_root / "00-system" / "project_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(payload), encoding="utf-8")


def test_normalize_semantic_base() -> None:
    assert (
        normalize_semantic_base("Chápter 03: The   Blockade Run!.md")
        == "chapter-03-the-blockade-run"
    )
    assert normalize_semantic_base("..") == "doc"
    assert len(normalize_semantic_base(f"{'a' * 80}.md")) == 48


def test_generate_suffix() -> None:
    assert re.fullmatch(r"[0-9a-z]{5}", generate_suffix())
    assert re.fullmatch(r"[0-9a-z]{8}", generate_suffix(8))
    with pytest.raises(ValueError, match="positive"):
        generate_suffix(0)


def test_compose_slug() -> None:
    assert compose_slug("omaf", "chapter-03", "k3f2q") == "omaf-chapter-03-k3f2q"
    with pytest.raises(ValueError, match="project_code"):
        compose_slug("", "chapter", "k3f2q")


def test_registry_resolution(tmp_path) -> None:
    vault_root = tmp_path / "vault"
    target_dir = vault_root / "projects" / "odyssey" / "drafts"
    target_dir.mkdir(parents=True, exist_ok=True)
    _write_registry(vault_root, {"projects": {"odyssey": {"project_code": "omaf"}}})

    assert find_vault_root(target_dir) == vault_root
    assert resolve_project_code(target_dir, load_registry(vault_root)) == "omaf"


def test_registry_requires_projects_path(tmp_path) -> None:
    vault_root = tmp_path / "vault"
    outside_projects = vault_root / "notes"
    outside_projects.mkdir(parents=True, exist_ok=True)
    _write_registry(vault_root, {"projects": {"odyssey": {"project_code": "omaf"}}})

    with pytest.raises(ValueError, match="projects"):
        resolve_project_code(outside_projects, load_registry(vault_root))


def test_create_slug_regenerates_on_collision(tmp_path, monkeypatch) -> None:
    vault_root = tmp_path / "vault"
    target_dir = vault_root / "projects" / "odyssey" / "drafts"
    target_dir.mkdir(parents=True, exist_ok=True)
    _write_registry(vault_root, {"projects": {"odyssey": {"project_code": "omaf"}}})

    collision = "omaf-chapter-03-the-blockade-run-abc12"
    existing = vault_root / "projects" / "odyssey" / "existing.md"
    existing.write_text(f"---\nslug: {collision}\n---\n\nOld", encoding="utf-8")

    suffixes = iter(["abc12", "z9y8x"])
    monkeypatch.setattr(
        "workbench.interop.identity.generate_suffix",
        lambda length=5: next(suffixes),
    )

    created = create_slug(target_dir, "Chapter 03: The Blockade Run.md")
    assert created == "omaf-chapter-03-the-blockade-run-z9y8x"
