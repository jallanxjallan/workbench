from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import repo
from repo.repo import _run_git
from transport import loads_record
from upload.profiles import (
    UploadProfilesError,
    iter_upload_profile_records,
    load_profile_yaml,
    upload_profiles,
)


class UploadProfilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.profiles_root = self.root / "profiles"
        self.profiles_root.mkdir()
        repo.init_repo(self.profiles_root, repo.DEFAULT_GITIGNORE_TEXT)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_profile(self, relpath: str, slug: str, extra: str = "") -> Path:
        path = self.profiles_root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        suffix = f"{extra}\n" if extra else ""
        path.write_text(f"slug: {slug}\n{suffix}", encoding="utf-8")
        return path

    def _tag_successful_upload(self, name: str) -> None:
        _run_git(["tag", "-a", name, "-m", name], cwd=self.profiles_root)

    def test_iter_upload_profile_records_emits_all_profiles_before_first_tag(self) -> None:
        first = self._write_profile("a.yaml", "prf.a")
        second = self._write_profile("b.yml", "prf.b")

        records = [loads_record(line) for line in iter_upload_profile_records(root=self.profiles_root)]

        self.assertEqual([record["input_record"]["slug"] for record in records], ["prf.a", "prf.b"])
        self.assertEqual(records[0]["input_record"]["origin"]["source_path"], str(first.resolve()))
        self.assertEqual(records[1]["input_record"]["origin"]["source_path"], str(second.resolve()))

    def test_iter_upload_profile_records_skips_clean_profiles_after_successful_tag(self) -> None:
        self._write_profile("a.yaml", "prf.a")
        repo.ensure_snapshot_commit(self.profiles_root, "initial snapshot")
        self._tag_successful_upload("successful_upload/profiles/prf")

        records = iter_upload_profile_records(root=self.profiles_root)

        self.assertEqual(records, [])

    def test_iter_upload_profile_records_includes_dirty_and_untracked_profiles_after_successful_tag(self) -> None:
        changed = self._write_profile("a.yaml", "prf.a")
        self._write_profile("b.yml", "prf.b")
        repo.ensure_snapshot_commit(self.profiles_root, "initial snapshot")
        self._tag_successful_upload("successful_upload/profiles/prf")

        changed.write_text("slug: prf.a\nupdated: true\n", encoding="utf-8")
        untracked = self._write_profile("c.yaml", "prf.c")

        records = [loads_record(line) for line in iter_upload_profile_records(root=self.profiles_root)]

        self.assertEqual([record["input_record"]["slug"] for record in records], ["prf.a", "prf.c"])
        self.assertEqual(records[1]["input_record"]["origin"]["source_path"], str(untracked.resolve()))

    def test_upload_profiles_writes_ndjson_to_stdout(self) -> None:
        self._write_profile("a.yaml", "prf.a")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = upload_profiles(root=self.profiles_root)

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(stdout.getvalue().splitlines()), 1)
        record = loads_record(stdout.getvalue().splitlines()[0])
        self.assertEqual(record["input_record"]["slug"], "prf.a")

    def test_invalid_yaml_hard_fails(self) -> None:
        path = self.profiles_root / "bad.yaml"
        path.write_text("slug: [unterminated\n", encoding="utf-8")

        with self.assertRaises(UploadProfilesError):
            load_profile_yaml(path)


if __name__ == "__main__":
    unittest.main()
