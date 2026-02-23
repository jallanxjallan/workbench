from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from workbench.adapters import write_vault_files


def _run_writer(
    records: list[dict[str, object]],
    *,
    base_dir: Path,
    mode: str,
    dry_run: bool = False,
) -> tuple[int, list[dict[str, object]]]:
    stdin_payload = "".join(json.dumps(record) + "\n" for record in records)
    stdin_buf = io.StringIO(stdin_payload)
    stdout_buf = io.StringIO()

    argv = ["--base-dir", str(base_dir), "--mode", mode]
    if dry_run:
        argv.append("--dry-run")

    old_stdin, old_stdout = sys.stdin, sys.stdout
    try:
        sys.stdin, sys.stdout = stdin_buf, stdout_buf
        rc = write_vault_files.main(argv)
    finally:
        sys.stdin, sys.stdout = old_stdin, old_stdout

    out_rows = [
        json.loads(line) for line in stdout_buf.getvalue().splitlines() if line.strip()
    ]
    return rc, out_rows


def test_writenew_fails_when_target_exists(tmp_path: Path) -> None:
    base_dir = tmp_path / "vault"
    base_dir.mkdir()
    target = base_dir / "note.md"
    target.write_text("original\n", encoding="utf-8")

    rc, rows = _run_writer(
        [{"content": "replacement\n", "output_path": "note.md"}],
        base_dir=base_dir,
        mode="writenew",
    )

    assert rc == 0
    assert len(rows) == 1
    row = rows[0]
    assert row["ok"] is False
    assert "already exists" in str(row["error"])
    assert target.read_text(encoding="utf-8") == "original\n"


def test_writeback_fails_when_target_missing(tmp_path: Path) -> None:
    base_dir = tmp_path / "vault"
    base_dir.mkdir()

    rc, rows = _run_writer(
        [{"content": "replacement\n", "output_path": "missing.md"}],
        base_dir=base_dir,
        mode="writeback",
    )

    assert rc == 0
    assert len(rows) == 1
    row = rows[0]
    assert row["ok"] is False
    assert "does not exist" in str(row["error"])


def test_containment_blocks_parent_escape(tmp_path: Path) -> None:
    base_dir = tmp_path / "vault"
    base_dir.mkdir()

    rc, rows = _run_writer(
        [{"content": "x", "output_path": "../escape.md"}],
        base_dir=base_dir,
        mode="writenew",
    )

    assert rc == 0
    assert len(rows) == 1
    row = rows[0]
    assert row["ok"] is False
    assert "escapes base_dir" in str(row["error"])
    assert not (tmp_path / "escape.md").exists()


def test_atomic_write_creates_file_with_expected_content(tmp_path: Path) -> None:
    base_dir = tmp_path / "vault"
    base_dir.mkdir()

    rc, rows = _run_writer(
        [{"content": "hello\nworld\n", "output_path": "notes/new.md"}],
        base_dir=base_dir,
        mode="writenew",
    )

    assert rc == 0
    assert len(rows) == 1
    row = rows[0]
    assert row["ok"] is True
    assert row["written"] is True

    target = base_dir / "notes" / "new.md"
    assert row["output_path"] == str(target.resolve())
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "hello\nworld\n"


def test_dry_run_does_not_write_file(tmp_path: Path) -> None:
    base_dir = tmp_path / "vault"
    base_dir.mkdir()

    rc, rows = _run_writer(
        [{"content": "hello\n", "output_path": "notes/dry.md"}],
        base_dir=base_dir,
        mode="writenew",
        dry_run=True,
    )

    assert rc == 0
    assert len(rows) == 1
    row = rows[0]
    assert row["ok"] is True
    assert row["written"] is False
    assert not (base_dir / "notes" / "dry.md").exists()
