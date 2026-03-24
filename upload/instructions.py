from __future__ import annotations

from pathlib import Path
import sys

from workbench.git import (
    find_repo_root,
    find_latest_tag,
    list_paths_changed_since_tag,
    list_tracked_paths,
    list_untracked_paths,
)
from workbench.vault import require_registered_vault_root
from workbench.document import load_document


INSTRUCTION_PREFIXES = ("gbl.", "cxt.", "spc.")
INSTRUCTION_TAG_GLOB = "successful_upload/instructions/*"
MARKDOWN_SUFFIXES = {".md", ".markdown"}


class UploadInstructionsError(RuntimeError):
    """Raised when upload-instructions cannot compile a filepath list."""


def is_instruction_file(path: Path) -> bool:
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        return False
    if not path.is_file():
        return False

    doc = load_document(path)
    slug = doc.frontmatter.get("slug")
    return isinstance(slug, str) and slug.startswith(INSTRUCTION_PREFIXES)


def discover_candidate_paths(vault_root: Path, repo_root: Path) -> list[Path]:
    last_tag = find_latest_tag(repo_root=repo_root, pattern=INSTRUCTION_TAG_GLOB)

    if last_tag is None:
        candidates = list_tracked_paths(repo_root=repo_root, scope=vault_root)
    else:
        candidates = list_paths_changed_since_tag(
            repo_root=repo_root,
            tag=last_tag,
            scope=vault_root,
            include_staged=True,
            include_unstaged=True,
        )

    candidates.extend(
        list_untracked_paths(repo_root=repo_root, scope=vault_root)
    )

    resolved: list[Path] = []
    seen: set[Path] = set()

    for raw_path in candidates:
        path = Path(raw_path).expanduser().resolve()
        if path in seen:
            continue
        seen.add(path)

        try:
            if is_instruction_file(path):
                resolved.append(path)
        except Exception:
            # Ignore invalid/non-pipeline markdown here.
            continue

    return sorted(resolved)


def iter_upload_instruction_paths(cwd: Path | None = None) -> list[Path]:
    start = Path.cwd() if cwd is None else Path(cwd)
    vault_root = require_registered_vault_root(start)
    repo_root = find_repo_root(vault_root)

    return discover_candidate_paths(
        vault_root=vault_root.resolve(),
        repo_root=repo_root.resolve(),
    )


def main() -> int:
    try:
        paths = iter_upload_instruction_paths()
    except Exception as exc:
        print(f"upload-instructions: {exc}", file=sys.stderr)
        return 1

    for path in paths:
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())