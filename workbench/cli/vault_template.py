"""Vault template command surface (`wkb vault template ...`)."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from workbench.interop.document import Document
from workbench.write.common import atomic_write_text

MARKDOWN_SUFFIXES = (".md", ".markdown")


class VaultTemplateError(RuntimeError):
    pass


@dataclass(frozen=True)
class TemplateApplyResult:
    template_path: Path
    vault_root: Path
    processed_files: int
    updated_files: int


@dataclass(frozen=True)
class PlannedChange:
    path: Path
    original_text: str
    updated_text: str


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vault template",
        description="Vault template operations.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    apply_parser = subparsers.add_parser(
        "apply",
        help="Apply one template to multiple markdown files.",
    )
    apply_parser.add_argument(
        "--template",
        required=True,
        help="Template name/path under <vault>/_control/templates.",
    )
    apply_parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="Target markdown files.",
    )

    return parser


def _resolve_existing_markdown_path(raw_path: str) -> Path:
    expanded = Path(str(raw_path)).expanduser()
    resolved = expanded.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise VaultTemplateError(f"ERROR: Target file does not exist: {resolved}")
    if resolved.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise VaultTemplateError(f"ERROR: Target file is not markdown: {resolved}")
    return resolved


def _resolve_target_files(raw_paths: list[str]) -> list[Path]:
    if not raw_paths:
        raise VaultTemplateError("ERROR: At least one target file is required.")

    resolved: list[Path] = []
    seen: set[Path] = set()
    for raw_path in raw_paths:
        path = _resolve_existing_markdown_path(raw_path)
        if path in seen:
            continue
        seen.add(path)
        resolved.append(path)

    if not resolved:
        raise VaultTemplateError("ERROR: No valid target files were provided.")
    return resolved


def _find_vault_root_for_file(path: Path) -> Path:
    for parent in [path.parent, *path.parents]:
        obsidian_dir = parent / ".obsidian"
        control_templates_dir = parent / "_control" / "templates"
        if obsidian_dir.is_dir() and control_templates_dir.is_dir():
            return parent.resolve()
    raise VaultTemplateError(
        f"ERROR: Could not resolve vault root from file path: {path}"
    )


def _resolve_templates_root(vault_root: Path) -> Path:
    templates_root = (vault_root / "_control" / "templates").resolve()
    if templates_root.exists() and templates_root.is_dir():
        return templates_root
    raise VaultTemplateError(f"ERROR: Template directory is missing: {templates_root}")


def _ensure_staging_dir(vault_root: Path) -> Path:
    staging_root = (vault_root / "_staging").resolve()
    if staging_root.exists():
        if not staging_root.is_dir():
            raise VaultTemplateError(f"ERROR: _staging path is not a directory: {staging_root}")
        return staging_root

    staging_root.mkdir(parents=True, exist_ok=False)
    return staging_root


def _resolve_template_path(template_name: str, vault_root: Path) -> Path:
    raw = template_name.strip()
    if not raw:
        raise VaultTemplateError("ERROR: Template name must be non-empty.")

    templates_root = _resolve_templates_root(vault_root)

    if raw.startswith("_control/templates/"):
        raw = raw[len("_control/templates/") :]

    selected: Path | None = None
    raw_path = Path(raw)
    if raw_path.is_absolute():
        candidate = raw_path.expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            selected = candidate
    else:
        candidates = [templates_root / raw_path]
        if raw_path.suffix == "":
            candidates.append(templates_root / f"{raw}.md")

        for candidate in candidates:
            candidate_resolved = candidate.resolve()
            if candidate_resolved.exists() and candidate_resolved.is_file():
                selected = candidate_resolved
                break

    if selected is None:
        raise VaultTemplateError(
            f"ERROR: Template not found in {templates_root}: {template_name}"
        )

    try:
        selected.relative_to(templates_root)
    except ValueError as exc:
        raise VaultTemplateError(
            f"ERROR: Template must resolve under {templates_root}: {selected}"
        ) from exc

    if selected.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise VaultTemplateError(f"ERROR: Template is not markdown: {selected}")

    return selected


def _load_template(path: Path) -> tuple[dict[str, object], str]:
    inspected = Document.inspect_file(path)
    if inspected.error:
        raise VaultTemplateError(
            f"ERROR: Template parse failed ({path}): {inspected.error}"
        )
    if not inspected.has_frontmatter:
        raise VaultTemplateError(
            f"ERROR: Template is missing frontmatter block: {path}"
        )
    doc = Document.read_file(path)
    return dict(doc.metadata or {}), doc.content


def _render_markdown(frontmatter: dict[str, object], body: str) -> str:
    doc = Document(content=body, metadata=frontmatter)
    return doc.write_text()


def _merge_frontmatter(
    *,
    current: dict[str, object],
    template: dict[str, object],
    target_path: Path,
) -> dict[str, object]:
    merged = dict(current)

    # Special case: preserve an existing slug under legacy_slug, then allow
    # template slug to merge in.
    if (
        "slug" in merged
        and "slug" in template
        and merged["slug"] != template["slug"]
    ):
        existing_slug = merged["slug"]
        if "legacy_slug" in merged and merged["legacy_slug"] != existing_slug:
            raise VaultTemplateError(
                f"ERROR: Frontmatter conflict for key 'legacy_slug' in file: {target_path}"
            )
        merged["legacy_slug"] = existing_slug
        del merged["slug"]

    for key, value in template.items():
        if key not in merged:
            merged[key] = value
    return merged


def _build_change_plan(template_path: Path, targets: list[Path]) -> list[PlannedChange]:
    template_frontmatter, template_body = _load_template(template_path)
    planned: list[PlannedChange] = []

    for target in targets:
        original = target.read_text(encoding="utf-8")
        try:
            current_doc = Document.read_file(target)
        except ValueError as exc:
            raise VaultTemplateError(f"ERROR: File parse failed ({target}): {exc}") from exc

        current_frontmatter = dict(current_doc.metadata or {})
        merged_frontmatter = _merge_frontmatter(
            current=current_frontmatter,
            template=template_frontmatter,
            target_path=target,
        )

        current_body = current_doc.content
        final_body = current_body if current_body.strip() else template_body
        updated = _render_markdown(merged_frontmatter, final_body)
        if updated == original:
            continue

        planned.append(
            PlannedChange(path=target, original_text=original, updated_text=updated)
        )

    return planned


def _apply_changes_atomically(changes: list[PlannedChange]) -> None:
    if not changes:
        return

    staged: dict[Path, Path] = {}
    applied: list[PlannedChange] = []
    try:
        for change in changes:
            fd, tmp_raw = tempfile.mkstemp(
                prefix=f".{change.path.name}.wkb.", dir=str(change.path.parent)
            )
            tmp_path = Path(tmp_raw)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(change.updated_text)
            staged[change.path] = tmp_path

        for change in changes:
            tmp_path = staged[change.path]
            os.replace(tmp_path, change.path)
            applied.append(change)
    except Exception as exc:
        for tmp_path in staged.values():
            tmp_path.unlink(missing_ok=True)

        rollback_errors: list[str] = []
        for change in reversed(applied):
            try:
                atomic_write_text(change.path, change.original_text)
            except Exception as rollback_exc:  # noqa: BLE001
                rollback_errors.append(f"{change.path}: {rollback_exc}")

        if rollback_errors:
            raise VaultTemplateError(
                "ERROR: Failed during apply; rollback encountered errors: "
                + "; ".join(rollback_errors)
            ) from exc

        raise VaultTemplateError(
            f"ERROR: Failed while applying template changes: {exc}"
        ) from exc


def apply_template_to_files(
    *,
    template_name: str,
    filepaths: list[str],
) -> TemplateApplyResult:
    targets = _resolve_target_files(filepaths)
    vault_roots = {_find_vault_root_for_file(path) for path in targets}
    if len(vault_roots) != 1:
        roots = ", ".join(str(path) for path in sorted(vault_roots))
        raise VaultTemplateError(
            f"ERROR: Target files span multiple vault roots: {roots}"
        )

    vault_root = next(iter(vault_roots))
    _ensure_staging_dir(vault_root)
    template_path = _resolve_template_path(template_name, vault_root)
    changes = _build_change_plan(template_path, targets)
    _apply_changes_atomically(changes)

    return TemplateApplyResult(
        template_path=template_path,
        vault_root=vault_root,
        processed_files=len(targets),
        updated_files=len(changes),
    )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.action != "apply":
        print(f"ERROR: Unsupported action: {args.action}", file=sys.stderr)
        return 2

    try:
        result = apply_template_to_files(
            template_name=str(args.template),
            filepaths=[str(path) for path in args.files],
        )
    except VaultTemplateError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("vault template apply: completed")
    print(f"Template: {result.template_path}")
    print(f"Vault: {result.vault_root}")
    print(f"Files processed: {result.processed_files}")
    print(f"Files updated: {result.updated_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
