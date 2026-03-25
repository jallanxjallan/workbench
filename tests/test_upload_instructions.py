from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import repo
from upload.instructions import iter_upload_instruction_paths, main


class UploadInstructionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.vault = self.root / "vault"
        self.vault.mkdir()
        (self.vault / ".obsidian").mkdir()
        repo.init_repo(self.vault, repo.DEFAULT_GITIGNORE_TEXT)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_instruction(self, relpath: str, slug: str, body: str = "body") -> Path:
        path = self.vault / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nslug: {slug}\n---\n{body}\n", encoding="utf-8")
        return path

    def _write_markdown(self, relpath: str, body: str) -> Path:
        path = self.vault / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_selects_committed_and_untracked_instruction_files_since_latest_upload(self) -> None:
        changed = self._write_instruction("_control/instructions/changed.md", "gbl.changed", "first")
        untouched = self._write_instruction("_control/instructions/untouched.md", "cxt.untouched", "same")
        other = self._write_instruction("_control/instructions/not-selected.md", "pss.ignore", "ignore me")
        baseline_commit = repo.ensure_snapshot_commit(self.vault, "initial snapshot")
        repo.write_upload_tag(
            self.vault,
            repo.UploadReceipt(
                receipt_id="upl.1234",
                created_at="2026-03-25T10:00:00Z",
                commit=baseline_commit,
                family="instructions",
                record_count=2,
                files=[
                    repo.UploadReceiptFile(
                        slug="gbl.changed",
                        path_rel="_control/instructions/changed.md",
                        content_hash=repo.file_content_hash(changed),
                    ),
                    repo.UploadReceiptFile(
                        slug="cxt.untouched",
                        path_rel="_control/instructions/untouched.md",
                        content_hash=repo.file_content_hash(untouched),
                    ),
                ],
                vault_root=str(self.vault),
            ),
        )

        changed.write_text("---\nslug: gbl.changed\n---\nsecond\n", encoding="utf-8")
        other.write_text("---\nslug: pss.ignore\n---\nchanged\n", encoding="utf-8")
        repo.ensure_snapshot_commit(self.vault, "instruction update")
        untracked = self._write_instruction("_control/instructions/new.md", "spc.new", "untracked")
        self._write_markdown("_control/instructions/readme.md", "# not an instruction\n")

        selected = iter_upload_instruction_paths(cwd=self.vault)

        self.assertEqual(selected, [changed.resolve(), untracked.resolve()])

    def test_first_upload_selects_all_instruction_files_in_sorted_absolute_order(self) -> None:
        later = self._write_instruction("_control/instructions/zeta.md", "spc.zeta")
        repo.ensure_snapshot_commit(self.vault, "initial snapshot")
        earlier = self._write_instruction("_control/instructions/alpha.md", "gbl.alpha")
        self._write_markdown("_control/instructions/notes.md", "---\nslug: pss.notes\n---\nignore\n")

        selected = iter_upload_instruction_paths(cwd=self.vault)

        self.assertEqual(selected, [earlier.resolve(), later.resolve()])
        self.assertTrue(all(path.is_absolute() for path in selected))

    def test_main_emits_one_absolute_filepath_per_line(self) -> None:
        first = self._write_instruction("_control/instructions/b.md", "gbl.b")
        second = self._write_instruction("_control/instructions/a.md", "cxt.a")

        stdout = io.StringIO()
        stderr = io.StringIO()
        previous_cwd = Path.cwd()
        try:
            os.chdir(self.vault)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main()
        finally:
            os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [str(second.resolve()), str(first.resolve())],
        )


if __name__ == "__main__":
    unittest.main()
