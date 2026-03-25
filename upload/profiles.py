from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import yaml

import repo
from repo.repo import _run_git
from transport import dumps_record


PROFILES_ROOT = Path("/home/jeremy/Workspace/Control/profiles").expanduser().resolve()
PROFILE_TAG_GLOB = "successful_upload/profiles/*"
YAML_SUFFIXES = {".yaml", ".yml"}


class UploadProfilesError(RuntimeError):
    """Raised when upload-profiles cannot compile profile records."""



def discover_profile_files(root: Path = PROFILES_ROOT) -> list[Path]:
    profiles_root = Path(root).expanduser().resolve()
    if not profiles_root.is_dir():
        raise UploadProfilesError(f"profiles root does not exist: {profiles_root}")

    discovered: set[Path] = set()
    for raw_path in _tracked_paths(profiles_root):
        path = Path(raw_path).expanduser().resolve()
        if is_profile_file(path):
            discovered.add(path)
    for raw_path in _untracked_paths(repo.discover_repo(profiles_root), profiles_root):
        if is_profile_file(raw_path):
            discovered.add(raw_path)
    return sorted(discovered)



def load_profile_yaml(path: Path) -> dict[str, Any]:
    file_path = Path(path).expanduser().resolve()

    try:
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UploadProfilesError(f"unable to read profile YAML: {file_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise UploadProfilesError(f"invalid YAML in {file_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise UploadProfilesError(f"profile must be a YAML object: {file_path}")

    return payload



def profile_slug(profile_yaml: dict[str, Any], path: Path) -> str:
    slug = profile_yaml.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise UploadProfilesError(f"profile is missing slug: {path}")
    return slug.strip()



def is_profile_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in YAML_SUFFIXES



def compile_profile_record(path: Path) -> dict[str, Any]:
    file_path = Path(path).expanduser().resolve()
    payload = load_profile_yaml(file_path)
    slug = profile_slug(payload, file_path)

    return {
        "content": payload,
        "input_record": {
            "slug": slug,
            "filename_hint": file_path.name,
            "origin": {
                "source_type": "file",
                "source_path": str(file_path),
                "record_kind": "profile",
            },
        },
    }



def discover_candidate_paths(root: Path = PROFILES_ROOT) -> list[Path]:
    profiles_root = Path(root).expanduser().resolve()
    git_repo = repo.discover_repo(profiles_root)
    last_tag = _find_latest_tag(repo_root=git_repo.root, pattern=PROFILE_TAG_GLOB)

    if last_tag is None:
        return discover_profile_files(profiles_root)

    changed_paths: set[Path] = set()
    tag_commit = _tag_commit(repo_root=git_repo.root, tag_name=last_tag)
    head_commit = git_repo.head().oid
    if tag_commit != head_commit:
        changed_paths.update(_paths_within_scope(git_repo.changed_paths_between(tag_commit, head_commit), profiles_root))

    changed_paths.update(_dirty_paths(git_repo, profiles_root, include_untracked=False))
    changed_paths.update(_untracked_paths(git_repo, profiles_root))

    return sorted(path for path in changed_paths if is_profile_file(path))



def iter_upload_profile_records(root: Path = PROFILES_ROOT) -> list[str]:
    candidate_paths = discover_candidate_paths(root=root)
    if not candidate_paths:
        return []

    records: list[str] = []
    seen_slugs: dict[str, Path] = {}

    for path in candidate_paths:
        record = compile_profile_record(path)
        slug = record["input_record"]["slug"]

        if slug in seen_slugs:
            other = seen_slugs[slug]
            raise UploadProfilesError(f"duplicate profile slug {slug}: {other} and {path}")

        seen_slugs[slug] = path
        records.append(f"{dumps_record(record)}\n")

    return records



def upload_profiles(root: Path = PROFILES_ROOT) -> int:
    for record in iter_upload_profile_records(root=root):
        sys.stdout.write(record)
    return 0



def main() -> int:
    try:
        return upload_profiles()
    except Exception as exc:
        print(f"upload-profiles: {exc}", file=sys.stderr)
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
        raise UploadProfilesError(f"tag does not resolve to a commit: {tag_name}")
    return commit



def _prefix_from_glob(pattern: str) -> str:
    if not pattern.endswith("*") or "*" in pattern[:-1]:
        raise UploadProfilesError(f"unsupported tag glob: {pattern}")
    return pattern[:-1]



def _tracked_paths(scope: Path) -> list[Path]:
    profiles_root = Path(scope).expanduser().resolve()
    git_repo = repo.discover_repo(profiles_root)
    proc = _run_git(["ls-files", "--", str(git_repo.relpath(profiles_root))], cwd=git_repo.root)
    return [
        (git_repo.root / line.strip()).resolve()
        for line in proc.stdout.splitlines()
        if line.strip()
    ]



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
