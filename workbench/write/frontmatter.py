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
LOCAL_CREATE_NOTE_RUNTIME_PATH = (
    WORKBENCH_ROOT / "obsidian" / "control" / "scripts" / "create_note_runtime.js"
)
_REGISTRY_BLOCK_RE = re.compile(
    r"```(?:yaml|yml|json)\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)
_CONTENT_KIND_PREFIXES_RE = re.compile(
    r"const\s+CONTENT_KIND_PREFIXES\s*=\s*\{(.*?)\};",
    re.DOTALL,
)
_CONTENT_KIND_PREFIX_ENTRY_RE = re.compile(
    r'(?P<key>"[^"]+"|[A-Za-z0-9_-]+)\s*:\s*"(?P<value>[a-z]+)"',
)
_LOCAL_CONTENT_KIND_PREFIX_FALLBACK = {
    "image-note": "img",
    "image": "img",
    "passage": "pss",
}


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
    project: str
    default_context: str | None


def discover_writenew_vault_context(cwd: Path | None = None) -> VaultContext:
    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    vault_root = discover_registered_vault_root(working_dir)
    registry = read_vault_registry(vault_root)
    project = _resolve_project_mnemonic(registry)
    default_context = _resolve_registry_context(registry)
    return VaultContext(
        vault_root=vault_root,
        registry=registry,
        project=project,
        default_context=default_context,
    )


def load_template_scaffold(
    template_id: str,
    *,
    template_root: Path | None = None,
) -> TemplateScaffold:
    normalized_id = _normalize_name(template_id, field="template")
    candidate = (template_root or DEFAULT_TEMPLATE_ROOT).expanduser().resolve()
    path = candidate / f"{normalized_id}.md"
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
    scaffold = load_template_scaffold(template_id, template_root=template_root)
    prefix_registry = load_prefix_registry(prefix_registry_path)
    normalized_class = _resolve_effective_class(class_name, scaffold)
    content = _extract_body(source_text)
    slug_parts = _resolve_slug_parts(
        scaffold=scaffold,
        class_name=normalized_class,
        target_path=target_path,
        vault_context=vault_context,
        overrides=overrides or {},
        prefix_registry=prefix_registry,
        slug_schema_path=slug_schema_path,
    )
    metadata = _build_frontmatter_metadata(
        scaffold=scaffold,
        class_name=normalized_class,
        slug_parts=slug_parts,
        overrides=overrides or {},
        slug_schema_path=slug_schema_path,
    )
    return Document(content=content, metadata=metadata).write_text()


def load_prefix_registry(path: Path | None = None) -> dict[str, Any]:
    if path is not None:
        return _load_prefix_registry_file(path)

    payload: dict[str, Any] = {}
    resolved = _discover_default_prefix_registry_path()
    if resolved is not None:
        payload = _load_prefix_registry_file(resolved)

    local_payload = _load_local_prefix_registry()
    merged = _merge_registry_mappings(local_payload, payload)
    if merged:
        return merged

    attempted = ", ".join(str(candidate) for candidate in _default_prefix_registry_candidates())
    raise FrontmatterBuildError(
        "slug prefix registry not found and no local fallback mappings were available: "
        f"{attempted}"
    )


def resolve_slug_prefix(
    *,
    template_id: str,
    class_name: str,
    prefix_registry: dict[str, Any],
    slug_schema_path: Path | None = None,
) -> str:
    normalized_template = _normalize_name(template_id, field="template")
    normalized_class = _normalize_name(class_name, field="class")

    if normalized_template == "content":
        mapped = _lookup_mapping(prefix_registry.get("content_classes"), normalized_class)
        if mapped:
            return _validate_prefix(mapped, slug_schema_path=slug_schema_path)

    mapped = _lookup_mapping(prefix_registry.get("classes"), normalized_class)
    if mapped:
        return _validate_prefix(mapped, slug_schema_path=slug_schema_path)

    mapped = _lookup_mapping(prefix_registry.get("templates"), normalized_template)
    if mapped:
        return _validate_prefix(mapped, slug_schema_path=slug_schema_path)

    matched_prefixes: list[str] = []
    prefixes = prefix_registry.get("prefixes")
    if isinstance(prefixes, dict):
        for prefix, entry in prefixes.items():
            if _prefix_entry_matches(
                entry,
                template_id=normalized_template,
                class_name=normalized_class,
            ):
                matched_prefixes.append(str(prefix))

    if len(matched_prefixes) == 1:
        return _validate_prefix(matched_prefixes[0], slug_schema_path=slug_schema_path)
    if len(matched_prefixes) > 1:
        joined = ", ".join(sorted(matched_prefixes))
        raise FrontmatterBuildError(
            f"multiple slug prefixes match template={normalized_template} class={normalized_class}: {joined}"
        )

    raise FrontmatterBuildError(
        f"slug prefix mapping missing for template={normalized_template} class={normalized_class}"
    )


def _build_frontmatter_metadata(
    *,
    scaffold: TemplateScaffold,
    class_name: str,
    slug_parts: dict[str, str],
    overrides: dict[str, Any],
    slug_schema_path: Path | None = None,
) -> dict[str, Any]:
    metadata = dict(scaffold.metadata)

    if scaffold.template_id == "content":
        metadata["class"] = "content"
        metadata["content_kind"] = class_name
    else:
        metadata["class"] = class_name

    metadata["project"] = slug_parts["project"]
    metadata["context"] = slug_parts["context"]
    metadata["slug"] = build_slug(slug_parts, path=slug_schema_path)

    for key, value in overrides.items():
        if key in {"slug", "type", "hint", "identity"}:
            raise FrontmatterBuildError(f"override not permitted for reserved field: {key}")
        metadata[key] = value

    return metadata


def _resolve_slug_parts(
    *,
    scaffold: TemplateScaffold,
    class_name: str,
    target_path: Path,
    vault_context: VaultContext,
    overrides: dict[str, Any],
    prefix_registry: dict[str, Any],
    slug_schema_path: Path | None,
) -> dict[str, str]:
    load_slug_schema(slug_schema_path)
    prefix = resolve_slug_prefix(
        template_id=scaffold.template_id,
        class_name=class_name,
        prefix_registry=prefix_registry,
        slug_schema_path=slug_schema_path,
    )
    project = _resolve_project_override(overrides, fallback=vault_context.project)
    context = _resolve_context_override(
        overrides,
        vault_default=vault_context.default_context,
        scaffold_default=scaffold.metadata.get("context"),
        project_default=vault_context.project,
    )
    hint = _resolve_hint_override(overrides, target_path=target_path)
    parts = {
        "type": prefix,
        "project": project,
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


def _resolve_effective_class(class_name: str | None, scaffold: TemplateScaffold) -> str:
    if class_name is not None and str(class_name).strip():
        return _normalize_name(class_name, field="class")
    if scaffold.template_id == "content":
        return "passage"

    scaffold_class = scaffold.metadata.get("class")
    if isinstance(scaffold_class, str) and scaffold_class.strip():
        return _normalize_name(scaffold_class, field="class")

    return scaffold.template_id


def _resolve_project_mnemonic(registry: dict[str, Any]) -> str:
    raw = str(registry.get("project_mnemonic") or registry.get("mnemonic") or "").strip().lower()
    normalized = re.sub(r"[^a-z]+", "", raw)
    if not normalized:
        raise FrontmatterBuildError(
            "required project mnemonic is missing from the local vault registry"
        )
    field = _slug_field("project")
    if not re.fullmatch(field["pattern"], normalized):
        raise FrontmatterBuildError(
            f"vault registry project mnemonic does not satisfy slug schema: {normalized}"
        )
    return normalized


def _resolve_registry_context(registry: dict[str, Any]) -> str | None:
    candidates = (
        "context",
        "default_context",
        "slug_context",
        "project_context",
    )
    for key in candidates:
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


def _resolve_project_override(overrides: dict[str, Any], *, fallback: str) -> str:
    value = overrides.get("project")
    if value is None:
        return fallback
    normalized = re.sub(r"[^a-z]+", "", str(value).strip().lower())
    if not normalized:
        raise FrontmatterBuildError("project override normalized to an empty value")
    field = _slug_field("project")
    if not re.fullmatch(field["pattern"], normalized):
        raise FrontmatterBuildError(f"project override does not satisfy slug schema: {normalized}")
    return normalized


def _resolve_context_override(
    overrides: dict[str, Any],
    *,
    vault_default: str | None,
    scaffold_default: Any,
    project_default: str,
) -> str:
    raw = overrides.get("context")
    if raw is None:
        raw = vault_default
    if raw is None:
        raw = scaffold_default
    if raw is None or not str(raw).strip():
        raw = project_default
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


def _prefix_entry_matches(entry: Any, *, template_id: str, class_name: str) -> bool:
    if not isinstance(entry, dict):
        return False

    template_keys = ("template", "templates", "template_id", "template_ids", "entity", "entities")
    class_keys = ("class", "classes", "content_kind", "content_kinds", "kinds")

    template_constraints = _collect_constraint_values(entry, template_keys)
    class_constraints = _collect_constraint_values(entry, class_keys)

    if template_constraints and template_id not in template_constraints:
        return False
    if class_constraints and class_name not in class_constraints:
        return False

    return bool(template_constraints or class_constraints)


def _collect_constraint_values(entry: dict[str, Any], keys: tuple[str, ...]) -> set[str]:
    values: set[str] = set()
    for key in keys:
        candidate = entry.get(key)
        if isinstance(candidate, str) and candidate.strip():
            values.add(_normalize_name(candidate, field=key))
        elif isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, str) and item.strip():
                    values.add(_normalize_name(item, field=key))
    return values


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
        CONTROL_ROOT / "Registry" / "prefix_registry.yaml",
        CONTROL_ROOT / "Registry" / "prefix_registry.yml",
        CONTROL_ROOT / "Registry" / "prefix_registry.json",
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
    if resolved.suffix.lower() == ".json":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FrontmatterBuildError(f"slug prefix registry is invalid JSON: {resolved}: {exc}") from exc
    elif resolved.suffix.lower() in {".yaml", ".yml"}:
        payload = _parse_yaml_payload(raw, path=resolved)
    else:
        match = _REGISTRY_BLOCK_RE.search(raw)
        if not match:
            raise FrontmatterBuildError(
                f"slug prefix registry markdown is missing a YAML or JSON code block: {resolved}"
            )
        payload = _parse_yaml_payload(match.group(1), path=resolved)

    if not isinstance(payload, dict):
        raise FrontmatterBuildError(f"slug prefix registry must be a mapping object: {resolved}")
    return payload


def _load_local_prefix_registry() -> dict[str, Any]:
    content_classes = _load_local_content_class_prefixes()
    if not content_classes:
        return {}
    return {
        "content_classes": content_classes,
    }


def _load_local_content_class_prefixes() -> dict[str, str]:
    if LOCAL_CREATE_NOTE_RUNTIME_PATH.exists():
        text = LOCAL_CREATE_NOTE_RUNTIME_PATH.read_text(encoding="utf-8")
        match = _CONTENT_KIND_PREFIXES_RE.search(text)
        if match:
            mappings: dict[str, str] = {}
            for entry in _CONTENT_KIND_PREFIX_ENTRY_RE.finditer(match.group(1)):
                key = entry.group("key").strip('"').strip().lower()
                value = entry.group("value").strip().lower()
                if key and value:
                    mappings[key] = value
            if mappings:
                return mappings
    return dict(_LOCAL_CONTENT_KIND_PREFIX_FALLBACK)


def _merge_registry_mappings(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in set(base) | set(override):
        base_value = base.get(key)
        override_value = override.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = {**base_value, **override_value}
            continue
        if key in override:
            merged[key] = override_value
            continue
        merged[key] = base_value
    return merged
