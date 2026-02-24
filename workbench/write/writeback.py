"""Write markdown batch documents back to existing files."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from workbench.framing.markdown import MarkdownRecord, emit_markdown_batch, parse_markdown_batch
from workbench.io.streams import read_stdin_text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="writeback",
        description=__doc__,
    )
    parser.add_argument(
        "--project-root",
        help="Project root used to resolve relative source_path and slug lookup (default: AUTOSCRIBE_PROJECT_ROOT or cwd).",
    )
    return parser


def _project_root(override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    configured = os.environ.get("AUTOSCRIBE_PROJECT_ROOT")
    if configured and configured.strip():
        return Path(configured).expanduser().resolve()
    return Path.cwd().resolve()


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        delete=False,
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def _parse_documents(text: str) -> list[MarkdownRecord]:
    if text.strip() == "":
        return []
    return parse_markdown_batch(text)


def _resolve_under_project(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    abs_path = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    try:
        abs_path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"resolved path escapes project root: {raw_path}") from exc
    return abs_path


def _slug_from_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        docs = parse_markdown_batch(text)
    except ValueError:
        return None
    if not docs:
        return None
    slug = docs[0].metadata.get("slug")
    if isinstance(slug, str) and slug.strip():
        return slug.strip()
    return None


def _resolve_by_slug(project_root: Path, slug: str) -> Path:
    matches: list[Path] = []
    for path in project_root.rglob("*.md"):
        if _slug_from_file(path) == slug:
            matches.append(path.resolve())

    if not matches:
        raise FileNotFoundError(f"writeback: no existing file found for slug '{slug}'")
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in sorted(matches))
        raise ValueError(f"writeback: slug '{slug}' is ambiguous across multiple files: {joined}")
    return matches[0]


def _resolve_target_path(project_root: Path, doc: MarkdownRecord, index: int) -> Path:
    source_path = doc.metadata.get("source_path")
    if isinstance(source_path, str) and source_path.strip():
        target_path = _resolve_under_project(project_root, source_path.strip())
        if not target_path.exists():
            raise FileNotFoundError(f"writeback: target does not exist: {target_path}")
        if target_path.is_dir():
            raise IsADirectoryError(f"writeback: target is a directory: {target_path}")
        return target_path

    slug = doc.metadata.get("slug")
    if isinstance(slug, str) and slug.strip():
        return _resolve_by_slug(project_root, slug.strip())

    raise ValueError(f"writeback: document {index} requires frontmatter slug or source_path")


def writeback_markdown_batch(text: str, project_root: Path) -> None:
    docs = _parse_documents(text)
    for index, doc in enumerate(docs, start=1):
        target_path = _resolve_target_path(project_root, doc, index)
        _atomic_write_text(target_path, emit_markdown_batch([doc]))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        writeback_markdown_batch(read_stdin_text(), _project_root(args.project_root))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"writeback: {exc}", file=sys.stderr)
        return 1
