"""Import draft-vault content into a target vault project scaffold."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from workbench.config.roots import RootResolutionError, resolve_content_root

PROJECT_SUBDIRECTORIES = ("manuscript", "assets", "notes", "instructions")
MARKDOWN_SUFFIX = ".md"


class ImportProjectError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportProjectResult:
    project_name: str
    destination: Path
    markdown_files: int
    asset_files: int
    mode: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="import-project",
        description="Import markdown/assets from a draft vault into a target vault project.",
    )
    parser.add_argument(
        "--vault-root",
        help="Content root containing target vault folders (or set WORKBENCH_CONTENT_ROOT).",
    )
    parser.add_argument(
        "--vault",
        required=True,
        dest="vault_name",
        help="Target vault folder name under the resolved content root.",
    )
    parser.add_argument(
        "--draft-path",
        required=True,
        help="Path to the draft vault directory to import from.",
    )
    parser.add_argument(
        "--project",
        dest="project_name",
        help="Optional destination project name. Defaults to draft directory name.",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying (default is copy).",
    )
    return parser.parse_args(argv)


def _normalize_project_name(project_name: str) -> str:
    normalized = project_name.strip()
    if not normalized:
        raise ImportProjectError("ERROR: Project name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise ImportProjectError(
            "ERROR: Project name must not contain path separators."
        )
    return normalized


def _resolve_draft_path(raw_path: str) -> Path:
    draft_path = Path(raw_path).expanduser().resolve()
    if not draft_path.exists() or not draft_path.is_dir():
        raise ImportProjectError(f"ERROR: Draft path does not exist: {draft_path}")
    return draft_path


def _iter_manuscript_markdown(draft_path: Path) -> list[Path]:
    assets_root = draft_path / "assets"
    files: list[Path] = []
    for path in draft_path.rglob(f"*{MARKDOWN_SUFFIX}"):
        if not path.is_file():
            continue
        if assets_root.exists() and path.is_relative_to(assets_root):
            continue
        files.append(path)
    files.sort()
    return files


def _transfer_file(*, source: Path, destination: Path, move: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ImportProjectError(f"ERROR: Destination already exists: {destination}")
    if move:
        shutil.move(str(source), str(destination))
    else:
        shutil.copy2(source, destination)


def _import_markdown(*, draft_path: Path, manuscript_dir: Path, move: bool) -> int:
    transferred = 0
    for source in _iter_manuscript_markdown(draft_path):
        rel = source.relative_to(draft_path)
        destination = manuscript_dir / rel
        _transfer_file(source=source, destination=destination, move=move)
        transferred += 1
    return transferred


def _iter_asset_files(assets_root: Path) -> list[Path]:
    files = [path for path in assets_root.rglob("*") if path.is_file()]
    files.sort()
    return files


def _import_assets(*, draft_path: Path, assets_dir: Path, move: bool) -> int:
    source_assets_root = draft_path / "assets"
    if not source_assets_root.exists():
        return 0
    if not source_assets_root.is_dir():
        raise ImportProjectError(
            f"ERROR: Draft assets path is not a directory: {source_assets_root}"
        )

    transferred = 0
    for source in _iter_asset_files(source_assets_root):
        rel = source.relative_to(source_assets_root)
        destination = assets_dir / rel
        _transfer_file(source=source, destination=destination, move=move)
        transferred += 1
    return transferred


def _write_instruction_placeholder(
    *, vault_path: Path, project_name: str, project_path: Path
) -> None:
    instruction_dir = vault_path / "instructions" / "project"
    instruction_dir.mkdir(parents=True, exist_ok=True)
    instruction_path = instruction_dir / f"{project_name}.md"
    content = (
        f"# Project Instructions: {project_name}\n\n"
        "## Paths\n"
        f"- Manuscript: `projects/{project_name}/manuscript`\n"
        f"- Assets: `projects/{project_name}/assets`\n"
        f"- Notes: `projects/{project_name}/notes`\n"
        f"- Project Root: `{project_path.relative_to(vault_path)}`\n\n"
        "## TODO\n"
        "- Add project-specific instruction macros.\n"
        "- Add ingestion/emit workflow notes.\n"
    )
    instruction_path.write_text(content, encoding="utf-8")


def _create_project_directory(*, vault_path: Path, project_name: str) -> Path:
    projects_root = vault_path / "projects"
    projects_root.mkdir(parents=True, exist_ok=True)

    project_path = projects_root / project_name
    if project_path.exists():
        raise ImportProjectError(f"ERROR: Project path already exists: {project_path}")
    project_path.mkdir(parents=False, exist_ok=False)
    return project_path


def _write_asset_index(*, assets_dir: Path) -> None:
    asset_files = [
        path.relative_to(assets_dir) for path in assets_dir.rglob("*") if path.is_file()
    ]
    asset_files.sort()
    lines = ["# Asset Index", ""]
    if not asset_files:
        lines.append("_No assets imported._")
    else:
        lines.extend(f"- `{path.as_posix()}`" for path in asset_files)
    (assets_dir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def import_project(
    *,
    vault_root: str | None,
    vault_name: str,
    draft_path: str,
    project_name: str | None,
    move: bool,
) -> ImportProjectResult:
    try:
        resolved_root = resolve_content_root(vault_root)
    except RootResolutionError as exc:
        raise ImportProjectError(f"ERROR: {exc}") from exc

    normalized_vault = vault_name.strip()
    if not normalized_vault:
        raise ImportProjectError("ERROR: Vault name must be non-empty.")

    vault_path = resolved_root / normalized_vault
    if not vault_path.exists() or not vault_path.is_dir():
        raise ImportProjectError(f"ERROR: Target vault does not exist: {vault_path}")

    resolved_draft = _resolve_draft_path(draft_path)
    selected_project_name = _normalize_project_name(project_name or resolved_draft.name)

    project_path = _create_project_directory(
        vault_path=vault_path,
        project_name=selected_project_name,
    )
    manuscript_dir = project_path / "manuscript"
    assets_dir = project_path / "assets"
    notes_dir = project_path / "notes"
    instructions_dir = project_path / "instructions"
    for directory in (manuscript_dir, assets_dir, notes_dir, instructions_dir):
        directory.mkdir(parents=True, exist_ok=True)

    markdown_files = _import_markdown(
        draft_path=resolved_draft,
        manuscript_dir=manuscript_dir,
        move=move,
    )
    asset_files = _import_assets(
        draft_path=resolved_draft,
        assets_dir=assets_dir,
        move=move,
    )
    _write_asset_index(assets_dir=assets_dir)
    _write_instruction_placeholder(
        vault_path=vault_path,
        project_name=selected_project_name,
        project_path=project_path,
    )

    return ImportProjectResult(
        project_name=selected_project_name,
        destination=project_path,
        markdown_files=markdown_files,
        asset_files=asset_files,
        mode="move" if move else "copy",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = import_project(
            vault_root=args.vault_root,
            vault_name=str(args.vault_name),
            draft_path=str(args.draft_path),
            project_name=str(args.project_name)
            if args.project_name is not None
            else None,
            move=bool(args.move),
        )
    except ImportProjectError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("import-project: completed")
    print(f"Imported project: {result.project_name}")
    print(f"Files copied: {result.markdown_files}")
    print(f"Assets copied: {result.asset_files}")
    print(f"Destination: {result.destination}")
    print(f"Mode: {result.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
