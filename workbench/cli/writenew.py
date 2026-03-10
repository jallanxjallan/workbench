"""Create one new markdown note from a vault template."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.write.common import (
    WriteError,
    atomic_write_text,
    ensure_directory,
    resolve_unique_markdown_path,
)

MARKDOWN_SUFFIXES = (".md", ".markdown")


class WriteNewTemplateError(WriteError):
    pass


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(
        prog="writenew",
        description="Create a new markdown note from a vault template.",
    )
    command_parser.add_argument(
        "--template",
        required=True,
        help="Template name/path under <vault>/_common/templates.",
    )
    command_parser.add_argument(
        "--name",
        default="",
        help="Output note name (without extension). Defaults to template stem.",
    )
    command_parser.add_argument(
        "--path",
        default=".",
        help="Target directory where the note is created (default: current directory).",
    )
    return command_parser


def _resolve_templates_root(vault_root: Path) -> Path:
    templates_root = (vault_root / "_common" / "templates").resolve()
    if templates_root.exists() and templates_root.is_dir():
        return templates_root
    raise WriteNewTemplateError(f"template directory is missing: {templates_root}")


def _resolve_template_path(template_name: str, vault_root: Path) -> Path:
    raw = str(template_name).strip()
    if not raw:
        raise WriteNewTemplateError("template name must be non-empty")

    templates_root = _resolve_templates_root(vault_root)

    if raw.startswith("_common/templates/"):
        raw = raw[len("_common/templates/") :]

    selected: Path | None = None
    raw_path = Path(raw)

    if raw_path.is_absolute():
        candidate = raw_path.expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            selected = candidate
    else:
        candidates = [templates_root / raw_path]
        if raw_path.suffix == "":
            candidates.append(templates_root / f"{raw}.md")

        for candidate in candidates:
            candidate_resolved = candidate.resolve()
            if candidate_resolved.exists() and candidate_resolved.is_file():
                selected = candidate_resolved
                break

    if selected is None:
        raise WriteNewTemplateError(
            f"template not found in {templates_root}: {template_name}"
        )

    try:
        selected.relative_to(templates_root)
    except ValueError as exc:
        raise WriteNewTemplateError(
            f"template must resolve under {templates_root}: {selected}"
        ) from exc

    if selected.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise WriteNewTemplateError(f"template is not markdown: {selected}")

    return selected


def _find_vault_root(start_path: Path) -> Path:
    for parent in [start_path.resolve(), *start_path.resolve().parents]:
        obsidian_dir = parent / ".obsidian"
        common_templates_dir = parent / "_common" / "templates"
        if obsidian_dir.is_dir() and common_templates_dir.is_dir():
            return parent

    raise WriteNewTemplateError(
        f"could not resolve vault root from path: {start_path}"
    )


def _resolve_note_stem(name: str, template_path: Path) -> str:
    text = str(name or "").strip()
    if not text:
        return template_path.stem
    return text.replace(".md", "").replace(".markdown", "").strip()


def run(*, template: str, name: str, path: str) -> Path:
    target_dir = ensure_directory(path)
    vault_root = _find_vault_root(target_dir)
    template_path = _resolve_template_path(template, vault_root)

    try:
        content = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WriteNewTemplateError(f"failed to read template: {template_path}") from exc

    stem = _resolve_note_stem(name, template_path)
    output_path = resolve_unique_markdown_path(target_dir, stem)
    atomic_write_text(output_path, content)
    return output_path


def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)

    try:
        created = run(template=args.template, name=args.name, path=args.path)
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(created)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
