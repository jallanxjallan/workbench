"""
Instruction set loader.

Instruction sets are YAML manifests that group instruction snippets into
named bundles. This loader snapshots those manifests into SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import typer
import yaml

from asc.core.timestamp import timestamp
from asc.store.sql.connect import connect
from asc.core.rg_mapper import SLUG_REGEX
from asc.instructions.slug_registry import resolve_instruction_ulid

from asc.core.contracts import ensure_contracts_shapes

ensure_contracts_shapes()
from autoscribe_shapes.regex import SLUG_VALUE_RE, SLUG_HAS_ALPHA_RE
from autoscribe_shapes.ndjson import (
    FIELD_BATCH,
    FIELD_BATCH_SNIPPETS,
    FIELD_CONTEXT,
    FIELD_CONTEXT_SNIPPETS,
    FIELD_GLOBAL,
    FIELD_GLOBAL_SNIPPETS,
    FIELD_MANIFEST,
    FIELD_MANIFEST_REF,
    FIELD_SLUG,
    FIELD_SNIPPETS,
)

app = typer.Typer(help="Load instruction sets into SQLite")


@dataclass(frozen=True)
class LoadSummary:
    created: int
    updated: int
    skipped: int

    @property
    def total(self) -> int:
        return self.created + self.updated + self.skipped


class InstructionSetLoaderNotImplemented(RuntimeError):
    pass


def _reject_db_path(db: Path | str | None) -> None:
    if db is not None:
        raise ValueError(
            "Explicit db paths are not allowed; "
            "set AUTOSCRIBE_DB_PATH instead."
        )


def _find_set_files(root: Path) -> list[Path]:
    yaml_files = list(root.rglob("*.yaml")) + list(root.rglob("*.yml"))
    return sorted({p.resolve() for p in yaml_files})


def _normalize_snippet_list(
    value: object,
    *,
    label: str,
    path: Path,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeError(f"{label} must be a list in {path}")

    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or item == "":
            raise RuntimeError(f"{label} contains invalid entry in {path}")
        if not SLUG_VALUE_RE.fullmatch(item) or not SLUG_HAS_ALPHA_RE.search(item):
            raise RuntimeError(
                f"{label} contains non-slug entry {item!r} in {path}"
            )
        if item in seen:
            raise RuntimeError(
                f"{label} contains duplicate entry {item!r} in {path}"
            )
        seen.add(item)
        items.append(item)

    return items


def _extract_set_fields(
    path: Path,
    *,
    root: Path,
) -> tuple[str, str, list[str], list[str], list[str]] | None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise RuntimeError(f"Instruction set YAML must be a mapping: {path}")

    # slug is the sole human-authored identifier for markdown instructions.
    slug = data.get(FIELD_SLUG)
    if slug is None:
        return None
    if not isinstance(slug, str) or slug == "":
        raise RuntimeError(f"Invalid slug {slug!r} in {path}")
    if not SLUG_VALUE_RE.fullmatch(slug) or not SLUG_HAS_ALPHA_RE.search(slug):
        raise RuntimeError(f"Invalid slug {slug!r} in {path}")

    manifest_ref = data.get(FIELD_MANIFEST_REF) or data.get(FIELD_MANIFEST)
    if manifest_ref is None:
        try:
            manifest_ref = str(path.relative_to(root))
        except ValueError:
            manifest_ref = str(path)
    if not isinstance(manifest_ref, str) or not manifest_ref.strip():
        raise RuntimeError(f"Missing or invalid manifest_ref in {path}")
    manifest_ref = manifest_ref.strip()

    explicit_keys = {
        FIELD_GLOBAL_SNIPPETS,
        FIELD_CONTEXT_SNIPPETS,
        FIELD_BATCH_SNIPPETS,
        FIELD_GLOBAL,
        FIELD_CONTEXT,
        FIELD_BATCH,
    }

    global_snippets: list[str] = []
    context_snippets: list[str] = []
    batch_snippets: list[str] = []

    if FIELD_SNIPPETS in data:
        if isinstance(data[FIELD_SNIPPETS], list):
            if explicit_keys.intersection(data.keys()):
                raise RuntimeError(
                    f"{path} uses 'snippets' list alongside explicit sections"
                )
            global_snippets = _normalize_snippet_list(
                data[FIELD_SNIPPETS],
                label="snippets",
                path=path,
            )
        elif isinstance(data[FIELD_SNIPPETS], dict):
            if explicit_keys.intersection(data.keys()):
                raise RuntimeError(
                    f"{path} mixes 'snippets' mapping with explicit sections"
                )
            global_snippets = _normalize_snippet_list(
                data[FIELD_SNIPPETS].get(FIELD_GLOBAL),
                label="snippets.global",
                path=path,
            )
            context_snippets = _normalize_snippet_list(
                data[FIELD_SNIPPETS].get(FIELD_CONTEXT),
                label="snippets.context",
                path=path,
            )
            batch_snippets = _normalize_snippet_list(
                data[FIELD_SNIPPETS].get(FIELD_BATCH),
                label="snippets.batch",
                path=path,
            )
        else:
            raise RuntimeError(f"snippets must be a list or mapping in {path}")
    else:
        key_map = {
            FIELD_GLOBAL: [FIELD_GLOBAL_SNIPPETS],
            FIELD_CONTEXT: [FIELD_CONTEXT_SNIPPETS],
            FIELD_BATCH: [FIELD_BATCH_SNIPPETS],
        }
        for name, keys in key_map.items():
            present = [k for k in keys + [name] if k in data]
            if len(present) > 1:
                raise RuntimeError(
                    f"{path} defines multiple keys for {name}: {present}"
                )
            if not present:
                continue
            items = _normalize_snippet_list(
                data[present[0]],
                label=present[0],
                path=path,
            )
            if name == FIELD_GLOBAL:
                global_snippets = items
            elif name == FIELD_CONTEXT:
                context_snippets = items
            else:
                batch_snippets = items

    if not (global_snippets or context_snippets or batch_snippets):
        raise RuntimeError(f"No snippets defined in {path}")

    return (
        slug,
        manifest_ref,
        global_snippets,
        context_snippets,
        batch_snippets,
    )


def _encode_snippets(items: list[str]) -> str | None:
    if not items:
        return None
    return json.dumps(items, separators=(",", ":"))


def _load_instruction_sets(root: Path, *, report: bool = True) -> LoadSummary:
    root = root.resolve()

    if not root.is_dir():
        typer.secho("Root path is not a directory", fg=typer.colors.RED)
        raise typer.Exit(1)

    files = _find_set_files(root)
    if not files:
        typer.secho("No instruction set YAML files found", fg=typer.colors.RED)
        raise typer.Exit(1)

    seen_slugs: dict[str, Path] = {}
    rows: list[tuple[str, str, list[str], list[str], list[str]]] = []

    for path in files:
        try:
            fields = _extract_set_fields(path, root=root)
        except Exception as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(1)

        if fields is None:
            continue

        slug = fields[0]
        if slug in seen_slugs:
            typer.secho(
                f"Duplicate instruction set slug {slug!r} in {path} "
                f"(already seen in {seen_slugs[slug]})",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        seen_slugs[slug] = path
        rows.append(fields)

    conn = connect()
    try:
        cur = conn.cursor()
        created = updated = skipped = 0

        for (
            slug,
            manifest_ref,
            global_snippets,
            context_snippets,
            batch_snippets,
        ) in rows:
            cur.execute(
                "SELECT set_ulid FROM instruction_sets WHERE slug = ?",
                (slug,),
            )
            row_by_slug = cur.fetchone()
            existing_ulid = row_by_slug["set_ulid"] if row_by_slug else None

            set_ulid = resolve_instruction_ulid(
                slug,
                existing_ulid=existing_ulid,
            )

            global_ulids = [resolve_instruction_ulid(s) for s in global_snippets]
            context_ulids = [resolve_instruction_ulid(s) for s in context_snippets]
            batch_ulids = [resolve_instruction_ulid(s) for s in batch_snippets]

            global_blob = _encode_snippets(global_ulids)
            context_blob = _encode_snippets(context_ulids)
            batch_blob = _encode_snippets(batch_ulids)

            cur.execute(
                """
                SELECT slug, manifest_ref, global_snippets, context_snippets, batch_snippets
                FROM instruction_sets
                WHERE set_ulid = ?
                """,
                (set_ulid,),
            )
            row = cur.fetchone()

            if row is None:
                cur.execute(
                    """
                    INSERT INTO instruction_sets
                    (set_ulid, slug, manifest_ref, global_snippets, context_snippets, batch_snippets, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        set_ulid,
                        slug,
                        manifest_ref,
                        global_blob,
                        context_blob,
                        batch_blob,
                        int(timestamp()),
                    ),
                )
                created += 1
                continue

            changed = (
                row["slug"] != slug
                or row["manifest_ref"] != manifest_ref
                or row["global_snippets"] != global_blob
                or row["context_snippets"] != context_blob
                or row["batch_snippets"] != batch_blob
            )

            if changed:
                cur.execute(
                    """
                    UPDATE instruction_sets
                    SET slug = ?, manifest_ref = ?, global_snippets = ?, context_snippets = ?, batch_snippets = ?
                    WHERE set_ulid = ?
                    """,
                    (
                        slug,
                        manifest_ref,
                        global_blob,
                        context_blob,
                        batch_blob,
                        set_ulid,
                    ),
                )
                updated += 1
            else:
                skipped += 1

        conn.commit()
    finally:
        conn.close()

    summary = LoadSummary(created=created, updated=updated, skipped=skipped)
    if report:
        typer.secho(
            f"{created} created, {updated} updated, {skipped} unchanged",
            fg=typer.colors.GREEN,
        )

    return summary


@app.command("sets")
def load_sets_command(
    root: Path = typer.Argument(
        Path.cwd(),
        help="Root directory of instruction sets",
    ),
) -> None:
    """
    Load instruction sets into SQLite.
    """
    _load_instruction_sets(root=root)


def load_sets(
    db: Path | str | None = None,
    root: Path | str | None = None,
    report: bool = True,
    return_summary: bool = False,
) -> LoadSummary | None:
    _reject_db_path(db)
    if root is None:
        raise ValueError("root is required")
    summary = _load_instruction_sets(root=Path(root), report=report)
    if return_summary:
        return summary
    return None


def load_instruction_sets(
    db: Path | str | None = None,
    root: Path | str | None = None,
    report: bool = True,
    return_summary: bool = False,
) -> LoadSummary | None:
    """
    Backwards-compatible alias for load_sets.
    """
    return load_sets(
        db=db,
        root=root,
        report=report,
        return_summary=return_summary,
    )


__all__ = [
    "load_sets_command",
    "load_sets",
    "load_instruction_sets",
    "InstructionSetLoaderNotImplemented",
    "LoadSummary",
]
