from __future__ import annotations

from pathlib import Path
import sys

from workbench.git import (
    find_repo_root,
    find_latest_tag,
    list_paths_changed_since_tag,
    list_untracked_paths,
)
from workbench.records import dump_record
from workbench.records.package import compile_package_record


PACKAGE_TAG_GLOB = "successful_upload/packages/*"


class UploadPackageError(RuntimeError):
    """Raised when upload-package cannot compile a package record."""


def package_changed_since_last_upload(package_path: Path, repo_root: Path) -> bool:
    last_tag = find_latest_tag(repo_root=repo_root, pattern=PACKAGE_TAG_GLOB)

    if last_tag is None:
        return True

    changed_paths = {
        Path(raw_path).expanduser().resolve()
        for raw_path in list_paths_changed_since_tag(
            repo_root=repo_root,
            tag=last_tag,
            scope=package_path.parent,
            include_staged=True,
            include_unstaged=True,
        )
    }

    changed_paths.update(
        Path(raw_path).expanduser().resolve()
        for raw_path in list_untracked_paths(
            repo_root=repo_root,
            scope=package_path.parent,
        )
    )

    return package_path in changed_paths


def iter_upload_package_records(package_path: Path) -> list[str]:
    path = Path(package_path).expanduser().resolve()
    if not path.is_file():
        raise UploadPackageError(f"package file does not exist: {path}")

    repo_root = find_repo_root(path.parent)

    if not package_changed_since_last_upload(path, repo_root):
        return []

    record = compile_package_record(path)
    return [dump_record(record)]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: wkb upload-package <package.json>", file=sys.stderr)
        return 2

    try:
        records = iter_upload_package_records(Path(sys.argv[1]))
    except Exception as exc:
        print(f"upload-package: {exc}", file=sys.stderr)
        return 1

    for record in records:
        sys.stdout.write(record)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())