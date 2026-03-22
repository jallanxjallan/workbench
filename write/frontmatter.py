"""Frontmatter scaffold and slug assembly for `writenew`."""

from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workbench.config.roots import CONTROL_ROOT, WORKBENCH_ROOT
from workbench.interop.document import Document
from workbench.runtime.slug_schema import build_slug, load_slug_schema, normalize_slug_component
from workbench.runtime.vaults import discover_registered_vault_root, read_vault_registry
from workbench.write.common import normalize_semantic_base

_SERDE_MODULE = importlib.import_module("YAML".lower())

DEFAULT_TEMPLATE_ROOT = WORKBENCH_ROOT / "obsidian" / "control" / "templates"
DEFAULT_PREFIX_REGISTRY_PATH = CONTROL_ROOT / "registry" / "prefix_registry.yaml"


class FrontmatterBuildError(RuntimeError):
    """Raised when `writenew` cannot assemble deterministic frontmatter."""


@dataclass(frozen=True)
class TemplateScaffold:
    template_id: str
    path: Path
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VaultContext:
    vault_root: Path
    registry: dict[str, Any]
    mnemonic: str
    default_context: str | None


def discover_writenew_vault_context(cwd: Path | None = None) -> VaultContext:
    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    vault_root = discover_registered_vault_root(working_dir)
    registry = read_vault_registry(vault_root)
    mnemonic = _resolve_registry_mnemonic(registry)
    default_context = _resolve_registry_context(registry)
    return VaultContext(
        vault_root=vault_root,
        registry=registry,
        mnemonic=mnemonic,
        default_context=default_context,
    )


def load_template_scaffold(
    template_id: str,
    *,
    template_root: Path | None = None,
) -> TemplateScaffold:
    normalized_id = _normalize_name(template_id, field="template")
    root = (template_root or DEFAULT_TEMPLATE_ROOT).expanduser().resolve()
    path = root / f"{normalized_id}.md"
    if not path.exists():
        raise FrontmatterBuildError(f"unknown template: {normalized_id}")

    parsed = Document.inspect_text(path.read_text(encoding="utf-8"))
    if parsed.error:
        raise FrontmatterBuildError(f"template has invalid frontmatter: {path}: {parsed.error}")
    if not parsed.has_frontmatter or not isinstance(parsed.metadata, dict):
        raise FrontmatterBuildError(f"template is missing frontmatter scaffold: {path}")

    return TemplateScaffold(
        template_id=normalized_id,
        path=path,
        metadata=dict(parsed.metadata),
    )


def build_writenew_document(
    *,
    source_text: str,
    template_id: str,
    class_name: str | None,
    target_path: Path,
    vault_context: VaultContext,
    overrides: dict[str, Any] | None = None,
    template_root: Path | None = None,
    prefix_registry_path: Path | None = None,
    slug_schema_path: Path | None = None,
) -> str:
    overrides = overrides or {}

    scaffold = load_template_scaffold(template_id, template_root=template_root)
    prefix_registry = load_prefix_registry(prefix_registry_path)
    kind = _resolve_effective_kind(class_name, scaffold)

    content = _extract_body(source_text)
    slug_parts = _resolve_slug_parts(
        scaffold=scaffold,
        kind=kind,
        target_path=target_path,
        vault_context=vault_context,
        overrides=overrides,
        prefix_registry=prefix_registry,
        slug_schema_path=slug_schema_path,
    )
    metadata = _build_frontmatter_metadata(
        scaffold=scaffold,
        kind=kind,
        slug_parts=slug_parts,
        overrides=overrides,
        slug_schema_path=slug_schema_path,
    )
    return Document(content=content, metadata=metadata).write_text()


def load_prefix_registry(path: Path | None = None) -> dict[str, Any]:
    resolved = (path or _discover_default_prefix_registry_path())
    if resolved is None:
        attempted = ", ".join(str(candidate) for candidate in _default_prefix_registry_candidates())
        raise FrontmatterBuildError(f"slug prefix registry not found: {attempted}")
    return _load_prefix_registry_file(resolved)


def resolve_slug_prefix(
    *,
    template_id: str,
    kind: str,
    prefix_registry: dict[str, Any],
    slug_schema_path: Path | None = None,
) -> str:
    normalized_template = _normalize_name(template_id, field="template")
    normalized_kind = _normalize_name(kind, field="kind")

    if normalized_template == "content":
        mapped = _lookup_mapping(prefix_registry.get("content_kinds"), normalized_kind)
        if mapped:
            return _validate_prefix(mapped, slug_schema_path=slug_schema_path)

        mapped = _lookup_mapping(prefix_registry.get("kinds"), normalized_kind)
        if mapped:
            return _validate_prefix(mapped, slug_schema_path=slug_schema_path)

    mapped = _lookup_mapping(prefix_registry.get("templates"), normalized_template)
    if mapped:
        return _validate_prefix(mapped, slug_schema_path=slug_schema_path)

    raise FrontmatterBuildError(
        f"slug prefix mapping missing for template={normalized_template} kind={normalized_kind}"
    )


def _build_frontmatter_metadata(
    *,
    scaffold: TemplateScaffold,
    kind: str,
    slug_parts: dict[str, str],
    overrides: dict[str, Any],
    slug_schema_path: Path | None = None,
) -> dict[str, Any]:
    metadata = dict(scaffold.metadata)

    metadata.setdefault("kind", kind)
    metadata["slug"] = build_slug(slug_parts, path=slug_schema_path)

    origin = _extract_origin(overrides)
    if origin is not None and "origin" not in metadata:
        metadata["origin"] = origin

    for key, value in overrides.items():
        if key in {
            "slug",
            "type",
            "hint",
            "identity",
            "seq",
            "class",
            "kind",
            "origin",
            "input_record",
        }:
            continue

        # Retain any non-empty value already present in the template scaffold.
        if key in metadata and _has_value(metadata[key]):
            continue

        metadata[key] = value

    return metadata


def _resolve_slug_parts(
    *,
    scaffold: TemplateScaffold,
    kind: str,
    target_path: Path,
    vault_context: VaultContext,
    overrides: dict[str, Any],
    prefix_registry: dict[str, Any],
    slug_schema_path: Path | None,
) -> dict[str, str]:
    load_slug_schema(slug_schema_path)

    prefix = resolve_slug_prefix(
        template_id=scaffold.template_id,
        kind=kind,
        prefix_registry=prefix_registry,
        slug_schema_path=slug_schema_path,
    )

    if scaffold.template_id == "content":
        context = _resolve_context_override(
            {},
            vault_default=vault_context.mnemonic,
            scaffold_default=None,
            mnemonic_default=vault_context.mnemonic,
        )
    else:
        context = _resolve_context_override(
            overrides,
            vault_default=vault_context.default_context,
            scaffold_default=scaffold.metadata.get("context"),
            mnemonic_default=vault_context.mnemonic,
        )

    hint = _resolve_hint_override(overrides, target_path=target_path)

    parts = {
        "type": prefix,
        "context": context,
        "hint": hint,
    }

    seq = overrides.get("seq")
    if seq is not None and str(seq).strip():
        parts["seq"] = str(seq).strip()

    return parts


def _extract_body(source_text: str) -> str:
    parsed = Document.inspect_text(source_text)
    if parsed.error:
        raise FrontmatterBuildError(f"input markdown has invalid frontmatter: {parsed.error}")
    return parsed.body if parsed.has_frontmatter else source_text


def _resolve_effective_kind(class_name: str | None, scaffold: TemplateScaffold) -> str:
    if class_name is not None and str(class_name).strip():
        return _normalize_name(class_name, field="kind")

    scaffold_kind = scaffold.metadata.get("kind")
    if isinstance(scaffold_kind, str) and scaffold_kind.strip():
        return _normalize_name(scaffold_kind, field="kind")

    scaffold_class = scaffold.metadata.get("class")
    if isinstance(scaffold_class, str) and scaffold_class.strip():
        return _normalize_name(scaffold_class, field="kind")

    if scaffold.template_id == "content":
        return "passage"

    return scaffold.template_id


def _resolve_registry_mnemonic(registry: dict[str, Any]) -> str:
    raw = str(registry.get("project_mnemonic") or registry.get("mnemonic") or "").strip().lower()
    normalized = re.sub(r"[^a-z]+", "", raw)
    if not normalized:
        raise FrontmatterBuildError(
            "required vault mnemonic is missing from the local vault registry"
        )
    field = _slug_field("context")
    if not re.fullmatch(field["pattern"], normalized):
        raise FrontmatterBuildError(
            f"vault registry mnemonic does not satisfy slug schema context field: {normalized}"
        )
    return normalized


def _resolve_registry_context(registry: dict[str, Any]) -> str | None:
    for key in ("context", "default_context", "slug_context", "project_context"):
        value = registry.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        normalized = normalize_slug_component(value)
        field = _slug_field("context")
        if not re.fullmatch(field["pattern"], normalized):
            raise FrontmatterBuildError(
                f"vault registry context does not satisfy slug schema: {normalized}"
            )
        return normalized
    return None


def _resolve_context_override(
    overrides: dict[str, Any],
    *,
    vault_default: str | None,
    scaffold_default: Any,
    mnemonic_default: str,
) -> str:
    raw = overrides.get("context")
    if raw is None:
        raw = vault_default
    if raw is None:
        raw = scaffold_default
    if raw is None or not str(raw).strip():
        raw = mnemonic_default

    normalized = normalize_slug_component(str(raw))
    field = _slug_field("context")
    if not re.fullmatch(field["pattern"], normalized):
        raise FrontmatterBuildError(f"context does not satisfy slug schema: {normalized}")
    return normalized


def _resolve_hint_override(overrides: dict[str, Any], *, target_path: Path) -> str:
    raw = overrides.get("hint")
    if raw is None:
        return normalize_semantic_base(target_path.name)

    normalized = normalize_slug_component(str(raw))
    field = _slug_field("hint")
    if not re.fullmatch(field["pattern"], normalized):
        raise FrontmatterBuildError(f"hint override does not satisfy slug schema: {normalized}")
    return normalized


def _extract_origin(overrides: dict[str, Any]) -> Any | None:
    if "origin" in overrides and _has_value(overrides["origin"]):
        return overrides["origin"]

    input_record = overrides.get("input_record")
    if isinstance(input_record, dict):
        if "origin" in input_record and _has_value(input_record["origin"]):
            return input_record["origin"]

    return None


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _validate_prefix(prefix: str, *, slug_schema_path: Path | None = None) -> str:
    normalized = _normalize_name(prefix, field="prefix")
    field = _slug_field("type", path=slug_schema_path)
    if not re.fullmatch(field["pattern"], normalized):
        raise FrontmatterBuildError(f"slug prefix does not satisfy slug schema: {normalized}")
    return normalized


def _slug_field(name: str, *, path: Path | None = None) -> dict[str, Any]:
    schema = load_slug_schema(path)
    fields = schema.get("slug", {}).get("fields", [])
    for field in fields:
        if str(field.get("name") or "").strip() == name:
            return field
    raise FrontmatterBuildError(f"slug schema field is missing: {name}")


def _lookup_mapping(candidate: Any, key: str) -> str | None:
    if not isinstance(candidate, dict):
        return None
    value = candidate.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _parse_yaml_payload(text: str, *, path: Path) -> Any:
    try:
        return _SERDE_MODULE.safe_load(text)
    except Exception as exc:  # noqa: BLE001
        raise FrontmatterBuildError(f"could not parse registry payload: {path}: {exc}") from exc


def _normalize_name(value: str, *, field: str) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        raise FrontmatterBuildError(f"{field} must be a non-empty string")
    return normalized


def _default_prefix_registry_candidates() -> tuple[Path, ...]:
    return (
        DEFAULT_PREFIX_REGISTRY_PATH,
        CONTROL_ROOT / "registry" / "prefix_registry.yml",
        CONTROL_ROOT / "registry" / "prefix_registry.json",
    )


def _discover_default_prefix_registry_path() -> Path | None:
    for candidate in _default_prefix_registry_candidates():
        resolved = candidate.expanduser().resolve()
        if resolved.exists():
            return resolved
    return None


def _load_prefix_registry_file(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise FrontmatterBuildError(f"slug prefix registry not found: {resolved}")

    raw = resolved.read_text(encoding="utf-8")
    suffix = resolved.suffix.lower()

    if suffix == ".json":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FrontmatterBuildError(
                f"slug prefix registry is invalid JSON: {resolved}: {exc}"
            ) from exc
    elif suffix in {".yaml", ".yml"}:
        payload = _parse_yaml_payload(raw, path=resolved)
    else:
        raise FrontmatterBuildError(
            f"unsupported slug prefix registry format: {resolved} (expected .yaml/.yml/.json)"
        )

    if not isinstance(payload, dict):
        raise FrontmatterBuildError(f"slug prefix registry must be a mapping object: {resolved}")

    return payload
