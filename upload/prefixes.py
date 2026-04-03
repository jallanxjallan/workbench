from __future__ import annotations

from dataclasses import dataclass


class PrefixMapError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrefixSpec:
    record_type: str
    target: str
    pandoc_defaults: str | None = None


PREFIX_SPECS: dict[str, PrefixSpec] = {
    "pss": PrefixSpec("prompt", "document", "upload_prompts"),
    "img": PrefixSpec("prompt", "document", "upload_prompts"),
    "scn": PrefixSpec("prompt", "document", "upload_prompts"),
    "gbl": PrefixSpec("instruction", "document", "upload_instructions"),
    "cxt": PrefixSpec("instruction", "document", "upload_instructions"),
    "spc": PrefixSpec("instruction", "document", "upload_instructions"),
    "bat": PrefixSpec("batch", "machine"),
    "pkg": PrefixSpec("package", "machine"),
    "web": PrefixSpec("prompt", "machine", "upload_prompts"),
}

DOCUMENT_PREFIXES: tuple[str, ...] = tuple(
    prefix for prefix, spec in PREFIX_SPECS.items() if spec.target == "document"
)

MACHINE_PREFIXES: tuple[str, ...] = tuple(
    prefix for prefix, spec in PREFIX_SPECS.items() if spec.target == "machine"
)


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



def record_type_for_slug(slug: str) -> str:
    return spec_for_slug(slug).record_type



def target_for_slug(slug: str) -> str:
    return spec_for_slug(slug).target



def pandoc_defaults_for_slug(slug: str) -> str:
    defaults = spec_for_slug(slug).pandoc_defaults
    if not defaults:
        raise PrefixMapError(f"no pandoc defaults configured for slug: {slug}")
    return defaults



def require_target(slug: str, *, target: str) -> PrefixSpec:
    spec = spec_for_slug(slug)
    if spec.target != target:
        raise PrefixMapError(
            f"slug target mismatch for {slug}: expected {target!r}, got {spec.target!r}"
        )
    return spec
