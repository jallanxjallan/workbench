"""Centralized Git repository inspection and mutation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib
import subprocess
from pathlib import Path

from workbench.config.roots import WORKBENCH_CONTROL_ROOT
from workbench.runtime.git_commit_message import render_commit_message


_YAML_MODULE = importlib.import_module("yaml".upper().lower())


class GitRepoError(RuntimeError):
    pass


_CONTROL_COMMIT_TEMPLATE_REGISTRY = (
    WORKBENCH_CONTROL_ROOT / "Registry" / "git_commit_messages.yaml"
)


def _resolve_default_template_registry() -> Path:
    return _CONTROL_COMMIT_TEMPLATE_REGISTRY


DEFAULT_COMMIT_TEMPLATE_REGISTRY = _resolve_default_template_registry()


def _run_git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or (exc.stdout or "").strip()
        if not detail:
            detail = f"git {' '.join(args)} failed"
        raise GitRepoError(detail) from exc
    return proc.stdout.strip()


def git(repo: Path, *args: str) -> str:
    repo_path = Path(repo).expanduser().resolve()
    return _run_git(repo_path, *args)


def get_repo_root(path: Path | str = ".") -> Path:
    candidate = Path(path).expanduser().resolve()
    try:
        result = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or (exc.stdout or "").strip() or "not a git repo"
        raise GitRepoError(detail) from exc
    root = result.stdout.strip()
    if not root:
        raise GitRepoError(f"unable to detect git repo root from {candidate}")
    return Path(root).resolve()


def get_head_commit(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")


def get_short_commit(repo: Path) -> str:
    return git(repo, "rev-parse", "--short", "HEAD")


def get_current_branch(repo: Path) -> str:
    return git(repo, "branch", "--show-current")


def is_repo_clean(repo: Path) -> bool:
    return git(repo, "status", "--porcelain").strip() == ""


def _parse_status_paths(status_output: str) -> list[str]:
    names: list[str] = []
    for line in status_output.splitlines():
        if not line:
            continue
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if path_text.startswith('"') and path_text.endswith('"') and len(path_text) >= 2:
            path_text = path_text[1:-1]
        if path_text:
            names.append(path_text)
    return names


def get_dirty_files(repo: Path) -> list[Path]:
    repo_root = get_repo_root(repo)
    status = git(repo_root, "status", "--porcelain")
    return [(repo_root / name).resolve() for name in _parse_status_paths(status)]


def get_untracked_files(repo: Path) -> list[Path]:
    repo_root = get_repo_root(repo)
    output = git(repo_root, "ls-files", "--others", "--exclude-standard")
    return [
        (repo_root / line).resolve()
        for line in output.splitlines()
        if line.strip()
    ]


def get_changed_files(repo: Path, since_commit: str) -> list[Path]:
    repo_root = get_repo_root(repo)
    output = git(repo_root, "diff", "--name-only", since_commit)
    return [
        (repo_root / line).resolve()
        for line in output.splitlines()
        if line.strip()
    ]


def get_tracked_files(repo: Path) -> list[Path]:
    repo_root = get_repo_root(repo)
    output = git(repo_root, "ls-files")
    return [
        (repo_root / line).resolve()
        for line in output.splitlines()
        if line.strip()
    ]


def tag_exists(repo: Path, tag_name: str) -> bool:
    repo_root = get_repo_root(repo)
    return git(repo_root, "tag", "-l", tag_name).strip() == tag_name


def read_annotated_tag_message(repo: Path, tag_name: str) -> str:
    repo_root = get_repo_root(repo)
    ref = f"refs/tags/{tag_name}"
    object_type = git(repo_root, "cat-file", "-t", ref).strip()
    if object_type != "tag":
        raise GitRepoError(f"tag is not annotated: {tag_name}")
    message = git(repo_root, "tag", "-l", tag_name, "--format=%(contents)")
    if message.strip() == "":
        raise GitRepoError(f"tag annotation unreadable: {tag_name}")
    return message


def create_annotated_tag(
    repo: Path,
    tag_name: str,
    *,
    message: str,
    target: str | None = None,
) -> None:
    repo_root = get_repo_root(repo)
    if tag_exists(repo_root, tag_name):
        raise GitRepoError(f"tag already exists: {tag_name}")

    args = ["tag", "-a", tag_name]
    if target:
        args.append(target)
    args.extend(["-m", message])
    git(repo_root, *args)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_templates(path: Path | None = None) -> dict[str, str]:
    registry_path = Path(path or DEFAULT_COMMIT_TEMPLATE_REGISTRY).expanduser().resolve()
    if not registry_path.is_file():
        raise GitRepoError(f"commit template registry not found: {registry_path}")

    try:
        loader = getattr(_YAML_MODULE, "safe" "_load")
        loaded = loader(registry_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise GitRepoError(f"invalid commit template registry {registry_path}: {exc}") from exc

    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise GitRepoError(f"commit template registry must be a mapping: {registry_path}")

    templates: dict[str, str] = {}
    for key, value in loaded.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise GitRepoError(
                f"commit template entries must be string->string: {registry_path}"
            )
        templates[key.strip().upper()] = value
    return templates


def _render_message(
    *,
    commit_type: str,
    batch_slug: str,
    file_count: int | None = None,
) -> str:
    templates = _load_templates()
    key = commit_type.strip().upper()
    template = templates.get(key)
    if template is None:
        raise GitRepoError(f"missing commit template for type '{key}'")

    fields: dict[str, object] = {"batch_slug": batch_slug}
    if file_count is not None:
        fields["file_count"] = file_count
    try:
        message = render_commit_message(template, **fields)
    except ValueError as exc:
        raise GitRepoError(str(exc)) from exc
    if message == "":
        raise GitRepoError(f"rendered commit message is empty for type '{key}'")
    return message


def _repo_internal_state_path(repo: Path, marker: str) -> Path:
    git_dir = git(repo, "rev-parse", "--git-dir")
    git_dir_path = Path(git_dir)
    if not git_dir_path.is_absolute():
        git_dir_path = (repo / git_dir_path).resolve()
    return git_dir_path / marker


def assert_repo_safe(repo: Path, *, require_clean: bool = True) -> None:
    repo_root = get_repo_root(repo)
    if require_clean and not is_repo_clean(repo_root):
        raise GitRepoError(f"repository is dirty: {repo_root}")

    for marker in ("MERGE_HEAD", "rebase-apply", "rebase-merge"):
        if _repo_internal_state_path(repo_root, marker).exists():
            raise GitRepoError(f"repository has in-progress git operation: {marker}")


def _resolve_file_for_add(repo: Path, file_path: Path) -> str:
    candidate = file_path if file_path.is_absolute() else (repo / file_path)
    resolved = candidate.expanduser().resolve()
    if not resolved.exists():
        raise GitRepoError(f"file does not exist: {resolved}")
    try:
        rel = resolved.relative_to(repo)
    except ValueError as exc:
        raise GitRepoError(f"file is outside repository: {resolved}") from exc
    return rel.as_posix()


def _staged_file_count(repo: Path) -> int:
    status = git(repo, "status", "--porcelain")
    return len([line for line in status.splitlines() if line.strip()])


def commit_new_files(repo: Path, files: list[Path], batch_slug: str) -> str:
    repo_root = get_repo_root(repo)
    if not files:
        raise GitRepoError("no files provided")
    stage_paths = [_resolve_file_for_add(repo_root, Path(path)) for path in files]

    assert_repo_safe(repo_root, require_clean=False)
    git(repo_root, "add", *stage_paths)
    message = _render_message(
        commit_type="INIT",
        batch_slug=batch_slug,
        file_count=len(stage_paths),
    )
    git(repo_root, "commit", "-m", message)
    return get_head_commit(repo_root)


def commit_batch(repo: Path, batch_slug: str, commit_type: str) -> str:
    repo_root = get_repo_root(repo)
    assert_repo_safe(repo_root, require_clean=False)
    git(repo_root, "add", "-A")

    changed_count = _staged_file_count(repo_root)
    if changed_count == 0:
        raise GitRepoError("no changes to commit")

    message = _render_message(
        commit_type=commit_type,
        batch_slug=batch_slug,
        file_count=changed_count,
    )
    git(repo_root, "commit", "-m", message)
    return get_head_commit(repo_root)


def create_batch_tag(repo: Path, batch_slug: str, commit: str) -> None:
    repo_root = get_repo_root(repo)
    git(repo_root, "tag", "-a", f"batch/{batch_slug}", commit, "-m", f"batch {batch_slug}")


__all__ = [
    "DEFAULT_COMMIT_TEMPLATE_REGISTRY",
    "GitRepoError",
    "assert_repo_safe",
    "commit_batch",
    "commit_new_files",
    "create_batch_tag",
    "create_annotated_tag",
    "get_changed_files",
    "get_current_branch",
    "get_dirty_files",
    "get_head_commit",
    "get_repo_root",
    "get_short_commit",
    "get_tracked_files",
    "get_untracked_files",
    "git",
    "is_repo_clean",
    "read_annotated_tag_message",
    "tag_exists",
    "utc_timestamp",
]
