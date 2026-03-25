from __future__ import annotations

from pathlib import Path
import sys

import repo
from intake.frontmatter import FrontmatterError, read_frontmatter
from scan import rg_search
from vault.validate import validate_vault


INSTRUCTION_PREFIXES = ("gbl.", "cxt.", "spc.")
MARKDOWN_EXTENSIONS = ["md", "markdown"]
SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]
INSTRUCTION_SLUG_PATTERN = r"^slug:\s*(?:gbl|cxt|spc)\..*$"


class UploadInstructionsError(RuntimeError):
    """Raised when upload-instructions cannot compile a filepath list."""



def is_instruction_file(path: Path, vault_root: Path) -> bool:
    normalized = Path(path).expanduser().resolve()
    if normalized.suffix.lower() not in {".md", ".markdown"}:
        return False
    if not normalized.is_file():
        return False

    try:
        normalized.relative_to(vault_root)
    except ValueError:
        return False

    frontmatter = read_frontmatter(normalized)
    slug = frontmatter.get("slug")
    return isinstance(slug, str) and slug.startswith(INSTRUCTION_PREFIXES)



def discover_candidate_paths(vault_root: Path, repo_root: Path) -> list[Path]:
    git_repo = repo.discover_repo(repo_root)
    latest_upload = repo.find_latest_upload_tag(repo_root, family="instructions")

    if latest_upload is None:
        return _discover_all_instruction_paths(vault_root)

    candidate_paths: list[Path] = []
    head_commit = git_repo.head().oid
    if latest_upload.commit != head_commit:
        candidate_paths.extend(git_repo.changed_paths_between(latest_upload.commit, head_commit))

    candidate_paths.extend(_dirty_paths_within_vault(git_repo, vault_root))
    return _filter_instruction_paths(candidate_paths, vault_root)



def emit_paths(paths: list[Path]) -> None:
    for path in paths:
        print(path)



def iter_upload_instruction_paths(cwd: Path | None = None) -> list[Path]:
    current_cwd = (Path.cwd() if cwd is None else Path(cwd)).expanduser().resolve()
    vault_root = validate_vault(current_cwd)
    repo_root = repo.discover_repo(vault_root).root
    return discover_candidate_paths(vault_root, repo_root)



def main() -> int:
    try:
        paths = iter_upload_instruction_paths()
    except Exception as exc:
        print(f"upload-instructions: {exc}", file=sys.stderr)
        return 1

    emit_paths(paths)
    return 0



def _discover_all_instruction_paths(vault_root: Path) -> list[Path]:
    matches = rg_search(
        pattern=INSTRUCTION_SLUG_PATTERN,
        root=vault_root,
        extensions=MARKDOWN_EXTENSIONS,
        exclude_dirs=SCAN_EXCLUDE_DIRS,
    )
    return _instruction_paths_from_matches(matches, vault_root)



def _dirty_paths_within_vault(git_repo: repo.GitRepo, vault_root: Path) -> list[Path]:
    paths: list[Path] = []
    for entry in git_repo.status_for_paths([vault_root], include_untracked=True):
        if entry.is_ignored or not entry.is_dirty:
            continue
        try:
            entry.path.relative_to(vault_root)
        except ValueError:
            continue
        paths.append(entry.path)
    return paths



def _filter_instruction_paths(candidate_paths: list[Path], vault_root: Path) -> list[Path]:
    existing_files = _dedupe_existing_files(candidate_paths, vault_root)
    if not existing_files:
        return []

    matches = rg_search(
        pattern=INSTRUCTION_SLUG_PATTERN,
        files=existing_files,
        extensions=MARKDOWN_EXTENSIONS,
        exclude_dirs=[],
    )
    return _instruction_paths_from_matches(matches, vault_root)



def _instruction_paths_from_matches(
    matches: list[dict[str, object]],
    vault_root: Path,
) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()

    for match in matches:
        raw_path = match.get("path")
        if not isinstance(raw_path, Path):
            raise UploadInstructionsError("scan returned a match without a path")

        normalized = raw_path.expanduser().resolve()
        if normalized in seen:
            continue
        seen.add(normalized)

        try:
            if is_instruction_file(normalized, vault_root):
                resolved.append(normalized)
        except (FrontmatterError, OSError):
            continue

    return sorted(resolved)



def _dedupe_existing_files(candidate_paths: list[Path], vault_root: Path) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()

    for raw_path in candidate_paths:
        normalized = Path(raw_path).expanduser().resolve()
        if normalized in seen:
            continue
        seen.add(normalized)
        if not normalized.exists() or not normalized.is_file():
            continue
        try:
            normalized.relative_to(vault_root)
        except ValueError:
            continue
        resolved.append(normalized)

    return sorted(resolved)


if __name__ == "__main__":
    raise SystemExit(main())
