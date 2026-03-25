from __future__ import annotations

import os
from pathlib import Path
import shutil
from subprocess import CompletedProcess, run
from typing import Iterable, Sequence

from .errors import (
    GitCommandError,
    GitError,
    GitReferenceError,
    NotAGitRepositoryError,
)
from .types import GitHead, GitStatusEntry, GitTag


_GIT_EXECUTABLE = shutil.which("git") or "git"


def _normalize_input_path(path: Path) -> Path:
    """Return an absolute resolved version of the given path."""
    return path.expanduser().resolve()


def _cwd_for(path: Path) -> Path:
    """
    Return an appropriate cwd for Git discovery.

    If `path` is a directory, use it directly. If it is a file path, use its
    parent. This allows callers to pass either kind of path naturally.
    """
    normalized = _normalize_input_path(path)
    return normalized if normalized.is_dir() else normalized.parent


def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> CompletedProcess[str]:
    """
    Run a Git command and return the completed process.

    Parameters
    ----------
    argv:
        Command arguments excluding the 'git' executable itself.
    cwd:
        Working directory for the command.
    check:
        If True, raise GitCommandError on non-zero exit.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed process with decoded text streams.

    Raises
    ------
    GitCommandError
        If the command exits non-zero and `check` is True.
    """
    full_argv = [_GIT_EXECUTABLE, *argv]
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "Workbench")
    env.setdefault("GIT_AUTHOR_EMAIL", "workbench@example.invalid")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
    proc = run(
        full_argv,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        raise GitCommandError(
            argv=full_argv,
            cwd=cwd,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    return proc


class GitRepo:
    """
    Typed Git repository/worktree interface.

    Instances of this class represent a specific Git worktree discovered from a
    file or directory path. Most callers should obtain an instance using
    `GitRepo.discover(...)`.

    Notes
    -----
    - This class is CLI-backed.
    - Returned paths are absolute, normalized Paths.
    - Methods that accept paths require those paths to lie inside this repo's
      worktree.
    """

    def __init__(self, root: Path) -> None:
        self._root = _normalize_input_path(root)

    @classmethod
    def discover(cls, path: Path) -> "GitRepo":
        """
        Discover the Git worktree containing `path`.

        Parameters
        ----------
        path:
            File or directory path located inside a Git worktree.

        Returns
        -------
        GitRepo
            Repository object rooted at the containing worktree.

        Raises
        ------
        NotAGitRepositoryError
            If no Git worktree can be discovered from the path.
        """
        cwd = _cwd_for(path)
        proc = _run_git(
            ["rev-parse", "--show-toplevel"],
            cwd=cwd,
            check=False,
        )
        if proc.returncode != 0:
            raise NotAGitRepositoryError(
                f"path is not inside a git worktree: {path}"
            )
        root = Path(proc.stdout.strip()).expanduser().resolve()
        return cls(root)

    @property
    def root(self) -> Path:
        """Return the absolute path to the repository worktree root."""
        return self._root

    def git_dir(self) -> Path:
        """
        Return the absolute path to the active .git directory.

        In linked worktrees this may not be `<root>/.git`.
        """
        proc = _run_git(
            ["rev-parse", "--absolute-git-dir"],
            cwd=self._root,
        )
        return Path(proc.stdout.strip()).expanduser().resolve()

    def is_inside_worktree(self) -> bool:
        """Return True if this object still points at a valid worktree."""
        proc = _run_git(
            ["rev-parse", "--is-inside-work-tree"],
            cwd=self._root,
            check=False,
        )
        return proc.returncode == 0 and proc.stdout.strip() == "true"

    def _normalize_repo_path(self, path: Path) -> Path:
        """
        Normalize a path and verify that it is inside this repo root.

        Returns the absolute normalized path.

        Raises
        ------
        ValueError
            If the path lies outside the repository root.
        """
        normalized = _normalize_input_path(path)
        try:
            normalized.relative_to(self._root)
        except ValueError as exc:
            raise ValueError(
                f"path is outside repository root {self._root}: {normalized}"
            ) from exc
        return normalized

    def relpath(self, path: Path) -> Path:
        """
        Return the repository-relative form of `path`.

        Parameters
        ----------
        path:
            Absolute or relative file/directory path inside this repo.

        Returns
        -------
        pathlib.Path
            Path relative to repo root.
        """
        normalized = self._normalize_repo_path(path)
        return normalized.relative_to(self._root)

    def head(self) -> GitHead:
        """
        Return structured information about HEAD.

        Returns
        -------
        GitHead

        Raises
        ------
        GitReferenceError
            If HEAD cannot be resolved, for example in an unborn repository.
        """
        oid_proc = _run_git(
            ["rev-parse", "HEAD"],
            cwd=self._root,
            check=False,
        )
        if oid_proc.returncode != 0:
            raise GitReferenceError("HEAD cannot be resolved")

        short_proc = _run_git(
            ["rev-parse", "--short", "HEAD"],
            cwd=self._root,
        )
        branch_proc = _run_git(
            ["symbolic-ref", "--quiet", "--short", "HEAD"],
            cwd=self._root,
            check=False,
        )
        branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else None

        return GitHead(
            oid=oid_proc.stdout.strip(),
            short_oid=short_proc.stdout.strip(),
            branch=branch,
        )

    def current_branch(self) -> str | None:
        """
        Return the current branch name, or None if HEAD is detached.
        """
        return self.head().branch

    def rev_parse(self, rev: str) -> str:
        """
        Resolve a revision expression to a full object ID.

        Parameters
        ----------
        rev:
            Any revision expression accepted by `git rev-parse`.

        Returns
        -------
        str
            Full resolved object ID.

        Raises
        ------
        GitReferenceError
            If the revision cannot be resolved.
        """
        proc = _run_git(
            ["rev-parse", rev],
            cwd=self._root,
            check=False,
        )
        if proc.returncode != 0:
            raise GitReferenceError(f"cannot resolve revision: {rev}")
        return proc.stdout.strip()

    def tag_names_at_head(self) -> list[str]:
        """
        Return all tag names pointing directly at HEAD.

        Includes both annotated and lightweight tags.
        """
        proc = _run_git(
            ["tag", "--points-at", "HEAD"],
            cwd=self._root,
        )
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    def annotated_tag_names_at_head(self) -> list[str]:
        """
        Return annotated tag names pointing at HEAD.

        This filters tag names at HEAD by checking whether each ref is itself a
        tag object rather than a direct lightweight pointer to a commit.
        """
        names = self.tag_names_at_head()
        return [name for name in names if self.is_annotated_tag(name)]

    def is_annotated_tag(self, tag_name: str) -> bool:
        """
        Return True if the named tag is annotated.

        A lightweight tag resolves as a 'commit' object at the tag ref itself.
        An annotated tag resolves as a 'tag' object.
        """
        proc = _run_git(
            ["cat-file", "-t", f"refs/tags/{tag_name}"],
            cwd=self._root,
            check=False,
        )
        if proc.returncode != 0:
            raise GitReferenceError(f"tag does not exist: {tag_name}")
        return proc.stdout.strip() == "tag"

    def tag(self, tag_name: str) -> GitTag:
        """
        Return metadata for a tag.

        Parameters
        ----------
        tag_name:
            Short tag name.

        Returns
        -------
        GitTag

        Raises
        ------
        GitReferenceError
            If the tag does not exist.
        """
        type_proc = _run_git(
            ["cat-file", "-t", f"refs/tags/{tag_name}"],
            cwd=self._root,
            check=False,
        )
        if type_proc.returncode != 0:
            raise GitReferenceError(f"tag does not exist: {tag_name}")

        target_proc = _run_git(
            ["rev-list", "-n", "1", tag_name],
            cwd=self._root,
            check=False,
        )
        if target_proc.returncode != 0 or not target_proc.stdout.strip():
            raise GitReferenceError(f"cannot resolve tag target: {tag_name}")

        return GitTag(
            name=tag_name,
            object_type=type_proc.stdout.strip(),
            target_oid=target_proc.stdout.strip(),
        )

    def annotated_tags_at_head(self) -> list[GitTag]:
        """
        Return full metadata for annotated tags pointing at HEAD.
        """
        return [self.tag(name) for name in self.annotated_tag_names_at_head()]

    def status(self, *, include_ignored: bool = False) -> list[GitStatusEntry]:
        """
        Return parsed repository status entries.

        Parameters
        ----------
        include_ignored:
            If True, include ignored files using `--ignored`.

        Returns
        -------
        list[GitStatusEntry]
            Parsed porcelain entries for the whole worktree.
        """
        argv = ["status", "--porcelain=v1"]
        if include_ignored:
            argv.append("--ignored")
        proc = _run_git(argv, cwd=self._root)
        return self._parse_status_porcelain(proc.stdout.splitlines())

    def status_for_paths(
        self,
        paths: Iterable[Path],
        *,
        include_untracked: bool = True,
    ) -> list[GitStatusEntry]:
        """
        Return parsed status entries limited to the given paths.

        Parameters
        ----------
        paths:
            File or directory paths inside this repo.
        include_untracked:
            Whether untracked files under the given paths should be reported.

        Returns
        -------
        list[GitStatusEntry]
            Parsed porcelain entries scoped to the supplied paths.
        """
        relpaths = [str(self.relpath(path)) for path in paths]
        argv = ["status", "--porcelain=v1"]
        if not include_untracked:
            argv.append("--untracked-files=no")
        argv.extend(["--", *relpaths])
        proc = _run_git(argv, cwd=self._root)
        return self._parse_status_porcelain(proc.stdout.splitlines())

    def is_tracked(self, path: Path) -> bool:
        """
        Return True if `path` is tracked by Git.

        This is a path-level check, not a status inspection.
        """
        rel = str(self.relpath(path))
        proc = _run_git(
            ["ls-files", "--error-unmatch", "--", rel],
            cwd=self._root,
            check=False,
        )
        return proc.returncode == 0

    def is_dirty(
        self,
        path: Path | None = None,
        *,
        include_untracked: bool = True,
    ) -> bool:
        """
        Return True if the repo or path has uncommitted changes.

        Parameters
        ----------
        path:
            If provided, restrict the check to this path. Otherwise check the
            entire repository.
        include_untracked:
            Whether untracked files count as dirty.

        Notes
        -----
        This method uses `git status --porcelain=v1` rather than `git diff`
        because Workbench generally cares about operator-visible working state,
        including staged changes and optionally untracked files.
        """
        if path is None:
            entries = self.status(include_ignored=False)
        else:
            entries = self.status_for_paths(
                [path],
                include_untracked=include_untracked,
            )

        for entry in entries:
            if entry.is_ignored:
                continue
            if not include_untracked and entry.is_untracked:
                continue
            if entry.is_dirty:
                return True
        return False

    def changed_paths(
        self,
        *,
        include_untracked: bool = True,
    ) -> list[Path]:
        """
        Return absolute paths with uncommitted changes.

        Parameters
        ----------
        include_untracked:
            Whether untracked files should be included.

        Returns
        -------
        list[pathlib.Path]
            Absolute normalized changed paths.
        """
        entries = self.status(include_ignored=False)
        changed: list[Path] = []
        for entry in entries:
            if entry.is_ignored:
                continue
            if not include_untracked and entry.is_untracked:
                continue
            if entry.is_dirty:
                changed.append(entry.path)
        return changed

    def has_uncommitted_changes(self, paths: Iterable[Path]) -> bool:
        """
        Return True if any of the supplied paths are dirty.

        Untracked files count as dirty.
        """
        return any(entry.is_dirty for entry in self.status_for_paths(paths))

    def file_changed_between(self, path: Path, older_rev: str, newer_rev: str) -> bool:
        """
        Return True if `path` differs between two revisions.

        Parameters
        ----------
        path:
            File path inside the repository.
        older_rev:
            Older revision expression.
        newer_rev:
            Newer revision expression.
        """
        rel = str(self.relpath(path))
        proc = _run_git(
            ["diff", "--quiet", older_rev, newer_rev, "--", rel],
            cwd=self._root,
            check=False,
        )
        if proc.returncode == 0:
            return False
        if proc.returncode == 1:
            return True
        raise GitCommandError(
            argv=("git", "diff", "--quiet", older_rev, newer_rev, "--", rel),
            cwd=self._root,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    def changed_paths_between(self, older_rev: str, newer_rev: str) -> list[Path]:
        """
        Return paths changed between two revisions.

        Returns absolute normalized paths.
        """
        proc = _run_git(
            ["diff", "--name-only", older_rev, newer_rev],
            cwd=self._root,
        )
        paths: list[Path] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            paths.append((self._root / line).resolve())
        return paths

    def _parse_status_porcelain(
        self,
        lines: Iterable[str],
    ) -> list[GitStatusEntry]:
        """
        Parse `git status --porcelain=v1` output.

        Supported forms include ordinary entries and rename/copy entries of the
        form `XY old -> new`.
        """
        entries: list[GitStatusEntry] = []

        for raw in lines:
            if not raw:
                continue

            if len(raw) < 4:
                raise GitError(f"unexpected git status porcelain line: {raw!r}")

            x = raw[0]
            y = raw[1]
            payload = raw[3:]

            original_path: Path | None = None
            display_path: str

            if " -> " in payload:
                old_s, new_s = payload.split(" -> ", 1)
                original_path = (self._root / old_s).resolve()
                display_path = new_s
            else:
                display_path = payload

            path = (self._root / display_path).resolve()

            entries.append(
                GitStatusEntry(
                    path=path,
                    index_status=x,
                    worktree_status=y,
                    original_path=original_path,
                )
            )

        return entries


def discover_repo(path: Path) -> GitRepo:
    """
    Discover and return the GitRepo containing `path`.

    This is a convenience wrapper around `GitRepo.discover`.
    """
    return GitRepo.discover(path)


def repo_root(path: Path) -> Path:
    """
    Return the Git worktree root containing `path`.

    This is a convenience helper for callers that only need the root and not
    a full GitRepo instance.
    """
    return GitRepo.discover(path).root
