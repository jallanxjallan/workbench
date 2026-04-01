from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from upload.dispatch import BatchDispatchError, dispatch_batch
import repo
from scan.api import resolve_slug_to_filepath
from vault.validate import require_vault_root, validate_vault


class BatchDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.vault = self.root / "vault"
        self.vault.mkdir()
        (self.vault / ".obsidian").mkdir()
        repo.init_repo(self.vault, repo.DEFAULT_GITIGNORE_TEXT)
        repo.ensure_snapshot_commit(self.vault, "initial snapshot")
        self.docs = self.vault / "records"
        self.docs.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_doc(self, relpath: str, slug: str, body: str = "body") -> Path:
        path = self.vault / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nslug: {slug}\n---\n{body}\n", encoding="utf-8")
        return path

    def _write_selection(self, slugs: list[str]) -> Path:
        path = self.vault / "selection.json"
        path.write_text(json.dumps(slugs), encoding="utf-8")
        return path

    def test_validate_vault_requires_root(self) -> None:
        nested = self.vault / "records" / "nested"
        nested.mkdir(parents=True)

        self.assertEqual(validate_vault(self.vault), self.vault)
        with self.assertRaises(Exception):
            validate_vault(nested)
        self.assertEqual(require_vault_root(nested), self.vault)

    def test_scan_resolve_slug_to_filepath_requires_exactly_one_match(self) -> None:
        first = self._write_doc("records/a.md", "pss.a")
        self.assertEqual(resolve_slug_to_filepath("pss.a", self.vault), first)

        with self.assertRaises(ValueError):
            resolve_slug_to_filepath("pss.missing", self.vault)

        self._write_doc("records/b.md", "pss.a", "duplicate")
        with self.assertRaises(ValueError):
            resolve_slug_to_filepath("pss.a", self.vault)

    def test_dispatch_preserves_order_and_writes_submit_receipt(self) -> None:
        second = self._write_doc("records/two.md", "pss.two", "two")
        first = self._write_doc("records/one.md", "pss.one", "one")
        selection = self._write_selection(["pss.two", "pss.one"])

        result = dispatch_batch(selection, cwd=self.vault)

        self.assertEqual(result.paths, [second, first])
        receipt = repo.find_matching_submit_tag(
            self.vault,
            [path.relative_to(self.vault).as_posix() for path in result.paths],
            slugs=["pss.two", "pss.one"],
        )
        self.assertEqual(receipt.record_count, 2)
        self.assertEqual(receipt.paths_abs, [str(second), str(first)])
        self.assertEqual(receipt.manifest_path, str(selection))
        self.assertEqual(receipt.cwd, str(self.vault))
        self.assertIsNotNone(receipt.manifest_hash)
        self.assertEqual(result.receipt_tag, receipt.tag_name)

    def test_dispatch_requires_vault_root_cwd(self) -> None:
        self._write_doc("records/one.md", "pss.one", "one")
        selection = self._write_selection(["pss.one"])
        nested = self.vault / "records"

        with self.assertRaises(Exception):
            dispatch_batch(selection, cwd=nested)

    def test_dispatch_rejects_duplicate_slugs_without_creating_tag(self) -> None:
        self._write_doc("records/one.md", "pss.one", "one")
        selection = self._write_selection(["pss.one", "pss.one"])

        with self.assertRaises(BatchDispatchError):
            dispatch_batch(selection, cwd=self.vault)

        self.assertEqual(repo.discover_repo(self.vault).tag_names_at_head(), [])

    def test_dispatch_rejects_path_outside_vault(self) -> None:
        self._write_doc("records/one.md", "pss.one", "one")
        outside = self.root / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        selection = self._write_selection(["pss.one"])

        with patch("upload.dispatch.resolve_slug_to_filepath", return_value=outside):
            with self.assertRaises(BatchDispatchError):
                dispatch_batch(selection, cwd=self.vault)

        self.assertEqual(repo.discover_repo(self.vault).tag_names_at_head(), [])


if __name__ == "__main__":
    unittest.main()
