from __future__ import annotations

import io
from pathlib import Path

import workbench.write.writenew as writenew_module
from workbench.interop.document import Document


def test_writenew_loads_schema_and_writes_expected_frontmatter(tmp_path: Path) -> None:
    studio_root = tmp_path / "Studio"
    schema_dir = studio_root / "_schemas"
    schema_dir.mkdir(parents=True)
    (schema_dir / "passage.yaml").write_text(
        "\n".join(
            [
                "schema: passage.v1",
                "class: passage",
                "defaults:",
                "  state: candidate",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    target_dir = tmp_path / "vault" / "passages"
    ndjson = io.StringIO(
        '{"batch_slug":"omaf.research","content":"Freeberg landed at dawn...","filename_hint":"freeberg","provenance":{"tool":"pandoc","source":"diary-1947"}}\n'
    )

    writenew_module.write_new_records(
        schema_name="passage",
        target_path=str(target_dir),
        studio_root=str(studio_root),
        debug_routing=False,
        input_stream=ndjson,
    )

    output = target_dir / "freeberg.md"
    assert output.exists()

    parsed = Document.read_file(output)
    assert parsed.metadata["class"] == "passage"
    assert parsed.metadata["batch"] == "omaf.research"
    assert parsed.metadata["state"] == "candidate"
    assert parsed.metadata["origin"] == {"tool": "pandoc", "source": "diary-1947"}
    assert "slug" not in parsed.metadata
    assert parsed.content.strip() == "Freeberg landed at dawn..."


def test_writenew_handles_filename_collisions_with_incrementing_suffix(
    tmp_path: Path,
) -> None:
    studio_root = tmp_path / "Studio"
    schema_dir = studio_root / "_schemas"
    schema_dir.mkdir(parents=True)
    (schema_dir / "passage.yaml").write_text(
        "\n".join(
            [
                "schema: passage.v1",
                "class: passage",
                "defaults:",
                "  state: candidate",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    target_dir = tmp_path / "vault" / "passages"
    target_dir.mkdir(parents=True)
    (target_dir / "freeberg.md").write_text("existing", encoding="utf-8")

    ndjson = io.StringIO(
        "\n".join(
            [
                '{"batch_slug":"batch-1","content":"first","filename_hint":"freeberg"}',
                '{"batch_slug":"batch-1","content":"second","filename_hint":"freeberg"}',
            ]
        )
        + "\n"
    )

    writenew_module.write_new_records(
        schema_name="passage",
        target_path=str(target_dir),
        studio_root=str(studio_root),
        debug_routing=False,
        input_stream=ndjson,
    )

    assert (target_dir / "freeberg.md").exists()
    assert (target_dir / "freeberg-2.md").exists()
    assert (target_dir / "freeberg-3.md").exists()


def test_writenew_defaults_to_unknown_stem_and_resolves_collisions(
    tmp_path: Path,
) -> None:
    studio_root = tmp_path / "Studio"
    schema_dir = studio_root / "_schemas"
    schema_dir.mkdir(parents=True)
    (schema_dir / "passage.yaml").write_text(
        "\n".join(
            [
                "schema: passage.v1",
                "class: passage",
                "defaults:",
                "  state: candidate",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    target_dir = tmp_path / "vault" / "passages"
    target_dir.mkdir(parents=True)
    (target_dir / "unknown.md").write_text("existing", encoding="utf-8")
    (target_dir / "unknown-2.md").write_text("existing", encoding="utf-8")

    ndjson = io.StringIO(
        "\n".join(
            [
                '{"batch_slug":"batch-1","content":"first"}',
                '{"batch_slug":"batch-1","content":"second"}',
            ]
        )
        + "\n"
    )

    writenew_module.write_new_records(
        schema_name="passage",
        target_path=str(target_dir),
        studio_root=str(studio_root),
        debug_routing=False,
        input_stream=ndjson,
    )

    assert (target_dir / "unknown.md").exists()
    assert (target_dir / "unknown-2.md").exists()
    assert (target_dir / "unknown-3.md").exists()
    assert (target_dir / "unknown-4.md").exists()
