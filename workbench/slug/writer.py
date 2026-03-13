"""Slug ensure/write operations for markdown files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from workbench.interop.document import Document
from workbench.lib.rg import RipgrepError, rg_search
from workbench.lib.regex_registry import RegexPattern, RegexRegistryError, load_regex
from workbench.slug.builder import build_slug
from workbench.slug.validator import validate_slug

MARKDOWN_SUFFIXES = (".md", ".markdown")
SLUG_DISCOVERY_EXCLUDED_DIRS = {"_common", "00-templates", ".obsidian"}
VAULT_REGISTRY_FILENAME = "_vault_registry.json"


class SlugGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SlugAssignment:
    file: Path
    slug: str


@dataclass(frozen=True)
class GenerateSlugsResult:
    discovered: int
    skipped: int
    generated: int
    written: int
    failed: int
    assignments: tuple[SlugAssignment, ...]
    errors: tuple[str, ...]


def _is_within_root(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _load_rg_pattern(name: str) -> RegexPattern:
    try:
        return load_regex(name)
    except RegexRegistryError as exc:
        raise RipgrepError(str(exc)) from exc


def _is_discoverable_slug_file(path: Path) -> bool:
    lowered_name = path.name.lower()
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        return False
    if lowered_name.endswith(".tmpl.md"):
        return False
    if any(part in SLUG_DISCOVERY_EXCLUDED_DIRS for part in path.parts):
        return False
    return True


def _discover_slug_placeholder_files(root: Path) -> list[Path]:
    pattern = _load_rg_pattern("slug_placeholder")
    matches = rg_search(pattern=pattern.pattern, root=root)
    discovered: set[Path] = set()
    for match in matches:
        line_number = match["line"]
        text = match["text"]
        _ = line_number, text
        file_path = match["path"]
        if not _is_discoverable_slug_file(file_path):
            continue
        discovered.add(file_path)
    return sorted(discovered)


def _find_files_with_slug_value(slug: str, *, root: Path) -> list[Path]:
    target_slug = slug.strip()
    pattern = _load_rg_pattern("slug_field")
    matches = rg_search(pattern=pattern.pattern, root=root)
    candidates: set[Path] = set()
    for match in matches:
        line_number = match["line"]
        text = match["text"]
        _ = line_number, text
        file_path = match["path"]
        if file_path.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        candidates.add(file_path)

    results: list[Path] = []
    for file_path in sorted(candidates):
        try:
            doc = Document.read_file(file_path)
        except Exception:  # noqa: BLE001
            continue
        value = doc.metadata.get("slug")
        if isinstance(value, str) and value.strip() == target_slug:
            results.append(file_path)
    return results


def find_vault_root(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser().resolve()
    start = path.parent if path.is_file() else path

    for parent in [start, *start.parents]:
        if (parent / VAULT_REGISTRY_FILENAME).is_file():
            return parent

    raise SlugGenerationError(f"vault root not found for {path}")


def vault_namespace(path_value: str | Path) -> str:
    root = find_vault_root(path_value)
    registry_path = root / VAULT_REGISTRY_FILENAME
    if not registry_path.is_file():
        raise SlugGenerationError(f"vault registry not found under {root}")

    try:
        raw = registry_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SlugGenerationError(
            f"invalid vault registry JSON: {registry_path}"
        ) from exc

    if not isinstance(data, dict):
        raise SlugGenerationError(
            f"vault registry root must be a mapping: {registry_path}"
        )

    mnemonic = data.get("mnemonic")
    if not isinstance(mnemonic, str) or not mnemonic.strip():
        raise SlugGenerationError(f"missing required key 'mnemonic' in {registry_path}")
    return mnemonic.strip()


def _build_slug_for_document(
    *,
    filepath: Path,
    document: Document,
    namespace: str,
) -> str:
    metadata = dict(document.metadata or {})

    file_class = metadata.get("class")
    if not isinstance(file_class, str) or not file_class.strip():
        raise SlugGenerationError(
            f"missing required frontmatter key 'class' in {filepath}"
        )

    context_raw = metadata.get("context")
    context = (
        context_raw if isinstance(context_raw, str) and context_raw.strip() else None
    )

    try:
        return build_slug(
            namespace=namespace,
            class_name=file_class,
            seed=filepath.stem,
            context=context,
        )
    except ValueError as exc:
        raise SlugGenerationError(str(exc)) from exc


def generate_slug_for_file(path: Path) -> str:
    filepath = Path(path).expanduser().resolve()
    doc = Document.read_file(filepath)
    namespace = vault_namespace(filepath)
    return _build_slug_for_document(
        filepath=filepath,
        document=doc,
        namespace=namespace,
    )


def generate_slugs(*, root: Path, write: bool) -> GenerateSlugsResult:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise SlugGenerationError(f"studio root does not exist: {root_path}")

    try:
        candidates = _discover_slug_placeholder_files(root_path)
    except RipgrepError as exc:
        raise SlugGenerationError(str(exc)) from exc

    discovered = len(candidates)
    skipped = 0

    if not candidates:
        return GenerateSlugsResult(
            discovered=discovered,
            skipped=skipped,
            generated=0,
            written=0,
            failed=0,
            assignments=tuple(),
            errors=tuple(),
        )

    namespace_source = root_path
    if not (namespace_source / VAULT_REGISTRY_FILENAME).is_file():
        namespace_source = candidates[0]
    namespace = vault_namespace(namespace_source)

    failed_files: set[Path] = set()
    errors: list[str] = []
    proposed: dict[Path, SlugAssignment] = {}
    documents: dict[Path, Document] = {}
    slug_index: dict[str, Path] = {}
    blocked_slugs: dict[str, Path] = {}

    for file_path in candidates:
        try:
            doc = Document.read_file(file_path)
            slug = _build_slug_for_document(
                filepath=file_path,
                document=doc,
                namespace=namespace,
            )
        except Exception as exc:  # noqa: BLE001
            failed_files.add(file_path)
            errors.append(f"{file_path}: {exc}")
            continue

        if slug in blocked_slugs:
            other = blocked_slugs[slug]
            failed_files.add(file_path)
            failed_files.add(other)
            errors.append(
                f"{file_path}: slug collision detected with {other}: {slug}"
            )
            continue

        if slug in slug_index:
            other = slug_index.pop(slug)
            blocked_slugs[slug] = other
            failed_files.add(file_path)
            failed_files.add(other)
            errors.append(
                f"{file_path}: slug collision detected with {other}: {slug}"
            )
            proposed.pop(other, None)
            documents.pop(other, None)
            continue

        slug_index[slug] = file_path
        documents[file_path] = doc
        proposed[file_path] = SlugAssignment(file=file_path, slug=slug)

    assignments = list(proposed.values())

    written = 0
    if write:
        for assignment in assignments:
            try:
                write_slug_to_document(
                    filepath=assignment.file,
                    document=documents[assignment.file],
                    slug=assignment.slug,
                    require_placeholder=False,
                )
            except Exception as exc:  # noqa: BLE001
                failed_files.add(assignment.file)
                errors.append(f"{assignment.file}: {exc}")
                continue
            written += 1

    return GenerateSlugsResult(
        discovered=discovered,
        skipped=skipped,
        generated=len(assignments),
        written=written,
        failed=len(failed_files),
        assignments=tuple(assignments),
        errors=tuple(errors),
    )


def write_slug_to_document(
    *,
    filepath: Path,
    document: Document,
    slug: str,
    require_placeholder: bool = True,
) -> str:
    path = Path(filepath).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError(f"target file does not exist: {path}")
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise ValueError(f"target file is not markdown: {path}")
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("slug must be a non-empty string")

    validate_slug(slug)

    metadata = dict(document.metadata or {})
    existing = metadata.get("slug")
    if require_placeholder:
        if not isinstance(existing, str) or existing.strip() != "__SLUG__":
            raise ValueError("slug placeholder '__SLUG__' not found")

    metadata["slug"] = slug
    Document(content=document.content, metadata=metadata).write_file(
        path, overwrite=True
    )
    return slug


def write_slug(filepath: Path, slug: str, *, require_placeholder: bool = True) -> str:
    path = Path(filepath).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError(f"target file does not exist: {path}")
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise ValueError(f"target file is not markdown: {path}")
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("slug must be a non-empty string")

    validate_slug(slug)

    doc = Document.read_file(path)
    return write_slug_to_document(
        filepath=path,
        document=doc,
        slug=slug,
        require_placeholder=require_placeholder,
    )


def ensure_slug(
    filepath: Path,
    *,
    namespace: str | None = None,
    slug_owner_index: dict[str, set[Path]] | None = None,
) -> str:
    """
    Ensure a file has a valid slug.

    If slug exists, it is validated and returned unchanged.
    If missing, a deterministic slug is built and written.
    """
    path = Path(filepath).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError(f"target file does not exist: {path}")
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise ValueError(f"target file is not markdown: {path}")

    inspected = Document.inspect_file(path)
    if inspected.error:
        raise ValueError(f"failed to parse markdown: {inspected.error}")
    if not inspected.has_frontmatter:
        raise ValueError("missing frontmatter block")
    doc = Document.read_file(path)

    metadata = dict(doc.metadata or {})

    if "slug" in metadata:
        existing = metadata["slug"]
        if existing is None:
            del metadata["slug"]
        elif isinstance(existing, str):
            existing_text = existing.strip()
            if not existing_text or existing_text.lower() == "__slug__":
                del metadata["slug"]
            else:
                validate_slug(existing)
                if slug_owner_index is not None:
                    slug_owner_index.setdefault(existing_text, set()).add(path)
                return existing
        else:
            raise ValueError("existing slug must be a string")

    class_raw = metadata.get("class")
    if not isinstance(class_raw, str) or not class_raw.strip():
        raise ValueError("missing class in frontmatter")

    context_raw = metadata.get("context")
    context = (
        context_raw if isinstance(context_raw, str) and context_raw.strip() else None
    )

    seed = path.stem
    slug = build_slug(
        namespace=namespace,
        class_name=class_raw,
        seed=seed,
        context=context,
    )

    if slug_owner_index is not None:
        owners = {
            owner
            for owner in slug_owner_index.get(slug, set())
            if _is_within_root(owner, path.parent)
        }
    else:
        try:
            owners = set(_find_files_with_slug_value(slug, root=path.parent))
        except RipgrepError as exc:
            raise ValueError(str(exc)) from exc
    if any(owner != path for owner in owners):
        raise ValueError(f"slug collision detected: {slug}")

    metadata["slug"] = slug
    Document(content=doc.content, metadata=metadata).write_file(path, overwrite=True)
    if slug_owner_index is not None:
        slug_owner_index.setdefault(slug, set()).add(path)
    return slug
