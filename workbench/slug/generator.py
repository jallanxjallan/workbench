"""Studio-wide slug generation logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workbench.cli.create_vault import load_registry
from workbench.interop.document import Document
from workbench.lib.rg import RipgrepError, find_files_with_slug, find_slug_sentinels
from workbench.slug.normalize import normalize_segment
from workbench.slug.writer import write_slug


class SlugGenerationError(RuntimeError):
    pass


class SlugSkipError(SlugGenerationError):
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


def _is_template_file(path: Path) -> bool:
    return "00-templates" in path.parts


def generate_slug_for_file(path: Path) -> str:
    filepath = Path(path).expanduser().resolve()
    doc = Document.read_file(filepath)
    metadata = dict(doc.metadata or {})

    file_class = metadata.get("class")
    if not isinstance(file_class, str) or not file_class.strip():
        if _is_template_file(filepath):
            raise SlugSkipError("template file has no class; skipping")
        raise SlugGenerationError(
            f"missing required frontmatter key 'class' in {filepath}"
        )

    vault_root = find_vault_root(filepath)
    vault_mnemonic = load_vault_mnemonic(vault_root)
    class_segment = normalize_segment(file_class)
    stem_segment = normalize_segment(filepath.stem)
    return f"{vault_mnemonic}.{class_segment}.{stem_segment}"


def _collision_owners(*, root: Path, slug: str, current_file: Path) -> list[Path]:
    owners = find_files_with_slug(slug, root=root)
    current = current_file.resolve()
    return sorted(path for path in owners if path.resolve() != current)


def generate_slugs(*, root: Path, write: bool) -> GenerateSlugsResult:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise SlugGenerationError(f"studio root does not exist: {root_path}")

    try:
        candidates = sorted(find_slug_sentinels(root_path))
    except RipgrepError as exc:
        raise SlugGenerationError(str(exc)) from exc

    discovered = len(candidates)
    skipped = 0
    failed_files: set[Path] = set()
    errors: list[str] = []
    proposed: list[SlugAssignment] = []

    for file_path in candidates:
        try:
            slug = generate_slug_for_file(file_path)
        except SlugSkipError:
            skipped += 1
            continue
        except Exception as exc:  # noqa: BLE001
            failed_files.add(file_path)
            errors.append(f"{file_path}: {exc}")
            continue
        proposed.append(SlugAssignment(file=file_path, slug=slug))

    slug_index: dict[str, list[Path]] = {}
    for assignment in proposed:
        slug_index.setdefault(assignment.slug, []).append(assignment.file)

    duplicate_files: set[Path] = set()
    for slug, files in slug_index.items():
        if len(files) < 2:
            continue
        for file_path in sorted(files):
            duplicate_files.add(file_path)
            failed_files.add(file_path)
            errors.append(f"{file_path}: slug collision detected: {slug}")

    assignments: list[SlugAssignment] = []
    for assignment in proposed:
        if assignment.file in duplicate_files:
            continue
        try:
            conflicts = _collision_owners(
                root=root_path,
                slug=assignment.slug,
                current_file=assignment.file,
            )
        except RipgrepError as exc:
            failed_files.add(assignment.file)
            errors.append(f"{assignment.file}: {exc}")
            continue

        if conflicts:
            failed_files.add(assignment.file)
            errors.append(f"{assignment.file}: slug collision detected: {assignment.slug}")
            continue

        assignments.append(assignment)

    written = 0
    if write:
        for assignment in assignments:
            try:
                write_slug(assignment.file, assignment.slug)
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
