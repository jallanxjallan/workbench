from __future__ import annotations

"""
Typed Git boundary for Workbench.

Why this package exists
-----------------------
Workbench depends on Git for repository state, safety checks, and operator
workflow markers such as annotated tags. The rest of the codebase should not
need to know which Git commands are run or how their output is parsed. This
package centralizes that behavior behind a small, documented Python interface.

Design goals
------------
1. Keep Git semantics in one place.
2. Return typed Python values instead of raw command strings.
3. Use pathlib consistently.
4. Fail with narrow, meaningful exceptions.
5. Make it easy to replace the implementation later (for example with a hybrid
   or library-backed backend) without changing callers.

Scope
-----
This is intentionally a repository-state layer, not a full Git object model.
It covers the operations Workbench is most likely to need for document-state
and workflow safety:

- repository discovery
- worktree root resolution
- tracked / untracked checks
- dirty-file checks
- HEAD commit lookup
- current branch lookup
- tag lookup at HEAD
- changed-file listing
- basic revision parsing

Conventions
-----------
- All public path arguments accept file or directory paths.
- Paths returned by this package are normalized to absolute resolved Paths.
- Methods that answer path-state questions are repo-relative internally, but
  they accept absolute or relative input paths.
- "Dirty" means any staged, unstaged, or untracked change affecting the path,
  depending on the method and options.
"""

from .errors import (
    GitCommandError,
    GitError,
    GitReferenceError,
    NotAGitRepositoryError,
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
