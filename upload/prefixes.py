from __future__ import annotations

from dataclasses import dataclass


class PrefixMapError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrefixSpec:
    kind: str
    target: str


PREFIX_SPECS: dict[str, PrefixSpec] = {
    "pss": PrefixSpec("prompt", "document"),
    "img": PrefixSpec("prompt", "document"),
    "scn": PrefixSpec("prompt", "document"),
    "gbl": PrefixSpec("instruction", "document"),
    "cxt": PrefixSpec("instruction", "document"),
    "spc": PrefixSpec("instruction", "document"),
    "bat": PrefixSpec("batch", "machine"),
    "pln": PrefixSpec("plan", "machine"),
    "web": PrefixSpec("prompt", "machine"),
}


def prefix_for_slug(slug: str) -> str:
    prefix = slug.split(".", 1)[0].strip()
    if not prefix:
        raise PrefixMapError(f"slug is missing prefix: {slug!r}")
    return prefix


def spec_for_slug(slug: str) -> PrefixSpec:
    prefix = prefix_for_slug(slug)
    try:
        return PREFIX_SPECS[prefix]
    except KeyError as exc:
        raise PrefixMapError(f"unsupported slug prefix: {prefix}") from exc


def kind_for_slug(slug: str) -> str:
    return spec_for_slug(slug).kind


def target_for_slug(slug: str) -> str:
    return spec_for_slug(slug).target


def require_target(slug: str, *, target: str) -> PrefixSpec:
    spec = spec_for_slug(slug)
    if spec.target != target:
        raise PrefixMapError(
            f"slug target mismatch for {slug}: expected {target!r}, got {spec.target!r}"
        )
    return spec