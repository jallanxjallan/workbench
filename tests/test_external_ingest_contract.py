from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from workbench.config.roots import WORKBENCH_ROOT
pytestmark = pytest.mark.skipif(
    shutil.which("pandoc") is None,
    reason="pandoc is required for external ingest contract tests",
)


def _pandoc_data_dir() -> Path:
    return WORKBENCH_ROOT / "tools" / "tls" / "pandoc"


def _run_external_ingest(
    *,
    args: list[str],
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pandoc", "--data-dir", str(_pandoc_data_dir()), "--defaults", "external_ingest", *args],
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_single_record(stdout: str) -> dict[str, object]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    return json.loads(lines[0])


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _init_vault_repo(tmp_path: Path) -> Path:
    vault = tmp_path / "VaultA"
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "_vault_registry.json").write_text(
        json.dumps({"mnemonic": "vault-a"}) + "\n",
        encoding="utf-8",
    )
    _git(vault, "init")
    _git(vault, "config", "user.email", "workbench-tests@example.com")
    _git(vault, "config", "user.name", "Workbench Tests")
    (vault / "README.md").write_text("seed\n", encoding="utf-8")
    _git(vault, "add", "README.md")
    _git(vault, "commit", "-m", "seed")
    return vault


def test_external_ingest_file_input_emits_canonical_record(tmp_path: Path) -> None:
    source = tmp_path / "Some File.md"
    source.write_text(
        "---\nslug: passages-sample\nproject: hhp\nlocked: false\n---\n\nBody text.\n",
        encoding="utf-8",
    )

    proc = _run_external_ingest(args=[str(source)])

    assert proc.returncode == 0, proc.stderr
    record = _parse_single_record(proc.stdout)
    assert record["content"] == "Body text.\n"
    assert "origin" not in record
    assert record["input_record"]["filename_hint"] == "Some File.md"
    assert record["input_record"]["origin"]["source_type"] == "file"
    assert record["input_record"]["origin"]["path"] == str(source)
    assert record["input_record"]["origin"]["slug"] == "passages-sample"
    assert record["input_record"]["origin"]["project"] == "hhp"


def test_external_ingest_stdin_markdown_emits_stdin_source_type() -> None:
    proc = _run_external_ingest(
        args=["--from", "markdown"],
        input_text="---\nslug: stdin-sample\n---\n\nHello.\n",
    )

    assert proc.returncode == 0, proc.stderr
    record = _parse_single_record(proc.stdout)
    assert record["content"] == "Hello.\n"
    assert record["input_record"]["origin"]["source_type"] == "stdin"
    assert record["input_record"]["origin"]["slug"] == "stdin-sample"
    assert "filename_hint" not in record["input_record"]
    assert "origin" not in record


def test_external_ingest_html_stream_preserves_known_format_metadata() -> None:
    proc = _run_external_ingest(
        args=["--from", "html", "--metadata", "format=html"],
        input_text="<p>Hello <strong>world</strong>.</p>\n",
    )

    assert proc.returncode == 0, proc.stderr
    record = _parse_single_record(proc.stdout)
    assert record["content"] == "Hello **world**.\n"
    assert record["input_record"]["origin"]["source_type"] == "stdin"
    assert record["input_record"]["origin"]["format"] == "html"


def test_external_ingest_empty_body_fails_loudly(tmp_path: Path) -> None:
    source = tmp_path / "Empty.md"
    source.write_text("---\nslug: empty-doc\n---\n", encoding="utf-8")

    proc = _run_external_ingest(args=[str(source)])

    assert proc.returncode != 0
    assert "emit_ndjson: document empty after filters" in proc.stderr
    assert "slug: empty-doc" in proc.stderr


def test_external_ingest_omits_empty_keys(tmp_path: Path) -> None:
    source = tmp_path / "Omit Empty.md"
    source.write_text(
        "---\nslug: keep-me\nblank: \"\"\nimages: []\ncontext: {}\n---\n\nBody.\n",
        encoding="utf-8",
    )

    proc = _run_external_ingest(args=[str(source)])

    assert proc.returncode == 0, proc.stderr
    record = _parse_single_record(proc.stdout)
    origin = record["input_record"]["origin"]
    assert origin["slug"] == "keep-me"
    assert "blank" not in origin
    assert "images" not in origin
    assert "context" not in origin


def test_migrate_pipe_writevault_succeeds_end_to_end(tmp_path: Path) -> None:
    vault = _init_vault_repo(tmp_path)
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "Alpha Note.md").write_text(
        "---\nslug: alpha-note\nproject: demo\n---\n\nAlpha body.\n",
        encoding="utf-8",
    )
    (source_dir / "Beta Note.md").write_text(
        "---\nproject: demo\n---\n\nBeta body.\n",
        encoding="utf-8",
    )

    migrate_proc = subprocess.Popen(
        [sys.executable, "-m", "workbench.cli.main", "migrate", str(source_dir)],
        cwd=vault,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert migrate_proc.stdout is not None
    writevault_proc = subprocess.run(
        [sys.executable, "-m", "workbench.cli.main", "writevault"],
        cwd=vault,
        stdin=migrate_proc.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    migrate_proc.stdout.close()
    migrate_stderr = migrate_proc.stderr.read() if migrate_proc.stderr is not None else ""
    migrate_rc = migrate_proc.wait()

    assert migrate_rc == 0, migrate_stderr
    assert writevault_proc.returncode == 0, writevault_proc.stderr

    assert (vault / "_ingest" / "Alpha Note.md").read_text(encoding="utf-8") == "Alpha body.\n"
    assert (vault / "_ingest" / "Beta Note.md").read_text(encoding="utf-8") == "Beta body.\n"
