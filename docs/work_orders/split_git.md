WO: split git.py into a small package without changing public behavior

Goal
Refactor the current single-file git helper into a small package so future Git growth stays organized, while preserving the existing public API shape and caller behavior. The current file already contains three natural layers: exceptions/data types, subprocess boundary helpers, and the GitRepo repository interface. :contentReference[oaicite:0]{index=0} :contentReference[oaicite:1]{index=1}

Scope
Only refactor the Git helper module.
Do not change business logic.
Do not add new features.
Do not change command semantics, path normalization, or exception behavior.
Do not touch callers except import paths if needed.

Target layout
git/
  __init__.py
  errors.py
  types.py
  repo.py

Use this minimal split for now. Do not create runner.py yet unless necessary. Keep _run_git and the private path helpers in repo.py for this pass. The current file is still cohesive enough that further fragmentation would be premature. GitRepo should remain intact as the central abstraction. :contentReference[oaicite:2]{index=2}

Move code as follows

1) errors.py
Move:
- GitError
- GitCommandError
- NotAGitRepositoryError
- GitReferenceError

2) types.py
Move:
- GitTag
- GitStatusEntry
- GitHead
and any other public dataclasses/value objects currently defined in git.py. These are already clearly separated in the current file. :contentReference[oaicite:3]{index=3}

3) repo.py
Move:
- GitRepo
- discover_repo
- repo_root
- all private helpers used by GitRepo, including:
  - _run_git
  - _cwd_for
  - _normalize_input_path
  - any other private parsing/path helpers

Keep GitRepo as one class in one file. Do not split status/tag/diff/history methods into separate modules yet. The current public repository interface is still one coherent unit. :contentReference[oaicite:4]{index=4} :contentReference[oaicite:5]{index=5}

4) __init__.py
Re-export only the public surface:

from .errors import (
    GitError,
    GitCommandError,
    NotAGitRepositoryError,
    GitReferenceError,
)
from .repo import GitRepo, discover_repo, repo_root
from .types import GitHead, GitStatusEntry, GitTag

__all__ = [
    "GitError",
    "GitCommandError",
    "NotAGitRepositoryError",
    "GitReferenceError",
    "GitRepo",
    "discover_repo",
    "repo_root",
    "GitHead",
    "GitStatusEntry",
    "GitTag",
]

Requirements
- Preserve all existing docstrings unless they become misleading after the move.
- Preserve type hints.
- Preserve exact runtime behavior.
- Preserve narrow exceptions.
- Keep all returned paths as absolute resolved pathlib Paths, as the current module promises. :contentReference[oaicite:6]{index=6}
- Keep GitRepo.discover(...) as the standard entry point.
- Callers should be able to import from git package root rather than submodules.

Import migration
Update existing imports from forms like:
  from git.git import GitRepo, NotAGitRepositoryError
to:
  from git import GitRepo, NotAGitRepositoryError

Apply this only where needed in the touched codebase. For example, overwrite.py currently imports from git.git and should be updated to package-root imports after the split. :contentReference[oaicite:7]{index=7}

Non-goals
- No switch to GitPython/pygit2/libgit2.
- No object-model expansion.
- No command caching.
- No async/background behavior.
- No new CLI wrapper layer.
- No backward-compat shim file named git.py unless absolutely required by unresolved imports elsewhere; if used temporarily, note it explicitly.

Verification
1) Static
- Imports resolve from package root:
  - from git import GitRepo
  - from git import GitStatusEntry
  - from git import NotAGitRepositoryError

2) Behavioral smoke checks
Verify these still behave exactly as before:
- GitRepo.discover(path)
- repo_root(path)
- repo.git_dir()
- repo.is_inside_worktree()
- status / status_for_paths parsing
- dirty-file detection
- file_changed_between(...)
- changed_paths_between(...)

3) Caller smoke check
- Confirm overwrite/writeback path still works with:
  from git import GitRepo, NotAGitRepositoryError
and no residual dependency on git.git remains in touched files. overwrite.py currently relies on GitRepo.discover(path) for dirty-file detection, so this import path must remain clean after the refactor. :contentReference[oaicite:8]{index=8}

Deliverable
A minimal package split that makes future Git growth easier while keeping today’s public interface simple and stable.
```

One tactical note for Codex: this is a refactor, not a redesign. Move code first, then fix imports, then run smoke checks.
