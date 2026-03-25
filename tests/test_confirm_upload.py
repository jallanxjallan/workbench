from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

import repo
from transport import dumps_record
from upload.confirm import ConfirmUploadError, confirm_upload


class ConfirmUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.vault = self.root / "vault"
        self.vault.mkdir()
        (self.vault / ".obsidian").mkdir()
        repo.init_repo(self.vault, repo.DEFAULT_GITIGNORE_TEXT)
        self.first = self._write_doc("records/a.md", "pss.a")
        self.second = self._write_doc("records/b.md", "pss.b")
        self.commit = repo.ensure_snapshot_commit(self.vault, "initial snapshot")
        self.submit_receipt = repo.SubmitReceipt(
            receipt_id="sub.1234",
            created_at="2026-03-25T10:00:00Z",
            commit=self.commit,
            record_count=2,
            slugs=["pss.a", "pss.b"],
            paths_rel=["records/a.md", "records/b.md"],
            paths_abs=[str(self.first), str(self.second)],
            vault_root=str(self.vault),
            cwd=str(self.vault),
        )
        self.submit_tag = repo.write_submit_tag(self.vault, self.submit_receipt)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_doc(self, relpath: str, slug: str) -> Path:
        path = self.vault / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nslug: {slug}\n---\nbody\n", encoding="utf-8")
        return path

    def _stream(self, trailer: dict) -> io.StringIO:
        records = [
            {
                "content": "body a",
                "input_record": {
                    "origin": {"filepath": str(self.first)},
                    "slug": "pss.a",
                },
            },
            {
                "content": "body b",
                "input_record": {
                    "origin": {"filepath": str(self.second)},
                    "slug": "pss.b",
                },
            },
            trailer,
        ]
        return io.StringIO("".join(f"{dumps_record(record)}\n" for record in records))

    def test_confirm_upload_writes_batch_receipt(self) -> None:
        tag_name = confirm_upload(
            self._stream(
                {
                    "_op": "asc.ingest.result",
                    "status": "ok",
                    "batch_id": "content.topic.xyz98765",
                    "record_count": 2,
                }
            ),
            cwd=self.vault,
        )

        batch = repo.read_batch_tag(self.vault, tag_name)
        self.assertEqual(batch.batch_id, "content.topic.xyz98765")
        self.assertEqual(batch.submit_receipt, self.submit_tag)
        self.assertEqual(batch.paths_abs, [str(self.first), str(self.second)])

    def test_confirm_upload_writes_failed_receipt(self) -> None:
        tag_name = confirm_upload(
            self._stream(
                {
                    "_op": "asc.ingest.result",
                    "status": "failed",
                    "error": "duplicate slug pss.foo.bar",
                    "record_count": 2,
                }
            ),
            cwd=self.vault,
        )

        failed = repo.read_tag(self.vault, tag_name)
        self.assertEqual(failed["error"], "duplicate slug pss.foo.bar")
        self.assertEqual(failed["submit_receipt"], self.submit_tag)
        self.assertEqual(failed["paths_abs"], [str(self.first), str(self.second)])

    def test_confirm_upload_requires_vault_root_cwd(self) -> None:
        nested = self.vault / "records"
        with self.assertRaises(Exception):
            confirm_upload(
                self._stream(
                    {
                        "_op": "asc.ingest.result",
                        "status": "ok",
                        "batch_id": "content.topic.xyz98765",
                        "record_count": 2,
                    }
                ),
                cwd=nested,
            )

    def test_confirm_upload_rejects_missing_trailer(self) -> None:
        stream = io.StringIO(
            f"{dumps_record({'content': 'body', 'input_record': {'origin': {'filepath': str(self.first)}, 'slug': 'pss.a'}})}\n"
        )
        with self.assertRaises(ConfirmUploadError):
            confirm_upload(stream, cwd=self.vault)


if __name__ == "__main__":
    unittest.main()
