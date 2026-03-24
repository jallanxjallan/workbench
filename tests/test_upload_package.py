from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from records.ndjson import iter_ndjson
from upload.package import UploadPackageError, load_package_json, upload_package


class UploadPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.vault = self.root / "vault"
        self.vault.mkdir()
        (self.vault / "_vault_registry.json").write_text(
            json.dumps({"mnemonic": "tv"}),
            encoding="utf-8",
        )
        self.guidance = self.home / "Guidance"
        self.guidance.mkdir()
        self.package_path = self.vault / "package.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_instruction(
        self,
        root: Path,
        relpath: str,
        slug: str,
        body: str = "body",
    ) -> Path:
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nslug: {slug}\n---\n{body}\n", encoding="utf-8")
        return path

    def _write_package(self, payload: dict[str, object]) -> None:
        self.package_path.write_text(json.dumps(payload), encoding="utf-8")

    def _run_upload(self) -> list[dict[str, object]]:
        captured: list[str] = []

        def fake_stream(lines):
            captured.extend(lines)
            return 0

        with patch("pathlib.Path.home", return_value=self.home), patch(
            "upload.package.stream_to_asc_upload",
            side_effect=fake_stream,
        ):
            old_cwd = Path.cwd()
            try:
                os.chdir(self.vault)
                result = upload_package(self.package_path)
            finally:
                os.chdir(old_cwd)
        self.assertEqual(result, 0)
        return list(iter_ndjson(captured))

    def test_uploads_only_referenced_instructions_then_package(self) -> None:
        self._write_instruction(self.vault, "vault/gbl-one.md", "gbl.one", "vault one")
        self._write_instruction(self.vault, "vault/spc-two.md", "spc.two", "vault two")
        self._write_instruction(
            self.guidance,
            "guide/cxt-three.md",
            "cxt.three",
            "guide three",
        )
        self._write_instruction(self.guidance, "guide/gbl-unused.md", "gbl.unused", "unused")
        self._write_package(
            {
                "slug": "pkg.alpha",
                "steps": [
                    {"instructions": {"gbl": ["gbl.one", "gbl.one"], "spc": ["spc.two"]}},
                    {"instructions": {"cxt": ["cxt.three"]}},
                ],
            }
        )

        records = self._run_upload()

        self.assertEqual(
            [record["slug"] for record in records],
            ["gbl.one", "spc.two", "cxt.three", "pkg.alpha"],
        )
        self.assertEqual(
            [record["kind"] for record in records[:-1]],
            ["instruction", "instruction", "instruction"],
        )
        self.assertEqual(records[-1]["kind"], "package")
        self.assertEqual(records[0]["input_record"]["origin"], "vault")
        self.assertEqual(records[2]["input_record"]["origin"], "guidance")
        self.assertNotIn("gbl.unused", [record["slug"] for record in records])

    def test_missing_slug_hard_fails_before_upload(self) -> None:
        self._write_instruction(self.vault, "vault/gbl-one.md", "gbl.one")
        self._write_package(
            {
                "slug": "pkg.alpha",
                "steps": [{"instructions": {"gbl": ["gbl.one"], "cxt": ["cxt.missing"]}}],
            }
        )

        with patch("pathlib.Path.home", return_value=self.home), patch(
            "upload.package.stream_to_asc_upload"
        ) as stream_mock:
            old_cwd = Path.cwd()
            try:
                os.chdir(self.vault)
                with self.assertRaises(UploadPackageError):
                    upload_package(self.package_path)
            finally:
                os.chdir(old_cwd)
        stream_mock.assert_not_called()

    def test_duplicate_slug_across_roots_hard_fails(self) -> None:
        self._write_instruction(self.vault, "vault/gbl-one.md", "gbl.one")
        self._write_instruction(self.guidance, "guide/gbl-one.md", "gbl.one")
        self._write_package({"slug": "pkg.alpha", "steps": [{"instructions": {"gbl": ["gbl.one"]}}]})

        with patch("pathlib.Path.home", return_value=self.home), patch(
            "upload.package.stream_to_asc_upload"
        ) as stream_mock:
            old_cwd = Path.cwd()
            try:
                os.chdir(self.vault)
                with self.assertRaises(UploadPackageError):
                    upload_package(self.package_path)
            finally:
                os.chdir(old_cwd)
        stream_mock.assert_not_called()

    def test_hash_changes_when_file_changes(self) -> None:
        instruction_path = self._write_instruction(
            self.vault,
            "vault/gbl-one.md",
            "gbl.one",
            "first",
        )
        self._write_package({"slug": "pkg.alpha", "steps": [{"instructions": {"gbl": ["gbl.one"]}}]})

        first = self._run_upload()[0]["hash"]
        instruction_path.write_text("---\nslug: gbl.one\n---\nsecond\n", encoding="utf-8")
        second = self._run_upload()[0]["hash"]

        self.assertNotEqual(first, second)

    def test_invalid_json_hard_fails_without_fallback(self) -> None:
        self.package_path.write_text("slug: pkg.alpha\n", encoding="utf-8")

        with self.assertRaises(UploadPackageError):
            load_package_json(self.package_path)


if __name__ == "__main__":
    unittest.main()
