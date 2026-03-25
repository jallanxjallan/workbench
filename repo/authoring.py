from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any, Callable, Sequence, TypeVar

from .errors import (
    GitCommandError,
    GitError,
    GitReferenceError,
    ReceiptError,
    ReceiptMatchError,
    TagCollisionError,
)
from .gitignore import template as DEFAULT_GITIGNORE_TEXT
from .repo import GitRepo, _normalize_input_path, _run_git


T = TypeVar("T")


@dataclass(frozen=True)
class SubmitReceipt:
    receipt_id: str
    created_at: str
    commit: str
    record_count: int
    slugs: list[str]
    paths_rel: list[str]
    vault_root: str | None = None
    vault_id: str | None = None
    tag_name: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "submit",
            "receipt_id": self.receipt_id,
            "created_at": self.created_at,
            "commit": self.commit,
            "record_count": self.record_count,
            "slugs": list(self.slugs),
            "paths_rel": list(self.paths_rel),
        }
        if self.vault_root is not None:
            payload["vault_root"] = self.vault_root
        if self.vault_id is not None:
            payload["vault_id"] = self.vault_id
        return payload

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        tag_name: str | None = None,
    ) -> "SubmitReceipt":
        _require_type(payload, "submit")
        return cls(
            receipt_id=_require_str(payload, "receipt_id"),
            created_at=_require_str(payload, "created_at"),
            commit=_require_str(payload, "commit"),
            record_count=_require_int(payload, "record_count"),
            slugs=_require_str_list(payload, "slugs"),
            paths_rel=_require_str_list(payload, "paths_rel"),
            vault_root=_optional_str(payload, "vault_root"),
            vault_id=_optional_str(payload, "vault_id"),
            tag_name=tag_name,
        )


@dataclass(frozen=True)
class InflightReceipt:
    created_at: str
    slug: str
    path_rel: str
    commit: str
    content_hash: str
    vault_root: str | None = None
    vault_id: str | None = None
    tag_name: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "inflight",
            "created_at": self.created_at,
            "slug": self.slug,
            "path_rel": self.path_rel,
            "commit": self.commit,
            "content_hash": self.content_hash,
        }
        if self.vault_root is not None:
            payload["vault_root"] = self.vault_root
        if self.vault_id is not None:
            payload["vault_id"] = self.vault_id
        return payload

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        tag_name: str | None = None,
    ) -> "InflightReceipt":
        _require_type(payload, "inflight")
        return cls(
            created_at=_require_str(payload, "created_at"),
            slug=_require_str(payload, "slug"),
            path_rel=_require_str(payload, "path_rel"),
            commit=_require_str(payload, "commit"),
            content_hash=_require_str(payload, "content_hash"),
            vault_root=_optional_str(payload, "vault_root"),
            vault_id=_optional_str(payload, "vault_id"),
            tag_name=tag_name,
        )


@dataclass(frozen=True)
class LandedReceipt:
    created_at: str
    slug: str
    path_rel: str
    commit: str
    content_hash: str
    source_batch_id: str
    vault_root: str | None = None
    vault_id: str | None = None
    tag_name: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "landed",
            "created_at": self.created_at,
            "slug": self.slug,
            "path_rel": self.path_rel,
            "commit": self.commit,
            "content_hash": self.content_hash,
            "source_batch_id": self.source_batch_id,
        }
        if self.vault_root is not None:
            payload["vault_root"] = self.vault_root
        if self.vault_id is not None:
            payload["vault_id"] = self.vault_id
        return payload

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        tag_name: str | None = None,
    ) -> "LandedReceipt":
        _require_type(payload, "landed")
        return cls(
            created_at=_require_str(payload, "created_at"),
            slug=_require_str(payload, "slug"),
            path_rel=_require_str(payload, "path_rel"),
            commit=_require_str(payload, "commit"),
            content_hash=_require_str(payload, "content_hash"),
            source_batch_id=_require_str(payload, "source_batch_id"),
            vault_root=_optional_str(payload, "vault_root"),
            vault_id=_optional_str(payload, "vault_id"),
            tag_name=tag_name,
        )


@dataclass(frozen=True)
class FailedReceipt:
    receipt_id: str
    created_at: str
    commit: str
    error: str
    record_count: int
    slugs: list[str]
    paths_rel: list[str]
    vault_root: str | None = None
    vault_id: str | None = None
    tag_name: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "failed",
            "receipt_id": self.receipt_id,
            "created_at": self.created_at,
            "commit": self.commit,
            "error": self.error,
            "record_count": self.record_count,
            "slugs": list(self.slugs),
            "paths_rel": list(self.paths_rel),
        }
        if self.vault_root is not None:
            payload["vault_root"] = self.vault_root
        if self.vault_id is not None:
            payload["vault_id"] = self.vault_id
        return payload

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        tag_name: str | None = None,
    ) -> "FailedReceipt":
        _require_type(payload, "failed")
        return cls(
            receipt_id=_require_str(payload, "receipt_id"),
            created_at=_require_str(payload, "created_at"),
            commit=_require_str(payload, "commit"),
            error=_require_str(payload, "error"),
            record_count=_require_int(payload, "record_count"),
            slugs=_require_str_list(payload, "slugs"),
            paths_rel=_require_str_list(payload, "paths_rel"),
            vault_root=_optional_str(payload, "vault_root"),
            vault_id=_optional_str(payload, "vault_id"),
            tag_name=tag_name,
        )


@dataclass(frozen=True)
class UploadReceiptFile:
    slug: str
    path_rel: str
    content_hash: str

    def to_payload(self) -> dict[str, str]:
        return {
            "slug": self.slug,
            "path_rel": self.path_rel,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "UploadReceiptFile":
        return cls(
            slug=_require_str(payload, "slug"),
            path_rel=_require_str(payload, "path_rel"),
            content_hash=_require_str(payload, "content_hash"),
        )


@dataclass(frozen=True)
class UploadReceipt:
    receipt_id: str
    created_at: str
    commit: str
    family: str
    record_count: int
    files: list[UploadReceiptFile]
    vault_root: str | None = None
    vault_id: str | None = None
    batch_id: str | None = None
    upload_target: str | None = None
    tag_name: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "upload",
            "receipt_id": self.receipt_id,
            "created_at": self.created_at,
            "commit": self.commit,
            "family": self.family,
            "record_count": self.record_count,
            "files": [item.to_payload() for item in self.files],
        }
        if self.vault_root is not None:
            payload["vault_root"] = self.vault_root
        if self.vault_id is not None:
            payload["vault_id"] = self.vault_id
        if self.batch_id is not None:
            payload["batch_id"] = self.batch_id
        if self.upload_target is not None:
            payload["upload_target"] = self.upload_target
        return payload

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        tag_name: str | None = None,
    ) -> "UploadReceipt":
        _require_type(payload, "upload")
        raw_files = payload.get("files")
        if not isinstance(raw_files, list):
            raise ReceiptError("upload receipt field 'files' must be a list")
        files = []
        for raw_file in raw_files:
            if not isinstance(raw_file, dict):
                raise ReceiptError("upload receipt files must be JSON objects")
            files.append(UploadReceiptFile.from_payload(raw_file))
        return cls(
            receipt_id=_require_str(payload, "receipt_id"),
            created_at=_require_str(payload, "created_at"),
            commit=_require_str(payload, "commit"),
            family=_require_str(payload, "family"),
            record_count=_require_int(payload, "record_count"),
            files=files,
            vault_root=_optional_str(payload, "vault_root"),
            vault_id=_optional_str(payload, "vault_id"),
            batch_id=_optional_str(payload, "batch_id"),
            upload_target=_optional_str(payload, "upload_target"),
            tag_name=tag_name,
        )


def init_repo(vault_root: Path, gitignore_text: str) -> None:
    root = _normalize_input_path(vault_root)
    if not root.exists() or not root.is_dir():
        raise GitError(f"vault root does not exist: {root}")
    if not (root / ".git").exists():
        _run_git(["init"], cwd=root)
    write_gitignore(root, gitignore_text)


def write_gitignore(vault_root: Path, content: str, *, replace: bool = False) -> None:
    root = _normalize_input_path(vault_root)
    if not root.exists() or not root.is_dir():
        raise GitError(f"vault root does not exist: {root}")
    target = root / ".gitignore"
    if target.exists():
        if target.is_dir():
            raise GitError(f".gitignore path is a directory: {target}")
        if not replace:
            return
    target.write_text(content, encoding="utf-8")


def is_dirty(repo_root: Path) -> bool:
    git_repo = GitRepo.discover(repo_root)
    return git_repo.is_dirty(include_untracked=True)


def is_file_dirty(repo_root: Path, path: Path) -> bool:
    root = _normalize_repo_root(repo_root)
    git_repo = GitRepo.discover(root)
    return git_repo.is_dirty(_normalize_path_in_repo(root, path), include_untracked=True)


def ensure_snapshot_commit(repo_root: Path, message: str) -> str:
    root = _normalize_repo_root(repo_root)
    if is_dirty(root):
        _run_git(["add", "-A"], cwd=root)
        _run_git(["commit", "-m", message], cwd=root)
        return _require_head_commit(root)

    head = _head_commit(root)
    if head is not None:
        return head

    _run_git(["commit", "--allow-empty", "-m", message], cwd=root)
    return _require_head_commit(root)


def write_submit_tag(repo_root: Path, receipt: SubmitReceipt) -> str:
    payload = receipt.to_payload()
    return _write_annotated_tag_json(
        repo_root,
        _submit_tag_name(receipt.receipt_id),
        _require_str(payload, "commit"),
        payload,
    )


def write_inflight_tag(repo_root: Path, receipt: InflightReceipt) -> str:
    payload = receipt.to_payload()
    return _write_annotated_tag_json(
        repo_root,
        _state_tag_name("inflight", receipt.slug, receipt.created_at),
        _require_str(payload, "commit"),
        payload,
    )


def write_landed_tag(repo_root: Path, receipt: LandedReceipt) -> str:
    payload = receipt.to_payload()
    return _write_annotated_tag_json(
        repo_root,
        _state_tag_name("landed", receipt.slug, receipt.created_at),
        _require_str(payload, "commit"),
        payload,
    )


def write_failed_tag(repo_root: Path, receipt: FailedReceipt) -> str:
    payload = receipt.to_payload()
    return _write_annotated_tag_json(
        repo_root,
        _failed_tag_name(receipt.receipt_id),
        _require_str(payload, "commit"),
        payload,
    )


def read_tag(repo_root: Path, tag_name: str) -> dict[str, Any]:
    root = _normalize_repo_root(repo_root)
    return _read_tag_json(root, tag_name)


def find_matching_submit_tag(
    repo_root: Path,
    paths_rel: list[str],
    slugs: list[str] | None = None,
) -> SubmitReceipt:
    root = _normalize_repo_root(repo_root)
    expected_paths = _normalize_relpaths(root, paths_rel)
    matches: list[SubmitReceipt] = []
    for tag_name in _list_tags_by_prefix(root, "submit/"):
        receipt = SubmitReceipt.from_payload(_read_tag_json(root, tag_name), tag_name=tag_name)
        if receipt.paths_rel != expected_paths:
            continue
        if slugs is not None and receipt.slugs != slugs:
            continue
        matches.append(receipt)
    if len(matches) != 1:
        raise ReceiptMatchError(
            f"expected exactly one matching submit receipt, found {len(matches)}"
        )
    return matches[0]


def find_latest_inflight_tag(repo_root: Path, slug: str) -> InflightReceipt | None:
    root = _normalize_repo_root(repo_root)
    return _find_latest_typed_tag(
        root,
        f"inflight/{_sanitize_ref_component(slug)}/",
        InflightReceipt.from_payload,
    )


def find_latest_landed_tag(repo_root: Path, slug: str) -> LandedReceipt | None:
    root = _normalize_repo_root(repo_root)
    return _find_latest_typed_tag(
        root,
        f"landed/{_sanitize_ref_component(slug)}/",
        LandedReceipt.from_payload,
    )


def write_upload_tag(repo_root: Path, receipt: UploadReceipt) -> str:
    payload = receipt.to_payload()
    return _write_annotated_tag_json(
        repo_root,
        _upload_tag_name(receipt.family, receipt.receipt_id),
        _require_str(payload, "commit"),
        payload,
    )


def find_latest_upload_tag(repo_root: Path, family: str | None = None) -> UploadReceipt | None:
    root = _normalize_repo_root(repo_root)
    prefix = "upload/" if family is None else f"upload/{_sanitize_ref_component(family)}/"
    return _find_latest_typed_tag(root, prefix, UploadReceipt.from_payload)


def read_upload_tag(repo_root: Path, tag_name: str) -> UploadReceipt:
    root = _normalize_repo_root(repo_root)
    return UploadReceipt.from_payload(_read_tag_json(root, tag_name), tag_name=tag_name)


def file_content_hash(path: Path) -> str:
    normalized = _normalize_input_path(path)
    return f"sha256:{sha256(normalized.read_bytes()).hexdigest()}"


def needs_upload(repo_root: Path, slug: str, path: Path, *, family: str) -> bool:
    root = _normalize_repo_root(repo_root)
    normalized_path = _normalize_path_in_repo(root, path)
    if is_file_dirty(root, normalized_path):
        return True

    path_rel = _normalize_relpath(root, normalized_path)
    receipt = _find_latest_upload_receipt_for_file(root, slug, path_rel, family)
    if receipt is None:
        return True

    latest_commit = find_latest_commit_touching_file(root, normalized_path)
    if latest_commit is None:
        return True
    if latest_commit == receipt.commit:
        return False
    return _is_ancestor(root, receipt.commit, latest_commit)


def find_latest_commit_touching_file(repo_root: Path, path: Path) -> str | None:
    root = _normalize_repo_root(repo_root)
    relpath = _normalize_relpath(root, path)
    proc = _run_git(
        ["log", "-n", "1", "--format=%H", "--", relpath],
        cwd=root,
        check=False,
    )
    if proc.returncode != 0:
        raise GitCommandError(
            argv=("git", "log", "-n", "1", "--format=%H", "--", relpath),
            cwd=root,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    commit = proc.stdout.strip()
    return commit or None


def _normalize_repo_root(repo_root: Path) -> Path:
    return GitRepo.discover(repo_root).root


def _normalize_path_in_repo(repo_root: Path, path: Path) -> Path:
    candidate = Path(path).expanduser()
    normalized = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
    try:
        normalized.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(
            f"path is outside repository root {repo_root}: {normalized}"
        ) from exc
    return normalized


def _normalize_relpath(repo_root: Path, path: Path | str) -> str:
    normalized = _normalize_path_in_repo(repo_root, Path(path))
    return normalized.relative_to(repo_root).as_posix()


def _normalize_relpaths(repo_root: Path, paths_rel: Sequence[str]) -> list[str]:
    return [_normalize_relpath(repo_root, item) for item in paths_rel]


def _head_commit(repo_root: Path) -> str | None:
    proc = _run_git(["rev-parse", "HEAD"], cwd=repo_root, check=False)
    commit = proc.stdout.strip()
    if proc.returncode != 0 or not commit:
        return None
    return commit


def _require_head_commit(repo_root: Path) -> str:
    commit = _head_commit(repo_root)
    if commit is None:
        raise GitReferenceError(f"HEAD cannot be resolved for repo: {repo_root}")
    return commit


def _submit_tag_name(receipt_id: str) -> str:
    return f"submit/{_sanitize_ref_component(receipt_id)}"


def _failed_tag_name(receipt_id: str) -> str:
    return f"failed/{_sanitize_ref_component(receipt_id)}"


def _state_tag_name(prefix: str, slug: str, created_at: str) -> str:
    return (
        f"{prefix}/{_sanitize_ref_component(slug)}/"
        f"{_sanitize_ref_component(created_at)}"
    )


def _upload_tag_name(family: str, receipt_id: str) -> str:
    return (
        f"upload/{_sanitize_ref_component(family)}/"
        f"{_sanitize_ref_component(receipt_id)}"
    )


def _sanitize_ref_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._/-]+", "-", value).strip("-")
    if not cleaned:
        raise ReceiptError("tag component cannot be empty")
    if cleaned.startswith("/") or cleaned.endswith("/") or "//" in cleaned:
        raise ReceiptError(f"invalid tag component: {value!r}")
    return cleaned


def _read_tag_json(repo_root: Path, tag_name: str) -> dict[str, Any]:
    if not _tag_exists(repo_root, tag_name):
        raise GitReferenceError(f"tag does not exist: {tag_name}")
    proc = _run_git(
        ["for-each-ref", "--format=%(contents)", f"refs/tags/{tag_name}"],
        cwd=repo_root,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ReceiptError(f"tag {tag_name} does not contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ReceiptError(f"tag {tag_name} JSON payload must be an object")
    return payload


def _write_annotated_tag_json(
    repo_root: Path,
    tag_name: str,
    commit: str,
    payload: dict[str, Any],
) -> str:
    root = _normalize_repo_root(repo_root)
    if _tag_exists(root, tag_name):
        raise TagCollisionError(f"tag already exists: {tag_name}")
    message = json.dumps(payload, indent=2, sort_keys=True)
    _run_git(["tag", "-a", tag_name, commit, "-m", message], cwd=root)
    return tag_name


def _tag_exists(repo_root: Path, tag_name: str) -> bool:
    proc = _run_git(
        ["rev-parse", "--verify", "--quiet", f"refs/tags/{tag_name}"],
        cwd=repo_root,
        check=False,
    )
    return proc.returncode == 0


def _list_tags_by_prefix(repo_root: Path, prefix: str) -> list[str]:
    proc = _run_git(
        [
            "for-each-ref",
            "--sort=-taggerdate",
            "--format=%(refname:strip=2)",
            f"refs/tags/{prefix}",
        ],
        cwd=repo_root,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _find_latest_typed_tag(
    repo_root: Path,
    prefix: str,
    parser: Callable[..., T],
) -> T | None:
    for tag_name in _list_tags_by_prefix(repo_root, prefix):
        return parser(_read_tag_json(repo_root, tag_name), tag_name=tag_name)
    return None


def _find_latest_upload_receipt_for_file(
    repo_root: Path,
    slug: str,
    path_rel: str,
    family: str,
) -> UploadReceipt | None:
    prefix = f"upload/{_sanitize_ref_component(family)}/"
    for tag_name in _list_tags_by_prefix(repo_root, prefix):
        receipt = UploadReceipt.from_payload(_read_tag_json(repo_root, tag_name), tag_name=tag_name)
        for item in receipt.files:
            if item.slug == slug or item.path_rel == path_rel:
                return receipt
    return None


def _is_ancestor(repo_root: Path, older: str, newer: str) -> bool:
    proc = _run_git(
        ["merge-base", "--is-ancestor", older, newer],
        cwd=repo_root,
        check=False,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    raise GitCommandError(
        argv=("git", "merge-base", "--is-ancestor", older, newer),
        cwd=repo_root,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _require_type(payload: dict[str, Any], expected: str) -> None:
    actual = payload.get("type")
    if actual != expected:
        raise ReceiptError(f"expected receipt type '{expected}', found {actual!r}")


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ReceiptError(f"receipt field '{key}' must be a non-empty string")
    return value


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ReceiptError(f"receipt field '{key}' must be a string when present")
    return value


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ReceiptError(f"receipt field '{key}' must be an integer")
    return value


def _require_str_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ReceiptError(f"receipt field '{key}' must be a list of strings")
    return list(value)
