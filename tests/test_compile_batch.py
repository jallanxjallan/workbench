from __future__ import annotations

import io
import importlib
from pathlib import Path
import subprocess

import pytest

compile_batch_module = importlib.import_module("workbench.control.compile_batch")
from workbench.control.compile_batch import CompileBatchError, compile_batch, status_tag_name


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "workbench-tests@example.com")
    _git(repo, "config", "user.name", "Workbench Tests")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "seed")
    return repo


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _seed_batch_repo(tmp_path: Path) -> tuple[Path, str, dict[str, Path]]:
    repo = _init_repo(tmp_path)
    files = {
        "omaf.opening_scene.abc123": _write(
            repo / "drafts" / "scene-01.md",
            "---\nslug: omaf.opening_scene.abc123\n---\n\nOpening\n",
        ),
        "omaf.radio_call.def456": _write(
            repo / "drafts" / "scene-02.md",
            "---\nslug: omaf.radio_call.def456\n---\n\nRadio\n",
        ),
        "omaf.crash_site.ghi789": _write(
            repo / "drafts" / "scene-03.md",
            "---\nslug: omaf.crash_site.ghi789\n---\n\nCrash\n",
        ),
    }
    _git(repo, "add", "drafts/scene-01.md", "drafts/scene-02.md", "drafts/scene-03.md")
    _git(repo, "commit", "-m", "add drafts")

    batch_slug = "omaf.ch3.rewrite.a1b2c3"
    tag_message = tmp_path / "batch-tag.yaml"
    tag_message.write_text(
        (
            f"batch: {batch_slug}\n"
            "order:\n"
            "  - omaf.radio_call.def456\n"
            "  - omaf.opening_scene.abc123\n"
            "  - omaf.crash_site.ghi789\n"
        ),
        encoding="utf-8",
    )
    _git(repo, "tag", "-a", f"batch/{batch_slug}", "-F", str(tag_message))
    return repo, batch_slug, files


def test_status_tag_name_formats_expected_values() -> None:
    assert status_tag_name(
        "omaf.ch3.rewrite.a1b2c3",
        "inflight",
        execution_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    ) == (
        "inflight/omaf.ch3.rewrite.a1b2c3-01ARZ3NDEKTSV4RRFFQ69G5FAV"
    )
    assert status_tag_name(
        "omaf.ch3.rewrite.a1b2c3",
        "failed",
        execution_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    ) == (
        "failed/omaf.ch3.rewrite.a1b2c3-01ARZ3NDEKTSV4RRFFQ69G5FAV"
    )


def test_compile_batch_requires_git_repo(tmp_path: Path) -> None:
    stream = io.StringIO()

    rc = compile_batch(batch_slug="sample.batch", repo=tmp_path, stdout=stream)

    assert rc == 1
    assert "Not inside a git repository." in stream.getvalue()


def test_compile_batch_preserves_order_and_ingests_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, batch_slug, files = _seed_batch_repo(tmp_path)
    compiled_paths: list[Path] = []
    ingest_calls: list[dict[str, object]] = []
    execution_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    def _fake_compile_file_record(
        *,
        source: Path,
        batch_slug: str,
        slug: str,
        inline_instruction: str | None = None,
    ) -> str:
        compiled_paths.append(source.resolve())
        return (
            '{"content":"Body","batch_slug":"'
            + batch_slug
            + '","input_record":{"slug":"'
            + slug
            + '"}}\n'
        )

    class _Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _fake_run_ingest(*, records: list[str], ingest_command: tuple[str, ...]):  # noqa: ANN001
        ingest_calls.append(
            {
                "args": list(ingest_command),
                "input": "".join(records),
            }
        )
        return _Result()

    monkeypatch.setattr(compile_batch_module, "compile_file_record", _fake_compile_file_record)
    monkeypatch.setattr(compile_batch_module, "_run_ingest", _fake_run_ingest)
    monkeypatch.setattr(compile_batch_module, "_generate_ulid", lambda: execution_id)

    stream = io.StringIO()
    rc = compile_batch(batch_slug=batch_slug, repo=repo / "drafts", stdout=stream)

    assert rc == 0
    assert compiled_paths == [
        files["omaf.radio_call.def456"].resolve(),
        files["omaf.opening_scene.abc123"].resolve(),
        files["omaf.crash_site.ghi789"].resolve(),
    ]
    assert ingest_calls == [
        {
            "args": ["asc", "ingest", "--stdin"],
            "input": (
                '{"content":"Body","batch_slug":"omaf.ch3.rewrite.a1b2c3","input_record":{"slug":"omaf.radio_call.def456"}}\n'
                '{"content":"Body","batch_slug":"omaf.ch3.rewrite.a1b2c3","input_record":{"slug":"omaf.opening_scene.abc123"}}\n'
                '{"content":"Body","batch_slug":"omaf.ch3.rewrite.a1b2c3","input_record":{"slug":"omaf.crash_site.ghi789"}}\n'
            ),
        }
    ]
    inflight_tag = f"inflight/{batch_slug}-{execution_id}"
    assert _git(repo, "tag", "-l", inflight_tag) == inflight_tag
    assert _git(repo, "tag", "-l", f"failed/{batch_slug}") == ""
    annotation = _git(repo, "tag", "-l", inflight_tag, "--format=%(contents)")
    assert f"batch_slug: {batch_slug}" in annotation
    assert "compiled_count: 3" in annotation
    assert f"ingest_batch_ulid: {execution_id}" in annotation
    assert "timestamp:" in annotation
    assert "Compiled 3 records" in stream.getvalue()
    assert f"Tagged {inflight_tag}" in stream.getvalue()


def test_compile_batch_marks_failed_when_ingest_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, batch_slug, _files = _seed_batch_repo(tmp_path)
    execution_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    def _fake_compile_file_record(
        *,
        source: Path,
        batch_slug: str,
        slug: str,
        inline_instruction: str | None = None,
    ) -> str:
        return (
            '{"content":"Body","batch_slug":"'
            + batch_slug
            + '","input_record":{"slug":"'
            + slug
            + '"}}\n'
        )

    class _Result:
        returncode = 1
        stdout = ""
        stderr = "ingest exploded"

    def _fake_run_ingest(*, records: list[str], ingest_command: tuple[str, ...]):  # noqa: ANN001
        result = _Result()
        raise CompileBatchError(result.stderr, stage="ingest")

    monkeypatch.setattr(compile_batch_module, "compile_file_record", _fake_compile_file_record)
    monkeypatch.setattr(compile_batch_module, "_run_ingest", _fake_run_ingest)
    monkeypatch.setattr(compile_batch_module, "_generate_ulid", lambda: execution_id)

    stream = io.StringIO()
    rc = compile_batch(batch_slug=batch_slug, repo=repo, stdout=stream)

    assert rc == 1
    failed_tag = f"failed/{batch_slug}-{execution_id}"
    assert _git(repo, "tag", "-l", failed_tag) == failed_tag
    assert _git(repo, "tag", "-l", f"inflight/{batch_slug}") == ""
    annotation = _git(repo, "tag", "-l", failed_tag, "--format=%(contents)")
    assert f"batch_slug: {batch_slug}" in annotation
    assert "compiled_count: 3" in annotation
    assert "failure_stage: ingest" in annotation
    assert "message: ingest exploded" in annotation


def test_compile_batch_marks_failed_when_compile_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, batch_slug, _files = _seed_batch_repo(tmp_path)
    ingest_called = False
    execution_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    def _fake_compile_file_record(
        *,
        source: Path,
        batch_slug: str,
        slug: str,
        inline_instruction: str | None = None,
    ) -> str:
        raise CompileBatchError("pandoc exploded", stage="pandoc")

    def _fake_run_ingest(*, records: list[str], ingest_command: tuple[str, ...]):  # noqa: ANN001
        nonlocal ingest_called
        ingest_called = True
        raise AssertionError("ingest should not be called")

    monkeypatch.setattr(compile_batch_module, "compile_file_record", _fake_compile_file_record)
    monkeypatch.setattr(compile_batch_module, "_run_ingest", _fake_run_ingest)
    monkeypatch.setattr(compile_batch_module, "_generate_ulid", lambda: execution_id)

    stream = io.StringIO()
    rc = compile_batch(batch_slug=batch_slug, repo=repo, stdout=stream)

    assert rc == 1
    assert ingest_called is False
    failed_tag = f"failed/{batch_slug}-{execution_id}"
    assert _git(repo, "tag", "-l", failed_tag) == failed_tag
    annotation = _git(repo, "tag", "-l", failed_tag, "--format=%(contents)")
    assert "failure_stage: pandoc" in annotation
    assert "message: pandoc exploded" in annotation


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ('{"batch_slug":"demo","input_record":{"slug":"alpha"}}\n', "content"),
        ('{"content":"Body","input_record":{"slug":"alpha"}}\n', "batch_slug"),
        ('{"content":"Body","batch_slug":"demo","input_record":{}}\n', "input_record.slug"),
        ('{"content":"   ","batch_slug":"demo","input_record":{"slug":"alpha"}}\n', "empty content"),
    ],
)
def test_validate_single_ndjson_record_requires_compile_boundary_fields(
    stdout: str,
    expected: str,
) -> None:
    with pytest.raises(CompileBatchError, match=expected):
        compile_batch_module._validate_single_ndjson_record(
            stdout,
            expected_batch_slug="demo",
            expected_slug="alpha",
        )


def test_compile_batch_refuses_dirty_batch_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, batch_slug, files = _seed_batch_repo(tmp_path)
    execution_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    files["omaf.radio_call.def456"].write_text(
        "---\nslug: omaf.radio_call.def456\n---\n\nRadio updated\n",
        encoding="utf-8",
    )

    def _fake_compile_file_record(**_kwargs: object) -> str:
        raise AssertionError("compile should not be called for dirty batch files")

    def _fake_run_ingest(**_kwargs: object) -> object:
        raise AssertionError("ingest should not be called for dirty batch files")

    monkeypatch.setattr(compile_batch_module, "compile_file_record", _fake_compile_file_record)
    monkeypatch.setattr(compile_batch_module, "_run_ingest", _fake_run_ingest)
    monkeypatch.setattr(compile_batch_module, "_generate_ulid", lambda: execution_id)

    stream = io.StringIO()
    rc = compile_batch(batch_slug=batch_slug, repo=repo, stdout=stream)

    assert rc == 1
    failed_tag = f"failed/{batch_slug}-{execution_id}"
    assert _git(repo, "tag", "-l", failed_tag) == failed_tag
    assert "File has uncommitted changes: drafts/scene-02.md" in stream.getvalue()
    assert "Refusing to compile batch." in stream.getvalue()


def test_compile_batch_fails_on_ambiguous_slug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, batch_slug, _files = _seed_batch_repo(tmp_path)
    execution_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    _write(
        repo / "notes" / "duplicate.md",
        "---\nslug: omaf.radio_call.def456\n---\n\nDuplicate\n",
    )
    _git(repo, "add", "notes/duplicate.md")
    _git(repo, "commit", "-m", "add duplicate slug")

    def _fake_compile_file_record(**_kwargs: object) -> str:
        raise AssertionError("compile should not be called for ambiguous slug resolution")

    def _fake_run_ingest(**_kwargs: object) -> object:
        raise AssertionError("ingest should not be called for ambiguous slug resolution")

    monkeypatch.setattr(compile_batch_module, "compile_file_record", _fake_compile_file_record)
    monkeypatch.setattr(compile_batch_module, "_run_ingest", _fake_run_ingest)
    monkeypatch.setattr(compile_batch_module, "_generate_ulid", lambda: execution_id)

    stream = io.StringIO()
    rc = compile_batch(batch_slug=batch_slug, repo=repo, stdout=stream)

    assert rc == 1
    failed_tag = f"failed/{batch_slug}-{execution_id}"
    assert _git(repo, "tag", "-l", failed_tag) == failed_tag
    assert "Slug resolution error: omaf.radio_call.def456 matched multiple files:" in stream.getvalue()
    assert "  - drafts/scene-02.md" in stream.getvalue()
    assert "  - notes/duplicate.md" in stream.getvalue()
