from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from contracts.uploads import successful_upload_tag
import repo
from transport import loads_record
from upload.package import (
    UploadPackageError,
    iter_upload_package_records,
    load_package_json,
    upload_package,
)


class UploadPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.repo_root = self.root / "vault"
        self.repo_root.mkdir()
        repo.init_repo(self.repo_root, repo.DEFAULT_GITIGNORE_TEXT)
        self.package_path = self.repo_root / "package.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_package(self, payload: dict[str, object]) -> None:
        self.package_path.write_text(json.dumps(payload), encoding="utf-8")

    def _tag_successful_upload(self, name: str) -> None:
        repo.discover_repo(self.repo_root).create_annotated_tag(name, message=name)

    def test_iter_upload_package_records_emits_current_package_record(self) -> None:
        self._write_package({"slug": "pkg.alpha", "steps": []})

        records = [loads_record(line) for line in iter_upload_package_records(self.package_path)]

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["content"], {"slug": "pkg.alpha", "steps": []})
        self.assertEqual(records[0]["input_record"]["slug"], "pkg.alpha")
        self.assertEqual(records[0]["input_record"]["origin"]["record_kind"], "package")
        self.assertEqual(records[0]["input_record"]["origin"]["filepath"], str(self.package_path.resolve()))

    def test_iter_upload_package_records_skips_clean_package_after_successful_tag(self) -> None:
        self._write_package({"slug": "pkg.alpha", "steps": []})
        repo.ensure_snapshot_commit(self.repo_root, "initial snapshot")
        self._tag_successful_upload(
            successful_upload_tag("packages", "pkg.alpha")
        )

        records = iter_upload_package_records(self.package_path)

        self.assertEqual(records, [])

    def test_iter_upload_package_records_includes_dirty_package_after_successful_tag(self) -> None:
        self._write_package({"slug": "pkg.alpha", "steps": []})
        repo.ensure_snapshot_commit(self.repo_root, "initial snapshot")
        self._tag_successful_upload(
            successful_upload_tag("packages", "pkg.alpha")
        )
        self._write_package({"slug": "pkg.alpha", "steps": [{"name": "changed"}]})

        records = [loads_record(line) for line in iter_upload_package_records(self.package_path)]

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["content"], {"slug": "pkg.alpha", "steps": [{"name": "changed"}]})

    def test_upload_package_writes_ndjson_to_stdout(self) -> None:
        self._write_package({"slug": "pkg.alpha", "steps": []})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = upload_package(self.package_path)

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(stdout.getvalue().splitlines()), 1)
        record = loads_record(stdout.getvalue().splitlines()[0])
        self.assertEqual(record["input_record"]["slug"], "pkg.alpha")

    def test_invalid_json_hard_fails_without_fallback(self) -> None:
        self.package_path.write_text("slug: pkg.alpha\n", encoding="utf-8")

        with self.assertRaises(UploadPackageError):
            load_package_json(self.package_path)


if __name__ == "__main__":
    unittest.main()
