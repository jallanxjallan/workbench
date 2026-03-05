from __future__ import annotations

from pathlib import Path

import pytest

import workbench.cli.slug as slug_module
from workbench.interop.document import Document


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    studio_root = tmp_path / "Studio"
    vault_root = studio_root / "omaf"
    vault_root.mkdir(parents=True, exist_ok=True)
    _write(vault_root / "_vault_registry.yaml", "vault: omaf\n")
    monkeypatch.setattr(slug_module, "STUDIO_ROOT", studio_root)
    return studio_root, vault_root


def test_slug_command_generates_expected_slug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, vault_root = _init_vault(tmp_path, monkeypatch)
    target = vault_root / "content" / "freeberg-breaks-the-blockade.md"
    _write(target, "---\nclass: passage\nslug: __SLUG__\n---\n\nBody\n")

    rc = slug_module.main([str(target)])
    out = capsys.readouterr().out

    assert rc == 0
    assert out.strip() == "omaf.passage.freeberg-breaks-the-blockade"


def test_slug_command_fails_when_class_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, vault_root = _init_vault(tmp_path, monkeypatch)
    target = vault_root / "content" / "missing-class.md"
    _write(target, "---\nslug: __SLUG__\n---\n\nBody\n")

    rc = slug_module.main([str(target)])
    err = capsys.readouterr().err

    assert rc == 1
    assert "Missing required frontmatter key 'class'" in err


def test_slug_command_detects_studio_wide_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, vault_root = _init_vault(tmp_path, monkeypatch)

    existing = vault_root / "archive" / "freeberg-breaks-the-blockade.md"
    _write(
        existing,
        "---\nclass: passage\nslug: omaf.passage.freeberg-breaks-the-blockade\n---\n\nBody\n",
    )

    target = vault_root / "content" / "freeberg-breaks-the-blockade.md"
    _write(target, "---\nclass: passage\nslug: __SLUG__\n---\n\nBody\n")

    rc = slug_module.main([str(target)])
    err = capsys.readouterr().err

    assert rc == 1
    assert "Slug collision detected" in err


def test_slug_command_write_replaces_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, vault_root = _init_vault(tmp_path, monkeypatch)
    target = vault_root / "content" / "freeberg-breaks-the-blockade.md"
    _write(target, "---\nclass: passage\nslug: __SLUG__\n---\n\nBody\n")

    rc = slug_module.main([str(target), "--write"])
    out = capsys.readouterr().out

    assert rc == 0
    assert out.strip() == "omaf.passage.freeberg-breaks-the-blockade"

    updated = Document.read_file(target)
    assert updated.metadata["slug"] == "omaf.passage.freeberg-breaks-the-blockade"
