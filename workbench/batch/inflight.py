"""Inflight tag helpers for batch confirmation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from workbench.batch.repository import BatchRepositoryError, load_batch_manifest
from workbench.runtime.git_repo import GitRepoError, create_annotated_tag, get_repo_root, git, tag_exists


class InflightTagError(RuntimeError):
    """Raised when inflight tag confirmation cannot complete."""


def _tag_message(*, batch_id: str, file_count: int) -> str:
    payload = {
        "batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "file_count": file_count,
    }
    return json.dumps(payload, indent=2) + "\n"


def confirm_inflight(
    *,
    batch_id: str,
    repo: Path | str = ".",
    push: bool = False,
    remote: str = "origin",
) -> str:
    normalized_batch_id = str(batch_id).strip()
    if not normalized_batch_id:
        raise InflightTagError("batch id is required")

    try:
        repo_root = get_repo_root(repo)
        manifest = load_batch_manifest(normalized_batch_id, repo=repo_root)
        inflight_tag = f"inflight/{normalized_batch_id}"
        if tag_exists(repo_root, inflight_tag):
            raise InflightTagError(f"inflight tag already exists: {inflight_tag}")

        create_annotated_tag(
            repo_root,
            inflight_tag,
            message=_tag_message(batch_id=normalized_batch_id, file_count=len(manifest.order)),
        )
        if push:
            git(repo_root, "push", remote, f"refs/tags/{inflight_tag}")
    except (BatchRepositoryError, GitRepoError) as exc:
        raise InflightTagError(str(exc)) from exc

    return inflight_tag


__all__ = ["InflightTagError", "confirm_inflight"]
