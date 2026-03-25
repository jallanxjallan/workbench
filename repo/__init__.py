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
"""

from .authoring import (
    DEFAULT_GITIGNORE_TEXT,
    FailedReceipt,
    InflightReceipt,
    LandedReceipt,
    SubmitReceipt,
    UploadReceipt,
    UploadReceiptFile,
    ensure_snapshot_commit,
    file_content_hash,
    find_latest_commit_touching_file,
    find_latest_inflight_tag,
    find_latest_landed_tag,
    find_latest_upload_tag,
    find_matching_submit_tag,
    init_repo,
    is_dirty,
    is_file_dirty,
    needs_upload,
    read_tag,
    read_upload_tag,
    write_failed_tag,
    write_gitignore,
    write_inflight_tag,
    write_landed_tag,
    write_submit_tag,
    write_upload_tag,
)
from .errors import (
    GitCommandError,
    GitError,
    GitReferenceError,
    NotAGitRepositoryError,
    ReceiptError,
    ReceiptMatchError,
    TagCollisionError,
)
from .repo import GitRepo, discover_repo, repo_root
from .types import GitHead, GitStatusEntry, GitTag

__all__ = [
    "GitError",
    "GitCommandError",
    "NotAGitRepositoryError",
    "GitReferenceError",
    "ReceiptError",
    "ReceiptMatchError",
    "TagCollisionError",
    "GitRepo",
    "discover_repo",
    "repo_root",
    "GitHead",
    "GitStatusEntry",
    "GitTag",
    "DEFAULT_GITIGNORE_TEXT",
    "SubmitReceipt",
    "InflightReceipt",
    "LandedReceipt",
    "FailedReceipt",
    "UploadReceiptFile",
    "UploadReceipt",
    "init_repo",
    "write_gitignore",
    "is_dirty",
    "is_file_dirty",
    "ensure_snapshot_commit",
    "write_submit_tag",
    "write_inflight_tag",
    "write_landed_tag",
    "write_failed_tag",
    "read_tag",
    "find_matching_submit_tag",
    "find_latest_inflight_tag",
    "find_latest_landed_tag",
    "write_upload_tag",
    "find_latest_upload_tag",
    "read_upload_tag",
    "file_content_hash",
    "needs_upload",
    "find_latest_commit_touching_file",
]
