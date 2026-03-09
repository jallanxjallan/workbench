"""Slug ensure/write operations for markdown files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workbench.cli.create_vault import load_registry
from workbench.interop.document import Document
from workbench.lib.rg import (
    RipgrepError,
    find_files_with_slug,
    find_slug_discovery_rows,
)
from workbench.slug.builder import build_slug
from workbench.slug.normalize import normalize_segment
from workbench.slug.validator import validate_slug

MARKDOWN_SUFFIXES = (".md", ".markdown")


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


def find_vault_root(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser().resolve()
    start = path.parent if path.is_file() else path

    for parent in [start, *start.parents]:
        if (parent / "_vault_registry").is_file():
            return parent
        if (parent / "_vault_registry.yaml").is_file():
            return parent
        if (parent / "_vault_registry.json").is_file():
            return parent

    raise SlugGenerationError(f"vault root not found for {path}")


def _resolve_registry_path(vault_root: Path) -> Path:
    ndjson_path = vault_root / "_vault_registry"
    if ndjson_path.is_file():
        return ndjson_path

    yaml_path = vault_root / "_vault_registry.yaml"
    if yaml_path.is_file():
        return yaml_path

    json_path = vault_root / "_vault_registry.json"
    if json_path.is_file():
        return json_path

    raise SlugGenerationError(f"vault registry not found under {vault_root}")


def load_vault_mnemonic(vault_root: Path) -> str:
    registry_path = _resolve_registry_path(vault_root)
    data = load_registry(registry_path)

    raw = data.get("mnemonic")
    if not isinstance(raw, str) or not raw.strip():
        raw = data.get("vault")

    if isinstance(raw, str) and raw.strip():
        return normalize_segment(raw)

    # Backward compatibility for vault registries created without mnemonic/vault key.
    return normalize_segment(vault_root.name)


def _is_placeholder_slug(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() == "__slug__"


def _build_existing_slug_owners(rows: list[dict[str, object]]) -> dict[str, set[Path]]:
    owners: dict[str, set[Path]] = {}
    for row in rows:
        slug_value = row.get("slug")
        file_value = row.get("file")
        if not isinstance(slug_value, str):
            continue
        if not isinstance(file_value, Path):
            continue
        if _is_placeholder_slug(slug_value):
            continue
        owners.setdefault(slug_value.strip(), set()).add(file_value.resolve())
    return owners


def _collect_sentinel_candidates(rows: list[dict[str, object]]) -> list[Path]:
    candidates: set[Path] = set()
    for row in rows:
        slug_value = row.get("slug")
        file_value = row.get("file")
        if not isinstance(slug_value, str):
            continue
        if not isinstance(file_value, Path):
            continue
        if _is_placeholder_slug(slug_value):
            candidates.add(file_value.resolve())
    return sorted(candidates)


def _build_slug_for_document(*, filepath: Path, document: Document) -> str:
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

    vault_root = find_vault_root(filepath)
    vault_mnemonic = load_vault_mnemonic(vault_root)
    try:
        return build_slug(
            namespace=vault_mnemonic,
            class_name=file_class,
            seed=filepath.stem,
            context=context,
        )
    except ValueError as exc:
        raise SlugGenerationError(str(exc)) from exc


def generate_slug_for_file(path: Path) -> str:
    filepath = Path(path).expanduser().resolve()
    doc = Document.read_file(filepath)
    return _build_slug_for_document(filepath=filepath, document=doc)


def generate_slugs(*, root: Path, write: bool) -> GenerateSlugsResult:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise SlugGenerationError(f"studio root does not exist: {root_path}")

    try:
        rows = find_slug_discovery_rows(root=root_path)
    except RipgrepError as exc:
        raise SlugGenerationError(str(exc)) from exc

    existing_slug_owners = _build_existing_slug_owners(rows)
    candidates = _collect_sentinel_candidates(rows)

    discovered = len(candidates)
    skipped = 0
    failed_files: set[Path] = set()
    errors: list[str] = []
    proposed: list[SlugAssignment] = []
    documents: dict[Path, Document] = {}

    for file_path in candidates:
        try:
            doc = Document.read_file(file_path)
            slug = _build_slug_for_document(filepath=file_path, document=doc)
        except Exception as exc:  # noqa: BLE001
            failed_files.add(file_path)
            errors.append(f"{file_path}: {exc}")
            continue
        documents[file_path] = doc
        proposed.append(SlugAssignment(file=file_path, slug=slug))

    all_owners: dict[str, set[Path]] = {
        slug: set(owners) for slug, owners in existing_slug_owners.items()
    }
    for assignment in proposed:
        all_owners.setdefault(assignment.slug, set()).add(assignment.file.resolve())

    assignments: list[SlugAssignment] = []
    for assignment in proposed:
        owners = {
            owner
            for owner in all_owners.get(assignment.slug, set())
            if owner.resolve() != assignment.file.resolve()
        }
        if owners:
            failed_files.add(assignment.file)
            errors.append(
                f"{assignment.file}: slug collision detected: {assignment.slug}"
            )
            continue
        assignments.append(assignment)

    written = 0
    if write:
        for assignment in assignments:
            try:
                write_slug_to_document(
                    filepath=assignment.file,
                    document=documents[assignment.file],
                    slug=assignment.slug,
                    require_placeholder=True,
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
            raise ValueError("slug sentinel '__SLUG__' not found")

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
            owners = set(find_files_with_slug(slug, root=path.parent))
        except RipgrepError as exc:
            raise ValueError(str(exc)) from exc
    if any(owner != path for owner in owners):
        raise ValueError(f"slug collision detected: {slug}")

    metadata["slug"] = slug
    Document(content=doc.content, metadata=metadata).write_file(path, overwrite=True)
    if slug_owner_index is not None:
        slug_owner_index.setdefault(slug, set()).add(path)
    return slug
