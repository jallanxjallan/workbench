from __future__ import annotations

from pathlib import Path

from PIL import Image

import workbench.cli.main as cli_main
from workbench.interop.document import Document
import workbench.lib.compile_assets as compile_assets_module
from workbench.lib.compile_assets import compile_assets
from workbench.lib.rg import RGMatch


def _create_vault(tmp_path: Path, name: str) -> tuple[Path, Path, Path]:
    studio_root = tmp_path / "Studio"
    vault_root = studio_root / name
    vault_root.mkdir(parents=True, exist_ok=True)

    assets_target = tmp_path / "Dropbox" / "Assets" / name
    assets_target.mkdir(parents=True, exist_ok=True)
    (vault_root / "_assets").symlink_to(assets_target, target_is_directory=True)

    return studio_root, vault_root, assets_target


def _write_image(path: Path, *, color: tuple[int, int, int] = (220, 20, 60)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1280, 720), color=color)
    image.save(path)
    return path


def test_compile_assets_handles_file_uri_jpg_updates_frontmatter_and_removes_inline_link(
    tmp_path: Path,
) -> None:
    studio_root, vault_root, assets_target = _create_vault(tmp_path, "vault-a")
    source_path = _write_image(tmp_path / "input" / "photo.jpg")
    source_uri = source_path.resolve().as_uri()

    markdown = vault_root / "notes" / "nested" / "doc.md"
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(
        (
            "---\n"
            "title: Sample\n"
            "sources:\n"
            "  - file:///existing/source.jpg\n"
            "assets:\n"
            "  - _assets/existing_thumb.jpg\n"
            "---\n\n"
            f"Intro [photo]({source_uri}) outro.\n"
        ),
        encoding="utf-8",
    )

    result = compile_assets(studio_root)
    updated = Document.read_file(markdown)

    assert result.matched_links == 1
    assert result.generated_assets == 1
    assert result.removed_inline_links == 1
    assert source_uri in updated.metadata["sources"]
    assert "_assets/photo_thumb.jpg" in updated.metadata["assets"]
    assert source_uri not in updated.content
    assert "[photo](" not in updated.content

    thumb = assets_target / "photo_thumb.jpg"
    assert thumb.is_file()
    assert thumb.parent.resolve() == assets_target.resolve()


def test_compile_assets_handles_file_uri_png(tmp_path: Path) -> None:
    studio_root, vault_root, assets_target = _create_vault(tmp_path, "vault-png")
    source_path = _write_image(tmp_path / "input" / "diagram.png", color=(0, 128, 220))
    source_uri = source_path.resolve().as_uri()

    markdown = vault_root / "doc.md"
    markdown.write_text(f"Diagram [png]({source_uri})\n", encoding="utf-8")

    result = compile_assets(studio_root)
    updated = Document.read_file(markdown)

    assert result.generated_assets == 1
    assert "_assets/diagram_thumb.png" in updated.metadata["assets"]
    assert (assets_target / "diagram_thumb.png").is_file()


def test_compile_assets_records_http_source_without_asset_handler(tmp_path: Path) -> None:
    studio_root, vault_root, assets_target = _create_vault(tmp_path, "vault-http")
    markdown = vault_root / "doc.md"
    remote_uri = "http://example.com/image.jpg"
    markdown.write_text(f"Remote [image]({remote_uri})\n", encoding="utf-8")

    result = compile_assets(studio_root)
    updated = Document.read_file(markdown)

    assert result.matched_links == 1
    assert result.generated_assets == 0
    assert remote_uri in updated.metadata["sources"]
    assert updated.metadata["assets"] == []
    assert remote_uri not in updated.content
    assert not any(assets_target.iterdir())


def test_compile_assets_avoids_duplicate_entries_and_thumbnail_regeneration(
    tmp_path: Path,
) -> None:
    studio_root, vault_root, assets_target = _create_vault(tmp_path, "vault-idempotent")
    source_path = _write_image(tmp_path / "input" / "photo.jpg")
    source_uri = source_path.resolve().as_uri()
    thumb = _write_image(assets_target / "photo_thumb.jpg", color=(10, 10, 10))
    before_mtime_ns = thumb.stat().st_mtime_ns

    markdown = vault_root / "doc.md"
    markdown.write_text(
        (
            "---\n"
            "sources:\n"
            f"  - {source_uri}\n"
            "assets:\n"
            "  - _assets/photo_thumb.jpg\n"
            "---\n\n"
            f"Body [photo]({source_uri})\n"
        ),
        encoding="utf-8",
    )

    result = compile_assets(studio_root)
    updated = Document.read_file(markdown)

    assert result.generated_assets == 0
    assert result.reused_assets == 1
    assert updated.metadata["sources"].count(source_uri) == 1
    assert updated.metadata["assets"].count("_assets/photo_thumb.jpg") == 1
    assert thumb.stat().st_mtime_ns == before_mtime_ns


def test_compile_assets_resolves_assets_symlink_for_correct_vault(tmp_path: Path) -> None:
    studio_root, vault_a, assets_a = _create_vault(tmp_path, "vault-a")
    _, vault_b, assets_b = _create_vault(tmp_path, "vault-b")
    source_path = _write_image(tmp_path / "input" / "vault_image.jpg")
    source_uri = source_path.resolve().as_uri()

    markdown = vault_b / "notes" / "deep" / "doc.md"
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(f"Use [img]({source_uri})\n", encoding="utf-8")

    result = compile_assets(studio_root)
    updated = Document.read_file(markdown)

    assert result.generated_assets == 1
    assert "_assets/vault_image_thumb.jpg" in updated.metadata["assets"]
    assert (assets_b / "vault_image_thumb.jpg").is_file()
    assert not (assets_a / "vault_image_thumb.jpg").exists()
    assert not (vault_a / "_assets" / "vault_image_thumb.jpg").exists()


def test_cli_dispatches_compile_assets_command(tmp_path: Path) -> None:
    studio_root, vault_root, _assets_target = _create_vault(tmp_path, "vault-cli")
    source_uri = _write_image(tmp_path / "input" / "photo.jpg").resolve().as_uri()
    markdown = vault_root / "doc.md"
    markdown.write_text(f"CLI [photo]({source_uri})\n", encoding="utf-8")

    rc = cli_main.main(["compile-assets", "--studio-root", str(studio_root)])

    assert rc == 0


def test_discover_uri_links_uses_single_rg_pass(
    tmp_path: Path,
    monkeypatch,
) -> None:
    studio_root = tmp_path / "Studio"
    studio_root.mkdir(parents=True, exist_ok=True)

    calls: list[tuple[str, Path]] = []

    def _fake_rg_search(
        pattern: str,
        root: Path,
    ) -> list[RGMatch]:
        calls.append((pattern, root))
        return [
            RGMatch(
                path=Path("vault/doc.md"),
                line=1,
                text="[img](file:///tmp/pic.jpg)",
            )
        ]

    monkeypatch.setattr(compile_assets_module, "rg_search", _fake_rg_search)

    links = compile_assets_module.discover_uri_links(studio_root)

    assert len(calls) == 1
    assert calls[0][0] == compile_assets_module.URI_LINK_PATTERN
    assert calls[0][1] == studio_root
    assert len(links) == 1
