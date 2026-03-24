from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitTag:
    """
    Tag metadata for a tag pointing at a commit.

    Attributes
    ----------
    name:
        Short tag name, for example 'v1.2.0' or 'review/accepted'.
    object_type:
        Git object type returned by `git cat-file -t refs/tags/<name>`.
        Usually 'tag' for annotated tags or 'commit' for lightweight tags.
    target_oid:
        The commit object ID the tag ultimately refers to.
    """

    name: str
    object_type: str
    target_oid: str


@dataclass(frozen=True)
class GitStatusEntry:
    """
    One parsed line from `git status --porcelain=v1`.

    Attributes
    ----------
    path:
        Absolute normalized path to the affected file.
    index_status:
        Index status code (first porcelain column), such as 'M', 'A', 'D', '?'.
    worktree_status:
        Worktree status code (second porcelain column), such as 'M', 'D', '?'.
    original_path:
        For renames/copies, the previous path. Otherwise None.
    """

    path: Path
    index_status: str
    worktree_status: str
    original_path: Path | None = None

    @property
    def is_untracked(self) -> bool:
        """Return True if this entry represents an untracked path."""
        return self.index_status == "?" and self.worktree_status == "?"

    @property
    def is_ignored(self) -> bool:
        """Return True if this entry represents an ignored path."""
        return self.index_status == "!" and self.worktree_status == "!"

    @property
    def is_staged(self) -> bool:
        """Return True if the index column indicates a staged change."""
        return self.index_status not in {" ", "?", "!"}

    @property
    def is_unstaged(self) -> bool:
        """Return True if the worktree column indicates an unstaged change."""
        return self.worktree_status not in {" ", "?", "!"}

    @property
    def is_dirty(self) -> bool:
        """
        Return True if the entry represents a meaningful change.

        Ignored entries are not considered dirty. Untracked entries are.
        """
        return not self.is_ignored and (
            self.is_untracked or self.is_staged or self.is_unstaged
        )


@dataclass(frozen=True)
class GitHead:
    """
    Information about HEAD.

    Attributes
    ----------
    oid:
        Full commit object ID for HEAD.
    short_oid:
        Shortened commit object ID.
    branch:
        Current branch name, or None if HEAD is detached.
    """

    oid: str
    short_oid: str
    branch: str | None
