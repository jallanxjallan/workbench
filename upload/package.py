from __future__ import annotations

from pathlib import Path
import sys

import repo
from repo.repo import _run_git
from transport import dumps_record, load_json_object


PACKAGE_TAG_GLOB = "successful_upload/packages/*"


class UploadPackageError(RuntimeError):
    """Raised when upload-package cannot compile a package record."""



def load_package_json(path: Path) -> dict[str, object]:
    file_path = Path(path).expanduser().resolve()
    try:
        return load_json_object(file_path)
    except ValueError as exc:
        raise UploadPackageError(str(exc)) from exc



def compile_package_record(path: Path) -> dict[str, object]:
    file_path = Path(path).expanduser().resolve()
    payload = load_package_json(file_path)
    slug = payload.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise UploadPackageError(f"package is missing slug: {file_path}")

    return {
        "content": payload,
        "input_record": {
            "slug": slug.strip(),
            "filename_hint": file_path.name,
            "origin": {
                "source_type": "file",
                "filepath": str(file_path),
                "record_kind": "package",
            },
        },
    }



def package_changed_since_last_upload(package_path: Path, repo_root: Path) -> bool:
    path = Path(package_path).expanduser().resolve()
    git_repo = repo.discover_repo(repo_root)
    last_tag = _find_latest_tag(repo_root=git_repo.root, pattern=PACKAGE_TAG_GLOB)

    if last_tag is None:
        return True

    changed_paths: set[Path] = set()
    tag_commit = _tag_commit(repo_root=git_repo.root, tag_name=last_tag)
    head_commit = git_repo.head().oid
    if tag_commit != head_commit:
        changed_paths.update(_paths_within_scope(git_repo.changed_paths_between(tag_commit, head_commit), path.parent))

    changed_paths.update(_dirty_paths(git_repo, path.parent, include_untracked=False))
    changed_paths.update(_untracked_paths(git_repo, path.parent))
    return path in changed_paths



def iter_upload_package_records(package_path: Path) -> list[str]:
    path = Path(package_path).expanduser().resolve()
    if not path.is_file():
        raise UploadPackageError(f"package file does not exist: {path}")

    repo_root = repo.discover_repo(path.parent).root
    if not package_changed_since_last_upload(path, repo_root):
        return []

    record = compile_package_record(path)
    return [f"{dumps_record(record)}\n"]



def upload_package(package_path: Path) -> int:
    for record in iter_upload_package_records(package_path):
        sys.stdout.write(record)
    return 0



def main() -> int:
    if len(sys.argv) != 2:
        print("usage: wkb upload-package <package.json>", file=sys.stderr)
        return 2

    try:
        return upload_package(Path(sys.argv[1]))
    except Exception as exc:
        print(f"upload-package: {exc}", file=sys.stderr)
        return 1



def _find_latest_tag(*, repo_root: Path, pattern: str) -> str | None:
    prefix = _prefix_from_glob(pattern)
    proc = _run_git(
        [
            "for-each-ref",
            "--sort=-taggerdate",
            "--format=%(refname:strip=2)",
            f"refs/tags/{prefix}",
        ],
        cwd=repo_root,
    )
    for line in proc.stdout.splitlines():
        tag_name = line.strip()
        if tag_name:
            return tag_name
    return None



def _tag_commit(*, repo_root: Path, tag_name: str) -> str:
    proc = _run_git(["rev-list", "-n", "1", tag_name], cwd=repo_root)
    commit = proc.stdout.strip()
    if not commit:
        raise UploadPackageError(f"tag does not resolve to a commit: {tag_name}")
    return commit



def _prefix_from_glob(pattern: str) -> str:
    if not pattern.endswith("*") or "*" in pattern[:-1]:
        raise UploadPackageError(f"unsupported tag glob: {pattern}")
    return pattern[:-1]



def _paths_within_scope(paths: list[Path], scope: Path) -> set[Path]:
    resolved_scope = Path(scope).expanduser().resolve()
    selected: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        try:
            path.relative_to(resolved_scope)
        except ValueError:
            continue
        selected.add(path)
    return selected



def _dirty_paths(git_repo: repo.GitRepo, scope: Path, *, include_untracked: bool) -> set[Path]:
    selected: set[Path] = set()
    for entry in git_repo.status_for_paths([scope], include_untracked=include_untracked):
        if entry.is_ignored or not entry.is_dirty:
            continue
        if not include_untracked and entry.is_untracked:
            continue
        try:
            entry.path.relative_to(scope)
        except ValueError:
            continue
        selected.add(entry.path)
    return selected



def _untracked_paths(git_repo: repo.GitRepo, scope: Path) -> set[Path]:
    selected: set[Path] = set()
    for entry in git_repo.status_for_paths([scope], include_untracked=True):
        if entry.is_ignored or not entry.is_untracked:
            continue
        try:
            entry.path.relative_to(scope)
        except ValueError:
            continue
        selected.add(entry.path)
    return selected


if __name__ == "__main__":
    raise SystemExit(main())
