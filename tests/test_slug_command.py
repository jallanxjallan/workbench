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


def test_slug_ensure_prefetches_candidates_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    one = tmp_path / "one.md"
    two = tmp_path / "two.md"
    _write(one, "---\nclass: passage\n---\n\nOne\n")
    _write(two, "---\nclass: passage\n---\n\nTwo\n")

    calls = {"prefetch": 0, "ensured": 0}

    def _fake_candidates(*, root: Path) -> list[dict[str, object]]:
        calls["prefetch"] += 1
        return []

    def _fake_has_slug(_path: Path) -> bool:
        return False

    def _fake_ensure(
        filepath: Path,
        *,
        namespace: str | None = None,
        slug_owner_index: dict[str, set[Path]] | None = None,
    ) -> str:
        assert namespace == "omaf"
        assert slug_owner_index is not None
        calls["ensured"] += 1
        return f"omaf.passage.{filepath.stem}"

    monkeypatch.setattr(slug_module, "find_markdown_slug_candidates", _fake_candidates)
    monkeypatch.setattr(slug_module, "_has_slug", _fake_has_slug)
    monkeypatch.setattr(slug_module, "ensure_slug", _fake_ensure)

    rc = slug_module.main(["ensure", str(one), str(two), "--namespace", "omaf"])
    out = capsys.readouterr().out

    assert rc == 0
    assert calls["prefetch"] == 1
    assert calls["ensured"] == 2
    assert "created: 2" in out
    assert "failed: 0" in out


def test_slug_validate_uses_prefetched_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    one = tmp_path / "one.md"
    two = tmp_path / "two.md"
    one.write_text("x", encoding="utf-8")
    two.write_text("x", encoding="utf-8")
    calls = {"prefetch": 0}

    def _fake_candidates(*, root: Path) -> list[dict[str, object]]:
        assert root == tmp_path.resolve()
        calls["prefetch"] += 1
        return [
            {"file": one.resolve(), "slug": "omaf.passage.one"},
            {"file": two.resolve(), "slug": None},
        ]

    monkeypatch.setattr(slug_module, "find_markdown_slug_candidates", _fake_candidates)

    rc = slug_module.main(["validate", str(tmp_path)])
    captured = capsys.readouterr()
    out = captured.out
    err = captured.err

    assert rc == 1
    assert calls["prefetch"] == 1
    assert "validated files: 2" in out
    assert "errors: 1" in out
    assert "missing slug" in err
