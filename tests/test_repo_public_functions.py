from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import repo
from repo.errors import ReceiptMatchError


class RepoPublicFunctionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _init_repo(self) -> str:
        repo.init_repo(self.root, repo.DEFAULT_GITIGNORE_TEXT)
        return repo.ensure_snapshot_commit(self.root, "initial snapshot")

    def _write_file(self, relpath: str, content: str) -> Path:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_init_repo_writes_gitignore_and_creates_repo(self) -> None:
        repo.init_repo(self.root, repo.DEFAULT_GITIGNORE_TEXT)

        self.assertTrue((self.root / ".git").exists())
        self.assertEqual(
            (self.root / ".gitignore").read_text(encoding="utf-8"),
            repo.DEFAULT_GITIGNORE_TEXT,
        )

    def test_is_file_dirty_returns_expected_result_for_modified_file(self) -> None:
        path = self._write_file("records/a.md", "alpha\n")
        self._init_repo()

        self.assertFalse(repo.is_file_dirty(self.root, path))

        path.write_text("beta\n", encoding="utf-8")

        self.assertTrue(repo.is_file_dirty(self.root, path))

    def test_submit_receipt_round_trip(self) -> None:
        path = self._write_file("records/a.md", "alpha\n")
        commit = self._init_repo()
        receipt = repo.SubmitReceipt(
            receipt_id="sub.1234",
            created_at="2026-03-25T10:00:00Z",
            commit=commit,
            record_count=1,
            slugs=["pss.a"],
            paths_rel=["records/a.md"],
            vault_root=str(self.root),
        )

        tag_name = repo.write_submit_tag(self.root, receipt)
        payload = repo.read_tag(self.root, tag_name)
        matched = repo.find_matching_submit_tag(self.root, [str(path)], slugs=["pss.a"])

        self.assertEqual(payload["type"], "submit")
        self.assertEqual(payload["receipt_id"], "sub.1234")
        self.assertEqual(matched.receipt_id, receipt.receipt_id)
        self.assertEqual(matched.paths_rel, receipt.paths_rel)
        self.assertEqual(matched.tag_name, tag_name)

    def test_inflight_receipt_round_trip(self) -> None:
        path = self._write_file("records/a.md", "alpha\n")
        commit = self._init_repo()
        receipt = repo.InflightReceipt(
            created_at="2026-03-25T10:00:00Z",
            slug="pss.a",
            path_rel="records/a.md",
            commit=commit,
            content_hash=repo.file_content_hash(path),
            vault_root=str(self.root),
        )

        tag_name = repo.write_inflight_tag(self.root, receipt)
        latest = repo.find_latest_inflight_tag(self.root, "pss.a")

        self.assertEqual(tag_name, latest.tag_name)
        self.assertEqual(latest.slug, "pss.a")
        self.assertEqual(latest.path_rel, "records/a.md")

    def test_landed_receipt_round_trip(self) -> None:
        path = self._write_file("records/a.md", "alpha\n")
        commit = self._init_repo()
        receipt = repo.LandedReceipt(
            created_at="2026-03-25T10:00:00Z",
            slug="pss.a",
            path_rel="records/a.md",
            commit=commit,
            content_hash=repo.file_content_hash(path),
            source_batch_id="content.topic.xyz98765",
            vault_root=str(self.root),
        )

        tag_name = repo.write_landed_tag(self.root, receipt)
        latest = repo.find_latest_landed_tag(self.root, "pss.a")

        self.assertEqual(tag_name, latest.tag_name)
        self.assertEqual(latest.source_batch_id, "content.topic.xyz98765")

    def test_upload_receipt_round_trip(self) -> None:
        path = self._write_file("_control/instructions/foo.md", "alpha\n")
        commit = self._init_repo()
        receipt = repo.UploadReceipt(
            receipt_id="upl.1234",
            created_at="2026-03-25T10:00:00Z",
            commit=commit,
            family="instructions",
            record_count=1,
            files=[
                repo.UploadReceiptFile(
                    slug="gbl.foo",
                    path_rel="_control/instructions/foo.md",
                    content_hash=repo.file_content_hash(path),
                )
            ],
            vault_root=str(self.root),
        )

        tag_name = repo.write_upload_tag(self.root, receipt)
        latest = repo.find_latest_upload_tag(self.root, family="instructions")
        reread = repo.read_upload_tag(self.root, tag_name)

        self.assertEqual(latest.tag_name, tag_name)
        self.assertEqual(reread.files[0].slug, "gbl.foo")
        self.assertEqual(reread.files[0].path_rel, "_control/instructions/foo.md")

    def test_find_matching_submit_tag_rejects_zero_and_multiple_matches(self) -> None:
        self._write_file("records/a.md", "alpha\n")
        commit = self._init_repo()

        with self.assertRaises(ReceiptMatchError):
            repo.find_matching_submit_tag(self.root, ["records/a.md"], slugs=["pss.a"])

        first = repo.SubmitReceipt(
            receipt_id="sub.1111",
            created_at="2026-03-25T10:00:00Z",
            commit=commit,
            record_count=1,
            slugs=["pss.a"],
            paths_rel=["records/a.md"],
        )
        second = repo.SubmitReceipt(
            receipt_id="sub.2222",
            created_at="2026-03-25T10:01:00Z",
            commit=commit,
            record_count=1,
            slugs=["pss.a"],
            paths_rel=["records/a.md"],
        )
        repo.write_submit_tag(self.root, first)
        repo.write_submit_tag(self.root, second)

        with self.assertRaises(ReceiptMatchError):
            repo.find_matching_submit_tag(self.root, ["records/a.md"], slugs=["pss.a"])

    def test_needs_upload_returns_true_when_file_is_dirty(self) -> None:
        path = self._write_file("_control/instructions/foo.md", "alpha\n")
        commit = self._init_repo()
        repo.write_upload_tag(
            self.root,
            repo.UploadReceipt(
                receipt_id="upl.1111",
                created_at="2026-03-25T10:00:00Z",
                commit=commit,
                family="instructions",
                record_count=1,
                files=[
                    repo.UploadReceiptFile(
                        slug="gbl.foo",
                        path_rel="_control/instructions/foo.md",
                        content_hash=repo.file_content_hash(path),
                    )
                ],
            ),
        )

        path.write_text("beta\n", encoding="utf-8")

        self.assertTrue(
            repo.needs_upload(self.root, "gbl.foo", path, family="instructions")
        )

    def test_needs_upload_returns_true_when_no_upload_receipt_exists(self) -> None:
        path = self._write_file("_control/instructions/foo.md", "alpha\n")
        self._init_repo()

        self.assertTrue(
            repo.needs_upload(self.root, "gbl.foo", path, family="instructions")
        )

    def test_needs_upload_returns_true_when_file_committed_after_receipt(self) -> None:
        path = self._write_file("_control/instructions/foo.md", "alpha\n")
        first_commit = self._init_repo()
        repo.write_upload_tag(
            self.root,
            repo.UploadReceipt(
                receipt_id="upl.1111",
                created_at="2026-03-25T10:00:00Z",
                commit=first_commit,
                family="instructions",
                record_count=1,
                files=[
                    repo.UploadReceiptFile(
                        slug="gbl.foo",
                        path_rel="_control/instructions/foo.md",
                        content_hash=repo.file_content_hash(path),
                    )
                ],
            ),
        )

        path.write_text("beta\n", encoding="utf-8")
        repo.ensure_snapshot_commit(self.root, "second snapshot")

        self.assertTrue(
            repo.needs_upload(self.root, "gbl.foo", path, family="instructions")
        )

    def test_needs_upload_returns_false_when_file_is_clean_and_unchanged(self) -> None:
        path = self._write_file("_control/instructions/foo.md", "alpha\n")
        commit = self._init_repo()
        repo.write_upload_tag(
            self.root,
            repo.UploadReceipt(
                receipt_id="upl.1111",
                created_at="2026-03-25T10:00:00Z",
                commit=commit,
                family="instructions",
                record_count=1,
                files=[
                    repo.UploadReceiptFile(
                        slug="gbl.foo",
                        path_rel="_control/instructions/foo.md",
                        content_hash=repo.file_content_hash(path),
                    )
                ],
            ),
        )

        self.assertFalse(
            repo.needs_upload(self.root, "gbl.foo", path, family="instructions")
        )


if __name__ == "__main__":
    unittest.main()
