"""Shared upload tag-name contracts."""

from __future__ import annotations


SUCCESSFUL_UPLOAD_TAG_NAMESPACE = "successful_upload"


def successful_upload_tag_prefix(family: str) -> str:
    return f"{SUCCESSFUL_UPLOAD_TAG_NAMESPACE}/{family}/"


def successful_upload_tag_glob(family: str) -> str:
    return f"{successful_upload_tag_prefix(family)}*"


def successful_upload_tag(family: str, name: str) -> str:
    return f"{successful_upload_tag_prefix(family)}{name}"
