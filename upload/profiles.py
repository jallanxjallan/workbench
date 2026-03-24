from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import yaml

from workbench.git import (
    find_repo_root,
    find_latest_tag,
    list_paths_changed_since_tag,
    list_tracked_paths,
    list_untracked_paths,
)
from workbench.records import dump_record


PROFILES_ROOT = Path("/home/jeremy/Workspace/Control/profiles").expanduser().resolve()
PROFILE_TAG_GLOB = "successful_upload/profiles/*"
YAML_SUFFIXES = {".yaml", ".yml"}


class UploadProfilesError(RuntimeError):
    """Raised when upload-profiles cannot compile profile records."""


def discover_profile_files(root: Path = PROFILES_ROOT) -> list[Path]:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise UploadProfilesError(f"profiles root does not exist: {root}")

    discovered: set[Path] = set()
    for pattern in ("*.yaml", "*.yml"):
        for path in root.rglob(pattern):
            if path.is_file():
                discovered.add(path.resolve())

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
    repo_root = find_repo_root(profiles_root)
    last_tag = find_latest_tag(repo_root=repo_root, pattern=PROFILE_TAG_GLOB)

    if last_tag is None:
        candidates = list_tracked_paths(repo_root=repo_root, scope=profiles_root)
    else:
        candidates = list_paths_changed_since_tag(
            repo_root=repo_root,
            tag=last_tag,
            scope=profiles_root,
            include_staged=True,
            include_unstaged=True,
        )

    candidates.extend(
        list_untracked_paths(repo_root=repo_root, scope=profiles_root)
    )

    resolved: list[Path] = []
    seen: set[Path] = set()

    for raw_path in candidates:
        path = Path(raw_path).expanduser().resolve()
        if path in seen:
            continue
        seen.add(path)

        if is_profile_file(path):
            resolved.append(path)

    return sorted(resolved)


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
        records.append(dump_record(record))

    return records


def main() -> int:
    try:
        records = iter_upload_profile_records()
    except Exception as exc:
        print(f"upload-profiles: {exc}", file=sys.stderr)
        return 1

    for record in records:
        sys.stdout.write(record)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())