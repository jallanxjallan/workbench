from __future__ import annotations

import importlib
import io
import tempfile
import unittest
from pathlib import Path

import repo
from intake.slug_to_path import stream_slug_to_path_records
from intake.writeback import WriteBackError, prepare_writeback_ndjson
from intake.writenew import prepare_writenew_ndjson


class SharedSymbolImportTests(unittest.TestCase):
    def test_active_modules_import_without_stale_symbol_failures(self) -> None:
        module_names = [
            "cli.create_vault",
            "cli.slug_filepaths",
            "cli.slug_to_path",
            "cli.stream",
            "cli.upload_package",
            "cli.upload_profiles",
            "cli.writeback",
            "cli.writenew",
            "intake.slug_to_path",
            "intake.writeback",
            "intake.writenew",
            "upload.dispatch",
            "vault.create",
        ]

        for module_name in module_names:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)


class WritebackAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.vault = self.root / "vault"
        self.vault.mkdir()
        (self.vault / ".obsidian").mkdir()
        repo.init_repo(self.vault, repo.DEFAULT_GITIGNORE_TEXT)
        self.doc = self.vault / "records" / "one.md"
        self.doc.parent.mkdir(parents=True, exist_ok=True)
        self.doc.write_text("---\nslug: pss.one\n---\nbody\n", encoding="utf-8")
        repo.ensure_snapshot_commit(self.vault, "initial snapshot")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_prepare_writeback_ndjson_uses_scan_and_repo_authorities(self) -> None:
        stream = io.StringIO(
            '{"content":"updated","input_record":{"slug":"pss.one"}}\n'
        )

        prepared = prepare_writeback_ndjson(
            stream.getvalue(),
            vault_root=self.vault,
        )

        self.assertIn('"mode":"writeback"', prepared)
        self.assertIn(str(self.doc), prepared)

    def test_prepare_writeback_ndjson_rejects_dirty_targets(self) -> None:
        self.doc.write_text("---\nslug: pss.one\n---\nchanged\n", encoding="utf-8")

        with self.assertRaisesRegex(WriteBackError, "dirty"):
            prepare_writeback_ndjson(
                '{"content":"updated","input_record":{"slug":"pss.one"}}\n',
                vault_root=self.vault,
            )


class WriteNewAuthorityTests(unittest.TestCase):
    def test_prepare_writenew_ndjson_emits_materialize_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            vault = Path(tempdir).resolve()
            (vault / "_ingest").mkdir()

            prepared = prepare_writenew_ndjson(
                '{"content":"body","input_record":{"slug":"pss.one"}}\n',
                vault_root=vault,
            )

            self.assertIn('"mode":"writenew"', prepared)
            self.assertIn(str(vault / "_ingest" / "pss.one.md"), prepared)


class SlugToPathAuthorityTests(unittest.TestCase):
    def test_stream_slug_files_uses_transport_and_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            vault = Path(tempdir).resolve()
            (vault / ".obsidian").mkdir()
            doc = vault / "records" / "one.md"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("---\nslug: pss.one\n---\nbody\n", encoding="utf-8")

            stdin = io.StringIO('{"input_record":{"slug":"pss.one"}}\n')
            stdout = io.StringIO()

            stream_slug_to_path_records(stdin, stdout, cwd=vault)

            self.assertIn('"content":"---\\nslug: pss.one\\n---\\nbody\\n"', stdout.getvalue())
            self.assertIn(str(doc), stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
