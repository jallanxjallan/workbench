from __future__ import annotations

from pathlib import Path
from typing import Sequence


class GitError(RuntimeError):
    """Base class for Git-related errors raised by this module."""


class GitCommandError(GitError):
    """
    Raised when a Git subprocess exits non-zero.

    Attributes
    ----------
    argv:
        The full command that was executed.
    cwd:
        Working directory used for the command.
    returncode:
        Process exit code.
    stdout:
        Decoded standard output.
    stderr:
        Decoded standard error.
    """

    def __init__(
        self,
        *,
        argv: Sequence[str],
        cwd: Path | None,
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        self.argv = tuple(argv)
        self.cwd = cwd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

        message = (
            f"git command failed with exit code {returncode}: {' '.join(argv)}"
        )
        if cwd is not None:
            message += f" (cwd={cwd})"
        if stderr.strip():
            message += f" :: {stderr.strip()}"
        super().__init__(message)


class NotAGitRepositoryError(GitError):
    """
    Raised when repository discovery fails for a path.

    This usually means the given path is not inside a Git worktree.
    """


class GitReferenceError(GitError):
    """
    Raised when a requested Git reference cannot be resolved.

    Examples include:
    - HEAD in a repo with no commits
    - an invalid revision string
    - a missing tag or commit-ish
    """


class ReceiptError(GitError):
    """Raised when a repo receipt cannot be parsed or validated."""


class ReceiptMatchError(ReceiptError):
    """Raised when receipt lookup is ambiguous or yields no match."""


class TagCollisionError(ReceiptError):
    """Raised when a receipt tag already exists and overwrite is disallowed."""
